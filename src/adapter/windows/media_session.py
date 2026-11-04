"""Управление тем, что сейчас играет (музыка, YouTube в браузере, плееры) через системные
мультимедиа-элементы Windows — те же, что у плашки громкости с названием трека."""
import asyncio
import datetime

PLAYING, PAUSED = 4, 5
TICKS = 10_000_000  # в Windows время меряется в 100-наносекундных тиках


def _run(coro):
    return asyncio.run(coro)


async def _sessions():
    from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as M
    mgr = await M.request_async()
    return mgr, list(mgr.get_sessions())


async def _pick(prefer_playing=True, source=None):
    """Сессия, которой управляем: та, что играет; иначе та, что Капри ставила на паузу (source);
    иначе «текущая» по мнению Windows; иначе первая."""
    mgr, sessions = await _sessions()
    if not sessions:
        return None
    if source and not prefer_playing:
        for s in sessions:
            if s.source_app_user_model_id == source:
                return s
    if prefer_playing:
        for s in sessions:
            if s.get_playback_info().playback_status == PLAYING:
                return s
    return mgr.get_current_session() or sessions[0]


def _position(s):
    """Текущая позиция в секундах с поправкой на время, прошедшее с последнего обновления."""
    tl = s.get_timeline_properties()
    pos = tl.position.total_seconds()
    if s.get_playback_info().playback_status == PLAYING:
        upd = tl.last_updated_time
        if upd.year > 1970:
            pos += max(0.0, (datetime.datetime.now(datetime.UTC) - upd).total_seconds())
    return pos, tl.end_time.total_seconds()


async def _describe(s):
    p = await s.try_get_media_properties_async()
    title = (p.title or "").strip()
    artist = (p.artist or "").strip()
    return f"{artist} — {title}" if artist and artist.lower() not in ("неизв. исполнитель", "unknown artist") else title


def now_playing():
    """(описание, источник, играет ли) или None."""
    async def go():
        s = await _pick()
        if not s:
            return None
        return await _describe(s), s.source_app_user_model_id, s.get_playback_info().playback_status == PLAYING
    return _run(go())


def control(action, source=None):
    """pause / play / toggle / next / prev → (ok, описание трека, источник)."""
    async def go():
        s = await _pick(prefer_playing=action != "play", source=source)
        if not s:
            return False, None, None
        if action == "pause" and s.get_playback_info().playback_status != PLAYING:
            return False, None, None  # ничего не играет — нечего ставить на паузу
        f = {"pause": s.try_pause_async, "play": s.try_play_async, "toggle": s.try_toggle_play_pause_async,
             "next": s.try_skip_next_async, "prev": s.try_skip_previous_async}[action]
        ok = await f()
        return ok, await _describe(s), s.source_app_user_model_id
    return _run(go())


def seek(seconds=None, delta=None):
    """Перемотка: на абсолютное время (seconds) или на смещение (delta, может быть отрицательным).
    Возвращает (ok, новая позиция, источник)."""
    async def go():
        s = await _pick()
        if not s:
            return False, None, None
        pos, end = _position(s)
        target = seconds if seconds is not None else pos + (delta or 0)
        if end > 0:
            target = min(target, end - 1)
        target = max(0.0, target)
        ok = False
        if s.get_playback_info().controls.is_playback_position_enabled:
            ok = await s.try_change_playback_position_async(int(target * TICKS))
        return ok, target, s.source_app_user_model_id
    return _run(go())
