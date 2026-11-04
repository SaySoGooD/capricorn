"""Описание exe-файла из его ресурсов (как в диспетчере задач)."""
import ctypes

_desc_cache = {}


def file_description(path):
    """Описание программы из свойств exe-файла (то, что показывает диспетчер задач),
    например «Steam Client WebHelper». Пустая строка, если описания нет."""
    if not path:
        return ""
    if path in _desc_cache:
        return _desc_cache[path]
    desc = ""
    try:
        v = ctypes.windll.version
        size = v.GetFileVersionInfoSizeW(path, None)
        if size:
            buf = ctypes.create_string_buffer(size)
            if v.GetFileVersionInfoW(path, 0, size, buf):
                ptr, ln = ctypes.c_void_p(), ctypes.c_uint()
                if v.VerQueryValueW(buf, "\\VarFileInfo\\Translation", ctypes.byref(ptr), ctypes.byref(ln)) and ln.value:
                    lang, cp = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_ushort * 2)).contents
                    key = f"\\StringFileInfo\\{lang:04x}{cp:04x}\\FileDescription"
                    sptr = ctypes.c_wchar_p()
                    if v.VerQueryValueW(buf, key, ctypes.byref(sptr), ctypes.byref(ln)) and ln.value:
                        desc = sptr.value or ""
    except Exception:
        pass
    _desc_cache[path] = desc
    return desc
