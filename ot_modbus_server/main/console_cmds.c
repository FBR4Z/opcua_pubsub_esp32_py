#include "console_cmds.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "esp_console.h"
#include "esp_log.h"

#include "servo_driver.h"
#include "conveyor_driver.h"
#include "hc_sr04_driver.h"
#include "lcd_driver.h"

static const char *TAG = "console_cmds";

// Eixo ativo — equivalente ao _idx_ativo do servo_jog_calib_v3.py
static servo_axis_t s_eixo_ativo = SERVO_BASE;

// ============================================================
// eixo [nome]
// ============================================================
static int cmd_eixo(int argc, char **argv)
{
    if (argc < 2) {
        printf("Eixo ativo: %s\n", servo_axis_name(s_eixo_ativo));
        printf("Opcoes: base ombro cotovelo garra\n");
        return 0;
    }
    servo_axis_t axis;
    if (!servo_axis_from_name(argv[1], &axis)) {
        printf("Eixo invalido: %s (use base|ombro|cotovelo|garra)\n", argv[1]);
        return 1;
    }
    s_eixo_ativo = axis;
    printf("Eixo ativo -> %s\n", servo_axis_name(s_eixo_ativo));
    return 0;
}

// ============================================================
// ir <angulo>
// ============================================================
static int cmd_ir(int argc, char **argv)
{
    if (argc < 2) {
        printf("Uso: ir <angulo 0-180>\n");
        return 1;
    }
    int ang = atoi(argv[1]);
    if (ang < 0 || ang > 180) {
        printf("Angulo fora da faixa 0-180: %d\n", ang);
        return 1;
    }
    servo_write_angle(s_eixo_ativo, (uint16_t)ang);
    printf("%s -> %d graus\n", servo_axis_name(s_eixo_ativo), ang);
    return 0;
}

// ============================================================
// ler — mostra o angulo atual de todos os eixos
// ============================================================
static int cmd_ler(int argc, char **argv)
{
    for (servo_axis_t axis = 0; axis < SERVO_COUNT; axis++) {
        uint16_t ang;
        const char *marcador = (axis == s_eixo_ativo) ? ">" : " ";
        if (servo_get_angle(axis, &ang)) {
            printf("%s%-10s %d graus\n", marcador, servo_axis_name(axis), ang);
        } else {
            printf("%s%-10s solto (sem posicao)\n", marcador, servo_axis_name(axis));
        }
    }
    return 0;
}

// ============================================================
// soltar — solta o eixo ativo (duty 0)
// ============================================================
static int cmd_soltar(int argc, char **argv)
{
    servo_release(s_eixo_ativo);
    printf("%s solto\n", servo_axis_name(s_eixo_ativo));
    return 0;
}

// ============================================================
// esteira <on|off> [velocidade 0-100]
// ============================================================
static int cmd_esteira(int argc, char **argv)
{
    if (argc < 2) {
        printf("Uso: esteira <on|off> [velocidade 0-100]\n");
        printf("Estado atual: %s, vel=%d%%\n",
               conveyor_is_running() ? "ligada" : "parada", conveyor_get_speed());
        return 0;
    }
    if (strcmp(argv[1], "off") == 0) {
        conveyor_stop();
        printf("Esteira parada\n");
        return 0;
    }
    if (strcmp(argv[1], "on") == 0) {
        int vel = 100;  // na bancada, só girou de fato acima de ~85-90%
        if (argc >= 3) {
            vel = atoi(argv[2]);
        }
        if (vel < 0 || vel > 100) {
            printf("Velocidade fora da faixa 0-100: %d\n", vel);
            return 1;
        }
        if (vel < 85) {
            printf("Aviso: na bancada, o motor so girou de fato acima de ~85%%.\n");
        }
        conveyor_set(1, (uint8_t)vel);
        printf("Esteira ligada, vel=%d%%\n", vel);
        return 0;
    }
    printf("Argumento invalido: %s (use on|off)\n", argv[1]);
    return 1;
}

// ============================================================
// sensor — dispara uma leitura do HC-SR04 agora e mostra o resultado
// ============================================================
static int cmd_sensor(int argc, char **argv)
{
    int dist = hc_sr04_measure_cm();
    if (dist < 0) {
        printf("Sensor: sem leitura (timeout)\n");
    } else {
        printf("Sensor: %d cm\n", dist);
    }
    return 0;
}

// ============================================================
// i2c_scan — diagnóstico: lista endereços I2C respondendo no barramento
// ============================================================
static int cmd_i2c_scan(int argc, char **argv)
{
    lcd_i2c_scan();
    return 0;
}

// ============================================================
// lcd_test — limpa e escreve "TESTE" nas duas linhas do LCD
// ============================================================
static int cmd_lcd_test(int argc, char **argv)
{
    lcd_test();
    return 0;
}

static void register_commands(void)
{
    const esp_console_cmd_t cmd_eixo_def = {
        .command = "eixo",
        .help = "Seleciona ou mostra o eixo ativo (base|ombro|cotovelo|garra)",
        .hint = NULL,
        .func = &cmd_eixo,
    };
    ESP_ERROR_CHECK(esp_console_cmd_register(&cmd_eixo_def));

    const esp_console_cmd_t cmd_ir_def = {
        .command = "ir",
        .help = "Move o eixo ativo para um angulo (0-180)",
        .hint = NULL,
        .func = &cmd_ir,
    };
    ESP_ERROR_CHECK(esp_console_cmd_register(&cmd_ir_def));

    const esp_console_cmd_t cmd_ler_def = {
        .command = "ler",
        .help = "Mostra o angulo atual de todos os eixos",
        .hint = NULL,
        .func = &cmd_ler,
    };
    ESP_ERROR_CHECK(esp_console_cmd_register(&cmd_ler_def));

    const esp_console_cmd_t cmd_soltar_def = {
        .command = "soltar",
        .help = "Solta o eixo ativo (duty 0)",
        .hint = NULL,
        .func = &cmd_soltar,
    };
    ESP_ERROR_CHECK(esp_console_cmd_register(&cmd_soltar_def));

    const esp_console_cmd_t cmd_esteira_def = {
        .command = "esteira",
        .help = "Liga/desliga a esteira: esteira <on|off> [velocidade 0-100]",
        .hint = NULL,
        .func = &cmd_esteira,
    };
    ESP_ERROR_CHECK(esp_console_cmd_register(&cmd_esteira_def));

    const esp_console_cmd_t cmd_sensor_def = {
        .command = "sensor",
        .help = "Faz uma leitura do HC-SR04 agora e mostra a distancia em cm",
        .hint = NULL,
        .func = &cmd_sensor,
    };
    ESP_ERROR_CHECK(esp_console_cmd_register(&cmd_sensor_def));

    const esp_console_cmd_t cmd_i2c_scan_def = {
        .command = "i2c_scan",
        .help = "Escaneia o barramento I2C e lista os enderecos encontrados",
        .hint = NULL,
        .func = &cmd_i2c_scan,
    };
    ESP_ERROR_CHECK(esp_console_cmd_register(&cmd_i2c_scan_def));

    const esp_console_cmd_t cmd_lcd_test_def = {
        .command = "lcd_test",
        .help = "Limpa o LCD e escreve TESTE nas duas linhas",
        .hint = NULL,
        .func = &cmd_lcd_test,
    };
    ESP_ERROR_CHECK(esp_console_cmd_register(&cmd_lcd_test_def));
}

void console_cmds_start(void)
{
    esp_console_repl_t *repl = NULL;
    esp_console_repl_config_t repl_config = ESP_CONSOLE_REPL_CONFIG_DEFAULT();
    repl_config.prompt = "ot>";
    repl_config.max_cmdline_length = 256;

    esp_console_dev_uart_config_t uart_config = ESP_CONSOLE_DEV_UART_CONFIG_DEFAULT();

    esp_console_register_help_command();
    register_commands();

    ESP_ERROR_CHECK(esp_console_new_repl_uart(&uart_config, &repl_config, &repl));
    ESP_ERROR_CHECK(esp_console_start_repl(repl));

    ESP_LOGI(TAG, "Console pronto. Comandos: eixo, ir, ler, soltar, help");
}