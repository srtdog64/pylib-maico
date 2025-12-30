from typing import Callable
from .types import (
    Result,
    MaicoState,
    MaicoConfig,
    LaserStatus,
    SubunitStatus,
    ScanConfig,
    TriggerSource,
    OutputTriggerKind,
)
from .errors import MaicoError, ErrorCode, create_error
from .fsm import MaicoFSM
from .guards import HardwareSafetyGuards
from .dcam_wrapper import DCAMWrapper
from .core import DCAMPropertyID, DCAMSubunitControl, DCAMScanMode


class MaicoController:
    def __init__(self, config: MaicoConfig) -> None:
        self._config = config
        self._fsm = MaicoFSM()
        self._guards = HardwareSafetyGuards(config)
        self._dcam = DCAMWrapper(simulation_mode=config.simulation_mode)
        self._is_laser_on = False
        self._current_power = 0
        self._active_subunit_index = 0

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

    def laser_on(self, subunit_index: int = 0, power_percent: int = 30) -> Result[None, MaicoError]:
        current_state = self._fsm.get_current_state()
        if current_state != MaicoState.LASER_OFF:
            return Result.err(create_error(
                ErrorCode.INVALID_STATE_TRANSITION,
                "Cannot turn laser on from current state",
                current_state=current_state.name
            ))

        guard_result = self._guards.check_power_limit(power_percent)
        if guard_result.is_err():
            return Result.err(guard_result.unwrap_err())

        self._active_subunit_index = subunit_index
        self._current_power = power_percent

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

        subunit_statuses = self._get_all_subunit_statuses()

        return LaserStatus(
            state=self._fsm.get_current_state(),
            is_laser_on=self._is_laser_on,
            is_capture_running=self._dcam.is_capture_running(),
            current_power_percent=self._current_power,
            temperature_celsius=temperature,
            active_subunits=subunit_statuses,
            simulation_mode=self._config.simulation_mode
        )

    def set_power(self, power_percent: int) -> Result[None, MaicoError]:
        guard_result = self._guards.check_power_limit(power_percent)
        if guard_result.is_err():
            return Result.err(guard_result.unwrap_err())

        if self._is_laser_on:
            power_result = self._dcam.set_subunit_laser_power(
                self._active_subunit_index, power_percent
            )
            if power_result.is_err():
                return power_result

        self._current_power = power_percent
        return Result.ok(None)

    def set_pmt_gain(
        self, subunit_index: int, gain: float
    ) -> Result[None, MaicoError]:
        return self._dcam.set_subunit_pmt_gain(subunit_index, gain)

    def get_scan_config(self) -> Result[ScanConfig, MaicoError]:
        mode_result = self._dcam.get_scan_mode()
        if mode_result.is_err():
            return Result.err(mode_result.unwrap_err())

        lines_result = self._dcam.get_scan_lines()
        zoom_result = self._dcam.get_zoom()
        binning_result = self._dcam.get_binning()
        avg_result = self._dcam.get_frame_averaging()

        mode = mode_result.unwrap()
        mode_str = "sequential" if mode == DCAMScanMode.SEQUENTIAL else "simultaneous"

        return Result.ok(ScanConfig(
            mode=mode_str,
            lines=lines_result.unwrap_or(480),
            zoom=zoom_result.unwrap_or(1),
            binning=binning_result.unwrap_or(1),
            frame_averaging_enabled=avg_result.unwrap_or((False, 2))[0],
            frame_averaging_frames=avg_result.unwrap_or((False, 2))[1],
        ))

    def set_scan_config(self, config: ScanConfig) -> Result[None, MaicoError]:
        mode = (
            DCAMScanMode.SEQUENTIAL
            if config.mode == "sequential"
            else DCAMScanMode.SIMULTANEOUS
        )

        mode_result = self._dcam.set_scan_mode(mode)
        if mode_result.is_err():
            return mode_result

        lines_result = self._dcam.set_scan_lines(config.lines)
        if lines_result.is_err():
            return lines_result

        zoom_result = self._dcam.set_zoom(config.zoom)
        if zoom_result.is_err():
            return zoom_result

        binning_result = self._dcam.set_binning(config.binning)
        if binning_result.is_err():
            return binning_result

        avg_result = self._dcam.set_frame_averaging(
            config.frame_averaging_enabled,
            config.frame_averaging_frames
        )
        if avg_result.is_err():
            return avg_result

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
        if exposure_result.is_err():
            return Result.err(exposure_result.unwrap_err())

        alloc_result = self._dcam.buf_alloc(self._config.buffer_frame_count)
        if alloc_result.is_err():
            return Result.err(alloc_result.unwrap_err())

        return Result.ok(None)

    def _execute_laser_on(self) -> Result[None, MaicoError]:
        if self._dcam.is_capture_running():
            stop_result = self._dcam.cap_stop()
            if stop_result.is_err():
                return Result.err(stop_result.unwrap_err())

        control_check = self._dcam.get_subunit_control(self._active_subunit_index)
        if control_check.is_err():
            return Result.err(control_check.unwrap_err())

        if control_check.unwrap() == DCAMSubunitControl.NOT_INSTALLED:
            return Result.err(create_error(
                ErrorCode.SUBUNIT_NOT_INSTALLED,
                "Subunit is not installed",
                subunit_index=self._active_subunit_index
            ))

        control_result = self._dcam.set_subunit_control(
            self._active_subunit_index, DCAMSubunitControl.ON
        )
        if control_result.is_err():
            return Result.err(control_result.unwrap_err())

        power_result = self._dcam.set_subunit_laser_power(
            self._active_subunit_index, self._current_power
        )
        if power_result.is_err():
            return Result.err(power_result.unwrap_err())

        transition_result = self._fsm.transition(MaicoState.LASER_ON)
        if transition_result.is_err():
            return Result.err(transition_result.unwrap_err())

        cap_result = self._dcam.cap_start()
        if cap_result.is_err():
            self._fsm.force_error_state()
            return Result.err(cap_result.unwrap_err())

        self._is_laser_on = True
        return Result.ok(None)

    def _execute_laser_off(self) -> Result[None, MaicoError]:
        stop_result = self._dcam.cap_stop()
        if stop_result.is_err():
            return Result.err(stop_result.unwrap_err())

        control_result = self._dcam.set_subunit_control(
            self._active_subunit_index, DCAMSubunitControl.OFF
        )
        if control_result.is_err():
            return Result.err(control_result.unwrap_err())

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

    def _get_all_subunit_statuses(self) -> tuple[SubunitStatus, ...]:
        count_result = self._dcam.get_subunit_count()
        if count_result.is_err():
            return ()

        subunit_count = count_result.unwrap()
        statuses = []

        for i in range(subunit_count):
            control_result = self._dcam.get_subunit_control(i)
            wavelength_result = self._dcam.get_subunit_wavelength(i)
            power_result = self._dcam.get_subunit_laser_power(i)
            gain_result = self._dcam.get_subunit_pmt_gain(i)

            if control_result.is_err():
                continue

            control = control_result.unwrap()
            wavelength = wavelength_result.unwrap_or(0)
            power = power_result.unwrap_or(0)
            gain = gain_result.unwrap_or(0.7)

            statuses.append(SubunitStatus(
                index=i,
                wavelength_nm=wavelength,
                is_on=(control == DCAMSubunitControl.ON),
                power_percent=power,
                pmt_gain=gain,
                is_installed=(control != DCAMSubunitControl.NOT_INSTALLED)
            ))

        return tuple(statuses)
