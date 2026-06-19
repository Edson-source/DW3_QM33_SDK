# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo US, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2

"""
Live UWB Measurement Monitor with Silent Capture

Real-time monitoring of serial port with ability to capture 5-second windows.
Results saved to HTML report at the end.

Features:
- Real-time display of measurements from port COM
- Silent capture: Press ',' to record 5-second windows (25 blocks)
- Multiple captures per session
- HTML report with all analyses
- Clean, minimalist terminal display

Usage:
    python live_monitor.py --port COM3
    python live_monitor.py --port COM3 --baudrate 921600

Controls:
    ','  (comma)  : Capture 5-second window (silent)
    's'           : Save and generate HTML report
    'q' / ESC     : Exit and save report
"""

import sys
import os
import serial
import threading
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import re

try:
    from pynput import keyboard
except ImportError:
    print("📦 Installing pynput...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pynput", "-q"])
    from pynput import keyboard

try:
    import numpy as np
except ImportError:
    print("📦 Installing numpy...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy", "-q"])
    import numpy as np


class LiveMonitor:
    """Real-time serial monitor with capture windows"""
    
    def __init__(self, port, baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        
        self.all_measurements = []
        self.current_measurements = []
        self.captures = []
        self.capture_active = False
        self.exit_flag = False
        
        self.start_time = None
        self.session_start = datetime.now()
        self.line_count = 0
        
        # Buffer for multi-line parsing
        self.line_buffer = ""
    
    def open_port(self):
        """Open serial port"""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"✓ Connected to {self.port} at {self.baudrate} baud")
            return True
        except serial.SerialException as e:
            print(f"❌ Failed to open {self.port}: {str(e)}")
            return False
    
    def _extract_distance(self, data):
        """Extract distance value from measurement string"""
        patterns = [
            r'distance\[cm\]=([\d.]+)',  # Captura em cm
            r'Distance:\s*([\d.]+)\s*m', # Captura em metros
            r'X=([\d.]+)',
            r'(\d+),(-?\d+),\d+,OK'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, data)
            if match:
                val = float(match.group(1))
                
                # Se o padrão lido for explicitamente em Metros, converte para CM
                if pattern == r'Distance:\s*([\d.]+)\s*m':
                    val = val * 100.0
                
                # Retorna o valor direto em Centímetros (Removida a divisão!)
                return val
        return None

    def _extract_media(self, data):
        """Extract media (average) distance"""
        match = re.search(r'media\[cm\]=([\d.]+)', data)
        if match:
            # Retorna o valor direto (Removida a divisão por 100.0!)
            return float(match.group(1)) 
        return None
    
    def _extract_rssi(self, data):
        """Extract RSSI value"""
        patterns = [
            r'RSSI\[dBm\]=([-?\d.]+)',  # NEW: RSSI[dBm]=-59.5
            r'RSSI:\s*(-?\d+)\s*dBm',
            r'Y=([\d.]+)',
            r'(\d+),(-?\d+),\d+,OK'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, data)
            if match:
                return float(match.group(1) if pattern != r'(\d+),(-?\d+),\d+,OK' else match.group(2))
        return None
    
    def _extract_per(self, data):
        """Extract Packet Error Rate"""
        match = re.search(r'PER=([\d.]+)', data)
        return float(match.group(1)) if match else None
    
    def _extract_block_index(self, data):
        """Extract block index number"""
        match = re.search(r'block_index=(\d+)', data)
        return int(match.group(1)) if match else None
    
    def print_header(self):
        """Print clean header"""
        print("\n" + "="*80)
        print("🔴 LIVE MEASUREMENT MONITOR - DWM3001CDK")
        print("="*80)
        print(f"Port: {self.port} | Baudrate: {self.baudrate} | Session: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-"*80)
        print("Controls:  ',' = Capture Window  |  's' = Save Report  |  'q/ESC' = Exit")
        print("="*80 + "\n")
    
    def on_key_press(self, key):
        """Handle keyboard input"""
        try:
            if key == keyboard.Key.esc or str(key) == "'q'":
                self.exit_flag = True
                print("\n\n⏹️  Stopping monitor...")
            elif str(key) == "','":
                if not self.capture_active:
                    self.capture_active = True
        except AttributeError:
            pass
    
    def capture_window(self):
        """Capture 5 seconds of measurements"""
        window_measurements = []
        capture_start = time.time()
        
        while time.time() - capture_start < 5.0:
            if self.all_measurements:
                # Get measurements added during this window
                if len(self.all_measurements) > len(window_measurements):
                    window_measurements = self.all_measurements[-25:]  # Last 25 blocks
            time.sleep(0.05)
        
        if window_measurements:
            capture_data = {
                'timestamp': datetime.now(),
                'measurements': window_measurements.copy()
            }
            self.captures.append(capture_data)
            
            # Display result
            distances = [m['distance'] for m in window_measurements if m['distance'] is not None]
            if distances:
                stats = self._calculate_stats(distances)
                print(f"\n📊 CAPTURED (Window #{len(self.captures)}): " +
                      f"Min={stats['min']:.2f}m | Max={stats['max']:.2f}m | " +
                      f"σ={stats['std']:.2f}cm\n")
        
        self.capture_active = False
    
    def _create_calculation_details(self, stats):
        """Create detailed calculation explanation for modal"""
        values = stats['values']
        sorted_values = np.sort(values)
        n = len(values)
        
        # Minimum explanation
        min_detail = f"""
        <p><strong>Mínimo:</strong> O menor valor encontrado nos {n} blocos coletados.</p>
        <div class="formula">
        min = {stats['min']:.2f} cm (Valor #{sorted_values.tolist().index(stats['min']) + 1})
        </div>
        <p>Este é o melhor resultado que você conseguiu durante esta janela.</p>
        """
        
        # Maximum explanation
        max_detail = f"""
        <p><strong>Máximo:</strong> O maior valor encontrado nos {n} blocos coletados.</p>
        <div class="formula">
        max = {stats['max']:.2f} cm (Valor #{sorted_values.tolist().index(stats['max']) + 1})
        </div>
        <p>Este é o pior resultado que você conseguiu durante esta janela.</p>
        """
        
        # Mean explanation
        mean_detail = f"""
        <p><strong>Média (Mean):</strong> A soma de todos os valores dividida pelo número de amostras.</p>
        <div class="formula">
        Σ(valores) / N = ({' + '.join([f'{v:.2f}' for v in values[:5]])}{' + ...' if n > 5 else ''}) / {n}<br/>
        = {np.sum(values):.2f} / {n}<br/>
        = {stats['mean']:.2f} cm
        </div>
        <p>Representa o valor "típico" ou central da sua medição.</p>
        """
        
        # Std Dev explanation
        std_detail = f"""
        <p><strong>Desvio Padrão (σ):</strong> Mede quanto os valores variam em relação à média.</p>
        <div class="formula">
        σ = √(Σ(xi - média)² / (N-1))
        </div>
        <p><strong>Passo 1:</strong> Calcular (valor - média)² para cada um:</p>
        """
        
        for i, v in enumerate(values[:5]):
            diff = v - stats['mean']
            std_detail += f"<div class='formula'>({{:.2f}} - {{:.2f}})² = {{:.4f}}</div>".format(v, stats['mean'], diff**2)
        
        if n > 5:
            std_detail += f"<p>... e mais {n-5} valores</p>"
        
        std_detail += f"""
        <p><strong>Passo 2:</strong> Somar todos os quadrados: {np.sum((values - stats['mean'])**2):.4f}</p>
        <p><strong>Passo 3:</strong> Dividir por (N-1) = {n-1}: {np.sum((values - stats['mean'])**2) / (n-1):.4f}</p>
        <p><strong>Passo 4:</strong> Tirar raiz quadrada: {stats['std']:.4f} cm = <strong>{stats['std']*10:.2f} mm</strong></p>
        <p style="color: #667eea; font-weight: bold;">Interpretação: Cerca de 68% dos valores estão entre {{:.2f}}±{{:.2f}} = {{:.2f}} a {{:.2f}} cm</p>
        """.format(stats['mean'] - stats['std'], stats['std'], 
                  stats['mean'] - stats['std'], stats['mean'] + stats['std'])
        
        # Median explanation
        median_detail = f"""
        <p><strong>Mediana:</strong> O valor do meio quando todos estão ordenados.</p>
        <p>Valores ordenados: {', '.join([f'{v:.2f}' for v in sorted_values])}</p>
        <div class="formula">
        Mediana = {stats['median']:.2f} cm
        </div>
        <p>50% dos valores estão abaixo da mediana, 50% acima. É resistente a valores extremos.</p>
        """
        
        # Range explanation
        range_val = stats['max'] - stats['min']
        range_detail = f"""
        <p><strong>Amplitude (Range):</strong> A diferença entre o máximo e o mínimo.</p>
        <div class="formula">
        Range = máximo - mínimo = {stats['max']:.2f} - {stats['min']:.2f} = {range_val:.2f} cm
        </div>
        <p>Mostra a "largura" dos seus dados. Quanto menor, mais estável a medição.</p>
        """
        
        return {
            'min': min_detail,
            'max': max_detail,
            'mean': mean_detail,
            'std': std_detail,
            'median': median_detail,
            'range': range_detail
        }
    
    def _calculate_stats(self, values):
        """Calculate statistics with detailed breakdown"""
        arr = np.array(values)
        mean_val = np.mean(arr)
        
        # Desvio padrão usando N-1 (amostra, não população)
        std_val = np.std(arr, ddof=1) if len(arr) > 1 else 0
        
        return {
            'min': np.min(arr),
            'max': np.max(arr),
            'mean': mean_val,
            'std': std_val,
            'median': np.median(arr),
            'count': len(values),
            'values': arr  # Guardar valores para mostrar cálculo
        }
    
    def monitor(self):
        """Main monitoring loop"""
        if not self.open_port():
            return False
        
        self.print_header()
        self.start_time = time.time()
        
        # Setup keyboard listener
        listener = keyboard.Listener(on_press=self.on_key_press)
        listener.start()
        
        # Setup capture thread
        capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        capture_thread.start()
        
        print("🔍 DEBUG: Waiting for data from serial port...")
        debug_count = 0
        
        try:
            while not self.exit_flag:
                if self.ser.in_waiting > 0:
                    try:
                        line = self.ser.readline().decode('utf-8', errors='ignore').rstrip()
                        
                        # Accumulate lines in buffer
                        self.line_buffer += " " + line
                        
                        # Check if we have a complete measurement (ends with }])
                        if ']}' in self.line_buffer:
                            debug_count += 1
                            
                            # DEBUG: Show parsed section
                            if debug_count <= 5:
                                print(f"[DEBUG] Section {debug_count}: {self.line_buffer[:100]}...")
                            
                            # Parse the complete section
                            timestamp = datetime.now()
                            distance = self._extract_distance(self.line_buffer)
                            rssi = self._extract_rssi(self.line_buffer)
                            per = self._extract_per(self.line_buffer)
                            media = self._extract_media(self.line_buffer)
                            block_index = self._extract_block_index(self.line_buffer)
                            
                            if distance is not None:
                                self.line_count += 1
                                measurement = {
                                    'timestamp': timestamp,
                                    'distance': distance,
                                    'rssi': rssi,
                                    'per': per,
                                    'media': media,
                                    'block_index': block_index,
                                    'raw': self.line_buffer
                                }
                                self.all_measurements.append(measurement)
                                
                                # Calculate moving average (last 25 blocks = 5 seconds)
                                recent_distances = [m['distance'] for m in self.all_measurements[-25:] if m['distance'] is not None]
                                moving_avg = np.mean(recent_distances) if recent_distances else None
                                
                                # Display on screen with block number
                                ts = timestamp.strftime("%H:%M:%S.%f")[:-3]
                                block_str = f"Block #{block_index}" if block_index is not None else "Block: N/A"
                                rssi_str = f"RSSI: {rssi:6.1f} dBm" if rssi else "RSSI: N/A"
                                per_str = f"PER: {per:5.1f}%" if per is not None else ""
                                moving_avg_str = f"Avg5s: {moving_avg:.2f}cm" if moving_avg else ""
                                
                                print(f"[{ts}] {block_str:10s} | Dist: {distance:.2f}cm | {rssi_str} | {per_str:12s} | {moving_avg_str}")
                            elif debug_count <= 5:
                                print(f"[DEBUG] Could not parse distance from: {self.line_buffer[:80]}...")
                            
                            # Clear buffer for next measurement
                            self.line_buffer = ""
                    
                    except Exception as e:
                        if debug_count <= 5:
                            print(f"[DEBUG] Exception: {str(e)}")
                
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            self.exit_flag = True
        
        finally:
            listener.stop()
            if self.ser:
                self.ser.close()
            print("\n✓ Port closed")
        
        return True
    
    def _capture_loop(self):
        """Background thread for capturing windows"""
        while not self.exit_flag:
            if self.capture_active:
                self.capture_window()
            time.sleep(0.1)
    
    def generate_html_report(self):
        """Generate HTML report with all captures"""
        if not self.captures:
            print("⚠️  No captures recorded")
            return False
        
        output_file = Path(__file__).parent / f"monitor_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UWB Measurement Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; text-align: center; }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .content {{ padding: 40px; }}
        .capture {{ margin-bottom: 30px; padding: 20px; background: #f8f9fa; border-left: 4px solid #667eea; border-radius: 6px; }}
        .capture h3 {{ color: #667eea; margin-bottom: 15px; font-size: 1.3em; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-top: 15px; }}
        .stat-item {{ background: white; padding: 15px; border-radius: 4px; text-align: center; border: 1px solid #ddd; cursor: pointer; transition: all 0.3s ease; }}
        .stat-item:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3); border-color: #667eea; }}
        .stat-label {{ font-size: 0.9em; color: #666; text-transform: uppercase; margin-bottom: 5px; }}
        .stat-value {{ font-size: 1.4em; font-weight: bold; color: #667eea; }}
        .measurements {{ margin-top: 15px; max-height: 300px; overflow-y: auto; background: white; border: 1px solid #ddd; border-radius: 4px; padding: 10px; }}
        .measurement-row {{ padding: 5px; border-bottom: 1px solid #eee; font-family: monospace; font-size: 0.85em; }}
        .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #666; border-top: 1px solid #ddd; }}
        .modal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0, 0, 0, 0.5); }}
        .modal.show {{ display: flex; align-items: center; justify-content: center; }}
        .modal-content {{ background-color: white; padding: 30px; border-radius: 8px; max-width: 600px; max-height: 80vh; overflow-y: auto; box-shadow: 0 10px 40px rgba(0,0,0,0.3); }}
        .modal-header {{ font-size: 1.5em; font-weight: bold; color: #667eea; margin-bottom: 15px; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
        .modal-body {{ font-size: 0.95em; line-height: 1.8; }}
        .formula {{ background: #f8f9fa; padding: 15px; border-left: 4px solid #667eea; margin: 15px 0; font-family: monospace; font-size: 0.9em; }}
        .close-btn {{ float: right; font-size: 1.5em; font-weight: bold; cursor: pointer; color: #667eea; }}
        .close-btn:hover {{ color: #764ba2; }}
    </style>
    <script>
        let currentModal = null;
        
        function showModal(title, contentId) {{
            const modal = document.getElementById('infoModal');
            const sourceContent = document.getElementById(contentId);
            
            if (!modal || !sourceContent) {{
                console.error("Erro: Elemento do modal ou conteúdo não encontrado!");
                return;
            }}
            
            document.getElementById('modalTitle').innerText = title;
            document.getElementById('modalBody').innerHTML = sourceContent.innerHTML;
            modal.classList.add('show');
            currentModal = modal;
        }}
        
        function closeModal() {{
            if (currentModal) {{
                currentModal.classList.remove('show');
            }}
        }}
        
        window.onclick = function(event) {{
            const modal = document.getElementById('infoModal');
            if (event.target === modal) {{
                closeModal();
            }}
        }}
    </script>
</head>
<body>
    <div id="infoModal" class="modal">
        <div class="modal-content">
            <span class="close-btn" onclick="closeModal()">&times;</span>
            <div class="modal-header" id="modalTitle">Detalhes do Cálculo</div>
            <div class="modal-body" id="modalBody"></div>
        </div>
    </div>
    
    <div class="container">
        <div class="header">
            <h1>📊 UWB Measurement Report</h1>
            <p>DWM3001CDK Live Monitor Analysis</p>
        </div>
        
        <div class="content">
"""
        
        for idx, capture in enumerate(self.captures, 1):
            measurements = capture['measurements']
            distances = [m['distance'] for m in measurements if m['distance'] is not None]
            pers = [m['per'] for m in measurements if m['per'] is not None]
            
            if distances:
                stats = self._calculate_stats(distances)
                per_mean = np.mean(pers) if pers else 0
                per_max = np.max(pers) if pers else 0
                
                details = self._create_calculation_details(stats)
                
                html += f"""
            <div class="capture">
                <h3>📈 Capture Window #{idx}</h3>
                
                <div id="modal-min-{idx}" style="display: none;">{details['min']}</div>
                <div id="modal-max-{idx}" style="display: none;">{details['max']}</div>
                <div id="modal-mean-{idx}" style="display: none;">{details['mean']}</div>
                <div id="modal-std-{idx}" style="display: none;">{details['std']}</div>
                <div id="modal-median-{idx}" style="display: none;">{details['median']}</div>
                <div id="modal-range-{idx}" style="display: none;">{details['range']}</div>

                <div class="stats-grid">
                    <div class="stat-item" onclick="showModal('Mínimo', 'modal-min-{idx}')">
                        <div class="stat-label">Minimum</div>
                        <div class="stat-value">{stats['min']:.2f} cm</div>
                    </div>
                    <div class="stat-item" onclick="showModal('Máximo', 'modal-max-{idx}')">
                        <div class="stat-label">Maximum</div>
                        <div class="stat-value">{stats['max']:.2f} cm</div>
                    </div>
                    <div class="stat-item" onclick="showModal('Média', 'modal-mean-{idx}')">
                        <div class="stat-label">Mean</div>
                        <div class="stat-value">{stats['mean']:.2f} cm</div>
                    </div>
                    <div class="stat-item" onclick="showModal('Desvio Padrão', 'modal-std-{idx}')">
                        <div class="stat-label">Std Dev</div>
                        <div class="stat-value">{stats['std']:.2f} cm</div>
                    </div>
                    <div class="stat-item" onclick="showModal('Mediana', 'modal-median-{idx}')">
                        <div class="stat-label">Median</div>
                        <div class="stat-value">{stats['median']:.2f} cm</div>
                    </div>
                    <div class="stat-item" onclick="showModal('Amplitude', 'modal-range-{idx}')">
                        <div class="stat-label">Range</div>
                        <div class="stat-value">{(stats['max']-stats['min']):.2f} cm</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Avg PER</div>
                        <div class="stat-value">{per_mean:.2f} %</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Max PER</div>
                        <div class="stat-value">{per_max:.2f} %</div>
                    </div>
                </div>
                
                <div class="measurements">
                    <strong>Measurements ({len(distances)} blocks):</strong>
"""
                
                for m in measurements[:25]:
                    if m['distance'] is not None:
                        ts = m['timestamp'].strftime("%H:%M:%S.%f")[:-3]
                        rssi_str = f"| RSSI: {m['rssi']:3.0f}dBm" if m['rssi'] else ""
                        per_str = f"| PER: {m['per']:.1f}%" if m['per'] is not None else ""
                        html += f'<div class="measurement-row">[{ts}] {m["distance"]:.2f}cm {rssi_str} {per_str}</div>\n'
                
                html += """
                </div>
            </div>
"""
        
        html += f"""
        </div>
        
        <div class="footer">
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Total Captures: {len(self.captures)} | Total Measurements: {self.line_count}</p>
            <p>Session Duration: {(datetime.now() - self.session_start).total_seconds():.1f} seconds</p>
        </div>
    </div>
</body>
</html>
"""
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"\n✅ Report saved: {output_file}")
            return True
        except Exception as e:
            print(f"❌ Error saving report: {str(e)}")
            return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Live UWB Measurement Monitor with Capture Windows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python live_monitor.py --port COM3
  python live_monitor.py --port COM3 --baudrate 921600
        """
    )
    
    parser.add_argument("--port", type=str, default="COM3",
                        help="COM port to monitor (default: COM3)")
    parser.add_argument("--baudrate", type=int, default=115200,
                        help="Baud rate (default: 115200)")
    
    args = parser.parse_args()
    
    monitor = LiveMonitor(args.port, args.baudrate)
    
    if monitor.monitor():
        print("\n" + "="*80)
        print("📊 Generating HTML Report...")
        print("="*80)
        monitor.generate_html_report()
        print("✅ Done!")


if __name__ == "__main__":
    main()