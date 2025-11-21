# MAICO API Reference

## MaicoController

Main controller class for MAICO laser system.

### Constructor

```python
controller = MaicoController(config: MaicoConfig)
```

### Methods

#### initialize() -> Result[None, MaicoError]

Initializes DCAM-API and opens the device.

**Returns:** Result indicating success or error

**Example:**
```python
result = controller.initialize()
if result.is_err():
    print(f"Error: {result.unwrap_err()}")
```

#### laser_on() -> Result[None, MaicoError]

Activates the laser by firing a software trigger.

**Pre-conditions:**
- Controller must be initialized
- Current state must be LASER_OFF

**Returns:** Result indicating success or error

#### laser_off() -> Result[None, MaicoError]

Deactivates the laser.

**Pre-conditions:**
- Current state must be LASER_ON

**Returns:** Result indicating success or error

#### shutdown() -> Result[None, MaicoError]

Safely shuts down the controller and releases hardware resources.

**Returns:** Result indicating success or error

#### get_status() -> LaserStatus

Retrieves current system status.

**Returns:** LaserStatus dataclass containing:
- state: Current MaicoState
- is_laser_on: Boolean indicating laser status
- current_power_percent: Current power setting
- temperature_celsius: Sensor temperature

#### set_power(power_percent: int) -> Result[None, MaicoError]

Sets the laser power percentage.

**Parameters:**
- power_percent: Integer between 0 and max_power_percent (from config)

**Returns:** Result indicating success or error

## Types

### MaicoConfig

Configuration for MAICO controller.

**Fields:**
- device_index: int = 0
- trigger_source: TriggerSource = SOFTWARE
- output_trigger_kind: OutputTriggerKind = EXPOSURE
- exposure_time_ms: float = 10.0
- max_power_percent: int = 100
- safety_timeout_ms: int = 5000

### MaicoState

Enum representing controller states:
- UNINITIALIZED
- INITIALIZED
- READY
- LASER_ON
- LASER_OFF
- ERROR
- SHUTDOWN

### Result[T, E]

Generic result type for error handling.

**Methods:**
- is_ok() -> bool
- is_err() -> bool
- unwrap() -> T
- unwrap_err() -> E
- unwrap_or(default: T) -> T

## Error Handling

All operations return Result types. Never use exceptions for control flow.

**Example:**
```python
result = controller.laser_on()
if result.is_ok():
    print("Laser activated")
else:
    error = result.unwrap_err()
    print(f"Failed: {error}")
```

## Safety Features

The library implements multiple safety guards:

1. Power Limit Enforcement
2. Exposure Time Validation
3. Rapid State Change Detection
4. State Transition Guards

All guards use Result pattern and never raise exceptions.
