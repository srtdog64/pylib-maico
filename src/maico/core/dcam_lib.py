import ctypes
import platform
from typing import Any
from .structs import DCAMAPI_INIT, DCAMDEV_OPEN
from .enums import DCAMERR


class LowLevelError(Exception):
    def __init__(self, message: str, error_code: int) -> None:
        super().__init__(message)
        self.error_code = error_code


class DCAMLib:
    def __init__(self) -> None:
        self._dcamapi = self._load_library()

    def _load_library(self) -> Any:
        system = platform.system()
        
        try:
            if system == "Windows":
                if not hasattr(ctypes, 'windll'):
                    raise OSError("windll not available on this platform")
                return ctypes.windll.LoadLibrary("dcamapi.dll")
            elif system == "Linux":
                return ctypes.cdll.LoadLibrary("libdcamapi.so")
            elif system == "Darwin":
                raise OSError(
                    "DCAM-API not available on macOS. "
                    "Use simulation_mode=True for development."
                )
            else:
                raise OSError(f"Unsupported platform: {system}")
        except (OSError, AttributeError) as e:
            raise LowLevelError(
                f"Failed to load DCAM library on {system}: {str(e)}",
                error_code=-1
            ) from e

    def dcamapi_init(self, param: DCAMAPI_INIT) -> int:
        return self._dcamapi.dcamapi_init(ctypes.byref(param))

    def dcamapi_uninit(self) -> int:
        return self._dcamapi.dcamapi_uninit()

    def dcamdev_open(self, param: DCAMDEV_OPEN) -> int:
        return self._dcamapi.dcamdev_open(ctypes.byref(param))

    def dcamdev_close(self, hdcam: Any) -> int:
        return self._dcamapi.dcamdev_close(hdcam)

    def dcamprop_setvalue(self, hdcam: Any, prop_id: int, value: float) -> int:
        c_value = ctypes.c_double(value)
        return self._dcamapi.dcamprop_setvalue(hdcam, prop_id, c_value)

    def dcamprop_getvalue(self, hdcam: Any, prop_id: int) -> tuple[int, float]:
        c_value = ctypes.c_double()
        result = self._dcamapi.dcamprop_getvalue(
            hdcam,
            prop_id,
            ctypes.byref(c_value)
        )
        return result, c_value.value

    def dcamcap_firetrigger(self, hdcam: Any) -> int:
        return self._dcamapi.dcamcap_firetrigger(hdcam, ctypes.c_int32(0))

    def dcamwait_open(self, hdcam: Any) -> tuple[int, Any]:
        from .structs import DCAMWAIT_OPEN
        param = DCAMWAIT_OPEN()
        param.size = ctypes.sizeof(param)
        param.hdcam = hdcam
        result = self._dcamapi.dcamwait_open(ctypes.byref(param))
        return result, param.hwait

    def dcamwait_start(self, hwait: Any, eventmask: int, timeout: int) -> int:
        from .structs import DCAMWAIT_START
        param = DCAMWAIT_START()
        param.size = ctypes.sizeof(param)
        param.eventmask = eventmask
        param.timeout = timeout
        return self._dcamapi.dcamwait_start(hwait, ctypes.byref(param))

    def dcamwait_close(self, hwait: Any) -> int:
        return self._dcamapi.dcamwait_close(hwait)
