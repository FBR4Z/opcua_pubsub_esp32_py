#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_err.h"
#include "esp_log.h"
#include "driver/uart.h"
#include "mbcontroller.h"

#include "modbus_params.h"
#include "servo_driver.h"
#include "conveyor_driver.h"
#include "hc_sr04_driver.h"
#include "lcd_driver.h"
#include "hmi_buttons.h"
#include "console_cmds.h"

static const char *TAG = "ot_modbus_server";

// Versão exibida no log de boot — atualizar a cada gravação na bancada.
#define FW_VERSION  "2026-09-26 (gravado via Iris)"

// ============================================================
// CONFIGURAÇÃO
// ============================================================
// Na API v2.x do espressif/esp-modbus, a pinagem NÃO é Kconfig — é setada
// via uart_set_pin() no código, chamada DEPOIS de mbc_slave_create_serial()
// (que instala o driver UART internamente com pinos padrão do chip) e
// ANTES de mbc_slave_start().
#define MB_PORT_NUM      2   // UART2
#define MB_SLAVE_ADDR    1
#define MB_BAUD_RATE     115200

#define MB_UART_TX_GPIO  17   // GPIO17 -> J7 pino 1 (vai pro RX do IT)
#define MB_UART_RX_GPIO  16   // GPIO16 <- J7 pino 2 (vem do TX do IT)

// Intervalo de atualização do banco de registradores pela task de controle
#define CONTROL_TASK_PERIOD_MS  20

// ============================================================
// BANCO DE REGISTRADORES
// ============================================================
static uint16_t holding_reg_area[HOLD_REG_COUNT];

// Mutex simples entre a task de controle (única escritora) e leituras
// pontuais de debug. O mbcontroller acessa holding_reg_area diretamente
// (é assim que a API de descriptor funciona) — como só a control_task
// escreve, e cada campo é um uint16_t alinhado (escrita atômica no ESP32),
// isso é seguro na prática. Se no futuro mais de uma task escrever,
// reavaliar e serializar via evento MB_EVENT_HOLDING_REG_WR.
static SemaphoreHandle_t reg_mutex;

// Handle de contexto do slave — obrigatório em toda chamada da API v2.x
static void *slave_handle = NULL;

// Última leitura do HC-SR04, atualizada pela sensor_task (baixa frequência,
// pois a medição é bloqueante ~30ms no timeout). -1 = sem leitura ainda/erro.
// Leitura/escrita de int em ESP32 é atômica o suficiente pra esse uso
// (single writer, single reader ocasional) — mesma lógica já aplicada aos
// ângulos dos servos.
static volatile int s_last_dist_cm = -1;

static void setup_reg_area(void)
{
    mb_register_area_descriptor_t reg_area = {
        .type = MB_PARAM_HOLDING,
        .start_offset = 0,
        .address = (void *)holding_reg_area,
        .size = sizeof(holding_reg_area),
    };
    ESP_ERROR_CHECK(mbc_slave_set_descriptor(slave_handle, reg_area));
}

// ============================================================
// TASK DE CONTROLE — servos, esteira, sensor
// ============================================================
// Servos, esteira e sensor já refletem valores reais. PENDENTE: aplicar os
// limites ang_min/ang_max reais de cada eixo (calibração ainda não fechada
// na bancada — ver ESTADO_BANCADA_calibracao.md §6); por enquanto o driver
// de servo aceita 0-180 cheio.
static void control_task(void *pv)
{
    while (1) {
        xSemaphoreTake(reg_mutex, portMAX_DELAY);

        uint16_t ang;

        holding_reg_area[HOLD_REG_BASE_ANG]      = servo_get_angle(SERVO_BASE, &ang)     ? ang : 90;
        holding_reg_area[HOLD_REG_OMBRO_ANG]     = servo_get_angle(SERVO_OMBRO, &ang)    ? ang : 90;
        holding_reg_area[HOLD_REG_COTOVELO_ANG]  = servo_get_angle(SERVO_COTOVELO, &ang) ? ang : 90;
        holding_reg_area[HOLD_REG_GARRA_ANG]     = servo_get_angle(SERVO_GARRA, &ang)    ? ang : 90;
        holding_reg_area[HOLD_REG_ESTEIRA_VEL]   = conveyor_get_speed();
        holding_reg_area[HOLD_REG_ESTEIRA_STATE] = conveyor_is_running() ? 1 : 0;
        // 0xFFFF = "sem leitura" (sensor nunca leu ou deu timeout) — distingue
        // de uma leitura real de 0cm (objeto colado no sensor).
        holding_reg_area[HOLD_REG_SENSOR_DIST]   = (s_last_dist_cm < 0) ? 0xFFFF : (uint16_t)s_last_dist_cm;

        xSemaphoreGive(reg_mutex);

        vTaskDelay(pdMS_TO_TICKS(CONTROL_TASK_PERIOD_MS));
    }
}

// ============================================================
// TASK DO SENSOR — HC-SR04 é bloqueante (~30ms no timeout), então roda
// separada da control_task (que precisa ficar responsiva a 20ms).
// ============================================================
#define SENSOR_TASK_PERIOD_MS  200

static void sensor_task(void *pv)
{
    while (1) {
        int dist = hc_sr04_measure_cm();
        s_last_dist_cm = dist;  // escrita única, leitura ocasional — sem mutex
        vTaskDelay(pdMS_TO_TICKS(SENSOR_TASK_PERIOD_MS));
    }
}

// ============================================================
// TASK DO MODBUS SERVER — apenas escuta eventos, o mbcontroller
// já responde às requisições internamente numa task própria.
// Isso aqui é só para log/observabilidade.
// ============================================================
static void modbus_event_task(void *pv)
{
    while (1) {
        mb_event_group_t event = mbc_slave_check_event(
            slave_handle, MB_EVENT_HOLDING_REG_RD | MB_EVENT_HOLDING_REG_WR);

        if (event & MB_EVENT_HOLDING_REG_RD) {
            ESP_LOGD(TAG, "Client leu holding registers");
        }
        if (event & MB_EVENT_HOLDING_REG_WR) {
            ESP_LOGD(TAG, "Client escreveu holding registers");
        }
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "Firmware %s", FW_VERSION);

    reg_mutex = xSemaphoreCreateMutex();

    servo_driver_init();
    conveyor_driver_init();
    hc_sr04_driver_init();
    lcd_driver_init();
    hmi_buttons_start();
    console_cmds_start();

    mb_communication_info_t comm = {
        .ser_opts.port = MB_PORT_NUM,
        .ser_opts.mode = MB_RTU,
        .ser_opts.baudrate = MB_BAUD_RATE,
        .ser_opts.parity = MB_PARITY_NONE,
        .ser_opts.uid = MB_SLAVE_ADDR,
        .ser_opts.data_bits = UART_DATA_8_BITS,
        .ser_opts.stop_bits = UART_STOP_BITS_1,
    };
    ESP_ERROR_CHECK(mbc_slave_create_serial(&comm, &slave_handle));

    // Remapear os pinos físicos da UART2 — a criação acima já instalou o
    // driver UART internamente com pinos padrão do chip; agora sobrescrevemos
    // com os pinos reais do carrier board OT (J7).
    ESP_ERROR_CHECK(uart_set_pin(MB_PORT_NUM, MB_UART_TX_GPIO, MB_UART_RX_GPIO,
                                  UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
    // NÃO chamamos uart_set_mode(UART_MODE_RS485_HALF_DUPLEX) — nosso link é
    // UART TTL ponto-a-ponto full-duplex, não RS485. Deixar assim é intencional.

    setup_reg_area();

    ESP_ERROR_CHECK(mbc_slave_start(slave_handle));
    ESP_LOGI(TAG, "Modbus RTU Server ativo (slave addr=%d, %d baud, TX=%d RX=%d)",
             MB_SLAVE_ADDR, MB_BAUD_RATE, MB_UART_TX_GPIO, MB_UART_RX_GPIO);

    xTaskCreate(control_task, "control_task", 4096, NULL, 5, NULL);
    xTaskCreate(sensor_task, "sensor_task", 4096, NULL, 4, NULL);
    xTaskCreate(modbus_event_task, "mb_event_task", 4096, NULL, 4, NULL);
}