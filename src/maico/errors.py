from enum import Enum, auto
from dataclasses import dataclass


class ErrorCode(Enum):
    DCAM_NOT_INITIALIZED = auto()
    DCAM_INIT_FAILED = auto()
    DEVICE_OPEN_FAILED = auto()
    DEVICE_NOT_FOUND = auto()
    INVALID_PARAMETER = auto()
    INVALID_STATE_TRANSITION = auto()
    PROPERTY_SET_FAILED = auto()
    PROPERTY_GET_FAILED = auto()
    TRIGGER_FIRE_FAILED = auto()
    HARDWARE_TIMEOUT = auto()
    BUFFER_ALLOCATION_FAILED = auto()
    SAFETY_GUARD_VIOLATION = auto()
    UNKNOWN_ERROR = auto()


@dataclass(frozen=True)
class MaicoError:
    code: ErrorCode
    message: str
    context: dict[str, str | int | float] | None = None

    def __str__(self) -> str:
        base_msg = f"[{self.code.name}] {self.message}"
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{base_msg} (Context: {context_str})"
        return base_msg


def create_error(
    code: ErrorCode,
    message: str,
    **context: str | int | float
) -> MaicoError:
    return MaicoError(
        code=code,
        message=message,
        context=context if context else None
    )
