#pragma once

#include <stdint.h>
#include <stdbool.h>

// ============================================================
// Eixos disponíveis — GPIOs conforme esp32-ot-carrier-board-reference
// ============================================================
typedef enum {
    SERVO_BASE = 0,     // GPIO13
    SERVO_OMBRO,        // GPIO14
    SERVO_COTOVELO,     // GPIO27
    SERVO_GARRA,        // GPIO26
    SERVO_COUNT
} servo_axis_t;

// Ângulo máximo da garra. Acima do ponto em que as pinças se encostam o servo
// fica forçando parado (corrente de travamento) e queima: foi o que aconteceu
// em 2026-11 com a "fechada" em 180. Medido pelo usuário: as pinças encostam
// em 170; a "fechada" do automático é 165 e o limite fica abaixo do contato.
// Servo novo: conferir com `ir` de 5 em 5 graus e ajustar se o ponto mudar.
#define SERVO_GARRA_ANG_MAX 167

// Inicializa o timer LEDC (50Hz) e os 4 canais PWM. Chamar uma vez no boot.
void servo_driver_init(void);

// Move o eixo para o ângulo (0-180), limitado ao máximo do eixo (a garra
// não passa de SERVO_GARRA_ANG_MAX, venha o comando do console, da IHM ou
// do ciclo automático). Demais eixos ainda sem limites de calibração.
void servo_write_angle(servo_axis_t axis, uint16_t angle_deg);

// Solta o eixo (duty 0), igual ao soltar() do script MicroPython.
void servo_release(servo_axis_t axis);

// Retorna true e preenche angle_out se o eixo tiver uma posição conhecida
// (foi movido e não foi solto). Retorna false se nunca movido ou solto.
bool servo_get_angle(servo_axis_t axis, uint16_t *angle_out);

// Nome do eixo em texto ("base", "ombro", "cotovelo", "garra").
const char *servo_axis_name(servo_axis_t axis);

// Resolve um nome de texto para o enum correspondente. Retorna false se
// não encontrar (nome inválido).
bool servo_axis_from_name(const char *name, servo_axis_t *axis_out);
