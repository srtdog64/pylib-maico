import pytest
from maico.types import MaicoState, Result
from maico.errors import ErrorCode
from maico.fsm import MaicoFSM


def test_fsm_initial_state():
    fsm = MaicoFSM()
    assert fsm.get_current_state() == MaicoState.UNINITIALIZED


def test_valid_state_transition():
    fsm = MaicoFSM()
    result = fsm.transition(MaicoState.INITIALIZED)
    assert result.is_ok()
    assert fsm.get_current_state() == MaicoState.INITIALIZED


def test_invalid_state_transition():
    fsm = MaicoFSM()
    result = fsm.transition(MaicoState.LASER_ON)
    assert result.is_err()
    error = result.unwrap_err()
    assert error.code == ErrorCode.INVALID_STATE_TRANSITION


def test_fsm_full_lifecycle():
    fsm = MaicoFSM()
    
    transitions = [
        MaicoState.INITIALIZED,
        MaicoState.READY,
        MaicoState.LASER_OFF,
        MaicoState.LASER_ON,
        MaicoState.LASER_OFF,
        MaicoState.READY,
        MaicoState.SHUTDOWN
    ]
    
    for target_state in transitions:
        result = fsm.transition(target_state)
        assert result.is_ok(), f"Failed to transition to {target_state.name}"
        assert fsm.get_current_state() == target_state


def test_fsm_error_state_always_accessible():
    fsm = MaicoFSM()
    assert fsm.can_transition(MaicoState.ERROR)
    
    fsm.transition(MaicoState.INITIALIZED)
    assert fsm.can_transition(MaicoState.ERROR)
    
    fsm.force_error_state()
    assert fsm.get_current_state() == MaicoState.ERROR


def test_fsm_guard_rejection():
    def rejecting_guard(from_state, to_state):
        from maico.errors import create_error
        return Result.err(create_error(
            ErrorCode.SAFETY_GUARD_VIOLATION,
            "Guard rejected transition"
        ))
    
    fsm = MaicoFSM()
    fsm.add_guard(rejecting_guard)
    
    result = fsm.transition(MaicoState.INITIALIZED)
    assert result.is_err()
    error = result.unwrap_err()
    assert error.code == ErrorCode.SAFETY_GUARD_VIOLATION
