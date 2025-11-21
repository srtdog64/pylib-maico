# pylib-maico

L2 Hardware Abstraction Layer for MAICO Laser Control System via Hamamatsu DCAM-API

## Overview

`pylib-maico` is a pure Python library providing safe, high-level control over MAICO laser systems through the Hamamatsu DCAM-API. This library implements robust hardware safeguards, FSM-based state management, and Result-pattern error handling.

## Key Features

- **Hardware Safe Guards** preventing dangerous state transitions
- **Thermal Protection** with automatic debounce (500ms cooldown between laser toggles)
- **FSM-based state management** for predictable operation
- **Result-pattern error handling** with no exceptions in business logic
- **ctypes-based wrapper** eliminating external dependencies
- **Thread-safe operations** using Python's GIL
- **✨ Simulation Mode** for hardware-independent development

## Design Principles

This library strictly adheres to BSD style coding standards and implements:
- Guard Clause pattern for input validation
- Dictionary Dispatch for command handling
- Maximum 25-line method limit
- Cyclomatic Complexity ≤ 8
- No exceptions in business logic layer

## Requirements

- Python 3.10+
- Hamamatsu DCAM-API v4.0+ (Windows/Linux) - **Not required for simulation mode**
- NumPy 1.24+

## Installation

### Development Mode
```bash
poetry install
```

### Production Mode
```bash
pip install pylib-maico
```

## Quick Start

### Simulation Mode (No Hardware Required)

Perfect for development in cafes, trains, or anywhere without hardware:

```python
from maico import MaicoController, MaicoConfig

config = MaicoConfig(
    device_index=0,
    simulation_mode=True  # ← Enable simulation
)

controller = MaicoController(config)

result = controller.initialize()
if result.is_ok():
    print("✓ Controller ready (simulation)")
    controller.laser_on()
```

### Real Hardware Mode

```python
from maico import MaicoController, MaicoConfig

config = MaicoConfig(
    device_index=0,
    simulation_mode=False
)

controller = MaicoController(config)

result = controller.initialize()
if result.is_err():
    print(f"Initialization failed: {result.unwrap_err()}")
    exit(1)

result = controller.laser_on()
if result.is_ok():
    print("Laser activated successfully")
```

## Architecture

```
pylib-maico/
├── src/maico/
│   ├── __init__.py
│   ├── controller.py      # Main MAICO Controller (L2)
│   ├── dcam_wrapper.py    # High-level DCAM wrapper
│   ├── simulation.py      # ✨ Mock hardware for testing
│   ├── fsm.py            # Finite State Machine
│   ├── guards.py         # Hardware Safety Guards
│   ├── types.py          # Result types and enums
│   ├── errors.py         # Error definitions
│   └── core/             # Low-level DCAM bindings
│       ├── dcam_lib.py   # ctypes DLL wrapper
│       ├── structs.py    # DCAM C structures
│       └── enums.py      # DCAM constants
├── tests/
│   ├── test_controller.py
│   ├── test_controller_sim.py  # ✨ Simulation tests
│   ├── test_fsm.py
│   └── test_guards.py
└── docs/
    └── API.md
```

## Safety Features

The library implements multiple layers of safety:

1. **Pre-condition Guards**: Validate all inputs before hardware interaction
2. **State Transition Guards**: Prevent invalid state changes
3. **Hardware Limits**: Enforce manufacturer-specified boundaries
4. **Thermal Protection**: 500ms cooldown between laser ON/OFF transitions
5. **Timeout Protection**: Prevent indefinite blocking operations

### Thermal Protection Example

```python
controller.laser_on()
time.sleep(0.1)  # Too fast!
result = controller.laser_off()
# Result.Err: "Laser toggled too quickly (Thermal Protection)"
# cooldown_remaining_sec: 0.4

time.sleep(0.5)  # Wait for cooldown
result = controller.laser_off()  # Now succeeds
```

## Testing

### Run all tests (including simulation)
```bash
poetry run pytest
```

### Run only simulation tests
```bash
poetry run pytest tests/test_controller_sim.py
```

### Run hardware tests (requires DCAM-API)
```bash
poetry run pytest tests/test_controller.py
```

## Development Workflow

### Without Hardware (Recommended)
```bash
# Develop and test business logic
poetry run pytest tests/test_controller_sim.py

# Run example in simulation mode
python examples/basic_usage.py
```

### With Hardware
```bash
# Test against real hardware
python examples/basic_usage.py --real
```

## Why Simulation Mode?

**Problem**: MAICO hardware is expensive and not portable. How do you develop:
- In a cafe?
- On a train?
- At home without hardware?

**Solution**: `simulation_mode=True`
- Full FSM and safety guard validation
- No DLL loading required
- Instant feedback
- 100% test coverage possible

## Platform Support

- **Windows**: Full hardware support
- **Linux**: Full hardware support
- **macOS**: Simulation mode only (DCAM-API not available)

## License

MIT License - See LICENSE file for details

## Contributing

Please follow BSD coding style and ensure all tests pass before submitting PRs.
