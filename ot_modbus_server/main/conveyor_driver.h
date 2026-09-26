#pragma once

#include <stdint.h>
#include <stdbool.h>

// Inicializa GPIOs de direção (IN1/IN2) e o canal LEDC do ENA. Chamar uma
// vez no boot.
void conveyor_driver_init(void);

// direcao: 1 = frente, -1 = ré, 0 = parar (independente de speed_percent).
// speed_percent: 0-100. Na bancada, o motor TT só girou de fato acima de
// ~85-90% (queda de tensão no L298N) — ver hardware-learnings.md.
void conveyor_set(int8_t direcao, uint8_t speed_percent);

void conveyor_stop(void);

bool conveyor_is_running(void);
uint8_t conveyor_get_speed(void);
int8_t conveyor_get_direction(void);