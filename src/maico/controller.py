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

    def start_capture(self) -> Result[None, MaicoError]:
        """Start capture without changing laser state."""
        current_state = self._fsm.get_current_state()
        if current_state in (MaicoState.UNINITIALIZED, MaicoState.ERROR, MaicoState.SHUTDOWN):
            return Result.err(create_error(
                ErrorCode.INVALID_STATE_TRANSITION,
                "Cannot start capture from current state",
                current_state=current_state.name
            ))

        return self._dcam.cap_start()

    def stop_capture(self) -> Result[None, MaicoError]:
        """Stop capture without changing laser state."""
        if self._fsm.get_current_state() == MaicoState.UNINITIALIZED:
            return Result.err(create_error(
                ErrorCode.INVALID_STATE_TRANSITION,
                "Cannot stop capture before initialization"
            ))

        return self._dcam.cap_stop()

    def all_lasers_off(self) -> Result[None, MaicoError]:
        """Turn off all installed subunits and stop capture."""
        if self._fsm.get_current_state() == MaicoState.UNINITIALIZED:
            return Result.err(create_error(
                ErrorCode.INVALID_STATE_TRANSITION,
                "Cannot turn off lasers before initialization"
            ))

        stop_result = self._dcam.cap_stop()
        if stop_result.is_err():
            return stop_result

        count_result = self._dcam.get_subunit_count()
        if count_result.is_err():
            return Result.err(count_result.unwrap_err())

        for i in range(count_result.unwrap()):
            control_result = self._dcam.get_subunit_control(i)
            if control_result.is_err():
                return Result.err(control_result.unwrap_err())

            if control_result.unwrap() == DCAMSubunitControl.NOT_INSTALLED:
                continue

            off_result = self._dcam.set_subunit_control(i, DCAMSubunitControl.OFF)
            if off_result.is_err():
                return Result.err(off_result.unwrap_err())

        self._is_laser_on = False
        if self._fsm.get_current_state() == MaicoState.LASER_ON:
            self._fsm.transition(MaicoState.LASER_OFF)

        return Result.ok(None)

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

    # --- Multi-channel API (bypasses FSM) ---

    def set_channel_enabled(
        self, channel_index: int, enabled: bool, power: int = 30
    ) -> Result[None, MaicoError]:
        """Enable/disable a specific laser channel (FSM-independent).

        This method allows multiple channels to be ON simultaneously.
        Use this for multi-channel operation instead of laser_on()/laser_off().

        IMPORTANT: Laser physically outputs only when capture is running.
        This method automatically manages capture start/stop.

        Args:
            channel_index: Subunit index (0-based)
            enabled: True to turn ON, False to turn OFF
            power: Power level (0-100) when enabling (default 30)

        Returns:
            Result[None, MaicoError]
        """
        current_state = self._fsm.get_current_state()
        if current_state not in (MaicoState.LASER_OFF, MaicoState.LASER_ON):
            return Result.err(create_error(
                ErrorCode.INVALID_STATE_TRANSITION,
                "Controller must be initialized before controlling channels",
                current_state=current_state.name
            ))

        # Check if subunit is installed
        control_check = self._dcam.get_subunit_control(channel_index)
        if control_check.is_err():
            return Result.err(control_check.unwrap_err())

        if control_check.unwrap() == DCAMSubunitControl.NOT_INSTALLED:
            return Result.err(create_error(
                ErrorCode.SUBUNIT_NOT_INSTALLED,
                "Subunit is not installed",
                subunit_index=channel_index
            ))

        # When enabling: set power BEFORE cap_start (critical for laser output)
        if enabled:
            guard_result = self._guards.check_power_limit(power)
            if guard_result.is_err():
                return Result.err(guard_result.unwrap_err())

            power_result = self._dcam.set_subunit_laser_power(channel_index, power)
            if power_result.is_err():
                return Result.err(power_result.unwrap_err())

        # Set subunit control
        control = DCAMSubunitControl.ON if enabled else DCAMSubunitControl.OFF
        control_result = self._dcam.set_subunit_control(channel_index, control)
        if control_result.is_err():
            return Result.err(control_result.unwrap_err())

        # Update FSM state and manage capture based on channel states
        # (cap_start is called here - power is already set above)
        self._update_laser_state_and_capture()

        return Result.ok(None)

    def set_channel_power(
        self, channel_index: int, power_percent: int
    ) -> Result[None, MaicoError]:
        """Set power for a specific channel.

        Args:
            channel_index: Subunit index (0-based)
            power_percent: Power level (0-100)

        Returns:
            Result[None, MaicoError]
        """
        guard_result = self._guards.check_power_limit(power_percent)
        if guard_result.is_err():
            return Result.err(guard_result.unwrap_err())

        return self._dcam.set_subunit_laser_power(channel_index, power_percent)

    def _update_laser_state_and_capture(self) -> None:
        """Update FSM state and manage capture based on channel states.

        - When any channel turns ON: start capture (laser physically outputs)
        - When all channels turn OFF: stop capture
        """
        statuses = self._get_all_subunit_statuses()
        any_on = any(s.is_on for s in statuses)
        was_on = self._is_laser_on
        self._is_laser_on = any_on

        # Manage capture: laser only outputs when capture is running
        if any_on and not was_on:
            # First channel turned ON -> start capture
            if not self._dcam.is_capture_running():
                cap_result = self._dcam.cap_start()
                if cap_result.is_err():
                    print(f"[MaicoController] Warning: cap_start failed: {cap_result.unwrap_err()}")
        elif not any_on and was_on:
            # All channels turned OFF -> stop capture
            if self._dcam.is_capture_running():
                self._dcam.cap_stop()

        # Sync FSM state with actual hardware state
        current_state = self._fsm.get_current_state()
        if any_on and current_state == MaicoState.LASER_OFF:
            self._fsm.transition(MaicoState.LASER_ON)
        elif not any_on and current_state == MaicoState.LASER_ON:
            self._fsm.transition(MaicoState.LASER_OFF)

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
