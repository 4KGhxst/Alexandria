"""Real hardware backend for a standard ELM327 OBD-II Bluetooth/USB dongle,
via the `python-obd` library. Not wired into the default run path yet —
switch to it by setting ALEXANDRIA_OBD_BACKEND=elm327 and
ALEXANDRIA_OBD_PORT once you've picked hardware and have a dongle plugged
into the vehicle's OBD-II port (under the dash, near the steering column
on virtually every car built since 1996).

`python-obd` is an optional dependency (`pip install alexandria[obd]`)
because it's meaningless without real hardware.
"""

from __future__ import annotations

from alexandria.diagnostics.obd_interface import ObdBackend, Snapshot


class Elm327Backend(ObdBackend):
    def __init__(self, port: str | None = None) -> None:
        self._port = port
        self._connection = None

    def connect(self) -> None:
        try:
            import obd
        except ImportError as exc:
            raise RuntimeError(
                "python-obd is not installed. Install it with `pip install alexandria[obd]` "
                "to use a real ELM327 dongle."
            ) from exc

        self._obd = obd
        self._connection = obd.OBD(self._port) if self._port else obd.OBD()
        if not self._connection.is_connected():
            raise RuntimeError(f"Could not connect to OBD-II adapter on port {self._port!r}")

    def is_connected(self) -> bool:
        return self._connection is not None and self._connection.is_connected()

    def read_snapshot(self) -> Snapshot:
        if not self.is_connected():
            raise RuntimeError("Elm327Backend.connect() must succeed first")

        obd = self._obd

        def query(cmd_name: str) -> float | None:
            cmd = getattr(obd.commands, cmd_name, None)
            if cmd is None:
                return None
            response = self._connection.query(cmd)
            if response.is_null():
                return None
            return response.value.magnitude

        dtc_codes: list[str] = []
        dtc_response = self._connection.query(obd.commands.GET_DTC)
        if not dtc_response.is_null():
            dtc_codes = [code for code, _description in dtc_response.value]

        return Snapshot(
            rpm=query("RPM"),
            speed_mph=query("SPEED"),
            coolant_temp_f=query("COOLANT_TEMP"),
            fuel_level_pct=query("FUEL_LEVEL"),
            engine_load_pct=query("ENGINE_LOAD"),
            battery_voltage=query("CONTROL_MODULE_VOLTAGE"),
            dtc_codes=dtc_codes,
        )

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
