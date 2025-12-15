# ============================================================================
# UWB Distance Monitor - PowerShell Version
# ============================================================================
# Real-time visualization of UWB ranging distances from DWM3001CDK serial output
#
# NOTE: DWM3001CDK measures DISTANCE and RSSI only
# For Angle of Arrival (AoA), you need QM33120WDK with antenna array
#
# Usage:
#   .\uwb_monitor.ps1 -Port COM3 -Baud 115200
#   .\uwb_monitor.ps1 -Port COM3 -CSV results.csv -Stats
#
# Features:
#   - Real-time distance display with color coding
#   - MAC address tracking
#   - RSSI information
#   - Optional CSV export
#   - Running statistics (min/max/avg)
#
# ============================================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$Port,
    
    [int]$Baud = 115200,
    
    [string]$CSV,
    
    [switch]$Stats,
    
    [int]$StatsInterval = 10,
    
    [double]$MinDistance,
    
    [double]$MaxDistance,
    
    [int]$Timeout = 1000
)

# Initialize statistics
$script:measurements = @()
$script:count = 0

# Colors for console output
$ColorDistance = @{
    Close = [System.ConsoleColor]::Red
    Good  = [System.ConsoleColor]::Green
    Far   = [System.ConsoleColor]::Yellow
    Info  = [System.ConsoleColor]::Cyan
}

function Get-DistanceColor {
    param([double]$Distance)
    
    if ($Distance -lt 100) { return $ColorDistance.Close }
    elseif ($Distance -lt 300) { return $ColorDistance.Good }
    else { return $ColorDistance.Far }
}

function Format-Measurement {
    param([string]$Line)
    
    $result = @{}
    
    # Extract distance
    if ($Line -match 'distance\[cm\]=\s*(-?\d+)') {
        $result.Distance = [int]$matches[1]
    }
    
    # Extract MAC address
    if ($Line -match 'mac_address=(0x[0-9a-fA-F]+)') {
        $result.MAC = $matches[1]
    }
    
    # Extract RSSI
    if ($Line -match 'RSSI\[dBm\]=\s*(-?\d+\.?\d*)') {
        $result.RSSI = [double]$matches[1]
    }
    
    # Extract status
    if ($Line -match 'status="([^"]+)"') {
        $result.Status = $matches[1]
    }
    
    # Extract azimuth
    if ($Line -match 'loc_az=(-?\d+\.?\d*)') {
        $result.Azimuth = [double]$matches[1]
    }
    
    return $result
}

function Print-Stats {
    if ($script:measurements.Count -eq 0) { return }
    
    $min = ($script:measurements | Measure-Object -Minimum).Minimum
    $max = ($script:measurements | Measure-Object -Maximum).Maximum
    $avg = ($script:measurements | Measure-Object -Average).Average
    $last = $script:measurements[-1]
    
    Write-Host "`n" -ForegroundColor $ColorDistance.Info
    Write-Host ("=" * 60) -ForegroundColor $ColorDistance.Info
    Write-Host "STATISTICS (last $(($script:measurements | Measure-Object).Count) measurements)" -ForegroundColor $ColorDistance.Info
    Write-Host ("=" * 60) -ForegroundColor $ColorDistance.Info
    Write-Host "  Total measurements: $($script:count)"
    Write-Host "  Min distance:       $([math]::Round($min, 1)) cm"
    Write-Host "  Max distance:       $([math]::Round($max, 1)) cm"
    Write-Host "  Average distance:   $([math]::Round($avg, 1)) cm"
    Write-Host "  Last measurement:   $([math]::Round($last, 1)) cm"
    Write-Host ("=" * 60) -ForegroundColor $ColorDistance.Info
    Write-Host ""
}

function Write-MeasurementLine {
    param([hashtable]$Data)
    
    $distance = $Data.Distance
    $mac = if ($Data.MAC) { $Data.MAC } else { "????" }
    $rssi = if ($Data.RSSI) { $Data.RSSI } else { "N/A" }
    $timestamp = Get-Date -Format "HH:mm:ss.fff"
    
    $distColor = Get-DistanceColor $distance
    
    # Build output (DWM3001CDK: distance + RSSI only)
    $output = "$timestamp | "
    Write-Host -NoNewline $output -ForegroundColor White
    Write-Host -NoNewline ("{0:6} cm" -f $distance) -ForegroundColor $distColor
    Write-Host -NoNewline " | $mac | RSSI=" -ForegroundColor White
    Write-Host -NoNewline ("{0:6} dBm" -f $rssi) -ForegroundColor White
    
    # NOTE: DWM3001CDK does NOT support AoA - no azimuth/elevation
    
    Write-Host ""  # Newline
}

# Open serial port
try {
    $port = New-Object System.IO.Ports.SerialPort($Port, $Baud)
    $port.Handshake = [System.IO.Ports.Handshake]::None
    $port.ReadTimeout = $Timeout
    $port.WriteTimeout = $Timeout
    $port.Open()
    Write-Host "✓ Connected to $Port @ ${Baud}bps" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to open $Port : $_" -ForegroundColor Red
    exit 1
}

# Setup CSV if requested
$csvFile = $null
if ($CSV) {
    try {
        $csvFile = $CSV
        $fileExists = Test-Path $csvFile
        
        if (-not $fileExists) {
            Add-Content $csvFile "Timestamp,Distance_cm,MAC,RSSI_dBm,Azimuth_deg,Status"
        }
        Write-Host "✓ CSV output: $CSV" -ForegroundColor Green
    } catch {
        Write-Host "⚠ Could not open CSV file: $_" -ForegroundColor Yellow
        $csvFile = $null
    }
}

Write-Host "Listening for FiRa measurements..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop.`n" -ForegroundColor Cyan

# Main loop
$buffer = ""
try {
    while ($true) {
        if ($port.BytesToRead -gt 0) {
            try {
                $char = $port.ReadChar()
                $buffer += $char
                
                # Process complete lines
                if ($char -eq "`n") {
                    $line = $buffer.Trim()
                    $buffer = ""
                    
                    # Check if this line has distance data
                    if ($line -match "distance\[cm\]") {
                        $data = Format-Measurement $line
                        
                        if ($data.Distance -ne $null) {
                            $distance = $data.Distance
                            
                            # Apply filters
                            if ($PSBoundParameters.ContainsKey('MinDistance') -and $distance -lt $MinDistance) {
                                continue
                            }
                            if ($PSBoundParameters.ContainsKey('MaxDistance') -and $distance -gt $MaxDistance) {
                                continue
                            }
                            
                            # Display measurement
                            Write-MeasurementLine $data
                            
                            # Track statistics
                            $script:measurements += $distance
                            if ($script:measurements.Count -gt 100) {
                                $script:measurements = $script:measurements[-100..-1]
                            }
                            $script:count++
                            
                            # Save to CSV
                            if ($csvFile) {
                                $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
                                $csvLine = "$timestamp,$($data.Distance),$($data.MAC),$($data.RSSI),$($data.Azimuth),$($data.Status)"
                                Add-Content $csvFile $csvLine
                            }
                            
                            # Print statistics periodically
                            if ($Stats -and ($script:count % $StatsInterval -eq 0)) {
                                Print-Stats
                            }
                        }
                    }
                }
            } catch {
                # Continue on error (timeout is normal)
            }
        } else {
            Start-Sleep -Milliseconds 10
        }
    }
} catch [Management.Automation.PSRemotingTransportException] {
    # Ctrl+C was pressed
} finally {
    Write-Host "`nStopped by user" -ForegroundColor Yellow
    
    if ($Stats) {
        Print-Stats
    }
    
    if ($port -and $port.IsOpen) {
        $port.Close()
        Write-Host "✓ Serial port closed" -ForegroundColor Green
    }
    
    if ($csvFile) {
        Write-Host "✓ Data saved to $csvFile" -ForegroundColor Green
    }
}
