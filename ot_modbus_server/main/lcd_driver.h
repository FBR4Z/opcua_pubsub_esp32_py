#pragma once

#include <stdint.h>

// Inicializa o barramento I2C (SDA=GPIO21, SCL=GPIO22) e o LCD 16x2
// via backpack PCF8574 (endereço 0x27). Chamar uma vez no boot.
void lcd_driver_init(void);

void lcd_clear(void);

// row: 0 ou 1. col: 0-15.
void lcd_set_cursor(uint8_t row, uint8_t col);

void lcd_print(const char *str);

// Escaneia o barramento I2C e imprime (via printf) os endereços de
// dispositivos encontrados. Ferramenta de diagnóstico — chamar depois
// de lcd_driver_init().
void lcd_i2c_scan(void);

// Limpa o display e escreve "TESTE" nas duas linhas — ferramenta de
// diagnóstico visual simples, sem depender de eixo/HMI.
void lcd_test(void);