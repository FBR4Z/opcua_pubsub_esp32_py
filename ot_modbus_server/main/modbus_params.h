#pragma once

#include <stdint.h>

// ============================================================
// LAYOUT DOS HOLDING REGISTERS (function code 0x03 - Read Holding Registers)
// O ESP32 IT (Client) faz polling nestes offsets.
// Cada registrador é 16 bits. Ângulos e velocidade cabem em uint16_t.
// ============================================================

typedef enum {
    HOLD_REG_BASE_ANG      = 0,  // ângulo atual do servo Base       (graus, 0-180)
    HOLD_REG_OMBRO_ANG     = 1,  // ângulo atual do servo Ombro      (graus, 0-180)
    HOLD_REG_COTOVELO_ANG  = 2,  // ângulo atual do servo Cotovelo   (graus, 0-180)
    HOLD_REG_GARRA_ANG     = 3,  // ângulo atual do servo Garra      (graus, 0-180)
    HOLD_REG_ESTEIRA_VEL   = 4,  // velocidade da esteira            (%, 0-100)
    HOLD_REG_ESTEIRA_STATE = 5,  // 0 = parada, 1 = girando
    HOLD_REG_SENSOR_DIST   = 6,  // distância HC-SR04                (cm, 0xFFFF = sem leitura)
    HOLD_REG_CYCLE_COUNT   = 7,  // ciclos pick-and-place completos  (contador, volta a 0 após 65535)
    HOLD_REG_AUTO_FASE     = 8,  // fase do ciclo automático         (auto_fase_t, 0 = parado)

    HOLD_REG_COUNT              // total de registradores — manter por último
} holding_reg_offset_t;

// Struct espelhando o array de registradores, para a task de controle
// escrever de forma legível (em vez de índices mágicos).
// O array real que o mbcontroller enxerga é uint16_t holding_reg_area[HOLD_REG_COUNT]
// em main.c — esta struct é só uma "view" com nomes, do mesmo tamanho.
typedef struct __attribute__((packed)) {
    uint16_t base_ang;
    uint16_t ombro_ang;
    uint16_t cotovelo_ang;
    uint16_t garra_ang;
    uint16_t esteira_vel;
    uint16_t esteira_state;
    uint16_t sensor_dist;
    uint16_t cycle_count;
    uint16_t auto_fase;
} modbus_holding_regs_t;

_Static_assert(sizeof(modbus_holding_regs_t) == HOLD_REG_COUNT * sizeof(uint16_t),
               "modbus_holding_regs_t precisa ter exatamente HOLD_REG_COUNT campos uint16_t");
