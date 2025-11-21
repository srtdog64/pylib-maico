import pytest
import time
from maico.guards import HardwareSafetyGuards
from maico.types import MaicoConfig, MaicoState
from maico.errors import ErrorCode


@pytest.fixture
def guards():
    config = MaicoConfig(max_power_percent=80)
    return HardwareSafetyGuards(config)


def test_power_limit_valid(guards):
    result = guards.check_power_limit(50)
    assert result.is_ok()


def test_power_limit_negative(guards):
    result = guards.check_power_limit(-10)
    assert result.is_err()
    error = result.unwrap_err()
    assert error.code == ErrorCode.INVALID_PARAMETER


def test_power_limit_exceeds_max(guards):
    result = guards.check_power_limit(90)
    assert result.is_err()
    error = result.unwrap_err()
    assert error.code == ErrorCode.SAFETY_GUARD_VIOLATION


def test_exposure_time_valid(guards):
    result = guards.check_exposure_time(100.0)
    assert result.is_ok()


def test_exposure_time_negative(guards):
    result = guards.check_exposure_time(-5.0)
    assert result.is_err()
    error = result.unwrap_err()
    assert error.code == ErrorCode.INVALID_PARAMETER


def test_exposure_time_exceeds_limit(guards):
    result = guards.check_exposure_time(15000.0)
    assert result.is_err()
    error = result.unwrap_err()
    assert error.code == ErrorCode.SAFETY_GUARD_VIOLATION


def test_rapid_toggle_debounce(guards):
    result1 = guards.check_rapid_state_change(
        MaicoState.LASER_OFF,
        MaicoState.LASER_ON
    )
    assert result1.is_ok()
    
    result2 = guards.check_rapid_state_change(
        MaicoState.LASER_ON,
        MaicoState.LASER_OFF
    )
    assert result2.is_err()
    error = result2.unwrap_err()
    assert error.code == ErrorCode.SAFETY_GUARD_VIOLATION
    assert "cooldown_remaining_sec" in error.context


def test_rapid_toggle_after_cooldown(guards):
    result1 = guards.check_rapid_state_change(
        MaicoState.LASER_OFF,
        MaicoState.LASER_ON
    )
    assert result1.is_ok()
    
    time.sleep(0.6)
    
    result2 = guards.check_rapid_state_change(
        MaicoState.LASER_ON,
        MaicoState.LASER_OFF
    )
    assert result2.is_ok()


def test_non_toggle_transitions_not_affected(guards):
    result = guards.check_rapid_state_change(
        MaicoState.READY,
        MaicoState.LASER_OFF
    )
    assert result.is_ok()
    
    result = guards.check_rapid_state_change(
        MaicoState.LASER_OFF,
        MaicoState.READY
    )
    assert result.is_ok()


def test_reset_toggle_timer(guards):
    guards.check_rapid_state_change(
        MaicoState.LASER_OFF,
        MaicoState.LASER_ON
    )
    
    guards.reset_toggle_timer()
    
    result = guards.check_rapid_state_change(
        MaicoState.LASER_ON,
        MaicoState.LASER_OFF
    )
    assert result.is_ok()
