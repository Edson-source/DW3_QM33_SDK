/**
 * @file      main.c
 *
 * @brief     FreeRTOS main
 *
 * @author    Qorvo Applications
 *
 * @copyright SPDX-FileCopyrightText: Copyright (c) 2024-2025 Qorvo US, Inc.
 *            SPDX-License-Identifier: LicenseRef-QORVO-2
 *
 */

#include "qos.h"
#include "HAL_error.h"
#include "HAL_cpu.h"
#include "anticollision.h"
#include "qlog.h"
#include "nrf_drv_clock.h"
#if CONFIG_LOG
#include "log_processing.h"
#endif

// extern void ble_init(char *gap_name);
// extern void ble_scan_start(void);

int main(void)
{
    handle_cpu_protect();

    ret_code_t ret = nrf_drv_clock_init();
    if ((ret != NRF_SUCCESS) && (ret != NRF_ERROR_MODULE_ALREADY_INITIALIZED))
    {
        error_handler(1, _ERR);
    }

    /* Start LFCLK for proper operation of the RTC. */
    nrfx_clock_lfclk_start();
    while (!nrfx_clock_lfclk_is_running())
        ;

#if CONFIG_LOG
    create_log_processing_task();
#endif

    // --- ADIÇÃO: GERAR NOME ÚNICO E LIGAR BLE ---
    char gap_name[16];
    uint16_t meu_id = (uint16_t)(NRF_FICR->DEVICEADDR[0] & 0xFFFF);
    sprintf(gap_name, "FROTA_%04X", meu_id);
    
    // Inicializa a pilha Bluetooth com o nome FROTA_XXXX
   //  ble_init(gap_name);
    
    // Inicia o scanner para procurar outros caminhões
   //  ble_scan_start(); 
    // --------------------------------------------
    
    error_e err = anticollision_init();
    if (err != _NO_ERR)
    {
        QLOGE("Falha fatal: Não foi possível inicializar o sistema de anticolisão");
        error_handler(1, err);
    }

    /* Start scheduler. */
    qos_start();

    /* This point should never be reached, as control is now taken by the scheduler. */
    while (1)
    {
    }

    return 0;
}
