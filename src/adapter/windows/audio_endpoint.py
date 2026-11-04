"""Общая громкость Windows и проверка, идёт ли звук из браузера (pycaw)."""
from src.application.assistant.browsers import BROWSERS

# ---------------- громкость / яркость ----------------

def _endpoint():
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    dev = AudioUtilities.GetSpeakers()
    if hasattr(dev, "EndpointVolume"):
        return dev.EndpointVolume
    from ctypes import POINTER, cast

    from comtypes import CLSCTX_ALL
    iface = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(iface, POINTER(IAudioEndpointVolume))


def get_volume():
    return round(_endpoint().GetMasterVolumeLevelScalar() * 100)


def set_volume(v):
    ep = _endpoint()
    ep.SetMasterVolumeLevelScalar(max(0, min(100, v)) / 100, None)
    if v > 0:
        ep.SetMute(0, None)


def set_mute(on):
    _endpoint().SetMute(1 if on else 0, None)


def browser_playing():
    """True, если из браузера сейчас реально идёт звук (по индикатору громкости в микшере Windows)."""
    from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
    for s in AudioUtilities.GetAllSessions():
        try:
            name = (s.Process.name() if s.Process else "").lower()
            if any(b in name for b in BROWSERS):
                meter = s._ctl.QueryInterface(IAudioMeterInformation)
                if meter.GetPeakValue() > 0.001:
                    return True
        except Exception:
            continue
    return False
