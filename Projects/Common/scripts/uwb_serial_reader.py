#!/usr/bin/env python3
"""
UWB Serial Reader - Real-time distance visualization for DWM3001CDK

Features:
- Listens on serial port for FiRa SESSION_INFO_NTF messages
- Extracts and displays: distance, MAC address, RSSI, azimuth, elevation
- Shows session info (sequence_number, block_index)
- Color-coded console output (requires colorama)
- Optional CSV export for data analysis
- Real-time statistics (min/max/avg distance)

Usage:
  python uwb_serial_reader.py --port COM3 --baud 115200 --csv results.csv --stats

Expected firmware output format:
  SESSION_INFO_NTF: {session_handle=0, sequence_number=0, block_index=0, n_measurements=1
   [mac_address=0xabcd, status="Success", distance[cm]=150, RSSI[dBm]=-80.5]
  }

Dependencies:
  pip install pyserial colorama

"""
import argparse
import re
import sys
import time
import json
from datetime import datetime
from collections import deque

try:
    import serial
except Exception as e:
    print("Missing dependency 'pyserial'. Install with: pip install pyserial")
    raise

# Optional: colorama for nice console colors (fallback to plain text)
try:
    from colorama import init, Fore, Back, Style
    HAS_COLOR = True
    init(autoreset=True)
except ImportError:
    HAS_COLOR = False
    class Fore:
        GREEN = ""
        CYAN = ""
        YELLOW = ""
        RED = ""
        WHITE = ""
    class Back:
        BLACK = ""
    class Style:
        BRIGHT = ""
        RESET_ALL = ""

# Regex patterns for parsing FiRa SESSION_INFO_NTF
# NOTE: DWM3001CDK does NOT support AoA (Angle of Arrival) - need QM33120WDK for that
PAT_SESSION_START = re.compile(r"SESSION_INFO_NTF:\s*\{([^}]+)")
PAT_DISTANCE = re.compile(r"distance\[cm\]=\s*(-?\d+)")
PAT_MAC = re.compile(r"mac_address=(0x[0-9a-fA-F]+)")
PAT_RSSI = re.compile(r"RSSI\[dBm\]=\s*(-?\d+\.?\d*)")
PAT_STATUS = re.compile(r'status="([^"]+)"')


def parse_args():
    p = argparse.ArgumentParser(
        description="Real-time UWB distance visualization from DWM3001CDK CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Listen on COM3 and display distances
  python uwb_serial_reader.py --port COM3

  # Save to CSV and show statistics every 10 measurements
  python uwb_serial_reader.py --port COM3 --csv data.csv --stats

  # Different baud rate
  python uwb_serial_reader.py --port /dev/ttyACM0 --baud 921600

  # Filter only distances > 200cm
  python uwb_serial_reader.py --port COM3 --min-distance 200
        """
    )
    p.add_argument("--port", "-p", required=True, help="Serial port (COM3, /dev/ttyACM0, etc.)")
    p.add_argument("--baud", "-b", type=int, default=115200, help="Baud rate (default: 115200)")
    p.add_argument("--csv", help="CSV file to save measurements (append mode)")
    p.add_argument("--stats", action="store_true", help="Print statistics every N measurements")
    p.add_argument("--stats-interval", type=int, default=10, help="Stats interval (default: 10 measurements)")
    p.add_argument("--min-distance", type=float, help="Only show distances >= this value")
    p.add_argument("--max-distance", type=float, help="Only show distances <= this value")
    p.add_argument("--timeout", type=float, default=1.0, help="Serial timeout in seconds")
    return p.parse_args()


def main():
    args = parse_args()

    # Open serial port
    ser = None
    try:
        ser = serial.Serial(args.port, args.baud, timeout=args.timeout)
        print(f"{Fore.GREEN}✓ Connected to {args.port} @ {args.baud}bps{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}✗ Failed to open {args.port}: {e}{Style.RESET_ALL}")
        sys.exit(1)

    # Setup CSV file if requested
    csv_fp = None
    csv_writer = None
    if args.csv:
        try:
            csv_fp = open(args.csv, "a", newline="", encoding="utf-8")
            import csv as _csv
            csv_writer = _csv.writer(csv_fp)
            # Write header if file is empty
            if csv_fp.tell() == 0:
                csv_writer.writerow(["timestamp", "distance_cm", "mac_address", "rssi_dbm", "status", "raw_line"])
            print(f"{Fore.GREEN}✓ CSV output: {args.csv}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}⚠ Could not open CSV file: {e}{Style.RESET_ALL}")
            csv_fp = None
            csv_writer = None

    # Statistics tracker
    stats = RollingStats(window_size=100)
    
    print(f"{Fore.CYAN}Listening for FiRa SESSION_INFO_NTF messages...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Press Ctrl+C to stop.\n{Style.RESET_ALL}")

    try:
        buffer = ""  # Buffer for incomplete lines
        while True:
            try:
                raw = ser.read(1)
            except Exception as e:
                print(f"{Fore.RED}Serial read error: {e}{Style.RESET_ALL}")
                time.sleep(0.5)
                continue

            if not raw:
                continue

            # Decode character
            try:
                char = raw.decode('utf-8', errors='ignore')
            except:
                continue

            buffer += char

            # Process complete lines
            if '\n' in buffer:
                lines = buffer.split('\n')
                buffer = lines[-1]  # Keep incomplete line in buffer
                
                for line in lines[:-1]:
                    line = line.strip()
                    if not line:
                        continue

                    # Look for distance measurements in this line
                    if "distance[cm]=" in line or "SESSION_INFO_NTF" in line:
                        data = parse_measurement(line)
                        
                        if "distance" in data:
                            distance = data["distance"]
                            
                            # Apply filters
                            if args.min_distance and distance < args.min_distance:
                                continue
                            if args.max_distance and distance > args.max_distance:
                                continue
                            
                            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            dist_str = str(distance)
                            
                            # Print formatted output
                            output = format_measurement(ts, data)
                            print(output)
                            
                            # Add to statistics
                            stats.add(distance)
                            
                            # Write to CSV
                            if csv_writer:
                                csv_writer.writerow([
                                    ts,
                                    distance,
                                    data.get("mac", ""),
                                    data.get("rssi", ""),
                                    data.get("status", ""),
                                    line
                                ])
                                csv_fp.flush()
                            
                            # Print stats periodically
                            if args.stats and stats.count % args.stats_interval == 0:
                                stats.print_stats()

    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Stopped by user{Style.RESET_ALL}")
        if args.stats:
            stats.print_stats()
    except Exception as e:
        print(f"{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
    finally:
        if ser and ser.is_open:
            ser.close()
            print(f"{Fore.GREEN}Serial port closed{Style.RESET_ALL}")
        if csv_fp:
            csv_fp.close()
            print(f"{Fore.GREEN}CSV file saved{Style.RESET_ALL}")


class RollingStats:
    """Track rolling statistics for distance measurements"""
    def __init__(self, window_size=100):
        self.window = deque(maxlen=window_size)
        self.count = 0
    
    def add(self, value):
        self.window.append(value)
        self.count += 1
    
    def print_stats(self):
        if not self.window:
            return
        
        distances = list(self.window)
        min_d = min(distances)
        max_d = max(distances)
        avg_d = sum(distances) / len(distances)
        
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"STATISTICS (last {len(distances)} measurements):")
        print(f"{'='*60}{Style.RESET_ALL}")
        print(f"  Total measurements: {self.count}")
        print(f"  Min distance:       {min_d:6.1f} cm")
        print(f"  Max distance:       {max_d:6.1f} cm")
        print(f"  Average distance:   {avg_d:6.1f} cm")
        print(f"  Last measurement:   {distances[-1]:6.1f} cm")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")


def parse_measurement(line):
    """Extract distance, MAC, RSSI, and other data from a serial line"""
    data = {}
    
    # Extract distance
    m = PAT_DISTANCE.search(line)
    if m:
        data["distance"] = int(m.group(1))
    
    # Extract MAC address
    m = PAT_MAC.search(line)
    if m:
        data["mac"] = m.group(1)
    
    # Extract RSSI
    m = PAT_RSSI.search(line)
    if m:
        data["rssi"] = float(m.group(1))
    
    # Extract status
    m = PAT_STATUS.search(line)
    if m:
        data["status"] = m.group(1)
    
    # NOTE: DWM3001CDK does NOT support AoA - remove AOA parsing
    # For AoA support, you need QM33120WDK with antenna array
    
    return data


def format_measurement(timestamp, data):
    """Format measurement data for console display"""
    distance = data.get("distance", "N/A")
    mac = data.get("mac", "????")
    rssi = data.get("rssi", "N/A")
    status = data.get("status", "N/A")
    
    # Color code by distance
    if isinstance(distance, (int, float)):
        if distance < 100:
            color = Fore.RED  # Close
        elif distance < 300:
            color = Fore.GREEN  # Good
        else:
            color = Fore.YELLOW  # Far
    else:
        color = Fore.WHITE
    
    # Build output string (DWM3001CDK: distance + RSSI only)
    parts = [
        f"{Fore.WHITE}{timestamp}{Style.RESET_ALL}",
        f"{color}{distance:6} cm{Style.RESET_ALL}",
        f"[{mac}]",
        f"RSSI={rssi:6}dBm" if isinstance(rssi, (int, float)) else f"RSSI={rssi}",
    ]
    
    # NOTE: DWM3001CDK does NOT support AoA (Angle of Arrival)
    # For Azimuth/Elevation angles, you need QM33120WDK with antenna array
    
    output = " | ".join(parts)
    return output


if __name__ == '__main__':
    main()
