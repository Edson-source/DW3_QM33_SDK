UWB Serial Reader
=================

Small helper to read FiRa/DWM3001 CLI serial output and extract distance measurements.

Setup
-----
Install Python dependencies (recommended to run in a virtualenv):

```powershell
python -m pip install --user virtualenv
python -m virtualenv .venv
.\.venv\Scripts\Activate.ps1
pip install pyserial
```

```cmd
cd .\Projects\Common\scripts
python .\uwb_serial_reader.py --port COM3 --baud 115200 --csv distances.csv
```

Usage
-----
Run the reader with the COM port and optional CSV output:

```powershell
python uwb_serial_reader.py --port COM3 --baud 115200 --csv distances.csv
```

What it does
------------
- Listens on the serial port
- Parses incoming lines for occurrences of `distance[cm]=<value>`
- Prints timestamped measurements and the full raw line
- Appends measurements to CSV when `--csv` is provided

Notes
-----
- The reader expects the firmware to print ranging results like the SDK FiRa example, e.g. `distance[cm]=123`. If your firmware prints a different format, update the regex in the script accordingly.
- If you want to capture all raw output, remove the filtering block in the script and print every line.
