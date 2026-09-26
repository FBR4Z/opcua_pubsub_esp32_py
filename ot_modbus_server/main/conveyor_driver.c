#include "conveyor_driver.h"

#include "driver/ledc.h"
#include "driver/gpio.h"
#include "esp_err.h"

// ============================================================
// Pinagem — J5 do carrier board OT
// ============================================================
#define CONV_ENA_GPIO   32
#define CONV_IN1_GPIO   33
#define CONV_IN2_GPIO   25

// 20kHz elimina o zumbido audível do L298N (validado na bancada MicroPython).
#define CONV_PWM_FREQ_HZ   20000
#define CONV_LEDC_RES      LEDC_TIMER_10_BIT
#define CONV_LEDC_TIMER    LEDC_TIMER_1      // timer separado do dos servos (LEDC_TIMER_0)
#define CONV_LEDC_CHANNEL  LEDC_CHANNEL_4    // canais 0-3 já usados pelos 4 servos

static bool s_running = false;
static uint8_t s_speed = 0;
static int8_t s_direction = 0;

void conveyor_driver_init(void)
{
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << CONV_IN1_GPIO) | (1ULL << CONV_IN2_GPIO),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&io_conf));
    gpio_set_level(CONV_IN1_GPIO, 0);
    gpio_set_level(CONV_IN2_GPIO, 0);

    ledc_timer_config_t timer_cfg = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .duty_resolution = CONV_LEDC_RES,
        .timer_num = CONV_LEDC_TIMER,
        .freq_hz = CONV_PWM_FREQ_HZ,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    ESP_ERROR_CHECK(ledc_timer_config(&timer_cfg));

    ledc_channel_config_t ch_cfg = {
        .gpio_num = CONV_ENA_GPIO,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = CONV_LEDC_CHANNEL,
        .timer_sel = CONV_LEDC_TIMER,
        .duty = 0,
        .hpoint = 0,
    };
    ESP_ERROR_CHECK(ledc_channel_config(&ch_cfg));
}

void conveyor_set(int8_t direcao, uint8_t speed_percent)
{
    if (speed_percent > 100) {
        speed_percent = 100;
    }

    gpio_set_level(CONV_IN1_GPIO, direcao > 0 ? 1 : 0);
    gpio_set_level(CONV_IN2_GPIO, direcao < 0 ? 1 : 0);

    uint32_t max_duty = (1u << CONV_LEDC_RES) - 1;
    uint32_t duty = (uint32_t)(((uint32_t)max_duty * speed_percent) / 100);
    ledc_set_duty(LEDC_LOW_SPEED_MODE, CONV_LEDC_CHANNEL, duty);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, CONV_LEDC_CHANNEL);

    s_direction = direcao;
    s_speed = speed_percent;
    s_running = (direcao != 0 && speed_percent > 0);
}

void conveyor_stop(void)
{
    conveyor_set(0, 0);
}

bool conveyor_is_running(void)
{
    return s_running;
}

uint8_t conveyor_get_speed(void)
{
    return s_speed;
}

int8_t conveyor_get_direction(void)
{
    return s_direction;
}