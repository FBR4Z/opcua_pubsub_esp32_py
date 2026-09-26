#include "hc_sr04_driver.h"

#include "driver/gpio.h"
#include "esp_timer.h"
#include "esp_rom_sys.h"   // esp_rom_delay_us — pulso de trigger de 10us

// ============================================================
// Pinagem — J6 do carrier board OT
// ============================================================
#define HC_SR04_TRIG_GPIO   23
#define HC_SR04_ECHO_GPIO   15   // via divisor de tensão R1(1k)/R2(2k)

// ~30ms cobre até uns 5m de alcance (ida+volta do som) — acima disso, timeout.
#define HC_SR04_TIMEOUT_US   30000

void hc_sr04_driver_init(void)
{
    gpio_config_t trig_conf = {
        .pin_bit_mask = (1ULL << HC_SR04_TRIG_GPIO),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&trig_conf);
    gpio_set_level(HC_SR04_TRIG_GPIO, 0);

    gpio_config_t echo_conf = {
        .pin_bit_mask = (1ULL << HC_SR04_ECHO_GPIO),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&echo_conf);
}

int hc_sr04_measure_cm(void)
{
    // Pulso de trigger de 10us
    gpio_set_level(HC_SR04_TRIG_GPIO, 0);
    esp_rom_delay_us(2);
    gpio_set_level(HC_SR04_TRIG_GPIO, 1);
    esp_rom_delay_us(10);
    gpio_set_level(HC_SR04_TRIG_GPIO, 0);

    // Espera o ECHO subir (início do eco)
    int64_t t_wait_start = esp_timer_get_time();
    while (gpio_get_level(HC_SR04_ECHO_GPIO) == 0) {
        if (esp_timer_get_time() - t_wait_start > HC_SR04_TIMEOUT_US) {
            return -1;  // eco nunca subiu — sensor desconectado ou fora de alcance
        }
    }

    // Mede quanto tempo o ECHO fica em nível alto
    int64_t t_echo_start = esp_timer_get_time();
    while (gpio_get_level(HC_SR04_ECHO_GPIO) == 1) {
        if (esp_timer_get_time() - t_echo_start > HC_SR04_TIMEOUT_US) {
            return -1;  // eco não desceu — leitura inválida
        }
    }
    int64_t duration_us = esp_timer_get_time() - t_echo_start;

    // distancia(cm) = duracao(us) / 58 — formula padrao HC-SR04
    return (int)(duration_us / 58);
}