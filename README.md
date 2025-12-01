# pylib-maico

MAICO C15890 Laser Controller Library for Python

A production-ready Python library for controlling Hamamatsu MAICO C15890 laser modules via DCAM-API.

## Critical Discovery

> **SI Code Analysis revealed that `dcamcap_start()` is the key to physical laser output!**

Simply setting `SUBUNIT_CONTROL` to ON is NOT sufficient to enable laser output. The correct sequence is:

1. Set `SUBUNIT_CONTROL` to ON
2. Set `SUBUNIT_LASERPOWER` to desired value  
3. Allocate buffer (`buf_alloc`)
4. **Start capture (`cap_start`)** ← This enables physical laser output!

Conversely, calling `cap_stop()` disables the physical laser output.

## Features

- **Result Pattern Error Handling**: No exceptions in business logic
- **FSM-based State Management**: Safe state transitions with guards
- **Thermal Protection**: Cooldown enforcement between laser toggles (500ms)
- **Simulation Mode**: Develop and test without hardware
- **Clean Architecture**: L1/L2 layer separation
- **Type Safety**: Full type hints with dataclasses

## Installation

```bash
pip install pylib-maico
```

Or for development:

```bash
git clone https://github.com/your-org/pylib-maico.git
cd pylib-maico
pip install -e .
```

## Quick Start

```python
from maico import MaicoController, MaicoConfig, TriggerSource

config = MaicoConfig(
    device_index=0,
    trigger_source=TriggerSource.SOFTWARE,
    simulation_mode=False,  # Set True for development without hardware
)

controller = MaicoController(config)

# Initialize
result = controller.initialize()
if result.is_err():
    print(f"Init failed: {result.unwrap_err()}")
    exit(1)

# Turn laser ON (subunit 0, 50% power)
# This internally calls: set_subunit_control(ON) + set_laser_power() + cap_start()
result = controller.laser_on(subunit_index=0, power_percent=50)
if result.is_ok():
    print("Laser is now ON - physical output enabled!")

# Get status
status = controller.get_status()
print(f"State: {status.state.name}")
print(f"Capture Running: {status.is_capture_running}")
print(f"Temperature: {status.temperature_celsius}C")

# Turn laser OFF
# This internally calls: cap_stop() + set_subunit_control(OFF)
result = controller.laser_off()

# Shutdown
controller.shutdown()
```

## API Reference

### MaicoController

| Method | Description |
|--------|-------------|
| `initialize()` | Initialize DCAM-API and open device |
| `laser_on(subunit_index, power_percent)` | Enable subunit + start capture (physical output) |
| `laser_off()` | Stop capture + disable subunit |
| `set_power(power_percent)` | Adjust laser power while running |
| `get_status()` | Get current controller status |
| `shutdown()` | Clean shutdown (auto laser-off) |

### MaicoConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `device_index` | int | 0 | DCAM device index |
| `trigger_source` | TriggerSource | SOFTWARE | Trigger source |
| `simulation_mode` | bool | False | Enable simulation mode |
| `max_power_percent` | int | 100 | Maximum allowed power |
| `buffer_frame_count` | int | 3 | Buffer frames for capture |

### LaserStatus

| Field | Type | Description |
|-------|------|-------------|
| `state` | MaicoState | Current FSM state |
| `is_laser_on` | bool | Logical laser state |
| `is_capture_running` | bool | Physical capture state |
| `current_power_percent` | int | Current power setting |
| `temperature_celsius` | float | Sensor temperature |
| `active_subunits` | tuple[SubunitStatus] | Subunit status list |

## State Machine

```
UNINITIALIZED → INITIALIZED → READY → LASER_OFF ⇄ LASER_ON
                                          ↓
                                      SHUTDOWN
```

## Simulation Mode

For development without hardware:

```python
config = MaicoConfig(simulation_mode=True)
controller = MaicoController(config)

# All operations work in simulation mode
controller.initialize()
controller.laser_on(subunit_index=0, power_percent=50)
status = controller.get_status()  # Returns simulated data
```

## Error Handling

```python
result = controller.laser_on(subunit_index=0, power_percent=150)

if result.is_err():
    error = result.unwrap_err()
    print(f"Error: {error.code.name}")
    print(f"Message: {error.message}")
    if error.context:
        print(f"Context: {error.context}")
```

## Testing

```bash
pytest tests/ -v
```

## License

BSD 3-Clause License

## Version History

- **v0.2.0**: Added `cap_start`/`cap_stop` sequence for physical laser output
- **v0.1.0**: Initial release with basic FSM and simulation mode
