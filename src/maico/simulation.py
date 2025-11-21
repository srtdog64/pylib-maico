import time
import ctypes
from typing import Any
from .core.structs import DCAMAPI_INIT, DCAMDEV_OPEN
from .core.enums import DCAMERR


class SimulatedDevice:
    def __init__(self) -> None:
        self._properties: dict[int, float] = {}
        self._is_initialized = False
        self._device_count = 1
        self._temperature = 25.0
        self._trigger_fired = False

    def get_property(self, prop_id: int) -> float:
        return self._properties.get(prop_id, 0.0)

    def set_property(self, prop_id: int, value: float) -> None:
        self._properties[prop_id] = value

    def fire_trigger(self) -> None:
        self._trigger_fired = True
        time.sleep(0.01)

    def reset_trigger(self) -> None:
        self._trigger_fired = False


class SimulationLib:
    def __init__(self) -> None:
        self._device = SimulatedDevice()
        self._hdcam: Any = ctypes.c_void_p(0xDEADBEEF)
        self._hwait: Any = ctypes.c_void_p(0xCAFEBABE)

    def dcamapi_init(self, param: DCAMAPI_INIT) -> int:
        if self._device._is_initialized:
            return DCAMERR.SUCCESS
        
        self._device._is_initialized = True
        param.iDeviceCount = self._device._device_count
        return DCAMERR.SUCCESS

    def dcamapi_uninit(self) -> int:
        self._device._is_initialized = False
        return DCAMERR.SUCCESS

    def dcamdev_open(self, param: DCAMDEV_OPEN) -> int:
        if not self._device._is_initialized:
            return DCAMERR.NOTREADY
        
        if param.index >= self._device._device_count:
            return DCAMERR.NOCAMERA
        
        param.hdcam = ctypes.cast(self._hdcam, ctypes.POINTER(ctypes.c_void_p))
        return DCAMERR.SUCCESS

    def dcamdev_close(self, hdcam: Any) -> int:
        return DCAMERR.SUCCESS

    def dcamprop_setvalue(self, hdcam: Any, prop_id: int, value: float) -> int:
        self._device.set_property(prop_id, value)
        return DCAMERR.SUCCESS

    def dcamprop_getvalue(self, hdcam: Any, prop_id: int) -> tuple[int, float]:
        value = self._device.get_property(prop_id)
        return DCAMERR.SUCCESS, value

    def dcamcap_firetrigger(self, hdcam: Any) -> int:
        self._device.fire_trigger()
        return DCAMERR.SUCCESS

    def dcamwait_open(self, hdcam: Any) -> tuple[int, Any]:
        return DCAMERR.SUCCESS, self._hwait

    def dcamwait_start(self, hwait: Any, eventmask: int, timeout: int) -> int:
        time.sleep(0.05)
        return DCAMERR.SUCCESS

    def dcamwait_close(self, hwait: Any) -> int:
        return DCAMERR.SUCCESS
