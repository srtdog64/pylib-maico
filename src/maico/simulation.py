import time
import ctypes
from typing import Any
from .core.structs import DCAMAPI_INIT, DCAMDEV_OPEN
from .core.enums import DCAMERR, DCAMPropertyID, SUBUNIT_OFFSET, DCAMSubunitControl


class SimulatedDevice:
    def __init__(self) -> None:
        self._properties: dict[int, float] = {}
        self._is_initialized = False
        self._device_count = 1
        self._temperature = 25.0
        self._trigger_fired = False
        self._buffer_allocated = False
        self._buffer_count = 0
        self._capture_running = False
        self._initialize_subunits()

    def _initialize_subunits(self) -> None:
        subunit_configs = [
            (405, 30),
            (488, 30),
            (561, 30),
            (638, 30),
        ]
        for i, (wavelength, power) in enumerate(subunit_configs):
            offset = SUBUNIT_OFFSET * i
            self._properties[DCAMPropertyID.SUBUNIT_CONTROL + offset] = float(
                DCAMSubunitControl.OFF
            )
            self._properties[DCAMPropertyID.SUBUNIT_WAVELENGTH + offset] = float(
                wavelength
            )
            self._properties[DCAMPropertyID.SUBUNIT_LASERPOWER + offset] = float(power)
            self._properties[DCAMPropertyID.SUBUNIT_PMTGAIN + offset] = 0.7
        self._properties[DCAMPropertyID.NUMBEROF_SUBUNIT] = 4.0

    def get_property(self, prop_id: int) -> float:
        return self._properties.get(prop_id, 0.0)

    def set_property(self, prop_id: int, value: float) -> None:
        self._properties[prop_id] = value

    def fire_trigger(self) -> None:
        self._trigger_fired = True
        time.sleep(0.01)

    def reset_trigger(self) -> None:
        self._trigger_fired = False

    def alloc_buffer(self, count: int) -> bool:
        self._buffer_allocated = True
        self._buffer_count = count
        return True

    def release_buffer(self) -> bool:
        self._buffer_allocated = False
        self._buffer_count = 0
        return True

    def start_capture(self) -> bool:
        if not self._buffer_allocated:
            return False
        self._capture_running = True
        return True

    def stop_capture(self) -> bool:
        self._capture_running = False
        return True


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

    def dcambuf_alloc(self, hdcam: Any, frame_count: int) -> int:
        if self._device.alloc_buffer(frame_count):
            return DCAMERR.SUCCESS
        return DCAMERR.NOMEMORY

    def dcambuf_release(self, hdcam: Any) -> int:
        if self._device.release_buffer():
            return DCAMERR.SUCCESS
        return DCAMERR.NOTREADY

    def dcamcap_start(self, hdcam: Any, mode: int) -> int:
        if self._device.start_capture():
            return DCAMERR.SUCCESS
        return DCAMERR.NOTREADY

    def dcamcap_stop(self, hdcam: Any) -> int:
        if self._device.stop_capture():
            return DCAMERR.SUCCESS
        return DCAMERR.NOTBUSY

    def dcamwait_open(self, hdcam: Any) -> tuple[int, Any]:
        return DCAMERR.SUCCESS, self._hwait

    def dcamwait_start(self, hwait: Any, eventmask: int, timeout: int) -> int:
        time.sleep(0.05)
        return DCAMERR.SUCCESS

    def dcamwait_close(self, hwait: Any) -> int:
        return DCAMERR.SUCCESS
