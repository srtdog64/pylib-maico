import pytest
from maico import MaicoController, MaicoConfig


def test_controller_simulation_mode_initialization():
    config = MaicoConfig(simulation_mode=True)
    controller = MaicoController(config)
    
    result = controller.initialize()
    assert result.is_ok(), f"Initialization failed: {result.unwrap_err()}"


def test_controller_simulation_full_lifecycle():
    config = MaicoConfig(
        simulation_mode=True,
        max_power_percent=80,
        exposure_time_ms=10.0
    )
    controller = MaicoController(config)
    
    init_result = controller.initialize()
    assert init_result.is_ok()
    
    power_result = controller.set_power(50)
    assert power_result.is_ok()
    
    status = controller.get_status()
    assert status.simulation_mode is True
    assert status.current_power_percent == 50
    
    laser_on_result = controller.laser_on()
    assert laser_on_result.is_ok()
    assert controller.get_status().is_laser_on is True
    
    laser_off_result = controller.laser_off()
    assert laser_off_result.is_ok()
    assert controller.get_status().is_laser_on is False
    
    shutdown_result = controller.shutdown()
    assert shutdown_result.is_ok()


def test_simulation_safety_guards_enforced():
    config = MaicoConfig(simulation_mode=True, max_power_percent=50)
    controller = MaicoController(config)
    
    controller.initialize()
    
    result = controller.set_power(80)
    assert result.is_err()
    
    error = result.unwrap_err()
    from maico.errors import ErrorCode
    assert error.code == ErrorCode.SAFETY_GUARD_VIOLATION


def test_simulation_invalid_state_transitions():
    config = MaicoConfig(simulation_mode=True)
    controller = MaicoController(config)
    
    controller.initialize()
    
    result = controller.laser_on()
    assert result.is_err()


def test_simulation_rapid_state_change_detection():
    config = MaicoConfig(simulation_mode=True)
    controller = MaicoController(config)
    
    controller.initialize()
    
    for _ in range(4):
        controller.laser_on()
        controller.laser_off()
    
    status = controller.get_status()
    from maico.types import MaicoState
    assert status.state != MaicoState.ERROR


def test_simulation_temperature_reading():
    config = MaicoConfig(simulation_mode=True)
    controller = MaicoController(config)
    
    controller.initialize()
    
    status = controller.get_status()
    assert status.temperature_celsius >= 0.0
