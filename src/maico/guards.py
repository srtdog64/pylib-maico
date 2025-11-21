from .types import MaicoState, Result, MaicoConfig
from .errors import MaicoError, ErrorCode, create_error


class HardwareSafetyGuards:
    def __init__(self, config: MaicoConfig) -> None:
        self._config = config
        self._consecutive_errors = 0
        self._max_consecutive_errors = 3

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
        dangerous_transitions = [
            (MaicoState.LASER_OFF, MaicoState.LASER_ON),
            (MaicoState.LASER_ON, MaicoState.LASER_OFF)
        ]

        if (from_state, to_state) in dangerous_transitions:
            if self._consecutive_errors >= self._max_consecutive_errors:
                return Result.err(create_error(
                    ErrorCode.SAFETY_GUARD_VIOLATION,
                    "Too many rapid state changes detected",
                    consecutive_errors=self._consecutive_errors
                ))

        return Result.ok(True)

    def record_error(self) -> None:
        self._consecutive_errors += 1

    def reset_error_count(self) -> None:
        self._consecutive_errors = 0
