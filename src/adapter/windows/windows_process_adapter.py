import contextlib
import difflib
import os
import time

import psutil

from src.adapter.windows.processes import file_description
from src.application.assistant.dto.process_dto import ProcessGroupDTO, ProcessUsageDTO, TopProcessesDTO
from src.application.assistant.fuzzy import sounds_like
from src.application.assistant.interfaces.i_process_adapter import IProcessAdapter
from src.application.assistant.processes import PROTECTED_PROCS
from src.application.assistant.text import norm


class WindowsProcessAdapter(IProcessAdapter):
    """Процессы текущего пользователя через psutil. Системные процессы и службы не трогаются."""

    def find_groups(self, variants: set[str], words: list[str]) -> list[ProcessGroupDTO]:
        me = psutil.Process().username()
        best: dict[str, ProcessGroupDTO] = {}
        for p in psutil.process_iter(["name", "pid", "username", "exe"]):
            name = (p.info["name"] or "").lower().removesuffix(".exe")
            # только свои программы: системные процессы и службы не трогаем никогда
            if not name or name in PROTECTED_PROCS or p.info["username"] != me or p.pid == os.getpid():
                continue
            score = 0.0
            for v in variants:
                if name == v:
                    s = 1.0
                elif name.startswith(v) or (len(name) >= 4 and v.startswith(name) and len(name) >= len(v) * 0.6):
                    s = 0.9  # «steam» не считается совпадением для «steamclienthelper»
                else:
                    s = difflib.SequenceMatcher(None, v, name).ratio()
                    if sounds_like(v, name):
                        s = max(s, 0.86)
                score = max(score, s)
            if score < 0.95 and words:
                # «steam client helper» → описание «Steam Client WebHelper» у steamwebhelper.exe
                desc = norm(file_description(p.info["exe"]))
                if desc:
                    if desc == " ".join(words):
                        score = 1.0
                    elif len(words) >= 2 and all(any(w in d for d in desc.split()) for w in words):
                        score = max(score, 0.92)
            if score >= 0.85:
                group = best.setdefault(name, ProcessGroupDTO(name=name, score=0.0))
                group.score = max(group.score, score)
                group.handles.append(p)
        return sorted(best.values(), key=lambda g: -g.score)

    def kill(self, group: ProcessGroupDTO, force: bool = False) -> str:
        """Сначала вежливо (как «Снять задачу»), а если не закрылись за 3 секунды
        или просили принудительно — жёстко."""
        alive = []
        for p in group.handles:
            try:
                p.kill() if force else p.terminate()
                alive.append(p)
            except psutil.NoSuchProcess:
                pass
            except psutil.AccessDenied:
                return "denied"
        _, still = psutil.wait_procs(alive, timeout=3)
        if still:
            for p in still:
                with contextlib.suppress(Exception):
                    p.kill()
            _, still = psutil.wait_procs(still, timeout=2)
        return "failed" if still else "closed"

    def top_usage(self, limit: int = 3) -> TopProcessesDTO:
        procs = list(psutil.process_iter(["name", "memory_info"]))
        for p in procs:
            with contextlib.suppress(Exception):
                p.cpu_percent(None)
        time.sleep(1.0)
        cpu: dict[str, float] = {}
        mem: dict[str, float] = {}
        for p in procs:
            try:
                n = (p.info["name"] or "").removesuffix(".exe")
                if n.lower() in ("system idle process", "idle", ""):
                    continue
                cpu[n] = cpu.get(n, 0) + p.cpu_percent(None) / psutil.cpu_count()
                mem[n] = mem.get(n, 0) + p.info["memory_info"].rss / 2**20
            except Exception:
                pass
        return TopProcessesDTO(
            cpu=[ProcessUsageDTO(n, v) for n, v in sorted(cpu.items(), key=lambda kv: -kv[1])[:limit]],
            memory=[ProcessUsageDTO(n, v) for n, v in sorted(mem.items(), key=lambda kv: -kv[1])[:limit]],
        )
