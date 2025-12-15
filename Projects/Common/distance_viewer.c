/**
 * @file      distance_viewer.c
 * @brief     Real-time distance viewer for UWB ranging (DWM3001CDK)
 * 
 * NOTE: DWM3001CDK measures DISTANCE and RSSI only
 * For Angle of Arrival (AoA), you need QM33120WDK with antenna array
 * 
 * Usage:
 *  1. Include this file in your project
 *  2. In your main.c or app task, call distance_viewer_print() to display measurements
 *  3. Compile and run your firmware
 * 
 * Example in fira_app.c (around line 810):
 * 
 *  if (rm->status == 0) {
 *      distance_viewer_print(rm->short_addr, (int)rm->distance_cm, (int)rm->rssi);
 *  }
 * 
 */

#include <stdio.h>
#include <stdint.h>
#include "deca_dbg.h"  // Uses existing diag_printf infrastructure

/**
 * @brief Print distance measurement to serial terminal
 * 
 * Displays: [MAC address] Distance [cm] | RSSI [dBm]
 * 
 * @param mac_addr  : MAC address (2 bytes)
 * @param distance  : Distance in centimeters
 * @param rssi      : RSSI in dBm (optional, set to 0 if not available)
 */
void distance_viewer_print(uint16_t mac_addr, int distance, int rssi)
{
    // Format: DIST: MAC=0xABCD Distance=150cm RSSI=-80dBm
    diag_printf("DIST: MAC=0x%04X Distance=%3dcm RSSI=%3ddBm\r\n", 
                mac_addr, distance, rssi);
}

/**
 * @brief Print distance with additional debug info
 * 
 * @param mac_addr   : MAC address
 * @param distance   : Distance in centimeters
 * @param rssi       : RSSI in dBm
 * @param seq_num    : Sequence number for tracking
 */
void distance_viewer_print_detailed(uint16_t mac_addr, int distance, 
                                    int rssi, uint32_t seq_num)
{
    diag_printf("[%04u] MAC=0x%04X Dist=%3dcm RSSI=%3ddBm\r\n", 
                seq_num, mac_addr, distance, rssi);
}

/**
 * @brief Simple continuous monitoring (call from a task)
 * 
 * This is a minimal example showing how to format and print distance data.
 * In practice, you'd integrate this into your FiRa app callback.
 * 
 * NOTE: DWM3001CDK does NOT have AoA - only distance and RSSI
 */
static int viewer_measurement_count = 0;

void distance_viewer_process_measurement(struct fira_session_info_ntf *results)
{
    if (!results || results->n_measurements == 0) {
        return;
    }

    struct fira_twr_measurements *rm = (struct fira_twr_measurements *)&results->measurements[0];
    
    if (rm->status != 0) {
        diag_printf("DIST: Status Error (%d) for MAC=0x%04X\r\n", rm->status, rm->short_addr);
        return;
    }

    viewer_measurement_count++;
    
    // Print basic measurement (distance + RSSI)
    diag_printf("[%04d] MAC=0x%04X: %3dcm ", 
                viewer_measurement_count, rm->short_addr, (int)rm->distance_cm);
    
    // Add RSSI if available
    if (rm->rssi) {
        int rssi_dbm = (int)(rm->rssi / 128.0);  // Convert from Q7 format
        diag_printf("| RSSI=%3ddBm", rssi_dbm);
    }
    
    diag_printf("\r\n");
}

/**
 * @brief Reset measurement counter
 */
void distance_viewer_reset(void)
{
    viewer_measurement_count = 0;
    diag_printf("Distance Viewer: Counter reset\r\n");
}

/**
 * @brief Print header line for monitoring
 * 
 * Call this at startup to show what's being monitored
 */
void distance_viewer_print_header(void)
{
    diag_printf("\r\n");
    diag_printf("===========================================\r\n");
    diag_printf("  UWB Ranging Monitor (DWM3001CDK)\r\n");
    diag_printf("  Supported: Distance + RSSI\r\n");
    diag_printf("  Format: [Seq] MAC=0xXXXX: Distance | RSSI\r\n");
    diag_printf("===========================================\r\n");
    diag_printf("  Note: For Angle of Arrival (AoA),\r\n");
    diag_printf("        upgrade to QM33120WDK\r\n");
    diag_printf("===========================================\r\n");
    diag_printf("\r\n");
}
