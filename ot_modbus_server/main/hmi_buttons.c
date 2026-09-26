#include "hmi_buttons.h"

#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_log.h"

#include "servo_driver.h"
#include "conveyor_driver.h"
#include "lcd_driver.h"

static const char *TAG = "hmi_buttons";

// ============================================================
// Pinagem — J14 do carrier board OT (input-only, pull-up EXTERNO 10K
// já na placa — 3V3, nunca 5V. Não usar pull-up interno, GPIO34/35/36
// nem têm essa opção em hardware.)
// ============================================================
#define BTN_CYCLE_GPIO   34   // cicla eixo: base->ombro->cotovelo->garra->esteira->base...
#define BTN_INC_GPIO     35   // A: +1 grau (servo) ou +5% (esteira)
#define BTN_DEC_GPIO     36   // B: -1 grau (servo) ou -5% (esteira)

#define HMI_POLL_MS         10
#define DEBOUNCE_THRESHOLD  3   // 3 * HMI_POLL_MS = 30ms estável antes de disparar

#define SERVO_STEP_DEG   1
#define ESTEIRA_STEP_PCT 5

// ============================================================
// Eixos ciclados pela HMI — os 4 primeiros mapeiam direto pro enum
// servo_axis_t (mesma ordem); o 5º é a esteira, tratada à parte.
// ============================================================
typedef enum {
    HMI_AXIS_BASE = 0,
    HMI_AXIS_OMBRO,
    HMI_AXIS_COTOVELO,
    HMI_AXIS_GARRA,
    HMI_AXIS_ESTEIRA,
    HMI_AXIS_COUNT
} hmi_axis_t;

static hmi_axis_t s_axis_ativo = HMI_AXIS_BASE;

static const char *hmi_axis_name(hmi_axis_t axis)
{
    switch (axis) {
        case HMI_AXIS_BASE:     return "Base";
        case HMI_AXIS_OMBRO:    return "Ombro";
        case HMI_AXIS_COTOVELO: return "Cotovelo";
        case HMI_AXIS_GARRA:    return "Garra";
        case HMI_AXIS_ESTEIRA:  return "Esteira";
        default:                return "?";
    }
}

// Válido apenas para HMI_AXIS_BASE..GARRA — depende da ordem do enum
// bater com servo_axis_t (SERVO_BASE=0...SERVO_GARRA=3). Se um dia
// reordenar um dos dois enums, atualizar aqui também.
static servo_axis_t hmi_axis_to_servo(hmi_axis_t axis)
{
    return (servo_axis_t)axis;
}

// ============================================================
// Debounce simples por contador
// ============================================================
typedef struct {
    gpio_num_t gpio;
    int counter;
    bool fired;
} debounced_btn_t;

static debounced_btn_t s_btn_cycle = { .gpio = BTN_CYCLE_GPIO };
static debounced_btn_t s_btn_inc   = { .gpio = BTN_INC_GPIO };
static debounced_btn_t s_btn_dec   = { .gpio = BTN_DEC_GPIO };

// Retorna true UMA VEZ por pressionamento (borda), não repete enquanto
// o botão fica segurado.
static bool button_check_pressed(debounced_btn_t *b)
{
    bool raw_pressed = (gpio_get_level(b->gpio) == 0);  // ativo baixo

    if (raw_pressed) {
        if (b->counter < DEBOUNCE_THRESHOLD) {
            b->counter++;
        }
    } else {
        b->counter = 0;
        b->fired = false;
    }

    if (b->counter >= DEBOUNCE_THRESHOLD && !b->fired) {
        b->fired = true;
        return true;
    }
    return false;
}

// ============================================================
// LCD — linha 1 = eixo ativo, linha 2 = valor atual
// ============================================================
static void hmi_update_lcd(void)
{
    char line1[17];
    char line2_raw[17];
    char line2[17];

    snprintf(line1, sizeof(line1), "Eixo: %-10s", hmi_axis_name(s_axis_ativo));

    if (s_axis_ativo == HMI_AXIS_ESTEIRA) {
        snprintf(line2_raw, sizeof(line2_raw), "%s %u%%",
                 conveyor_is_running() ? "ON" : "OFF", conveyor_get_speed());
    } else {
        uint16_t ang;
        servo_axis_t eixo = hmi_axis_to_servo(s_axis_ativo);
        if (servo_get_angle(eixo, &ang)) {
            snprintf(line2_raw, sizeof(line2_raw), "%u graus", ang);
        } else {
            snprintf(line2_raw, sizeof(line2_raw), "solto");
        }
    }
    snprintf(line2, sizeof(line2), "%-16s", line2_raw);

    lcd_set_cursor(0, 0);
    lcd_print(line1);
    lcd_set_cursor(1, 0);
    lcd_print(line2);
}

// ============================================================
// Task principal da HMI
// ============================================================
static void hmi_task(void *pv)
{
    ESP_LOGI(TAG, "hmi_task iniciada — atualizando LCD pela primeira vez");
    hmi_update_lcd();  // mostra o estado inicial
    ESP_LOGI(TAG, "Primeira atualizacao do LCD concluida, entrando no loop");

    while (1) {
        bool changed = false;

        if (button_check_pressed(&s_btn_cycle)) {
            ESP_LOGI(TAG, "botao CYCLE pressionado");
            s_axis_ativo = (hmi_axis_t)((s_axis_ativo + 1) % HMI_AXIS_COUNT);
            changed = true;
        }

        if (button_check_pressed(&s_btn_inc)) {
            ESP_LOGI(TAG, "botao INC pressionado");
            if (s_axis_ativo == HMI_AXIS_ESTEIRA) {
                int nova_vel = (int)conveyor_get_speed() + ESTEIRA_STEP_PCT;
                if (nova_vel > 100) {
                    nova_vel = 100;
                }
                conveyor_set(1, (uint8_t)nova_vel);
            } else {
                servo_axis_t eixo = hmi_axis_to_servo(s_axis_ativo);
                uint16_t ang;
                int atual = servo_get_angle(eixo, &ang) ? ang : 90;
                int novo = atual + SERVO_STEP_DEG;
                if (novo > 180) {
                    novo = 180;
                }
                servo_write_angle(eixo, (uint16_t)novo);
            }
            changed = true;
        }

        if (button_check_pressed(&s_btn_dec)) {
            ESP_LOGI(TAG, "botao DEC pressionado");
            if (s_axis_ativo == HMI_AXIS_ESTEIRA) {
                int nova_vel = (int)conveyor_get_speed() - ESTEIRA_STEP_PCT;
                if (nova_vel <= 0) {
                    conveyor_stop();
                } else {
                    conveyor_set(1, (uint8_t)nova_vel);
                }
            } else {
                servo_axis_t eixo = hmi_axis_to_servo(s_axis_ativo);
                uint16_t ang;
                int atual = servo_get_angle(eixo, &ang) ? ang : 90;
                int novo = atual - SERVO_STEP_DEG;
                if (novo < 0) {
                    novo = 0;
                }
                servo_write_angle(eixo, (uint16_t)novo);
            }
            changed = true;
        }

        if (changed) {
            hmi_update_lcd();
        }

        vTaskDelay(pdMS_TO_TICKS(HMI_POLL_MS));
    }
}

void hmi_buttons_start(void)
{
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << BTN_CYCLE_GPIO) | (1ULL << BTN_INC_GPIO) | (1ULL << BTN_DEC_GPIO),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,    // pull-up é EXTERNO (10K na placa)
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&io_conf);

    xTaskCreate(hmi_task, "hmi_task", 4096, NULL, 3, NULL);
}