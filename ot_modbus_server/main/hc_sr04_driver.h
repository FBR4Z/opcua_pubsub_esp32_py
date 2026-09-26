#pragma once

#include <stdint.h>

// Configura TRIG (saída) e ECHO (entrada, via divisor de tensão externo
// 1k/2k — obrigatório, o ECHO sai em 5V e o ESP32 não é 5V-tolerante).
void hc_sr04_driver_init(void);

// Dispara um pulso de trigger e mede o eco. Retorna a distância em cm,
// ou -1 se der timeout (nada no alcance, ou sensor desconectado).
// CHAMADA BLOQUEANTE — pode levar até ~30ms no pior caso (timeout).
// Não chamar direto de dentro do control_task (20ms de período); usar
// uma task própria de baixa frequência (ver sensor_task em main.c).
int hc_sr04_measure_cm(void);