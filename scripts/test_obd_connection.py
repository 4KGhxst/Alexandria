"""Standalone sanity check for a real ELM327 OBD-II dongle, without
running the whole Alexandria app. Connects, reads one snapshot, prints it.

    python scripts/test_obd_connection.py COM3

If no port is given, falls back to ALEXANDRIA_OBD_PORT from the
environment, then to python-obd's auto-detect.

Requires the `obd` extra: pip install -e ".[obd]"
"""

from __future__ import annotations

import sys

from alexandria.config import Config
from alexandria.diagnostics.obd_elm327 import Elm327Backend


def main() -> None:
    port = sys.argv[1] if len(sys.argv) > 1 else Config.from_env().obd_port

    print(f"Connecting to ELM327 on {port or '(auto-detect)'} ...")
    backend = Elm327Backend(port=port)
    try:
        backend.connect()
    except RuntimeError as exc:
        print(f"Connection failed: {exc}")
        print(
            "Checklist: ignition on (accessory or running), dongle plugged into the OBD-II port "
            "(usually under the dash near the steering column), Bluetooth dongle paired in Windows "
            "first if wireless, and the port matches what `python scripts/list_serial_ports.py` shows."
        )
        sys.exit(1)

    print("Connected. Reading a snapshot...")
    snapshot = backend.read_snapshot()
    print(snapshot)
    backend.close()


if __name__ == "__main__":
    main()
