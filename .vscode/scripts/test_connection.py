# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo US, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2

"""
Live Monitor - Debug Version

Versão com mais logs para diagnosticar problemas.
"""

import sys
import serial
import argparse
from datetime import datetime
from pathlib import Path
import re

def list_ports():
    """List available COM ports"""
    try:
        import serial.tools.list_ports
        ports = []
        for port_info in serial.tools.list_ports.comports():
            ports.append(port_info.device)
        return ports
    except:
        return []

def test_connection(port, baudrate):
    """Test serial connection"""
    print(f"\n🔍 DIAGNOSTIC MODE")
    print("="*60)
    
    # List available ports
    available_ports = list_ports()
    print(f"\n📋 Available COM ports: {available_ports if available_ports else 'None found'}")
    
    # Check if port exists
    if port not in available_ports:
        print(f"❌ Port {port} NOT found!")
        print(f"   Available: {available_ports}")
        return False
    
    print(f"✓ Port {port} found")
    
    # Try to open
    print(f"\n🔌 Attempting to open {port} at {baudrate} baud...")
    
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"✓ Port opened successfully")
        print(f"   Is open: {ser.is_open}")
        print(f"   Timeout: {ser.timeout}")
        print(f"   Baudrate: {ser.baudrate}")
        
        # Check for data
        print(f"\n📡 Waiting for data (5 seconds)...")
        print("-"*60)
        
        start = datetime.now()
        line_count = 0
        
        while (datetime.now() - start).total_seconds() < 5:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').rstrip()
                    if line:
                        line_count += 1
                        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {line}")
                except:
                    pass
        
        ser.close()
        
        print("-"*60)
        print(f"\n✅ Received {line_count} lines in 5 seconds")
        
        if line_count == 0:
            print("⚠️  No data received!")
            print("   Check:")
            print("   - Hardware is powered on")
            print("   - Port is correct")
            print("   - Baudrate is correct")
            print("   - Data cable is connected")
            return False
        else:
            print("✅ Connection successful!")
            return True
            
    except serial.SerialException as e:
        print(f"❌ Error opening port: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Live Monitor - Debug Version")
    parser.add_argument("--port", type=str, default="COM3", help="COM port")
    parser.add_argument("--baudrate", type=int, default=115200, help="Baud rate")
    
    args = parser.parse_args()
    
    if test_connection(args.port, args.baudrate):
        print("\n" + "="*60)
        print("Você pode usar: python live_monitor.py --port {} --baudrate {}".format(
            args.port, args.baudrate))
        print("="*60)
    else:
        print("\n❌ Connection test failed")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
