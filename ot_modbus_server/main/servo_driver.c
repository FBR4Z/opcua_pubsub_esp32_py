#include "servo_driver.h"

#include <string.h>
#include "driver/ledc.h"
#include "esp_err.h"

// ============================================================
// Mesma faixa validada na bancada MicroPython: 1.0-2.0ms, 50Hz.
// NUNCA usar 0.5-2.5ms — bate nos batentes mecânicos e queima o servo.
// ============================================================
#define SERVO_FREQ_HZ       50
#define SERVO_LEDC_RES      LEDC_TIMER_16_BIT   // resolução 16 bits, igual ao duty_u16() do MicroPython
#define SERVO_PULSE_MIN_US  1000
#define SERVO_PULSE_MAX_US  2000
#define SERVO_PERIOD_US     20000               // 1/50Hz

typedef struct {
    int gpio;
    ledc_channel_t channel;
    const char *name;
} servo_cfg_t;

static const servo_cfg_t s_cfg[SERVO_COUNT] = {
    [SERVO_BASE]     = { 13, LEDC_CHANNEL_0, "base" },
    [SERVO_OMBRO]    = { 14, LEDC_CHANNEL_1, "ombro" },
    [SERVO_COTOVELO] = { 27, LEDC_CHANNEL_2, "cotovelo" },
    [SERVO_GARRA]    = { 26, LEDC_CHANNEL_3, "garra" },
};

static bool s_has_angle[SERVO_COUNT] = {0};
static uint16_t s_angle[SERVO_COUNT] = {0};

static uint32_t angle_to_duty(uint16_t angle_deg)
{
    if (angle_deg > 180) {
        angle_deg = 180;
    }
    uint32_t pulse_us = SERVO_PULSE_MIN_US +
        ((uint32_t)(SERVO_PULSE_MAX_US - SERVO_PULSE_MIN_US) * angle_deg) / 180;
    uint32_t max_duty_plus_one = 1u << SERVO_LEDC_RES;
    return (uint32_t)(((uint64_t)pulse_us * max_duty_plus_one) / SERVO_PERIOD_US);
}

void servo_driver_init(void)
{
    ledc_timer_config_t timer_cfg = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .duty_resolution = SERVO_LEDC_RES,
        .timer_num = LEDC_TIMER_0,
        .freq_hz = SERVO_FREQ_HZ,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    ESP_ERROR_CHECK(ledc_timer_config(&timer_cfg));

    for (int i = 0; i < SERVO_COUNT; i++) {
        ledc_channel_config_t ch_cfg = {
            .gpio_num = s_cfg[i].gpio,
            .speed_mode = LEDC_LOW_SPEED_MODE,
            .channel = s_cfg[i].channel,
            .timer_sel = LEDC_TIMER_0,
            .duty = 0,
            .hpoint = 0,
        };
        ESP_ERROR_CHECK(ledc_channel_config(&ch_cfg));
    }
    // Importante: nunca chamar ledc_channel_config() de novo em operação
    // (equivalente ao pwm.deinit() do MicroPython) — remapeia os canais e
    // causa bug de eixo cruzado. Usar sempre ledc_set_duty()/ledc_update_duty().
}

void servo_write_angle(servo_axis_t axis, uint16_t angle_deg)
{
    if (axis >= SERVO_COUNT) {
        return;
    }
    if (angle_deg > 180) {
        angle_deg = 180;
    }
    uint32_t duty = angle_to_duty(angle_deg);
    ledc_set_duty(LEDC_LOW_SPEED_MODE, s_cfg[axis].channel, duty);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, s_cfg[axis].channel);
    s_angle[axis] = angle_deg;
    s_has_angle[axis] = true;
}

void servo_release(servo_axis_t axis)
{
    if (axis >= SERVO_COUNT) {
        return;
    }
    ledc_set_duty(LEDC_LOW_SPEED_MODE, s_cfg[axis].channel, 0);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, s_cfg[axis].channel);
    s_has_angle[axis] = false;
}

bool servo_get_angle(servo_axis_t axis, uint16_t *angle_out)
{
    if (axis >= SERVO_COUNT || !s_has_angle[axis]) {
        return false;
    }
    if (angle_out) {
        *angle_out = s_angle[axis];
    }
    return true;
}

const char *servo_axis_name(servo_axis_t axis)
{
    if (axis >= SERVO_COUNT) {
        return "?";
    }
    return s_cfg[axis].name;
}

bool servo_axis_from_name(const char *name, servo_axis_t *axis_out)
{
    for (int i = 0; i < SERVO_COUNT; i++) {
        if (strcmp(name, s_cfg[i].name) == 0) {
            if (axis_out) {
                *axis_out = (servo_axis_t)i;
            }
            return true;
        }
    }
    return false;
}
