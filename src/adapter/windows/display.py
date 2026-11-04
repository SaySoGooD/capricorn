"""Яркость экрана (screen_brightness_control)."""


def get_brightness():
    import screen_brightness_control as sbc
    return sbc.get_brightness()[0]


def set_brightness(v):
    import screen_brightness_control as sbc
    sbc.set_brightness(max(0, min(100, v)))
