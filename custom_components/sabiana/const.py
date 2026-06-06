"""Constants for the Sabiana Fan Coil integration."""
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "sabiana"

CONF_PORT = "port"
CONF_BAUDRATE = "baudrate"
CONF_SLAVE_ADDRESS = "slave_address"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_SUPPORT_COOLING = "support_cooling"
CONF_SUPPORT_HEATING = "support_heating"
CONF_MODEL_SCHEMA = "model_schema"

DEFAULT_PORT = "/dev/sabiana"
DEFAULT_BAUDRATE = 9600
DEFAULT_SLAVE_ADDRESS = 1
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_SUPPORT_COOLING = True
DEFAULT_SUPPORT_HEATING = True
DEFAULT_MODEL_SCHEMA = "auto"




# Registers
# Read-Only or Read-Write status/states
REG_MODEL = 0x1000            # uns16 R
REG_FIRMWARE = 0x1001         # uns16 R
REG_T1 = 0x1002               # sig16 R (ambient temp * 10)
REG_T2 = 0x1003               # sig16 R (water temp * 10)
REG_T3 = 0x1004               # sig16 R (min probe temp * 10)
REG_SLAVE_MASTER = 0x1006     # uns16 R (dip 2, 1: slave, 2: master)
REG_DIP3_T3_PROBE_ON = 0x1007  # uns16 R (0: T3 probe off, 1: T3 probe on)


REG_MACHINE_STATE = 0x100F    # uns16 R (0: OFF, 1: ON)
REG_FAN_ONLY_MODE = 0x1010    # uns16 R (0: OFF, 1: ON)
REG_AUTO_MODE = 0x1011        # uns16 R (0: OFF, 1: ON)
REG_SEASON_IN_USE = 0x1013    # uns16 R (0: Summer, 1: Winter)
REG_T2_PROBE_FOUND = 0x1014    # uns16 R (0: No, 1: Yes)

REG_AUTO_VENT = 0x1017        # uns16 R (0: OFF, 1: ON)
REG_FAN_MIN_STATE = 0x1019    # uns16 R (0: OFF, 1: ON)
REG_FAN_MED_STATE = 0x101A    # uns16 R (0: OFF, 1: ON)
REG_FAN_MAX_STATE = 0x101B    # uns16 R (0: OFF, 1: ON)

REG_T1_FAULT = 0x1028        # uns16 R (0: OFF, 1: ON)
REG_T2_FAULT = 0x1029        # uns16 R (0: OFF, 1: ON)
REG_T3_FAULT = 0x102A        # uns16 R (0: OFF, 1: ON)
REG_CONDENS_ALARM = 0x102B   # uns16 R (0: OFF, 1: ON)

REG_SUMMER_SETPOINT = 0x102D  # sig16 RW (temp * 10)
REG_WINTER_SETPOINT = 0x102E  # sig16 RW (temp * 10)


REG_BOARD_TIME = 0x105F       # uns32 R (2 registers)
REG_MACHINE_TIME = 0x1069     # uns32 R (2 registers)

REG_TMB_PRESENT = 0x1072      # uns16 R (0: Absent, 1: Present)
REG_IR_PRESENT = 0x1073       # uns16 R (0: Absent, 1: Present)

# Commands (Write Only or Writeable)
CMD_ON_OFF = 0x105C           # uns16 W (1: ON, 0: OFF)
CMD_MODE = 0x105D             # uns16 W (0: Summer, 1: Winter, 2: Only Ventilation, 3: Auto)
CMD_FAN = 0x105E              # uns16 W (0: Auto, 1: Min, 2: Med, 3: Max)


