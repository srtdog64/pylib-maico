from typing import Any
from .types import Result
from .errors import MaicoError, ErrorCode, create_error
from .core import DCAMLib, DCAMAPI_INIT, DCAMDEV_OPEN, DCAMERR, DCAMPropertyID
from .core.dcam_lib import LowLevelError
from .simulation import SimulationLib


class DCAMWrapper:
    def __init__(self, simulation_mode: bool = False) -> None:
        self._simulation_mode = simulation_mode
        self._lib: Any = None
        self._hdcam: Any = None
        self._is_initialized = False
        self._initialize_library()

    def _initialize_library(self) -> None:
        try:
            if self._simulation_mode:
                self._lib = SimulationLib()
            else:
                self._lib = DCAMLib()
        except LowLevelError as e:
            self._lib = None

    def _check_status(self, error_code: int) -> Result[None, MaicoError]:
        if error_code != DCAMERR.SUCCESS:
            return Result.err(create_error(
                ErrorCode.UNKNOWN_ERROR,
                "DCAM operation failed",
                dcam_error_code=error_code
            ))
        return Result.ok(None)

    def initialize(self) -> Result[int, MaicoError]:
        if self._is_initialized:
            return Result.ok(0)

        if self._lib is None:
            return Result.err(create_error(
                ErrorCode.DCAM_NOT_INITIALIZED,
                "DCAM library not loaded (simulation mode available)"
            ))

        param = DCAMAPI_INIT()
        param.size = len(param)
        param.initoption = None
        param.guid = None

        result = self._lib.dcamapi_init(param)
        status_check = self._check_status(result)
        
        if status_check.is_err():
            return Result.err(create_error(
                ErrorCode.DCAM_INIT_FAILED,
                "Failed to initialize DCAM-API",
                dcam_error=result,
                simulation_mode=self._simulation_mode
            ))

        self._is_initialized = True
        return Result.ok(param.iDeviceCount)

    def uninitialize(self) -> Result[None, MaicoError]:
        if not self._is_initialized:
            return Result.ok(None)

        result = self._lib.dcamapi_uninit()
        self._is_initialized = False
        return self._check_status(result)

    def open_device(self, device_index: int) -> Result[None, MaicoError]:
        if not self._is_initialized:
            return Result.err(create_error(
                ErrorCode.DCAM_NOT_INITIALIZED,
                "DCAM-API not initialized"
            ))

        param = DCAMDEV_OPEN()
        param.size = len(param)
        param.index = device_index

        result = self._lib.dcamdev_open(param)
        status_check = self._check_status(result)
        
        if status_check.is_err():
            return Result.err(create_error(
                ErrorCode.DEVICE_OPEN_FAILED,
                "Failed to open DCAM device",
                device_index=device_index
            ))

        self._hdcam = param.hdcam
        return Result.ok(None)

    def close_device(self) -> Result[None, MaicoError]:
        if self._hdcam is None:
            return Result.ok(None)

        result = self._lib.dcamdev_close(self._hdcam)
        self._hdcam = None
        return self._check_status(result)

    def set_property(self, prop_id: int, value: float) -> Result[None, MaicoError]:
        if self._hdcam is None:
            return Result.err(create_error(
                ErrorCode.DEVICE_NOT_FOUND,
                "Device not opened"
            ))

        result = self._lib.dcamprop_setvalue(self._hdcam, prop_id, value)
        
        if result != DCAMERR.SUCCESS:
            return Result.err(create_error(
                ErrorCode.PROPERTY_SET_FAILED,
                "Failed to set DCAM property",
                property_id=hex(prop_id),
                value=value,
                dcam_error=result
            ))

        return Result.ok(None)

    def get_property(self, prop_id: int) -> Result[float, MaicoError]:
        if self._hdcam is None:
            return Result.err(create_error(
                ErrorCode.DEVICE_NOT_FOUND,
                "Device not opened"
            ))

        result, value = self._lib.dcamprop_getvalue(self._hdcam, prop_id)
        
        if result != DCAMERR.SUCCESS:
            return Result.err(create_error(
                ErrorCode.PROPERTY_GET_FAILED,
                "Failed to get DCAM property",
                property_id=hex(prop_id),
                dcam_error=result
            ))

        return Result.ok(value)

    def fire_trigger(self) -> Result[None, MaicoError]:
        if self._hdcam is None:
            return Result.err(create_error(
                ErrorCode.DEVICE_NOT_FOUND,
                "Device not opened"
            ))

        result = self._lib.dcamcap_firetrigger(self._hdcam)
        
        if result != DCAMERR.SUCCESS:
            return Result.err(create_error(
                ErrorCode.TRIGGER_FIRE_FAILED,
                "Failed to fire software trigger",
                dcam_error=result
            ))

        return Result.ok(None)

    def get_sensor_temperature(self) -> Result[float, MaicoError]:
        return self.get_property(DCAMPropertyID.SENSORTEMPERATURE)
