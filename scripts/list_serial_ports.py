"""Lists available serial ports so you can find which one your ELM327
OBD-II dongle landed on (varies by machine and USB port on Windows, e.g.
COM3, COM4, ...). Run this with the dongle plugged in/paired, then again
with it unplugged, to spot which entry disappears.

    python scripts/list_serial_ports.py

Requires pyserial, which comes in automatically with the `obd` extra:
    pip install -e ".[obd]"
"""

from __future__ import annotations


def main() -> None:
    from serial.tools import list_ports

    ports = list(list_ports.comports())
    if not ports:
        print("No serial ports found.")
        return

    for port in ports:
        print(f"{port.device}  —  {port.description}")


if __name__ == "__main__":
    main()
