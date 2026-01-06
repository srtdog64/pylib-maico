from typing import TypeVar, Generic, Union
from enum import IntEnum, auto
from dataclasses import dataclass, field


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
class SubunitConfig:
    index: int
    power_percent: int = 30
    enabled: bool = True


@dataclass(frozen=True)
class MaicoConfig:
    device_index: int = 0
    trigger_source: TriggerSource = TriggerSource.INTERNAL  # INTERNAL for continuous scanning
    output_trigger_kind: OutputTriggerKind = OutputTriggerKind.EXPOSURE
    exposure_time_ms: float = 10.0
    max_power_percent: int = 100
    safety_timeout_ms: int = 5000
    simulation_mode: bool = False
    subunits: tuple[SubunitConfig, ...] = field(default_factory=lambda: (
        SubunitConfig(index=0, power_percent=30),
    ))
    buffer_frame_count: int = 3


@dataclass(frozen=True)
class SubunitStatus:
    index: int
    wavelength_nm: int
    is_on: bool
    power_percent: int
    pmt_gain: float
    is_installed: bool


@dataclass(frozen=True)
class ScanConfig:
    mode: str  # "sequential" or "simultaneous"
    lines: int  # 240, 480, 960
    zoom: int  # 1 or 2
    binning: int  # 1 or 2
    frame_averaging_enabled: bool
    frame_averaging_frames: int  # 2-1024


@dataclass(frozen=True)
class LaserStatus:
    state: MaicoState
    is_laser_on: bool
    is_capture_running: bool
    current_power_percent: int
    temperature_celsius: float
    active_subunits: tuple[SubunitStatus, ...] = ()
    simulation_mode: bool = False
    last_error: str | None = None
