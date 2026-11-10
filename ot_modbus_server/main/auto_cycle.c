#include "auto_cycle.h"

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_timer.h"

#include "servo_driver.h"
#include "conveyor_driver.h"
#include "lcd_driver.h"

static const char *TAG = "auto_cycle";

// ============================================================
// Parâmetros do movimento
// ============================================================
#define PASSO_MS            25    // 1 grau a cada 25 ms = 40 graus/s (velocidade média)
#define PAUSA_EIXO_MS       150   // pausa entre um eixo e o próximo
#define ESTEIRA_VEL_PCT     100   // na bancada o motor só gira acima de ~85%
#define LIMIAR_PADRAO_CM    8     // peça "presente" abaixo desta distância
#define ESTEIRA_PADRAO_S    3     // tempo que a esteira gira depois de receber a peça
#define PAUSA_GARRA_MS      300

// ============================================================
// Poses (base, ombro, cotovelo), calibradas na bancada em 2026-11-07.
// "pega" é onde o sensor vê a peça; "solta" é em cima da esteira. Para
// recalibrar: `eixo`/`ir` (ou os botões) + `auto pose <nome>` e copiar a
// saída de `auto status` para cá.
// ============================================================
typedef enum {
    POSE_REPOUSO = 0,
    POSE_PEGA_ACIMA,
    POSE_PEGA,
    POSE_SOLTA_ACIMA,
    POSE_SOLTA,
    POSE_COUNT
} pose_id_t;

typedef struct {
    uint16_t ang[3];   // SERVO_BASE, SERVO_OMBRO, SERVO_COTOVELO
} pose_t;

static const char *s_pose_nomes[POSE_COUNT] = {
    [POSE_REPOUSO]     = "repouso",
    [POSE_PEGA_ACIMA]  = "pega_acima",
    [POSE_PEGA]        = "pega",
    [POSE_SOLTA_ACIMA] = "solta_acima",
    [POSE_SOLTA]       = "solta",
};

// Mesmos nomes do enum, para `auto status` imprimir a tabela pronta pra colar
static const char *s_pose_enum[POSE_COUNT] = {
    [POSE_REPOUSO]     = "POSE_REPOUSO",
    [POSE_PEGA_ACIMA]  = "POSE_PEGA_ACIMA",
    [POSE_PEGA]        = "POSE_PEGA",
    [POSE_SOLTA_ACIMA] = "POSE_SOLTA_ACIMA",
    [POSE_SOLTA]       = "POSE_SOLTA",
};

static pose_t s_poses[POSE_COUNT] = {
    [POSE_REPOUSO]     = { {  90,  90, 180 } },
    [POSE_PEGA_ACIMA]  = { {  90, 140, 180 } },
    [POSE_PEGA]        = { {  90, 180, 180 } },
    [POSE_SOLTA_ACIMA] = { { 180,  60, 180 } },
    [POSE_SOLTA]       = { { 180,  90, 180 } },
};
static bool s_pose_ensinada[POSE_COUNT] = {0};

static uint16_t s_garra_aberta  = 90;
static uint16_t s_garra_fechada = 165;  // pinças encostam em 170; 180 forçava e queimou o servo
static bool s_garra_aberta_ensinada  = false;
static bool s_garra_fechada_ensinada = false;

// ============================================================
// Estado (escrito só pela auto_task, exceto s_running)
// ============================================================
static volatile bool s_running = false;
static volatile bool s_botao_a = false;
static volatile auto_fase_t s_fase = AUTO_FASE_PARADO;
static volatile uint16_t s_count = 0;
static volatile int s_limiar_cm = LIMIAR_PADRAO_CM;
static volatile int s_esteira_s = ESTEIRA_PADRAO_S;
static int64_t s_esteira_ate_us = 0;  // 0 = esteira parada; só a auto_task mexe
static int (*s_dist_cm)(void) = NULL;
static TaskHandle_t s_task = NULL;

const char *auto_fase_name(auto_fase_t fase)
{
    switch (fase) {
        case AUTO_FASE_PARADO:     return "parado";
        case AUTO_FASE_AGUARDA:    return "aguarda";
        case AUTO_FASE_PEGA:       return "pega";
        case AUTO_FASE_TRANSPORTA: return "transporta";
        case AUTO_FASE_SOLTA:      return "solta";
        case AUTO_FASE_ESTEIRA:    return "esteira";
        default:                   return "?";
    }
}

// O que o operador pode fazer em cada fase (linha 2 do LCD)
static const char *dica_da_fase(auto_fase_t fase)
{
    switch (fase) {
        case AUTO_FASE_PARADO:  return "A=liga";
        case AUTO_FASE_AGUARDA: return "peca+A";
        default:                return "B=para";
    }
}

static void lcd_mostra(auto_fase_t fase, const char *dica)
{
    char l1[17], l2[17];
    snprintf(l1, sizeof(l1), "AUTO %-11s", auto_fase_name(fase));
    snprintf(l2, sizeof(l2), "%-8s n=%-5u", dica, s_count);
    lcd_set_cursor(0, 0);
    lcd_print(l1);
    lcd_set_cursor(1, 0);
    lcd_print(l2);
}

void auto_cycle_mostra_lcd(void)
{
    lcd_mostra(s_fase, dica_da_fase(s_fase));
}

static void muda_fase(auto_fase_t fase)
{
    s_fase = fase;
    ESP_LOGI(TAG, "fase %d (%s), ciclos=%u", (int)fase, auto_fase_name(fase), s_count);
    auto_cycle_mostra_lcd();
}

// Desliga a esteira quando o tempo dela acabar. Chamada nos laços de espera
// e de movimento, então a esteira gira enquanto o braço já volta ao repouso.
static void esteira_confere(void)
{
    if (s_esteira_ate_us != 0 && esp_timer_get_time() >= s_esteira_ate_us) {
        conveyor_stop();
        s_esteira_ate_us = 0;
        ESP_LOGI(TAG, "esteira parada apos %d s", s_esteira_s);
    }
}

static void esteira_desliga(void)
{
    conveyor_stop();
    s_esteira_ate_us = 0;
}

// Espera ms em fatias curtas. Retorna false se o ciclo foi parado.
static bool espera_ms(int ms)
{
    while (ms > 0) {
        esteira_confere();
        if (!s_running) {
            return false;
        }
        int fatia = ms < 50 ? ms : 50;
        vTaskDelay(pdMS_TO_TICKS(fatia));
        ms -= fatia;
    }
    return s_running;
}

// Move um servo, 1 grau por passo, até o alvo. Eixo sem posição conhecida
// (solto) vai direto ao alvo.
static bool move_eixo(servo_axis_t eixo, uint16_t alvo)
{
    uint16_t ang;
    if (!servo_get_angle(eixo, &ang)) {
        servo_write_angle(eixo, alvo);
        return espera_ms(PAUSA_EIXO_MS);
    }
    int atual = ang;
    if (atual == alvo) {
        return true;
    }

    while (atual != alvo) {
        esteira_confere();
        if (!s_running) {
            return false;
        }
        atual += (atual < alvo) ? 1 : -1;
        servo_write_angle(eixo, (uint16_t)atual);
        vTaskDelay(pdMS_TO_TICKS(PASSO_MS));
    }
    return espera_ms(PAUSA_EIXO_MS);
}

// Move um eixo de cada vez. Ombro menor = braço mais alto (pega_acima 140 >
// pega 180, solta_acima 60 > solta 90), então: se o ombro vai subir, ele
// sobe antes de a base girar; se vai descer, a base gira primeiro. Assim o
// braço nunca gira baixo. A garra é sempre a última.
static bool move_para(const uint16_t alvo[SERVO_COUNT])
{
    static const servo_axis_t ordem_sobe[SERVO_COUNT] = {
        SERVO_OMBRO, SERVO_COTOVELO, SERVO_BASE, SERVO_GARRA,
    };
    static const servo_axis_t ordem_desce[SERVO_COUNT] = {
        SERVO_BASE, SERVO_OMBRO, SERVO_COTOVELO, SERVO_GARRA,
    };

    uint16_t ombro;
    bool sobe = servo_get_angle(SERVO_OMBRO, &ombro) && alvo[SERVO_OMBRO] < ombro;
    const servo_axis_t *ordem = sobe ? ordem_sobe : ordem_desce;

    for (int i = 0; i < SERVO_COUNT; i++) {
        if (!move_eixo(ordem[i], alvo[ordem[i]])) {
            return false;
        }
    }
    return true;
}

static bool vai_pose(pose_id_t pose, bool garra_fechada)
{
    uint16_t alvo[SERVO_COUNT] = {
        [SERVO_BASE]     = s_poses[pose].ang[0],
        [SERVO_OMBRO]    = s_poses[pose].ang[1],
        [SERVO_COTOVELO] = s_poses[pose].ang[2],
        [SERVO_GARRA]    = garra_fechada ? s_garra_fechada : s_garra_aberta,
    };
    return move_para(alvo);
}

static bool peca_presente(int *dist)
{
    *dist = s_dist_cm ? s_dist_cm() : -1;
    return *dist >= 0 && *dist < s_limiar_cm;
}

// Espera o botão A. Só segue se, no momento do aperto, o sensor estiver
// vendo a peça abaixo do limiar; aperto sem peça é descartado.
static bool espera_peca_e_botao(void)
{
    s_botao_a = false;  // aperto antigo (ex.: o que ligou o ciclo) não conta
    while (1) {
        if (s_botao_a) {
            s_botao_a = false;
            int d;
            if (peca_presente(&d)) {
                ESP_LOGI(TAG, "botao A com peca a %d cm", d);
                return true;
            }
            ESP_LOGW(TAG, "botao A sem peca (leitura %d cm, limiar %d cm)", d, s_limiar_cm);
            lcd_mostra(s_fase, "sem peca");
        }
        if (!espera_ms(50)) {
            return false;
        }
    }
}

static bool espera_esteira_parar(void)
{
    if (s_esteira_ate_us != 0) {
        ESP_LOGI(TAG, "esperando a esteira parar");
    }
    while (s_esteira_ate_us != 0) {
        if (!espera_ms(50)) {
            return false;
        }
    }
    return true;
}

static bool um_ciclo(void)
{
    muda_fase(AUTO_FASE_AGUARDA);
    if (!vai_pose(POSE_REPOUSO, false) || !espera_peca_e_botao()) {
        return false;
    }

    muda_fase(AUTO_FASE_PEGA);
    if (!vai_pose(POSE_PEGA_ACIMA, false) || !vai_pose(POSE_PEGA, false) ||
        !vai_pose(POSE_PEGA, true) || !espera_ms(PAUSA_GARRA_MS) ||
        !vai_pose(POSE_PEGA_ACIMA, true)) {
        return false;
    }

    muda_fase(AUTO_FASE_TRANSPORTA);
    if (!vai_pose(POSE_SOLTA_ACIMA, true) || !espera_esteira_parar()) {
        return false;
    }

    muda_fase(AUTO_FASE_SOLTA);
    if (!vai_pose(POSE_SOLTA, true) || !vai_pose(POSE_SOLTA, false) ||
        !espera_ms(PAUSA_GARRA_MS) || !vai_pose(POSE_SOLTA_ACIMA, false)) {
        return false;
    }

    // A esteira gira em segundo plano: o próximo ciclo já começa voltando ao
    // repouso, e a fase TRANSPORTA do ciclo seguinte espera ela parar.
    muda_fase(AUTO_FASE_ESTEIRA);
    conveyor_set(1, ESTEIRA_VEL_PCT);
    s_esteira_ate_us = esp_timer_get_time() + (int64_t)s_esteira_s * 1000000;
    s_count++;
    return true;
}

static void auto_task(void *pv)
{
    while (1) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);  // espera auto_cycle_start()
        ESP_LOGI(TAG, "ciclo automatico ligado");
        esteira_desliga();  // esteira ligada no manual não conta como "do ciclo"
        while (s_running && um_ciclo()) {
        }
        esteira_desliga();
        s_running = false;
        ESP_LOGI(TAG, "ciclo automatico parado, ciclos=%u", s_count);
        lcd_mostra(AUTO_FASE_PARADO, dica_da_fase(AUTO_FASE_PARADO));
        // Por último: a IHM só volta a escrever no LCD depois de ver a fase 0
        s_fase = AUTO_FASE_PARADO;
    }
}

void auto_cycle_init(int (*dist_cm_fn)(void))
{
    s_dist_cm = dist_cm_fn;
    xTaskCreate(auto_task, "auto_task", 4096, NULL, 4, &s_task);
}

bool auto_cycle_start(void)
{
    if (s_running || s_fase != AUTO_FASE_PARADO) {
        return false;
    }
    s_running = true;
    xTaskNotifyGive(s_task);
    return true;
}

void auto_cycle_stop(void)
{
    s_running = false;
}

void auto_cycle_botao_a(void)
{
    s_botao_a = true;
}

bool auto_cycle_is_running(void)
{
    return s_running || s_fase != AUTO_FASE_PARADO;
}

auto_fase_t auto_cycle_get_fase(void)
{
    return s_fase;
}

uint16_t auto_cycle_get_count(void)
{
    return s_count;
}

bool auto_cycle_save_pose(const char *name)
{
    for (int p = 0; p < POSE_COUNT; p++) {
        if (strcmp(name, s_pose_nomes[p]) != 0) {
            continue;
        }
        uint16_t ang[3];
        for (int i = 0; i < 3; i++) {
            if (!servo_get_angle((servo_axis_t)i, &ang[i])) {
                printf("%s esta solto: mova-o com `ir` antes de gravar a pose\n",
                       servo_axis_name((servo_axis_t)i));
                return false;
            }
        }
        memcpy(s_poses[p].ang, ang, sizeof(ang));
        s_pose_ensinada[p] = true;
        printf("Pose %s = base %u, ombro %u, cotovelo %u\n", name, ang[0], ang[1], ang[2]);
        return true;
    }
    printf("Pose invalida: %s (use repouso|pega_acima|pega|solta_acima|solta)\n", name);
    return false;
}

bool auto_cycle_save_garra(bool fechada)
{
    uint16_t ang;
    if (!servo_get_angle(SERVO_GARRA, &ang)) {
        printf("garra esta solta: mova-a com `ir` antes de gravar\n");
        return false;
    }
    if (fechada) {
        s_garra_fechada = ang;
        s_garra_fechada_ensinada = true;
    } else {
        s_garra_aberta = ang;
        s_garra_aberta_ensinada = true;
    }
    printf("Garra %s = %u graus\n", fechada ? "fechada" : "aberta", ang);
    return true;
}

void auto_cycle_set_limiar_cm(int cm)
{
    s_limiar_cm = cm;
}

void auto_cycle_set_esteira_s(int s)
{
    s_esteira_s = s;
}

void auto_cycle_print_status(void)
{
    printf("Estado: %s, fase %d (%s), ciclos=%u\n",
           auto_cycle_is_running() ? "rodando" : "parado",
           (int)s_fase, auto_fase_name(s_fase), s_count);
    printf("Limiar da peca: %d cm, esteira gira %d s apos receber a peca\n",
           s_limiar_cm, s_esteira_s);
    printf("Poses (* = provisoria, ainda nao gravada nesta sessao):\n");
    printf("static pose_t s_poses[POSE_COUNT] = {\n");
    for (int p = 0; p < POSE_COUNT; p++) {
        printf("    [%-16s] = { { %3u, %3u, %3u } },%s\n", s_pose_enum[p],
               s_poses[p].ang[0], s_poses[p].ang[1], s_poses[p].ang[2],
               s_pose_ensinada[p] ? "" : "  // *");
    }
    printf("};\n");
    printf("static uint16_t s_garra_aberta  = %u;%s\n", s_garra_aberta,
           s_garra_aberta_ensinada ? "" : "  // *");
    printf("static uint16_t s_garra_fechada = %u;%s\n", s_garra_fechada,
           s_garra_fechada_ensinada ? "" : "  // *");
}
