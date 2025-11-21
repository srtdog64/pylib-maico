import time
from .types import MaicoState, Result, MaicoConfig
from .errors import MaicoError, ErrorCode, create_error


class HardwareSafetyGuards:
    def __init__(self, config: MaicoConfig) -> None:
        self._config = config
        self._last_toggle_time: float = 0.0
        self._min_toggle_interval: float = 0.5

    def check_power_limit(self, power_percent: int) -> Result[bool, MaicoError]:
        if power_percent < 0:
            return Result.err(create_error(
                ErrorCode.INVALID_PARAMETER,
                "Power percentage cannot be negative",
                requested_power=power_percent
            ))

        if power_percent > self._config.max_power_percent:
            return Result.err(create_error(
                ErrorCode.SAFETY_GUARD_VIOLATION,
                "Power exceeds configured maximum",
                requested_power=power_percent,
                max_allowed=self._config.max_power_percent
            ))

        return Result.ok(True)

    def check_exposure_time(self, exposure_ms: float) -> Result[bool, MaicoError]:
        if exposure_ms <= 0:
            return Result.err(create_error(
                ErrorCode.INVALID_PARAMETER,
                "Exposure time must be positive",
                requested_exposure=exposure_ms
            ))

        if exposure_ms > 10000.0:
            return Result.err(create_error(
                ErrorCode.SAFETY_GUARD_VIOLATION,
                "Exposure time exceeds safety limit (10000ms)",
                requested_exposure=exposure_ms
            ))

        return Result.ok(True)

    def check_rapid_state_change(
        self,
        from_state: MaicoState,
        to_state: MaicoState
    ) -> Result[bool, MaicoError]:
        is_toggle = {from_state, to_state} == {
            MaicoState.LASER_OFF,
            MaicoState.LASER_ON
        }
        
        if is_toggle:
            now = time.time()
            elapsed = now - self._last_toggle_time
            
            if elapsed < self._min_toggle_interval:
                remaining = self._min_toggle_interval - elapsed
                return Result.err(create_error(
                    ErrorCode.SAFETY_GUARD_VIOLATION,
                    "Laser toggled too quickly (Thermal Protection)",
                    cooldown_remaining_sec=round(remaining, 3),
                    min_interval_sec=self._min_toggle_interval
                ))
            
            self._last_toggle_time = now

        return Result.ok(True)

    def reset_error_count(self) -> None:
        pass

    def record_error(self) -> None:
        pass

    def reset_toggle_timer(self) -> None:
        self._last_toggle_time = 0.0
