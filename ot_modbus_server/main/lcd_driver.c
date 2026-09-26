#include "lcd_driver.h"

#include <stdio.h>
#include "driver/i2c_master.h"
#include "esp_err.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "lcd_driver";

// ============================================================
// Pinagem — J13 do carrier board OT (I2C compartilhado, padrão ESP32)
// ============================================================
#define LCD_SDA_GPIO     21
#define LCD_SCL_GPIO     22
#define LCD_I2C_ADDR     0x27
#define LCD_I2C_PORT     I2C_NUM_0
#define LCD_I2C_FREQ_HZ  100000

// Layout de bits do backpack PCF8574 (mesmo padrão da lib MicroPython
// lcd_api.py/i2c_lcd.py já usada na bancada):
// bit0=RS, bit1=RW(não usado, sempre 0/write), bit2=Enable, bit3=Backlight,
// bits4-7=D4-D7
#define LCD_BACKLIGHT_BIT   0x08
#define LCD_ENABLE_BIT      0x04
#define LCD_RS_BIT          0x01

static i2c_master_bus_handle_t s_bus_handle;
static i2c_master_dev_handle_t s_dev_handle;

static void lcd_write_raw(uint8_t data)
{
    esp_err_t err = i2c_master_transmit(s_dev_handle, &data, 1, -1);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Falha na escrita I2C (0x%02X): %s", data, esp_err_to_name(err));
    }
}

static void lcd_pulse_enable(uint8_t data)
{
    lcd_write_raw(data | LCD_ENABLE_BIT);
    esp_rom_delay_us(1);
    lcd_write_raw(data & (uint8_t)(~LCD_ENABLE_BIT));
    esp_rom_delay_us(50);
}

// Envia um nibble (já alinhado nos bits 4-7) — usado direto na sequência
// de inicialização, antes do display estar em modo 4-bit "de verdade".
static void lcd_write4bits(uint8_t nibble, uint8_t rs)
{
    uint8_t data = (nibble & 0xF0) | LCD_BACKLIGHT_BIT | (rs ? LCD_RS_BIT : 0);
    lcd_pulse_enable(data);
}

// Envia um byte completo (comando ou caractere) em dois nibbles.
static void lcd_send_byte(uint8_t value, uint8_t rs)
{
    lcd_write4bits(value & 0xF0, rs);
    lcd_write4bits((uint8_t)(value << 4) & 0xF0, rs);
}

static void lcd_command(uint8_t cmd)
{
    lcd_send_byte(cmd, 0);
}

static void lcd_write_char(char c)
{
    lcd_send_byte((uint8_t)c, 1);
}

void lcd_driver_init(void)
{
    i2c_master_bus_config_t bus_config = {
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .i2c_port = LCD_I2C_PORT,
        .scl_io_num = LCD_SCL_GPIO,
        .sda_io_num = LCD_SDA_GPIO,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = false,  // backpack PCF8574 já tem pull-up próprio
    };
    ESP_ERROR_CHECK(i2c_new_master_bus(&bus_config, &s_bus_handle));

    i2c_device_config_t dev_config = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = LCD_I2C_ADDR,
        .scl_speed_hz = LCD_I2C_FREQ_HZ,
    };
    ESP_ERROR_CHECK(i2c_master_bus_add_device(s_bus_handle, &dev_config, &s_dev_handle));

    // Sequência padrão de inicialização HD44780 em modo 4-bit
    vTaskDelay(pdMS_TO_TICKS(50));  // espera pós-power-on do LCD

    lcd_write4bits(0x30, 0);
    vTaskDelay(pdMS_TO_TICKS(5));
    lcd_write4bits(0x30, 0);
    vTaskDelay(pdMS_TO_TICKS(1));
    lcd_write4bits(0x30, 0);
    lcd_write4bits(0x20, 0);  // agora sim entra em modo 4-bit de vez

    lcd_command(0x28);  // function set: 4-bit, 2 linhas, fonte 5x8
    lcd_command(0x0C);  // display on, cursor off, blink off — direto, sem "display off" intermediário
    lcd_command(0x01);  // clear display
    vTaskDelay(pdMS_TO_TICKS(2));
    lcd_command(0x06);  // entry mode: incrementa cursor, sem shift
}

void lcd_clear(void)
{
    lcd_command(0x01);
    vTaskDelay(pdMS_TO_TICKS(2));
}

void lcd_set_cursor(uint8_t row, uint8_t col)
{
    static const uint8_t row_offsets[] = { 0x00, 0x40 };
    if (row > 1) {
        row = 1;
    }
    lcd_command((uint8_t)(0x80 | (row_offsets[row] + col)));
}

void lcd_print(const char *str)
{
    while (*str) {
        lcd_write_char(*str++);
    }
}

void lcd_i2c_scan(void)
{
    printf("Escaneando barramento I2C (0x08-0x77)...\n");
    int found = 0;
    for (uint8_t addr = 0x08; addr <= 0x77; addr++) {
        esp_err_t err = i2c_master_probe(s_bus_handle, addr, 50);
        if (err == ESP_OK) {
            printf("  Dispositivo encontrado em 0x%02X\n", addr);
            found++;
        }
    }
    if (found == 0) {
        printf("Nenhum dispositivo encontrado. Verifique fiacao/alimentacao/GND.\n");
    }
}

void lcd_test(void)
{
    lcd_clear();
    lcd_set_cursor(0, 0);
    lcd_print("TESTE LINHA 1");
    lcd_set_cursor(1, 0);
    lcd_print("TESTE LINHA 2");
    printf("Comando de teste enviado ao LCD.\n");
}