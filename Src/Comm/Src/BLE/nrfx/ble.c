/**
 * @file    ble.c
 *
 * @brief   Implementation of the Qorvo Apple Nearby Interaction example
 *
 * @author    Qorvo Applications
 *
 * @copyright SPDX-FileCopyrightText: Copyright (c) 2024-2025 Qorvo US, Inc.
 * SPDX-License-Identifier: LicenseRef-QORVO-2
 */

#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include "sdk_config.h"
#include "nordic_common.h"
#include "app_error.h"
#include "nrf.h"
#include "ble.h"
#include "ble_hci.h"
#include "ble_srv_common.h"
#include "ble_advdata.h"
#include "ble_advertising.h"
#include "ble_gap.h"
#include "ble_qnis.h"
#include "ble_anis.h"
#include "ble_conn_params.h"
#include "ble_conn_state.h"
#include "peer_manager.h"
#include "peer_manager_handler.h"
#include "nrf_sdh.h"
#include "nrf_sdh_soc.h"
#include "nrf_sdh_ble.h"
#include "nrf_sdh_freertos.h"
#include "nrf_ble_gatt.h"
#include "nrf_ble_qwr.h"
#include "nrf_nvic.h"

#include "app_ble.h"
#include "boards.h"
#include "qlog.h"

#define APP_BLE_OBSERVER_PRIO 3 /**< Application's BLE observer priority. */
#define APP_BLE_CONN_CFG_TAG  1 /**< A tag identifying the SoftDevice BLE configuration. */

#define APP_ADV_INTERVAL_FAST 320  /**< 200 ms */
#define APP_ADV_INTERVAL_SLOW 1600 /**< 1s */
#define APP_ADV_DURATION      0    /**< Never stop. */

// --- ADIÇÃO: PARÂMETROS DE SCAN ---
#define SCAN_INTERVAL 0x00A0 /**< 100 ms */
#define SCAN_WINDOW   0x0050 /**< 50 ms */

// Buffer físico obrigatório para o SDK 17.1.0 armazenar pacotes recebidos
static uint8_t m_scan_buffer_data[BLE_GAP_SCAN_BUFFER_MIN];
static ble_data_t m_scan_buffer = {
    .p_data = m_scan_buffer_data,
    .len = BLE_GAP_SCAN_BUFFER_MIN};

static ble_gap_scan_params_t m_scan_params = {
    .active = 1,
    .interval = SCAN_INTERVAL,
    .window = SCAN_WINDOW,
    .filter_policy = BLE_GAP_SCAN_FP_ACCEPT_ALL,
    .timeout = BLE_GAP_SCAN_TIMEOUT_UNLIMITED,
    .extended = 0,
};
// ----------------------------------

#define MIN_CONN_INTERVAL              MSEC_TO_UNITS(25, UNIT_1_25_MS)
#define MAX_CONN_INTERVAL              MSEC_TO_UNITS(250, UNIT_1_25_MS)
#define SLAVE_LATENCY                  6
#define CONN_SUP_TIMEOUT               MSEC_TO_UNITS(16000, UNIT_10_MS)

#define FIRST_CONN_PARAMS_UPDATE_DELAY 5000
#define NEXT_CONN_PARAMS_UPDATE_DELAY  30000
#define MAX_CONN_PARAMS_UPDATE_COUNT   2

#define SEC_PARAM_BOND                 1
#define SEC_PARAM_MITM                 0
#define SEC_PARAM_LESC                 0
#define SEC_PARAM_KEYPRESS             0
#define SEC_PARAM_IO_CAPABILITIES      BLE_GAP_IO_CAPS_NONE
#define SEC_PARAM_OOB                  0
#define SEC_PARAM_MIN_KEY_SIZE         7
#define SEC_PARAM_MAX_KEY_SIZE         16

BLE_QNIS_DEF(m_qnis, NRF_SDH_BLE_TOTAL_LINK_COUNT);
BLE_ANIS_DEF(m_anis, NRF_SDH_BLE_TOTAL_LINK_COUNT);
NRF_BLE_GATT_DEF(m_gatt);                              /**< GATT module instance. */
NRF_BLE_QWRS_DEF(m_qwr, NRF_SDH_BLE_TOTAL_LINK_COUNT); /**< Context for the Queued Write module.*/
BLE_ADVERTISING_DEF(m_advertising);                    /**< Advertising module instance. */

static ble_uuid_t m_adv_uuids[] = {{BLE_UUID_QNIS_SERVICE, BLE_UUID_TYPE_VENDOR_BEGIN}};
static void advertising_start(void *parm);

static void pm_evt_handler(pm_evt_t const *p_evt)
{
    pm_handler_on_pm_evt(p_evt);
    pm_handler_flash_clean(p_evt);
}

static void qnis_data_handler(ble_qnis_evt_t *p_evt)
{
    if (p_evt->type == BLE_QNIS_EVT_RX_DATA)
    {
        handle_niq_data(p_evt->conn_handle, p_evt->params.rx_data.p_data, p_evt->params.rx_data.length);
    }
}

static void gap_params_init(char *gap_name)
{
    static ret_code_t err_code;
    ble_gap_conn_params_t gap_conn_params;
    ble_gap_conn_sec_mode_t sec_mode;
    BLE_GAP_CONN_SEC_MODE_SET_OPEN(&sec_mode);
    err_code = sd_ble_gap_device_name_set(&sec_mode, (const uint8_t *)gap_name, strlen(gap_name));
    APP_ERROR_CHECK(err_code);
    err_code = sd_ble_gap_appearance_set(BLE_APPEARANCE_GENERIC_TAG);
    APP_ERROR_CHECK(err_code);
    memset(&gap_conn_params, 0, sizeof(gap_conn_params));
    gap_conn_params.min_conn_interval = MIN_CONN_INTERVAL;
    gap_conn_params.max_conn_interval = MAX_CONN_INTERVAL;
    gap_conn_params.slave_latency = SLAVE_LATENCY;
    gap_conn_params.conn_sup_timeout = CONN_SUP_TIMEOUT;
    err_code = sd_ble_gap_ppcp_set(&gap_conn_params);
    APP_ERROR_CHECK(err_code);
}

static void gatt_init(void)
{
    ret_code_t err_code = nrf_ble_gatt_init(&m_gatt, NULL);
    APP_ERROR_CHECK(err_code);
}

static void nrf_qwr_error_handler(uint32_t nrf_error)
{
    APP_ERROR_HANDLER(nrf_error);
}

static void services_init(void)
{
    ret_code_t err_code;
    ble_qnis_init_t qnis_init;
    nrf_ble_qwr_init_t qwr_init = {0};
    qwr_init.error_handler = nrf_qwr_error_handler;
    for (uint32_t i = 0; i < NRF_SDH_BLE_TOTAL_LINK_COUNT; i++)
    {
        err_code = nrf_ble_qwr_init(&m_qwr[i], &qwr_init);
        APP_ERROR_CHECK(err_code);
    }
    memset(&qnis_init, 0, sizeof(qnis_init));
    qnis_init.data_handler = qnis_data_handler;
    err_code = ble_qnis_init(&m_qnis, &qnis_init);
    APP_ERROR_CHECK(err_code);
    err_code = ble_anis_init(&m_anis);
    APP_ERROR_CHECK(err_code);
}

static void peer_manager_init(void)
{
    ble_gap_sec_params_t sec_param;
    ret_code_t err_code;
    err_code = pm_init();
    APP_ERROR_CHECK(err_code);
    memset(&sec_param, 0, sizeof(ble_gap_sec_params_t));
    sec_param.bond = SEC_PARAM_BOND;
    sec_param.mitm = SEC_PARAM_MITM;
    sec_param.lesc = SEC_PARAM_LESC;
    sec_param.keypress = SEC_PARAM_KEYPRESS;
    sec_param.io_caps = SEC_PARAM_IO_CAPABILITIES;
    sec_param.oob = SEC_PARAM_OOB;
    sec_param.min_key_size = SEC_PARAM_MIN_KEY_SIZE;
    sec_param.max_key_size = SEC_PARAM_MAX_KEY_SIZE;
    sec_param.kdist_own.enc = 1;
    sec_param.kdist_own.id = 1;
    sec_param.kdist_peer.enc = 1;
    sec_param.kdist_peer.id = 1;
    err_code = pm_sec_params_set(&sec_param);
    APP_ERROR_CHECK(err_code);
    err_code = pm_register(pm_evt_handler);
    APP_ERROR_CHECK(err_code);
}

static void on_conn_params_evt(ble_conn_params_evt_t *p_evt)
{
    if (p_evt->evt_type == BLE_CONN_PARAMS_EVT_FAILED)
    {
        sd_ble_gap_disconnect(p_evt->conn_handle, BLE_HCI_CONN_INTERVAL_UNACCEPTABLE);
    }
}

static void conn_params_init(void)
{
    ret_code_t err_code;
    ble_conn_params_init_t cp_init;
    memset(&cp_init, 0, sizeof(cp_init));
    cp_init.p_conn_params = NULL;
    cp_init.first_conn_params_update_delay = FIRST_CONN_PARAMS_UPDATE_DELAY;
    cp_init.next_conn_params_update_delay = NEXT_CONN_PARAMS_UPDATE_DELAY;
    cp_init.max_conn_params_update_count = MAX_CONN_PARAMS_UPDATE_COUNT;
    cp_init.start_on_notify_cccd_handle = BLE_GATT_HANDLE_INVALID;
    cp_init.disconnect_on_fail = false;
    cp_init.evt_handler = on_conn_params_evt;
    cp_init.error_handler = APP_ERROR_HANDLER;
    err_code = ble_conn_params_init(&cp_init);
    APP_ERROR_CHECK(err_code);
}

static void on_adv_evt(ble_adv_evt_t ble_adv_evt)
{
    switch (ble_adv_evt)
    {
        case BLE_ADV_EVT_IDLE:
            advertising_start(NULL);
            break;
        default:
            break;
    }
}

/**
 * @brief Adição da lógica de tratamento de eventos Bluetooth
 */
static void ble_evt_handler(ble_evt_t const *p_ble_evt, void *p_context)
{
    uint32_t err_code;
    ble_gap_evt_t const *p_gap_evt = &p_ble_evt->evt.gap_evt;

    switch (p_ble_evt->header.evt_id)
    {
        case BLE_GAP_EVT_CONNECTED:
            ble_evt_connected_handler(p_gap_evt->conn_handle);
            for (uint32_t i = 0; i < NRF_SDH_BLE_PERIPHERAL_LINK_COUNT; i++)
            {
                if (m_qwr[i].conn_handle == BLE_CONN_HANDLE_INVALID)
                {
                    err_code = nrf_ble_qwr_conn_handle_assign(&m_qwr[i], p_gap_evt->conn_handle);
                    APP_ERROR_CHECK(err_code);
                    break;
                }
            }
            break;

        case BLE_GAP_EVT_DISCONNECTED:
            ble_evt_disconnected_handler(p_gap_evt->conn_handle);
            advertising_start(NULL);
            break;

        // --- ADIÇÃO: QUANDO UM CAMINHÃO É DESCOBERTO ---
        case BLE_GAP_EVT_ADV_REPORT:
        {
            const ble_gap_evt_adv_report_t *p_adv_report = &p_gap_evt->params.adv_report;
            uint16_t offset = 0;
            char discovered_name[32] = {0};

            // Busca o nome completo (AD_TYPE 0x09) no pacote recebido
            uint16_t name_len = ble_advdata_search(p_adv_report->data.p_data, p_adv_report->data.len, &offset, 0x09);

            if (name_len > 0)
            {
                memcpy(discovered_name, &p_adv_report->data.p_data[offset], (name_len < 31 ? name_len : 31));

                // Se o nome for da nossa frota, extraímos o ID
                if (strstr(discovered_name, "FROTA_") != NULL)
                {
                    uint16_t id_vizinho = (uint16_t)strtol(discovered_name + 6, NULL, 16);
                    extern uint16_t meu_id_dinamico;

                    if (id_vizinho < meu_id_dinamico)
                    {
                        extern void anticollision_add_neighbor(uint16_t addr);
                        anticollision_add_neighbor(id_vizinho);
                    }
                }
            }
            // Reinicia o scan (passando o buffer obrigatório para o SDK 17.x)
            sd_ble_gap_scan_start(NULL, &m_scan_buffer);
            break;
        }

        case BLE_GAP_EVT_PHY_UPDATE_REQUEST:
        {
            ble_gap_phys_t const phys = {.rx_phys = BLE_GAP_PHY_AUTO, .tx_phys = BLE_GAP_PHY_AUTO};
            sd_ble_gap_phy_update(p_gap_evt->conn_handle, &phys);
            break;
        }

        default:
            break;
    }
}

static void ble_stack_init(void)
{
    ret_code_t err_code;
    nrf_sdh_disable_request();
    err_code = nrf_sdh_enable_request();
    APP_ERROR_CHECK(err_code);
    uint32_t ram_start = 0;
    err_code = nrf_sdh_ble_default_cfg_set(APP_BLE_CONN_CFG_TAG, &ram_start);
    APP_ERROR_CHECK(err_code);
    err_code = nrf_sdh_ble_enable(&ram_start);
    APP_ERROR_CHECK(err_code);
    NRF_SDH_BLE_OBSERVER(m_ble_observer, APP_BLE_OBSERVER_PRIO, ble_evt_handler, NULL);
}

static void advertising_init(void)
{
    ret_code_t err_code;
    ble_advertising_init_t init;
    memset(&init, 0, sizeof(init));
    init.advdata.name_type = BLE_ADVDATA_FULL_NAME;
    init.advdata.flags = BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE;
    init.config.ble_adv_fast_enabled = true;
    init.config.ble_adv_fast_interval = APP_ADV_INTERVAL_FAST;
    init.config.ble_adv_slow_enabled = true;
    init.config.ble_adv_slow_interval = APP_ADV_INTERVAL_SLOW;
    init.evt_handler = on_adv_evt;
    err_code = ble_advertising_init(&m_advertising, &init);
    APP_ERROR_CHECK(err_code);
    ble_advertising_conn_cfg_tag_set(&m_advertising, APP_BLE_CONN_CFG_TAG);
}

static void advertising_start(void *parm)
{
    sd_ble_advertising_start(&m_advertising, BLE_ADV_MODE_FAST);
}

void ble_init(char *gap_name)
{
    ble_stack_init();
    gap_params_init(gap_name);
    gatt_init();
    services_init();
    peer_manager_init();
    advertising_init();
    conn_params_init();
    nrf_sdh_freertos_init(advertising_start, NULL);
}

// --- ADIÇÃO: FUNÇÃO PARA INICIAR O SCANNER EXTERNAMENTE ---
void ble_scan_start(void)
{
    ret_code_t err_code = sd_ble_gap_scan_start(&m_scan_params, &m_scan_buffer);
    APP_ERROR_CHECK(err_code);
    QLOGI("Scanner de frota iniciado!");
}