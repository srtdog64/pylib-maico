import ctypes


class DCAMAPI_INIT(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_int32),
        ("iDeviceCount", ctypes.c_int32),
        ("reserved", ctypes.c_int32),
        ("initoptionbytes", ctypes.c_int32),
        ("initoption", ctypes.c_char_p),
        ("guid", ctypes.c_char_p)
    ]


class DCAMDEV_OPEN(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_int32),
        ("index", ctypes.c_int32),
        ("hdcam", ctypes.POINTER(ctypes.c_void_p))
    ]


class DCAMDEV_STRING(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_int32),
        ("iString", ctypes.c_int32),
        ("text", ctypes.c_char_p),
        ("textbytes", ctypes.c_int32)
    ]


class DCAMPROP_ATTR(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_int32),
        ("iProp", ctypes.c_int32),
        ("option", ctypes.c_int32),
        ("iReserved1", ctypes.c_int32),
        ("attribute", ctypes.c_int32),
        ("iGroup", ctypes.c_int32),
        ("iUnit", ctypes.c_int32),
        ("attribute2", ctypes.c_int32),
        ("valuemin", ctypes.c_double),
        ("valuemax", ctypes.c_double),
        ("valuestep", ctypes.c_double),
        ("valuedefault", ctypes.c_double),
        ("nMaxChannel", ctypes.c_int32),
        ("iReserved3", ctypes.c_int32),
        ("nMaxView", ctypes.c_int32),
        ("iProp_NumberOfElement", ctypes.c_int32),
        ("iProp_ArrayBase", ctypes.c_int32),
        ("iPropStep_Element", ctypes.c_int32)
    ]


class DCAMWAIT_OPEN(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_int32),
        ("supportevent", ctypes.c_int32),
        ("hwait", ctypes.POINTER(ctypes.c_void_p)),
        ("hdcam", ctypes.POINTER(ctypes.c_void_p))
    ]


class DCAMWAIT_START(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_int32),
        ("eventhappened", ctypes.c_int32),
        ("eventmask", ctypes.c_int32),
        ("timeout", ctypes.c_int32)
    ]


class DCAM_TIMESTAMP(ctypes.Structure):
    _fields_ = [
        ("sec", ctypes.c_uint32),
        ("microsec", ctypes.c_int32)
    ]


class DCAMBUF_FRAME(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_int32),
        ("iKind", ctypes.c_int32),
        ("option", ctypes.c_int32),
        ("iFrame", ctypes.c_int32),
        ("buf", ctypes.c_void_p),
        ("rowbytes", ctypes.c_int32),
        ("type", ctypes.c_int32),
        ("width", ctypes.c_int32),
        ("height", ctypes.c_int32),
        ("left", ctypes.c_int32),
        ("top", ctypes.c_int32),
        ("timestamp", DCAM_TIMESTAMP),
        ("framestamp", ctypes.c_int32),
        ("camerastamp", ctypes.c_int32)
    ]


class DCAMCAP_TRANSFERINFO(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_int32),
        ("iKind", ctypes.c_int32),
        ("nNewestFrameIndex", ctypes.c_int32),
        ("nFrameCount", ctypes.c_int32)
    ]
