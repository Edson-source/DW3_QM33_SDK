/**
 * @file      anticollision.c
 *
 * @brief     Implementation of anticollision application
 *
 * @author    Qorvo Applications
 *
 * @copyright SPDX-FileCopyrightText: Copyright (c) 2024-2025 Qorvo US, Inc.
 *            SPDX-License-Identifier: LicenseRef-QORVO-2
 *
 */
#include "anticollision.h"

#include "qthread.h"
#include "qmalloc.h"
#include "qlog.h"
// #include "ble.h"
#include "deca_error.h"
#include "qplatform.h"
#include "llhw.h"
#include "uwbmac/uwbmac.h"
#include "persistent_time.h"
#include "uwbmac/fira_helper.h"
#include "quwbs/fbs/defs.h"
#include "nrfx_wdt.h"

#include <stdio.h>


// 1. DEFINIÇÕES DE SEGURANÇA E STACK
#define RANGING_TASK_STACK_SIZE 2048
#define CLEANUP_TASK_STACK_SIZE 1024  // Stack um pouco maior para segurança do QLOG
#define ALERT_DISTANCE_CM       3000 // Distância de alerta de colisão (30 metros)
#define MAX_VIZINHOS            10   // Capacidade da lista
#define VIZINHO_TIMEOUT_MS      15000
#define FAXINA_INTERVALO_MS     5000

// 2. DECLARAÇÃO DA ESTRUTURA E LISTA (Acessível via extern no ble.c)
typedef struct
{
    uint16_t endereco;
    uint32_t ultima_vez_visto;
    bool ativo;
} vizinho_t;

extern struct l1_config_platform_ops l1_config_platform_ops;

struct uwbmac_context *uwbmac_ctx = NULL;
struct fira_context fira_ctx;
uint32_t session_id = 0x12345678;
vizinho_t lista_vizinhos[MAX_VIZINHOS];

static enum qerr uwb_stack_init(struct uwbmac_context **uwbmac_ctx)
{
    enum qerr r;

    r = qplatform_init();
    if (r != QERR_SUCCESS)
        return r;

    r = l1_config_init(&l1_config_platform_ops);
    if (r != QERR_SUCCESS)
        goto deinit_qplatform;

    r = llhw_init();
    if (r != QERR_SUCCESS)
        goto deinit_l1_config;

    r = uwbmac_init(uwbmac_ctx);

    /* Success. */
    if (r == QERR_SUCCESS)
        goto exit;

    llhw_deinit();
deinit_l1_config:
    l1_config_deinit();
deinit_qplatform:
    qplatform_deinit();
exit:
    return r;
}

// --- FUNÇÃO AUXILIAR PARA O BLE.C ---
void anticollision_add_neighbor(uint16_t addr)
{
    uint32_t agora_ms = (uint32_t)(qtime_get_uptime_us() / 1000);
    int slot_vazio = -1;

    for (int i = 0; i < MAX_VIZINHOS; i++)
    {
        if (lista_vizinhos[i].ativo && lista_vizinhos[i].endereco == addr)
        {
            lista_vizinhos[i].ultima_vez_visto = agora_ms;
            return;
        }
        if (!lista_vizinhos[i].ativo && slot_vazio == -1)
            slot_vazio = i;
    }

    if (slot_vazio != -1)
    {
        struct controlee_parameters cp = {.address = addr};
        // Comando FiRa para adicionar o novo caminhão ao rádio dinamicamente
        int ret = fira_helper_add_controlee(&fira_ctx, session_id, &cp);
        if (ret >= 0)
        {
            lista_vizinhos[slot_vazio].endereco = addr;
            lista_vizinhos[slot_vazio].ultima_vez_visto = agora_ms;
            lista_vizinhos[slot_vazio].ativo = true;
            QLOGI("UWB: Vizinho 0x%04X adicionado dinamicamente", addr);
        }
    }
}

// Callback: Onde o caminhão recebe a distância dos outros
static void anticollision_ntf_cb(enum fira_helper_cb_type cb_type, const void *content, void *user_data)
{
    if (cb_type == FIRA_HELPER_CB_TYPE_TWR_RANGE_NTF)
    {
        const struct fira_twr_ranging_results *results = (const struct fira_twr_ranging_results *)content;

        for (int i = 0; i < results->n_measurements; i++)
        {
            int32_t dist_cm = results->measurements[i].distance_cm;
            uint16_t addr = results->measurements[i].short_addr;

            // Filtro básico para ignorar leituras inválidas
            if (dist_cm > 0 && dist_cm < 20000) // Até 200m
            {
                if (dist_cm < ALERT_DISTANCE_CM)
                {
                    QLOGW("!!! ALERTA DE COLISAO !!! Veiculo 0x%04X a %ld cm", addr, dist_cm);
                    // Aqui você acionaria o GPIO do seu Buzzer
                }
                else
                {
                    QLOGI("Monitorando: Veiculo 0x%04X a %ld cm", addr, dist_cm);
                }
            }
        }
    }
}

static void anticollision_task(void *arg)
{
   
    persistent_time_init(0);
    if (uwb_stack_init(&uwbmac_ctx) != QERR_SUCCESS)
    {
        QLOGE("Erro ao iniciar stack UWB");
        return;
    }

    if (fira_helper_open(&fira_ctx, uwbmac_ctx, anticollision_ntf_cb, "fbs", 0, NULL) != QERR_SUCCESS)
    {
        QLOGE("Erro ao abrir Fira Helper");
        return;
    }

    struct fbs_session_init_rsp rsp;
    fira_helper_init_session(&fira_ctx, session_id, QUWBS_FBS_SESSION_TYPE_RANGING_NO_IN_BAND_DATA, &rsp);
    fira_helper_set_session_device_type(&fira_ctx, session_id, QUWBS_FBS_DEVICE_TYPE_CONTROLLER);
    fira_helper_set_session_device_role(&fira_ctx, session_id, QUWBS_FBS_DEVICE_ROLE_INITIATOR);

    // ATENÇÃO: Habilitar modo Multi-Node para aceitar vários caminhões
    fira_helper_set_session_multi_node_mode(&fira_ctx, session_id, FBS_MULTI_NODE_MODE_ONE_TO_MANY);

    fira_helper_set_session_ranging_round_usage(&fira_ctx, session_id, 2);
    fira_helper_set_session_channel_number(&fira_ctx, session_id, 9);

    // Pegamos o ID dinâmico do chip (FICR) como endereço UWB
    uint16_t meu_id = (uint16_t)(NRF_FICR->DEVICEADDR[0] & 0xFFFF);
    fira_helper_set_session_short_address(&fira_ctx, session_id, meu_id);

    // REMOVIDO: target_addr estático. Agora o BLE adiciona via anticollision_add_neighbor.

    fira_helper_start_session(&fira_ctx, session_id);
    QLOGI("Sistema Anti-colisao Ativo. ID: 0x%04X", meu_id);

    while (1)
    {
        nrfx_wdt_feed();
        qtime_msleep_yield(100);
    }
}

static void anticollision_cleanup_task(void *arg)
{
    while (1)
    {
        QLOGI("Task cleanup ativa, dormindo por 5 segundos...");
      
        // Dorme por 5 segundos
        qtime_msleep_yield(FAXINA_INTERVALO_MS);

        uint32_t agora_ms = (uint32_t)(qtime_get_uptime_us() / 1000);

        for (int i = 0; i < MAX_VIZINHOS; i++)
        {
            if (lista_vizinhos[i].ativo)
            {
                // Calcula há quanto tempo não vemos este caminhão
                uint32_t tempo_sem_sinal = agora_ms - lista_vizinhos[i].ultima_vez_visto;

                if (tempo_sem_sinal > VIZINHO_TIMEOUT_MS)
                {
                    QLOGW("UWB: Caminhão 0x%04X sumiu. Removendo...", lista_vizinhos[i].endereco);

                    // 1. Comando físico para o rádio parar de medir esse cara
                    struct controlee_parameters cp;
                    cp.address = lista_vizinhos[i].endereco;
                    fira_helper_delete_controlee(&fira_ctx, session_id, &cp);

                    // 2. Limpa o slot na nossa lista para novos vizinhos
                    lista_vizinhos[i].ativo = false;
                    lista_vizinhos[i].endereco = 0;
                }
            }
        }
    }
}

/**
 * @brief Inicializa o sistema de anticolisão e a limpeza de vizinhos.
 * @return error_e status da inicialização.
 */
error_e anticollision_init(void)
{
    QLOGI("Iniciando UWB agora...");
    // Alocação segura com verificação de NULL
    void *ranging_stack = qmalloc(RANGING_TASK_STACK_SIZE);
    void *cleanup_stack = qmalloc(CLEANUP_TASK_STACK_SIZE);

    if (!ranging_stack || !cleanup_stack)
    {
        QLOGE("FALHA DE MEMORIA: Nao foi possivel alocar as Stacks!");
        return _ERR_Cannot_Alloc_Memory;
    }

    if (!qthread_create(anticollision_task, NULL, "AC_Ranging", ranging_stack, RANGING_TASK_STACK_SIZE, QTHREAD_PRIORITY_NORMAL))
        return _ERR_Create_Task_Bad;

    if (!qthread_create(anticollision_cleanup_task, NULL, "AC_Cleanup", cleanup_stack, CLEANUP_TASK_STACK_SIZE, QTHREAD_PRIORITY_LOW))
        return _ERR_Create_Task_Bad;

    return _NO_ERR;
}