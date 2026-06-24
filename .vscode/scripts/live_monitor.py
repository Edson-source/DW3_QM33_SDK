# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo US, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2

"""
Live UWB Measurement Monitor with Silent Capture
"""

import sys
import os
import serial
import threading
import time
import json
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
        
        # CORREÇÃO: Inicialização do timestamp para evitar AttributeError
        self.last_timestamp = None
        self.line_buffer = ""
    
    def open_port(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"✓ Connected to {self.port} at {self.baudrate} baud")
            return True
        except serial.SerialException as e:
            print(f"❌ Failed to open {self.port}: {str(e)}")
            return False
    
    def _extract_distance(self, data):
        patterns = [
            r'distance\[cm\]=([\d.]+)',
            r'distance_bruta\[cm\]=([\d.-]+)',
            r'Distance:\s*([\d.]+)\s*m',
            r'X=([\d.]+)',
            r'(\d+),(-?\d+),\d+,OK'
        ]
        for pattern in patterns:
            match = re.search(pattern, data)
            if match:
                val = float(match.group(1))
                if pattern == r'Distance:\s*([\d.]+)\s*m':
                    val = val * 100.0
                return val
        return None

    def _extract_kalman(self, data):
        match = re.search(r'kalman\[cm\]=([\d.-]+)', data)
        return float(match.group(1)) if match else None

    def _extract_media_movel(self, data):
        match = re.search(r'media_movel\[cm\]=([\d.-]+)', data)
        return float(match.group(1)) if match else None
    
    def _extract_rssi(self, data):
        patterns = [
            r'RSSI\[dBm\]=([-?\d.]+)',
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
        match = re.search(r'PER=([\d.]+)', data)
        return float(match.group(1)) if match else None
    
    def _extract_block_index(self, data):
        match = re.search(r'block_index=(\d+)', data)
        return int(match.group(1)) if match else None
        
    def _get_rssi_bars(self, rssi):
        if rssi is None:
            return "[    ]"
        if rssi >= -75:
            return "[████]"
        elif rssi >= -82:
            return "[███ ]"
        elif rssi >= -90:
            return "[██  ]"
        else:
            return "[█   ]"
    
    def print_header(self):
        print("\n" + "="*105)
        print("🔴 LIVE MEASUREMENT MONITOR - DWM3001CDK")
        print("="*105)
        print(f"Port: {self.port} | Baudrate: {self.baudrate} | Session: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-"*105)
        print("Controls:  ',' = Capture Window  |  's' = Save Report  |  'q/ESC' = Exit")
        print("="*105 + "\n")
    
    def on_key_press(self, key):
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
        window_measurements = []
        capture_start = time.time()
        
        while time.time() - capture_start < 5.0:
            if self.all_measurements:
                if len(self.all_measurements) > len(window_measurements):
                    window_measurements = self.all_measurements[-25:]
            time.sleep(0.05)
        
        if window_measurements:
            capture_data = {
                'timestamp': datetime.now(),
                'measurements': window_measurements.copy()
            }
            self.captures.append(capture_data)
            
            distances = [m['distance'] for m in window_measurements if m['distance'] is not None]
            if distances:
                stats = self._calculate_stats(distances)
                print(f"\n📊 CAPTURED (Window #{len(self.captures)}): " +
                      f"Min={stats['min']:.2f}cm | Max={stats['max']:.2f}cm | " +
                      f"σ={stats['std']:.2f}cm\n")
        
        self.capture_active = False

    def _create_moving_avg_details(self):
        return """
        <p><strong>Média Móvel:</strong> Filtro passa-baixa básico que calcula a média aritmética das últimas <em>N</em> amostras (no seu firmware configurado para 30 leituras).</p>
        <p><strong>Comportamento:</strong></p>
        <ul>
            <li>Suaviza o sinal e apresenta o <strong>menor range de variação</strong> matemático.</li>
            <li><strong>Desvantagem (Lag):</strong> Introduz um atraso mecânico significativo. Mudanças rápidas na distância física demoram vários ciclos para refletir no valor.</li>
        </ul>
        """
    
    def _create_kalman_details(self):
        return """
        <p><strong>Filtro de Kalman (1D):</strong> Algoritmo de estimação preditiva. Permanente e dinâmico, ele rastreia mudanças rapidamente sem introduzir arrasto mecânico pesado.</p>
        <p><strong>Parâmetros (C Firmware):</strong></p>
        <ul>
            <li><strong>Q (Ruído do Processo):</strong> 0.10</li>
            <li><strong>R (Ruído da Medição - Jitter):</strong> 15.00</li>
        </ul>
        """
    
    def _calculate_stats(self, values):
        if not values:
            return {'min': 0.0, 'max': 0.0, 'mean': 0.0, 'std': 0.0, 'median': 0.0, 'range': 0.0, 'count': 0}
            
        arr = np.array(values)
        val_min = np.min(arr)
        val_max = np.max(arr)
        
        return {
            'min': val_min,
            'max': val_max,
            'mean': np.mean(arr),
            'std': np.std(arr, ddof=1) if len(arr) > 1 else 0,
            'median': np.median(arr),
            'range': val_max - val_min,
            'count': len(values)
        }
    
    def monitor(self):
        if not self.open_port():
            return False
        
        self.print_header()
        self.start_time = time.time()
        
        listener = keyboard.Listener(on_press=self.on_key_press)
        listener.start()
        
        capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        capture_thread.start()
        
        try:
            while not self.exit_flag:
                if self.ser.in_waiting > 0:
                    try:
                        line = self.ser.readline().decode('utf-8', errors='ignore').rstrip()
                        self.line_buffer += " " + line
                        
                        if ']}' in self.line_buffer:
                            timestamp = datetime.now()
                            
                            # CORREÇÃO: Cálculo seguro do Delta T
                            delta_t = 0
                            if self.last_timestamp:
                                delta_t = int((timestamp - self.last_timestamp).total_seconds() * 1000)
                            self.last_timestamp = timestamp
                            
                            distance = self._extract_distance(self.line_buffer)
                            kalman = self._extract_kalman(self.line_buffer)
                            media_mov = self._extract_media_movel(self.line_buffer)
                            rssi = self._extract_rssi(self.line_buffer)
                            per = self._extract_per(self.line_buffer)
                            block_index = self._extract_block_index(self.line_buffer)
                            
                            if distance is not None:
                                self.line_count += 1
                                measurement = {
                                    'timestamp': timestamp,
                                    'delta_t': delta_t,
                                    'distance': distance,
                                    'kalman': kalman,
                                    'media_movel': media_mov,
                                    'rssi': rssi,
                                    'per': per,
                                    'block_index': block_index,
                                    'raw': self.line_buffer
                                }
                                self.all_measurements.append(measurement)
                                
                                # TERMINAL ORIGINAL: Exibição limpa
                                ts = timestamp.strftime("%H:%M:%S.%f")[:-3]
                                block_str = f"Blk #{block_index:<5}" if block_index is not None else "Blk #----"
                                rssi_bar = self._get_rssi_bars(rssi)
                                rssi_str = f"RSSI: {rssi:6.1f} dBm {rssi_bar}" if rssi else "RSSI: N/A"
                                per_str = f"PER: {per:5.1f}%" if per is not None else ""
                                kalman_str = f"| Kalm: {kalman:6.2f}cm" if kalman is not None else ""
                                mov_str = f"| Mov: {media_mov:6.2f}cm" if media_mov is not None else ""
                                
                                print(f"[{ts}] {block_str} | Dist: {distance:6.2f}cm {kalman_str} {mov_str} | {rssi_str} | {per_str}")
                            
                            self.line_buffer = ""
                    except Exception as e:
                        pass
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
        while not self.exit_flag:
            if self.capture_active:
                self.capture_window()
            time.sleep(0.1)
    
    def generate_html_report(self):
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
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background: #e9ecef; padding: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #4b6cb7 0%, #182848 100%); color: white; padding: 30px; text-align: center; }}
        .header h1 {{ font-size: 2.2em; margin-bottom: 5px; }}
        .content {{ padding: 30px; }}
        
        .capture {{ margin-bottom: 40px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 6px; overflow: hidden; }}
        .capture-header {{ background: #fff; padding: 15px 20px; border-bottom: 2px solid #4b6cb7; display: flex; justify-content: space-between; align-items: center; }}
        .capture-title {{ font-size: 1.2em; color: #4b6cb7; font-weight: bold; }}
        .capture-health {{ font-size: 0.9em; background: #e9ecef; padding: 5px 15px; border-radius: 20px; color: #495057; font-weight: 600; display: flex; gap: 15px; }}
        
        .capture-body {{ display: flex; flex-direction: row; padding: 20px; gap: 25px; }}
        
        .stats-panel {{ flex: 0 0 340px; display: flex; flex-direction: column; gap: 20px; }}
        .stat-group {{ background: #fff; border-radius: 6px; border: 1px solid #e9ecef; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.02); }}
        .stat-group-header {{ background: #f1f3f5; padding: 8px 15px; font-size: 0.85em; color: #495057; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e9ecef; display: flex; justify-content: space-between; align-items: center; }}
        .info-icon {{ cursor: pointer; color: #4b6cb7; font-weight: bold; background: #e2e6ea; border-radius: 50%; width: 20px; height: 20px; display: inline-flex; justify-content: center; align-items: center; font-size: 0.85em; }}
        .info-icon:hover {{ background: #4b6cb7; color: white; }}
        
        .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1px; background: #e9ecef; }}
        
        .stat-item {{ background: #fff; padding: 12px; text-align: center; }}
        .stat-item:hover {{ background: #f8f9fa; }}
        .stat-item.highlight {{ background: #fdfcff; }}
        .stat-label {{ font-size: 0.70em; color: #868e96; text-transform: uppercase; margin-bottom: 2px; font-weight: 600; }}
        .stat-value {{ font-size: 1.1em; font-weight: bold; color: #343a40; }}
        .highlight .stat-value {{ color: #764ba2; }}
        
        .log-panel {{ flex: 1; display: flex; flex-direction: column; gap: 15px; overflow: hidden; }}
        .chart-container {{ background: white; border: 1px solid #e9ecef; border-radius: 6px; padding: 15px; height: 250px; position: relative; }}
        
        /* CORREÇÃO AQUI: Força espaço preformatado e barra de rolagem horizontal */
        .measurements {{ flex: 1; min-height: 250px; max-height: 350px; overflow-y: auto; overflow-x: auto; background: #212529; color: #a1ef8c; border-radius: 6px; padding: 15px; font-family: 'Consolas', monospace; font-size: 0.85em; line-height: 1.5; box-shadow: inset 0 2px 10px rgba(0,0,0,0.5); }}
        .measurement-row {{ border-bottom: 1px solid rgba(255,255,255,0.05); padding: 3px 0; white-space: pre; }}
        .measurement-row:hover {{ background: rgba(255,255,255,0.05); }}
        .blk-col {{ color: #ffc107; }}
        .dt-col {{ color: #17a2b8; }}
        
        .footer {{ background: #fff; padding: 20px; text-align: center; color: #6c757d; border-top: 1px solid #dee2e6; font-size: 0.9em; }}
        
        .modal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0, 0, 0, 0.6); backdrop-filter: blur(3px); }}
        .modal.show {{ display: flex; align-items: center; justify-content: center; }}
        .modal-content {{ background-color: white; padding: 30px; border-radius: 8px; max-width: 500px; max-height: 80vh; overflow-y: auto; box-shadow: 0 15px 50px rgba(0,0,0,0.3); }}
        .modal-header {{ font-size: 1.3em; font-weight: bold; color: #4b6cb7; margin-bottom: 15px; border-bottom: 2px solid #4b6cb7; padding-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }}
        .modal-body {{ font-size: 0.95em; line-height: 1.7; color: #495057; }}
        .close-btn {{ font-size: 1.2em; font-weight: bold; cursor: pointer; color: #adb5bd; border: none; background: none; }}
        .close-btn:hover {{ color: #dc3545; }}
    </style>
    <script>
        let currentModal = null;
        function showModal(title, contentId) {{
            const modal = document.getElementById('infoModal');
            const sourceContent = document.getElementById(contentId);
            if (!modal || !sourceContent) {{ return; }}
            document.getElementById('modalTitleText').innerText = title;
            document.getElementById('modalBody').innerHTML = sourceContent.innerHTML;
            modal.classList.add('show');
            currentModal = modal;
        }}
        function closeModal() {{
            if (currentModal) {{ currentModal.classList.remove('show'); }}
        }}
        window.onclick = function(event) {{
            const modal = document.getElementById('infoModal');
            if (event.target === modal) {{ closeModal(); }}
        }}
        document.addEventListener('keydown', function(event) {{
            if (event.key === "Escape") {{ closeModal(); }}
        }});
    </script>
</head>
<body>
    <div id="infoModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <span id="modalTitleText">Detalhes</span>
                <button class="close-btn" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body" id="modalBody"></div>
        </div>
    </div>
    
    <div class="container">
        <div class="header">
            <h1>📡 Relatório de Medição UWB</h1>
            <p>DWM3001CDK Análise Comparativa de Filtros & Qualidade de Sinal</p>
        </div>
        
        <div class="content">
"""
        
        for idx, capture in enumerate(self.captures, 1):
            measurements = capture['measurements']
            
            distances = [m['distance'] for m in measurements if m['distance'] is not None]
            kalmans = [m['kalman'] for m in measurements if m.get('kalman') is not None]
            mov_avgs = [m['media_movel'] for m in measurements if m.get('media_movel') is not None]
            rssis = [m['rssi'] for m in measurements if m.get('rssi') is not None]
            pers = [m['per'] for m in measurements if m.get('per') is not None]
            dts = [m['delta_t'] for m in measurements if m.get('delta_t') is not None]
            
            if distances:
                st_raw = self._calculate_stats(distances)
                st_kal = self._calculate_stats(kalmans)
                st_mov = self._calculate_stats(mov_avgs)
                
                avg_rssi = np.mean(rssis) if rssis else 0
                avg_per = np.mean(pers) if pers else 0
                avg_dt = np.mean(dts) if dts else 0
                
                labels_js = [m.get('block_index', i) for i, m in enumerate(measurements)]
                raw_js = [m['distance'] if m['distance'] is not None else 'null' for m in measurements]
                kal_js = [m['kalman'] if m.get('kalman') is not None else 'null' for m in measurements]
                mov_js = [m['media_movel'] if m.get('media_movel') is not None else 'null' for m in measurements]
                
                html += f"""
            <div class="capture">
                <div class="capture-header">
                    <div class="capture-title">📈 Janela de Captura #{idx}</div>
                    <div class="capture-health">
                        <span>Δt Médio: {avg_dt:.1f} ms</span>
                        <span>RSSI Médio: {avg_rssi:.1f} dBm</span>
                        <span>PER Médio: {avg_per:.1f}%</span>
                    </div>
                </div>
                
                <div id="modal-kalman-{idx}" style="display: none;">{self._create_kalman_details()}</div>
                <div id="modal-movavg-{idx}" style="display: none;">{self._create_moving_avg_details()}</div>

                <div class="capture-body">
                    <div class="stats-panel">
                        
                        <div class="stat-group">
                            <div class="stat-group-header">
                                Filtro de Kalman (1D)
                                <span class="info-icon" onclick="showModal('Filtro de Kalman', 'modal-kalman-{idx}')">?</span>
                            </div>
                            <div class="stat-grid">
                                <div class="stat-item highlight"><div class="stat-label">Média</div><div class="stat-value">{st_kal['mean']:.2f} cm</div></div>
                                <div class="stat-item highlight"><div class="stat-label">Std Dev (σ)</div><div class="stat-value">{st_kal['std']:.2f} cm</div></div>
                                <div class="stat-item"><div class="stat-label">Range</div><div class="stat-value">{st_kal['range']:.2f} cm</div></div>
                                <div class="stat-item"><div class="stat-label">Min / Max</div><div class="stat-value">{st_kal['min']:.1f} / {st_kal['max']:.1f}</div></div>
                            </div>
                        </div>

                        <div class="stat-group">
                            <div class="stat-group-header">
                                Média Móvel (30 Leituras)
                                <span class="info-icon" onclick="showModal('Média Móvel', 'modal-movavg-{idx}')">?</span>
                            </div>
                            <div class="stat-grid">
                                <div class="stat-item"><div class="stat-label">Média</div><div class="stat-value">{st_mov['mean']:.2f} cm</div></div>
                                <div class="stat-item"><div class="stat-label">Std Dev (σ)</div><div class="stat-value">{st_mov['std']:.2f} cm</div></div>
                                <div class="stat-item"><div class="stat-label">Range</div><div class="stat-value">{st_mov['range']:.2f} cm</div></div>
                                <div class="stat-item"><div class="stat-label">Min / Max</div><div class="stat-value">{st_mov['min']:.1f} / {st_mov['max']:.1f}</div></div>
                            </div>
                        </div>

                        <div class="stat-group">
                            <div class="stat-group-header">Sinal Bruto (Raw Data)</div>
                            <div class="stat-grid">
                                <div class="stat-item"><div class="stat-label">Média</div><div class="stat-value">{st_raw['mean']:.2f} cm</div></div>
                                <div class="stat-item"><div class="stat-label">Std Dev (σ)</div><div class="stat-value">{st_raw['std']:.2f} cm</div></div>
                                <div class="stat-item"><div class="stat-label">Range</div><div class="stat-value">{st_raw['range']:.2f} cm</div></div>
                                <div class="stat-item"><div class="stat-label">Min / Max</div><div class="stat-value">{st_raw['min']:.1f} / {st_raw['max']:.1f}</div></div>
                            </div>
                        </div>
                        
                    </div>
                    
                    <div class="log-panel">
                        <div class="chart-container">
                            <canvas id="chart-{idx}"></canvas>
                        </div>
                        
                        <div class="measurements">
"""
                
                for m in measurements[:25]:
                    if m['distance'] is not None:
                        # CORREÇÃO DA FORMATAÇÃO DA STRING
                        ts = m['timestamp'].strftime("%H:%M:%S.%f")[:-3]
                        
                        blk_val = m.get('block_index')
                        blk_str = f"Blk #{blk_val:<4}" if blk_val is not None else "Blk #---"
                        
                        dt_val = m.get('delta_t', 0)
                        dt_str = f"{dt_val:3d}ms" # Garante o alinhamento com 3 digitos
                        
                        kalm_str = f"| Kalm: {m['kalman']:6.2f}cm" if m.get('kalman') is not None else ""
                        mov_str  = f"| Mov: {m['media_movel']:6.2f}cm" if m.get('media_movel') is not None else ""
                        
                        rssi_bar = self._get_rssi_bars(m['rssi'])
                        rssi_str = f"| RSSI: {m['rssi']:3.0f}dBm {rssi_bar}" if m['rssi'] else ""
                        
                        per_str = f"| PER: {m['per']:4.1f}%" if m['per'] is not None else ""
                        
                        # Espaçamento literal na string para garantir visual de terminal
                        html += f'<div class="measurement-row"><span>[{ts}]</span> <span class="dt-col">Δt: {dt_str}</span> <span class="blk-col">{blk_str}</span>   <span>Raw: {m["distance"]:6.2f}cm {kalm_str} {mov_str} {rssi_str} {per_str}</span></div>\n'
                
                html += f"""
                        </div>
                    </div>
                </div>
            </div>
            
            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    const ctx = document.getElementById('chart-{idx}').getContext('2d');
                    new Chart(ctx, {{
                        type: 'line',
                        data: {{
                            labels: {json.dumps(labels_js)},
                            datasets: [
                                {{
                                    label: 'Raw Data',
                                    data: {json.dumps(raw_js)},
                                    borderColor: '#adb5bd',
                                    borderDash: [5, 5],
                                    borderWidth: 1.5,
                                    pointRadius: 2,
                                    fill: false,
                                    tension: 0
                                }},
                                {{
                                    label: 'Kalman Filter',
                                    data: {json.dumps(kal_js)},
                                    borderColor: '#764ba2',
                                    borderWidth: 2.5,
                                    pointRadius: 3,
                                    pointBackgroundColor: '#764ba2',
                                    fill: false,
                                    tension: 0.1
                                }},
                                {{
                                    label: 'Média Móvel',
                                    data: {json.dumps(mov_js)},
                                    borderColor: '#20c997',
                                    borderWidth: 2,
                                    pointRadius: 0,
                                    fill: false,
                                    tension: 0.3
                                }}
                            ]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{ position: 'top', labels: {{ boxWidth: 12 }} }}
                            }},
                            scales: {{
                                x: {{ display: true, title: {{ display: true, text: 'Block Index' }} }},
                                y: {{ display: true, title: {{ display: true, text: 'Distance (cm)' }} }}
                            }}
                        }}
                    }});
                }});
            </script>
"""
        
        html += f"""
        </div>
        
        <div class="footer">
            <p>Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Total de Capturas: {len(self.captures)} | Total de Medições: {self.line_count}</p>
            <p>Duração da Sessão: {(datetime.now() - self.session_start).total_seconds():.1f} segundos</p>
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
        print("\n" + "="*105)
        print("📊 Generating HTML Report...")
        print("="*105)
        monitor.generate_html_report()
        print("✅ Done!")


if __name__ == "__main__":
    main()