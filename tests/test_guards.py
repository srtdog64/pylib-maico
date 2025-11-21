import pytest
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


def test_rapid_state_change_detection(guards):
    for _ in range(3):
        guards.record_error()
    
    result = guards.check_rapid_state_change(
        MaicoState.LASER_OFF,
        MaicoState.LASER_ON
    )
    assert result.is_err()
    error = result.unwrap_err()
    assert error.code == ErrorCode.SAFETY_GUARD_VIOLATION


def test_error_count_reset(guards):
    guards.record_error()
    guards.record_error()
    guards.reset_error_count()
    
    result = guards.check_rapid_state_change(
        MaicoState.LASER_OFF,
        MaicoState.LASER_ON
    )
    assert result.is_ok()
