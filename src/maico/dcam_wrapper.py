import ctypes
from typing import Any
from .types import Result
from .errors import MaicoError, ErrorCode, create_error
from .core import (
    DCAMLib,
    DCAMAPI_INIT,
    DCAMDEV_OPEN,
    DCAMERR,
    DCAMPropertyID,
    DCAMCaptureMode,
    DCAMSubunitControl,
    DCAMScanMode,
    DCAMFrameAveraging,
    SUBUNIT_OFFSET,
    LowLevelError,
)
from .simulation import SimulationLib


class DCAMWrapper:
    def __init__(self, simulation_mode: bool = False) -> None:
        self._simulation_mode = simulation_mode
        self._lib: Any = None
        self._hdcam: Any = None
        self._is_initialized = False
        self._buffer_allocated = False
        self._capture_running = False
        self._initialize_library()

    def _initialize_library(self) -> None:
        try:
            if self._simulation_mode:
                self._lib = SimulationLib()
            else:
                self._lib = DCAMLib()
        except LowLevelError:
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
        param.size = ctypes.sizeof(param)
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
        param.size = ctypes.sizeof(param)
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

        if self._capture_running:
            self.cap_stop()

        if self._buffer_allocated:
            self.buf_release()

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

    def buf_alloc(self, frame_count: int = 3) -> Result[None, MaicoError]:
        if self._hdcam is None:
            return Result.err(create_error(
                ErrorCode.DEVICE_NOT_FOUND,
                "Device not opened"
            ))

        if self._buffer_allocated:
            release_result = self.buf_release()
            if release_result.is_err():
                return release_result

        result = self._lib.dcambuf_alloc(self._hdcam, frame_count)
        
        if result != DCAMERR.SUCCESS:
            return Result.err(create_error(
                ErrorCode.BUFFER_ALLOC_FAILED,
                "Failed to allocate image buffer",
                frame_count=frame_count,
                dcam_error=result
            ))

        self._buffer_allocated = True
        return Result.ok(None)

    def buf_release(self) -> Result[None, MaicoError]:
        if self._hdcam is None:
            return Result.err(create_error(
                ErrorCode.DEVICE_NOT_FOUND,
                "Device not opened"
            ))

        if not self._buffer_allocated:
            return Result.ok(None)

        result = self._lib.dcambuf_release(self._hdcam)
        
        if result != DCAMERR.SUCCESS:
            return Result.err(create_error(
                ErrorCode.BUFFER_RELEASE_FAILED,
                "Failed to release image buffer",
                dcam_error=result
            ))

        self._buffer_allocated = False
        return Result.ok(None)

    def cap_start(
        self, mode: DCAMCaptureMode = DCAMCaptureMode.SEQUENCE
    ) -> Result[None, MaicoError]:
        if self._hdcam is None:
            return Result.err(create_error(
                ErrorCode.DEVICE_NOT_FOUND,
                "Device not opened"
            ))

        if not self._buffer_allocated:
            alloc_result = self.buf_alloc()
            if alloc_result.is_err():
                return alloc_result

        result = self._lib.dcamcap_start(self._hdcam, mode.value)
        
        if result != DCAMERR.SUCCESS:
            return Result.err(create_error(
                ErrorCode.CAPTURE_START_FAILED,
                "Failed to start capture",
                mode=mode.name,
                dcam_error=result
            ))

        self._capture_running = True
        return Result.ok(None)

    def cap_stop(self) -> Result[None, MaicoError]:
        if self._hdcam is None:
            return Result.err(create_error(
                ErrorCode.DEVICE_NOT_FOUND,
                "Device not opened"
            ))

        if not self._capture_running:
            return Result.ok(None)

        result = self._lib.dcamcap_stop(self._hdcam)
        
        if result != DCAMERR.SUCCESS:
            return Result.err(create_error(
                ErrorCode.CAPTURE_STOP_FAILED,
                "Failed to stop capture",
                dcam_error=result
            ))

        self._capture_running = False
        return Result.ok(None)

    def set_subunit_control(
        self, subunit_index: int, control: DCAMSubunitControl
    ) -> Result[None, MaicoError]:
        prop_id = DCAMPropertyID.SUBUNIT_CONTROL + (SUBUNIT_OFFSET * subunit_index)
        return self.set_property(prop_id, float(control.value))

    def get_subunit_control(self, subunit_index: int) -> Result[DCAMSubunitControl, MaicoError]:
        prop_id = DCAMPropertyID.SUBUNIT_CONTROL + (SUBUNIT_OFFSET * subunit_index)
        result = self.get_property(prop_id)
        
        if result.is_err():
            return Result.err(result.unwrap_err())

        return Result.ok(DCAMSubunitControl(int(result.unwrap())))

    def set_subunit_laser_power(
        self, subunit_index: int, power: int
    ) -> Result[None, MaicoError]:
        prop_id = DCAMPropertyID.SUBUNIT_LASERPOWER + (SUBUNIT_OFFSET * subunit_index)
        return self.set_property(prop_id, float(power))

    def get_subunit_laser_power(self, subunit_index: int) -> Result[int, MaicoError]:
        prop_id = DCAMPropertyID.SUBUNIT_LASERPOWER + (SUBUNIT_OFFSET * subunit_index)
        result = self.get_property(prop_id)
        
        if result.is_err():
            return Result.err(result.unwrap_err())

        return Result.ok(int(result.unwrap()))

    def get_subunit_wavelength(self, subunit_index: int) -> Result[int, MaicoError]:
        prop_id = DCAMPropertyID.SUBUNIT_WAVELENGTH + (SUBUNIT_OFFSET * subunit_index)
        result = self.get_property(prop_id)
        
        if result.is_err():
            return Result.err(result.unwrap_err())

        return Result.ok(int(result.unwrap()))

    def get_subunit_count(self) -> Result[int, MaicoError]:
        result = self.get_property(DCAMPropertyID.NUMBEROF_SUBUNIT)
        
        if result.is_err():
            return Result.err(result.unwrap_err())

        return Result.ok(int(result.unwrap()))

    def get_sensor_temperature(self) -> Result[float, MaicoError]:
        return self.get_property(DCAMPropertyID.SENSORTEMPERATURE)

    def is_capture_running(self) -> bool:
        return self._capture_running

    def is_buffer_allocated(self) -> bool:
        return self._buffer_allocated

    # --- PMT Gain ---

    def set_subunit_pmt_gain(
        self, subunit_index: int, gain: float
    ) -> Result[None, MaicoError]:
        if gain < 0.5 or gain > 0.9:
            return Result.err(create_error(
                ErrorCode.INVALID_PARAMETER,
                "PMT gain must be between 0.5 and 0.9",
                gain=gain
            ))
        prop_id = DCAMPropertyID.SUBUNIT_PMTGAIN + (SUBUNIT_OFFSET * subunit_index)
        return self.set_property(prop_id, gain)

    def get_subunit_pmt_gain(self, subunit_index: int) -> Result[float, MaicoError]:
        prop_id = DCAMPropertyID.SUBUNIT_PMTGAIN + (SUBUNIT_OFFSET * subunit_index)
        return self.get_property(prop_id)

    # --- Confocal Scan Configuration ---

    def set_scan_mode(self, mode: DCAMScanMode) -> Result[None, MaicoError]:
        return self.set_property(DCAMPropertyID.CONFOCAL_SCANMODE, float(mode.value))

    def get_scan_mode(self) -> Result[DCAMScanMode, MaicoError]:
        result = self.get_property(DCAMPropertyID.CONFOCAL_SCANMODE)
        if result.is_err():
            return Result.err(result.unwrap_err())
        value = int(result.unwrap())
        # Default to SEQUENTIAL if hardware returns invalid value (0)
        if value not in (1, 2):
            value = DCAMScanMode.SEQUENTIAL.value
        return Result.ok(DCAMScanMode(value))

    def set_scan_lines(self, lines: int) -> Result[None, MaicoError]:
        if lines not in (240, 480, 960):
            return Result.err(create_error(
                ErrorCode.INVALID_PARAMETER,
                "Scan lines must be 240, 480, or 960",
                lines=lines
            ))
        return self.set_property(DCAMPropertyID.CONFOCAL_SCANLINES, float(lines))

    def get_scan_lines(self) -> Result[int, MaicoError]:
        result = self.get_property(DCAMPropertyID.CONFOCAL_SCANLINES)
        if result.is_err():
            return Result.err(result.unwrap_err())
        return Result.ok(int(result.unwrap()))

    def set_zoom(self, zoom: int) -> Result[None, MaicoError]:
        if zoom not in (1, 2):
            return Result.err(create_error(
                ErrorCode.INVALID_PARAMETER,
                "Zoom must be 1 or 2",
                zoom=zoom
            ))
        return self.set_property(DCAMPropertyID.CONFOCAL_ZOOM, float(zoom))

    def get_zoom(self) -> Result[int, MaicoError]:
        result = self.get_property(DCAMPropertyID.CONFOCAL_ZOOM)
        if result.is_err():
            return Result.err(result.unwrap_err())
        return Result.ok(int(result.unwrap()))

    # --- Binning ---

    def set_binning(self, binning: int) -> Result[None, MaicoError]:
        if binning not in (1, 2):
            return Result.err(create_error(
                ErrorCode.INVALID_PARAMETER,
                "Binning must be 1 or 2",
                binning=binning
            ))
        return self.set_property(DCAMPropertyID.BINNING, float(binning))

    def get_binning(self) -> Result[int, MaicoError]:
        result = self.get_property(DCAMPropertyID.BINNING)
        if result.is_err():
            return Result.err(result.unwrap_err())
        return Result.ok(int(result.unwrap()))

    # --- Frame Averaging ---

    def set_frame_averaging(
        self, enable: bool, frames: int = 2
    ) -> Result[None, MaicoError]:
        mode = DCAMFrameAveraging.ON if enable else DCAMFrameAveraging.OFF
        mode_result = self.set_property(
            DCAMPropertyID.FRAMEAVERAGINGMODE, float(mode.value)
        )
        if mode_result.is_err():
            return mode_result

        if enable:
            if frames < 2 or frames > 1024:
                return Result.err(create_error(
                    ErrorCode.INVALID_PARAMETER,
                    "Frame averaging frames must be between 2 and 1024",
                    frames=frames
                ))
            return self.set_property(
                DCAMPropertyID.FRAMEAVERAGINGFRAMES, float(frames)
            )
        return Result.ok(None)

    def get_frame_averaging(self) -> Result[tuple[bool, int], MaicoError]:
        mode_result = self.get_property(DCAMPropertyID.FRAMEAVERAGINGMODE)
        if mode_result.is_err():
            return Result.err(mode_result.unwrap_err())

        enabled = int(mode_result.unwrap()) == DCAMFrameAveraging.ON

        frames_result = self.get_property(DCAMPropertyID.FRAMEAVERAGINGFRAMES)
        frames = int(frames_result.unwrap_or(2))

        return Result.ok((enabled, frames))
