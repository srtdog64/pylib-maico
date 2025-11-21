from typing import Callable
from .types import (
    Result,
    MaicoState,
    MaicoConfig,
    LaserStatus,
    TriggerSource,
    OutputTriggerKind
)
from .errors import MaicoError, ErrorCode, create_error
from .fsm import MaicoFSM
from .guards import HardwareSafetyGuards
from .dcam_wrapper import DCAMWrapper
from .core import DCAMPropertyID


class MaicoController:
    def __init__(self, config: MaicoConfig) -> None:
        self._config = config
        self._fsm = MaicoFSM()
        self._guards = HardwareSafetyGuards(config)
        self._dcam = DCAMWrapper(simulation_mode=config.simulation_mode)
        self._is_laser_on = False
        self._current_power = 0

        self._fsm.add_guard(self._guards.check_rapid_state_change)
        
        self._command_dispatch: dict[str, Callable[[], Result[None, MaicoError]]] = {
            "initialize": self._execute_initialize,
            "laser_on": self._execute_laser_on,
            "laser_off": self._execute_laser_off,
            "shutdown": self._execute_shutdown,
        }

    def initialize(self) -> Result[None, MaicoError]:
        if self._fsm.get_current_state() != MaicoState.UNINITIALIZED:
            return Result.err(create_error(
                ErrorCode.INVALID_STATE_TRANSITION,
                "Controller already initialized"
            ))

        result = self._execute_command("initialize")
        if result.is_err():
            self._fsm.force_error_state()
        return result

    def laser_on(self) -> Result[None, MaicoError]:
        current_state = self._fsm.get_current_state()
        if current_state != MaicoState.LASER_OFF:
            return Result.err(create_error(
                ErrorCode.INVALID_STATE_TRANSITION,
                "Cannot turn laser on from current state",
                current_state=current_state.name
            ))

        result = self._execute_command("laser_on")
        if result.is_err():
            self._guards.record_error()
        else:
            self._guards.reset_error_count()
        return result

    def laser_off(self) -> Result[None, MaicoError]:
        current_state = self._fsm.get_current_state()
        if current_state != MaicoState.LASER_ON:
            return Result.err(create_error(
                ErrorCode.INVALID_STATE_TRANSITION,
                "Cannot turn laser off from current state",
                current_state=current_state.name
            ))

        result = self._execute_command("laser_off")
        if result.is_err():
            self._guards.record_error()
        else:
            self._guards.reset_error_count()
        return result

    def shutdown(self) -> Result[None, MaicoError]:
        if self._is_laser_on:
            laser_off_result = self.laser_off()
            if laser_off_result.is_err():
                return laser_off_result

        return self._execute_command("shutdown")

    def get_status(self) -> LaserStatus:
        temp_result = self._dcam.get_sensor_temperature()
        temperature = temp_result.unwrap_or(25.0)

        return LaserStatus(
            state=self._fsm.get_current_state(),
            is_laser_on=self._is_laser_on,
            current_power_percent=self._current_power,
            temperature_celsius=temperature,
            simulation_mode=self._config.simulation_mode
        )

    def set_power(self, power_percent: int) -> Result[None, MaicoError]:
        guard_result = self._guards.check_power_limit(power_percent)
        if guard_result.is_err():
            return Result.err(guard_result.unwrap_err())

        self._current_power = power_percent
        return Result.ok(None)

    def _execute_command(self, command: str) -> Result[None, MaicoError]:
        handler = self._command_dispatch.get(command)
        if handler is None:
            return Result.err(create_error(
                ErrorCode.INVALID_PARAMETER,
                f"Unknown command: {command}"
            ))

        return handler()

    def _execute_initialize(self) -> Result[None, MaicoError]:
        init_result = self._dcam.initialize()
        if init_result.is_err():
            return Result.err(init_result.unwrap_err())

        transition_result = self._fsm.transition(MaicoState.INITIALIZED)
        if transition_result.is_err():
            return Result.err(transition_result.unwrap_err())

        open_result = self._dcam.open_device(self._config.device_index)
        if open_result.is_err():
            return Result.err(open_result.unwrap_err())

        transition_result = self._fsm.transition(MaicoState.READY)
        if transition_result.is_err():
            return Result.err(transition_result.unwrap_err())

        config_result = self._configure_hardware()
        if config_result.is_err():
            return Result.err(config_result.unwrap_err())

        transition_result = self._fsm.transition(MaicoState.LASER_OFF)
        return Result.ok(None) if transition_result.is_ok() else Result.err(
            transition_result.unwrap_err()
        )

    def _configure_hardware(self) -> Result[None, MaicoError]:
        trigger_result = self._dcam.set_property(
            DCAMPropertyID.TRIGGERSOURCE,
            float(self._config.trigger_source.value)
        )
        if trigger_result.is_err():
            return Result.err(trigger_result.unwrap_err())

        output_result = self._dcam.set_property(
            DCAMPropertyID.OUTPUTTRIGGER_KIND,
            float(self._config.output_trigger_kind.value)
        )
        if output_result.is_err():
            return Result.err(output_result.unwrap_err())

        exposure_ms = self._config.exposure_time_ms
        guard_result = self._guards.check_exposure_time(exposure_ms)
        if guard_result.is_err():
            return Result.err(guard_result.unwrap_err())

        exposure_result = self._dcam.set_property(
            DCAMPropertyID.EXPOSURETIME,
            exposure_ms / 1000.0
        )
        
        return Result.ok(None) if exposure_result.is_ok() else Result.err(
            exposure_result.unwrap_err()
        )

    def _execute_laser_on(self) -> Result[None, MaicoError]:
        transition_result = self._fsm.transition(MaicoState.LASER_ON)
        if transition_result.is_err():
            return Result.err(transition_result.unwrap_err())

        trigger_result = self._dcam.fire_trigger()
        if trigger_result.is_err():
            self._fsm.force_error_state()
            return Result.err(trigger_result.unwrap_err())

        self._is_laser_on = True
        return Result.ok(None)

    def _execute_laser_off(self) -> Result[None, MaicoError]:
        transition_result = self._fsm.transition(MaicoState.LASER_OFF)
        if transition_result.is_err():
            return Result.err(transition_result.unwrap_err())

        self._is_laser_on = False
        return Result.ok(None)

    def _execute_shutdown(self) -> Result[None, MaicoError]:
        transition_result = self._fsm.transition(MaicoState.SHUTDOWN)
        if transition_result.is_err():
            return Result.err(transition_result.unwrap_err())

        close_result = self._dcam.close_device()
        if close_result.is_err():
            return Result.err(close_result.unwrap_err())

        uninit_result = self._dcam.uninitialize()
        return Result.ok(None) if uninit_result.is_ok() else Result.err(
            uninit_result.unwrap_err()
        )
