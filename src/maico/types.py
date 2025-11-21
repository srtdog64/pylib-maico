from typing import TypeVar, Generic, Union
from enum import IntEnum, auto
from dataclasses import dataclass


T = TypeVar('T')
E = TypeVar('E')


class Result(Generic[T, E]):
    def __init__(self, value: Union[T, E], is_success: bool) -> None:
        self._value = value
        self._is_success = is_success

    @staticmethod
    def ok(value: T) -> 'Result[T, E]':
        return Result(value, True)

    @staticmethod
    def err(error: E) -> 'Result[T, E]':
        return Result(error, False)

    def is_ok(self) -> bool:
        return self._is_success

    def is_err(self) -> bool:
        return not self._is_success

    def unwrap(self) -> T:
        if not self._is_success:
            raise ValueError("Called unwrap on an Err value")
        return self._value

    def unwrap_err(self) -> E:
        if self._is_success:
            raise ValueError("Called unwrap_err on an Ok value")
        return self._value

    def unwrap_or(self, default: T) -> T:
        if self._is_success:
            return self._value
        return default


class MaicoState(IntEnum):
    UNINITIALIZED = auto()
    INITIALIZED = auto()
    READY = auto()
    LASER_ON = auto()
    LASER_OFF = auto()
    ERROR = auto()
    SHUTDOWN = auto()


class TriggerSource(IntEnum):
    INTERNAL = 1
    EXTERNAL = 2
    SOFTWARE = 3


class OutputTriggerKind(IntEnum):
    LOW = 1
    EXPOSURE = 2
    PROGRAMABLE = 3
    TRIGGER_READY = 4
    HIGH = 5


@dataclass(frozen=True)
class MaicoConfig:
    device_index: int = 0
    trigger_source: TriggerSource = TriggerSource.SOFTWARE
    output_trigger_kind: OutputTriggerKind = OutputTriggerKind.EXPOSURE
    exposure_time_ms: float = 10.0
    max_power_percent: int = 100
    safety_timeout_ms: int = 5000
    simulation_mode: bool = False


@dataclass(frozen=True)
class LaserStatus:
    state: MaicoState
    is_laser_on: bool
    current_power_percent: int
    temperature_celsius: float
    simulation_mode: bool = False
    last_error: str | None = None
