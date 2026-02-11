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

#include "deca_error.h"
#include "qplatform.h"
#include "llhw.h"
#include "uwbmac/uwbmac.h"
#include "persistent_time.h"

#include "uwbmac/fira_helper.h" // Helper principal
#include "quwbs/fbs/defs.h"    // Onde moram as constantes que você enviou

#include <stdio.h>

#define ANTI_COLLISION_TASK_STACK_SIZE_BYTES 2048
#define ALERT_DISTANCE_CM 3000 // 30 metros

extern struct l1_config_platform_ops l1_config_platform_ops;

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
                } else {
                    QLOGI("Monitorando: Veiculo 0x%04X a %ld cm", addr, dist_cm);
                }
            }
        }
    }
}

static void anticollision_task(void *arg)
{
    struct uwbmac_context *uwbmac_ctx = NULL;
    struct fira_context fira_ctx;
    uint32_t session_id = 0x12345678; // ID da sua frota

    persistent_time_init(0);

    // 1. Inicializa a Stack UWB
    if (uwb_stack_init(&uwbmac_ctx) != QERR_SUCCESS) {
        QLOGE("Erro ao iniciar stack UWB");
        return;
    }

    // 2. Abre o Helper FiRa (usando o scheduler padrão 'fbs')
    if (fira_helper_open(&fira_ctx, uwbmac_ctx, anticollision_ntf_cb, "fbs", 0, NULL) != QERR_SUCCESS) {
        QLOGE("Erro ao abrir Fira Helper");
        return;
    }

    // 3. Inicializa a Sessão FiRa
    struct fbs_session_init_rsp rsp;
    fira_helper_init_session(&fira_ctx, session_id, QUWBS_FBS_SESSION_TYPE_RANGING_NO_IN_BAND_DATA, &rsp);

    // 4. Configuração do Caminhão (Controller + Initiator)
    fira_helper_set_session_device_type(&fira_ctx, session_id, QUWBS_FBS_DEVICE_TYPE_CONTROLLER);
    fira_helper_set_session_device_role(&fira_ctx, session_id, QUWBS_FBS_DEVICE_ROLE_INITIATOR);
    
    // DS-TWR (Double-Sided) é o valor 2 no FiRa padrão para máxima precisão
    fira_helper_set_session_ranging_round_usage(&fira_ctx, session_id, 2); 
    fira_helper_set_session_channel_number(&fira_ctx, session_id, 9);
    fira_helper_set_session_short_address(&fira_ctx, session_id, 0x0001); // ID deste caminhão

    // Define para quem perguntar a distância (Ex: caminhão 0x0002)
    uint16_t target_addr = 0x0002;
    fira_helper_set_session_destination_short_addresses(&fira_ctx, session_id, 1, &target_addr);

    // 5. Inicia o Ranging automático
    fira_helper_start_session(&fira_ctx, session_id);

    QLOGI("Sistema Anti-colisao Ativo - Caminhao 0x0001");

    while (1)
    {
        // O rádio trabalha em background via interrupção.
        // O loop principal pode ser usado para outras lógicas do caminhão.
        qtime_msleep_yield(1000);
    }
}

error_e anticollision_init(void)
{
    /* Create an anticollision task. */
    const size_t task_size = ANTI_COLLISION_TASK_STACK_SIZE_BYTES;
    static uint8_t *anticollision_task_stack;
    static struct qthread *anticollision_thread;

    anticollision_task_stack = qmalloc(task_size);
    if (anticollision_task_stack == NULL)
    {
        QLOGE("Failed to allocate memory for Anticollision task stack.");
        return _ERR_Cannot_Alloc_Memory;
    }

    anticollision_thread = qthread_create(anticollision_task, NULL, "Anticollision", anticollision_task_stack, ANTI_COLLISION_TASK_STACK_SIZE_BYTES, QTHREAD_PRIORITY_NORMAL);
    if (!anticollision_thread)
    {
        QLOGE("Failed to create Anticollision task.");
        qfree(anticollision_task_stack);
        return _ERR_Create_Task_Bad;
    }

    return _NO_ERR;
}

// static void uwb_stack_deinit(struct uwbmac_context *uwbmac_ctx)
// {
//     uwbmac_exit(uwbmac_ctx);
//     llhw_deinit();
//     l1_config_deinit();
//     qplatform_deinit();
// }