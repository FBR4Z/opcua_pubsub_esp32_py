#pragma once

#include <stdint.h>
#include <stdbool.h>

// ============================================================
// Ciclo automático pick-and-place. O valor numérico da fase vai pro
// holding register HOLD_REG_AUTO_FASE, então não reordenar.
// ============================================================
typedef enum {
    AUTO_FASE_PARADO = 0,   // ciclo desligado
    AUTO_FASE_AGUARDA,      // 1: repouso, garra aberta, esperando peça no sensor + botão A
    AUTO_FASE_PEGA,         // 2: braço desce, fecha a garra e sobe com a peça
    AUTO_FASE_TRANSPORTA,   // 3: leva a peça até acima da esteira e espera ela parar
    AUTO_FASE_SOLTA,        // 4: desce, abre a garra e sai da esteira
    AUTO_FASE_ESTEIRA,      // 5: liga a esteira por N s (ela para sozinha) e reinicia
} auto_fase_t;

// dist_cm_fn: devolve a última leitura do HC-SR04 em cm (-1 = sem leitura).
// O ciclo NÃO dispara o sensor por conta própria — quem mede é a
// sensor_task do main.c; duas tasks disparando o mesmo HC-SR04 se atrapalham.
void auto_cycle_init(int (*dist_cm_fn)(void));

// Liga o ciclo. Retorna false se já estava rodando.
bool auto_cycle_start(void);

// Para o ciclo no próximo passo de movimento (~15 ms): esteira desliga e
// os servos ficam parados onde estão (não voltam sozinhos ao repouso).
void auto_cycle_stop(void);

// Botão A da IHM apertado com o ciclo rodando. Na fase AGUARDA, dispara a
// pega se o sensor estiver vendo a peça; nas outras fases é ignorado.
void auto_cycle_botao_a(void);

bool auto_cycle_is_running(void);
auto_fase_t auto_cycle_get_fase(void);
uint16_t auto_cycle_get_count(void);
const char *auto_fase_name(auto_fase_t fase);

// Desenha no LCD a tela do modo automático (fase, dica do botão e contador).
void auto_cycle_mostra_lcd(void);

// Grava os ângulos ATUAIS de base, ombro e cotovelo na pose de nome dado
// (repouso | pega_acima | pega | solta_acima | solta). Os servos precisam
// ter posição conhecida (movidos com `ir` ou com os botões, não soltos). Só
// em RAM: depois de calibrar, copiar os valores impressos pra s_poses em
// auto_cycle.c.
bool auto_cycle_save_pose(const char *name);

// Grava o ângulo atual da garra como "aberta" ou "fechada".
bool auto_cycle_save_garra(bool fechada);

void auto_cycle_set_limiar_cm(int cm);
void auto_cycle_set_esteira_s(int s);

// Imprime estado, contador, limiar e a tabela de poses (formato pronto
// pra colar no código).
void auto_cycle_print_status(void);
