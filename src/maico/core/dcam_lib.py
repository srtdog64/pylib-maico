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
        self._setup_function_signatures()

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

    def _setup_function_signatures(self) -> None:
        """Set up argtypes and restype for all DCAM functions.

        This is critical for correct parameter passing, especially on 64-bit systems.
        Matches the official dcamapi4.py definitions.
        """
        dll = self._dcamapi

        # dcamapi_init: DCAMERR dcamapi_init(DCAMAPI_INIT* param)
        dll.dcamapi_init.argtypes = [ctypes.c_void_p]
        dll.dcamapi_init.restype = ctypes.c_int32

        # dcamapi_uninit: DCAMERR dcamapi_uninit()
        dll.dcamapi_uninit.argtypes = []
        dll.dcamapi_uninit.restype = ctypes.c_int32

        # dcamdev_open: DCAMERR dcamdev_open(DCAMDEV_OPEN* param)
        dll.dcamdev_open.argtypes = [ctypes.c_void_p]
        dll.dcamdev_open.restype = ctypes.c_int32

        # dcamdev_close: DCAMERR dcamdev_close(HDCAM hdcam)
        dll.dcamdev_close.argtypes = [ctypes.c_void_p]
        dll.dcamdev_close.restype = ctypes.c_int32

        # dcamprop_setvalue: DCAMERR dcamprop_setvalue(HDCAM h, int32 iProp, double fValue)
        dll.dcamprop_setvalue.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_double]
        dll.dcamprop_setvalue.restype = ctypes.c_int32

        # dcamprop_getvalue: DCAMERR dcamprop_getvalue(HDCAM h, int32 iProp, double* pValue)
        dll.dcamprop_getvalue.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_double)]
        dll.dcamprop_getvalue.restype = ctypes.c_int32

        # dcamcap_start: DCAMERR dcamcap_start(HDCAM h, int32 mode)
        dll.dcamcap_start.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        dll.dcamcap_start.restype = ctypes.c_int32

        # dcamcap_stop: DCAMERR dcamcap_stop(HDCAM h)
        dll.dcamcap_stop.argtypes = [ctypes.c_void_p]
        dll.dcamcap_stop.restype = ctypes.c_int32

        # dcamcap_firetrigger: DCAMERR dcamcap_firetrigger(HDCAM h, int32 iKind)
        dll.dcamcap_firetrigger.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        dll.dcamcap_firetrigger.restype = ctypes.c_int32

        # dcambuf_alloc: DCAMERR dcambuf_alloc(HDCAM h, int32 framecount)
        dll.dcambuf_alloc.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        dll.dcambuf_alloc.restype = ctypes.c_int32

        # dcambuf_release: DCAMERR dcambuf_release(HDCAM h, int32 iKind)
        dll.dcambuf_release.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        dll.dcambuf_release.restype = ctypes.c_int32

        # dcamwait_open: DCAMERR dcamwait_open(DCAMWAIT_OPEN* param)
        dll.dcamwait_open.argtypes = [ctypes.c_void_p]
        dll.dcamwait_open.restype = ctypes.c_int32

        # dcamwait_start: DCAMERR dcamwait_start(HDCAMWAIT hWait, DCAMWAIT_START* param)
        dll.dcamwait_start.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        dll.dcamwait_start.restype = ctypes.c_int32

        # dcamwait_close: DCAMERR dcamwait_close(HDCAMWAIT hWait)
        dll.dcamwait_close.argtypes = [ctypes.c_void_p]
        dll.dcamwait_close.restype = ctypes.c_int32

    def dcamapi_init(self, param: DCAMAPI_INIT) -> int:
        return self._dcamapi.dcamapi_init(ctypes.byref(param))

    def dcamapi_uninit(self) -> int:
        return self._dcamapi.dcamapi_uninit()

    def dcamdev_open(self, param: DCAMDEV_OPEN) -> int:
        return self._dcamapi.dcamdev_open(ctypes.byref(param))

    def dcamdev_close(self, hdcam: Any) -> int:
        return self._dcamapi.dcamdev_close(hdcam)

    def dcamprop_setvalue(self, hdcam: Any, prop_id: int, value: float) -> int:
        # argtypes handles conversion: [c_void_p, c_int32, c_double]
        return self._dcamapi.dcamprop_setvalue(hdcam, prop_id, value)

    def dcamprop_getvalue(self, hdcam: Any, prop_id: int) -> tuple[int, float]:
        c_value = ctypes.c_double()
        result = self._dcamapi.dcamprop_getvalue(hdcam, prop_id, ctypes.byref(c_value))
        return result, c_value.value

    def dcamcap_firetrigger(self, hdcam: Any) -> int:
        # argtypes handles conversion: [c_void_p, c_int32]
        return self._dcamapi.dcamcap_firetrigger(hdcam, 0)

    def dcambuf_alloc(self, hdcam: Any, frame_count: int) -> int:
        # argtypes handles conversion: [c_void_p, c_int32]
        return self._dcamapi.dcambuf_alloc(hdcam, frame_count)

    def dcambuf_release(self, hdcam: Any) -> int:
        # argtypes handles conversion: [c_void_p, c_int32]
        return self._dcamapi.dcambuf_release(hdcam, 0)

    def dcamcap_start(self, hdcam: Any, mode: int) -> int:
        # argtypes handles conversion: [c_void_p, c_int32]
        return self._dcamapi.dcamcap_start(hdcam, mode)

    def dcamcap_stop(self, hdcam: Any) -> int:
        return self._dcamapi.dcamcap_stop(hdcam)

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
