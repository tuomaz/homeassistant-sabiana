"""Modbus Hub for Sabiana Fan Coil."""
import asyncio
import inspect
from pymodbus.client import ModbusSerialClient
from .const import (
    LOGGER,
    REG_MODEL,
    REG_FIRMWARE,
    REG_T1,
    REG_T2,
    REG_T3,
    REG_SLAVE_MASTER,
    REG_MACHINE_STATE,
    REG_FAN_ONLY_MODE,
    REG_AUTO_MODE,
    REG_SEASON_IN_USE,
    REG_AUTO_VENT,
    REG_FAN_MIN_STATE,
    REG_FAN_MED_STATE,
    REG_FAN_MAX_STATE,
    REG_T1_FAULT,
    REG_T2_FAULT,
    REG_T3_FAULT,
    REG_CONDENS_ALARM,
    REG_SUMMER_SETPOINT,
    REG_WINTER_SETPOINT,
    REG_BOARD_TIME,
    REG_MACHINE_TIME,
    REG_TMB_PRESENT,
    REG_IR_PRESENT,
    REG_DIP3_T3_PROBE_ON,
    REG_T2_PROBE_FOUND,
    CMD_ON_OFF,
    CMD_MODE,
    CMD_FAN,
)


def _detect_slave_keyword(client: ModbusSerialClient) -> str:
    """Detect the correct keyword argument for the slave/unit address.

    pymodbus changed the parameter name across versions:
      - 2.x: 'unit'
      - 3.0-3.10: 'slave'
      - 3.11+: 'device_id'
    """
    sig = inspect.signature(client.read_holding_registers)
    params = sig.parameters
    for candidate in ("device_id", "slave", "unit"):
        if candidate in params:
            LOGGER.debug("Detected pymodbus slave keyword: %s", candidate)
            return candidate
    # Fallback — shouldn't happen
    LOGGER.warning("Could not detect pymodbus slave keyword, defaulting to 'slave'")
    return "slave"


class SabianaHub:
    """Wrapper class for pymodbus client interfacing with the Sabiana unit."""

    def __init__(self, port: str, baudrate: int, slave_address: int, schema_pref: str = "auto") -> None:
        """Initialize the Modbus hub."""
        self._port = port
        self._baudrate = baudrate
        self._slave = slave_address
        self._schema_pref = schema_pref

        # Default registers (Schema A)
        self.reg_board_time = REG_BOARD_TIME
        self.reg_machine_time = REG_MACHINE_TIME
        self.reg_tmb_present = REG_TMB_PRESENT
        self.reg_ir_present = REG_IR_PRESENT
        self.cmd_on_off = CMD_ON_OFF
        self.cmd_mode = CMD_MODE
        self.cmd_fan = CMD_FAN
        self.block3_count = 25

        self._client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            parity="N",
            stopbits=1,
            bytesize=8,
            timeout=1,
        )
        self._lock = asyncio.Lock()

        # Detect the correct keyword for slave/unit/device_id at init time
        self._slave_kw = _detect_slave_keyword(self._client)

    async def detect_schema(self) -> None:
        """Read controller model and set register offsets accordingly."""
        schema = "schema_a"
        if self._schema_pref == "auto":
            try:
                # Read model register (0x1000)
                model_block = await self.read_holding_registers(REG_MODEL, 1)
                model_val = model_block[0]
                LOGGER.info("Detected Sabiana model ID: %s (hex: 0x%04X)", model_val, model_val)
                # Schema B models: 0x5004 (CVP async), 0x5005 (CVP ECM), 0x5006 (QCV async), 0x5007 (QCV ECM)
                if model_val in [0x5004, 0x5005, 0x5006, 0x5007]:
                    schema = "schema_b"
                else:
                    schema = "schema_a"
            except Exception as err:
                LOGGER.warning("Could not auto-detect model schema, falling back to Schema A: %s", err)
                schema = "schema_a"
        else:
            schema = self._schema_pref

        if schema == "schema_b":
            LOGGER.info("Configuring registers for CVP/QCV (Schema B)")
            self.reg_board_time = 0x105F
            self.reg_machine_time = 0x1069
            self.reg_tmb_present = 0x1072
            self.reg_ir_present = 0x1073
            self.cmd_on_off = 0x105C
            self.cmd_mode = 0x105D
            self.cmd_fan = 0x105E
            self.block3_count = 21
        else:
            LOGGER.info("Configuring registers for standard Cassette/Fancoil/CCP-ECM (Schema A)")
            self.reg_board_time = 0x105A
            self.reg_machine_time = 0x1064
            self.reg_tmb_present = 0x1071
            self.reg_ir_present = 0x1072
            self.cmd_on_off = 0x1057
            self.cmd_mode = 0x1058
            self.cmd_fan = 0x1059
            self.block3_count = 25

    async def connect(self) -> bool:
        """Connect to the Modbus device."""
        async with self._lock:
            return await asyncio.to_thread(self._client.connect)

    async def close(self) -> None:
        """Close the Modbus connection."""
        async with self._lock:
            await asyncio.to_thread(self._client.close)

    async def read_holding_registers(self, address: int, count: int) -> list[int]:
        """Read holding registers thread-safely."""
        kwargs = {"address": address, "count": count, self._slave_kw: self._slave}
        async with self._lock:
            result = await asyncio.to_thread(
                lambda: self._client.read_holding_registers(**kwargs)
            )
            if result.isError():
                LOGGER.error("Error reading registers %s: %s", address, result)
                raise Exception(f"Modbus error reading registers at {address}: {result}")
            return result.registers

    async def write_register(self, address: int, value: int) -> None:
        """Write holding register thread-safely."""
        kwargs = {"address": address, "value": value, self._slave_kw: self._slave}
        async with self._lock:
            result = await asyncio.to_thread(
                lambda: self._client.write_register(**kwargs)
            )
            if result.isError():
                LOGGER.error("Error writing register %s value %s: %s", address, value, result)
                raise Exception(f"Modbus error writing register at {address}: {result}")



    async def async_update_data(self) -> dict:
        """Retrieve all register data in bulk blocks."""
        # Read status block 1000-101B (28 registers)
        block1 = await self.read_holding_registers(REG_MODEL, 28)
        # Read alarms and setpoints block 1028-102E (7 registers)
        block2 = await self.read_holding_registers(REG_T1_FAULT, 7)
        # Read counters and presence
        block3 = await self.read_holding_registers(self.reg_board_time, self.block3_count)

        tmb_idx = 23 if self.block3_count == 25 else 19
        ir_idx = 24 if self.block3_count == 25 else 20

        data = {
            REG_MODEL: block1[0],
            REG_FIRMWARE: block1[1],
            REG_T1: block1[2],
            REG_T2: block1[3],
            REG_T3: block1[4],
            REG_SLAVE_MASTER: block1[6],
            REG_MACHINE_STATE: block1[15],
            REG_FAN_ONLY_MODE: block1[16],
            REG_AUTO_MODE: block1[17],
            REG_SEASON_IN_USE: block1[19],
            REG_AUTO_VENT: block1[23],
            REG_FAN_MIN_STATE: block1[25],
            REG_FAN_MED_STATE: block1[26],
            REG_FAN_MAX_STATE: block1[27],
            REG_DIP3_T3_PROBE_ON: block1[7],
            REG_T2_PROBE_FOUND: block1[20],
            
            REG_T1_FAULT: block2[0],
            REG_T2_FAULT: block2[1],
            REG_T3_FAULT: block2[2],
            REG_CONDENS_ALARM: block2[3],
            REG_SUMMER_SETPOINT: block2[5],
            REG_WINTER_SETPOINT: block2[6],
            
            # Board time is uns32 (2 registers)
            self.reg_board_time: (block3[0] << 16) | block3[1],
            # Machine time is uns32 (2 registers) at index 10 (1069-105F = 10 or 1064-105A = 10)
            self.reg_machine_time: (block3[10] << 16) | block3[11],
            # TMB present
            self.reg_tmb_present: block3[tmb_idx],
            # IR present
            self.reg_ir_present: block3[ir_idx],
        }
        return data

