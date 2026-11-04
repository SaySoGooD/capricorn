"""Диагностика ПК: процессор, память, диски, драйверы, журналы Windows, автозагрузка."""
import contextlib
import datetime
import os
import re

import psutil

from src.adapter.windows.powershell import ps_json, run_ps

# ---------------- диагностика ----------------

def _dir_size(path, limit=200000):
    total, n = 0, 0
    for root, _, files in os.walk(path):
        for f in files:
            with contextlib.suppress(OSError):
                total += os.path.getsize(os.path.join(root, f))
            n += 1
            if n > limit:
                return total
    return total


def analyze_pc():
    """Возвращает (список проблем, полный текстовый отчёт)."""
    issues, lines = [], []
    add = lines.append
    now = datetime.datetime.now()
    add(f"ДИАГНОСТИКА ПК — {now:%d.%m.%Y %H:%M}")
    add("=" * 60)

    cpu = psutil.cpu_percent(interval=1.5)
    mem = psutil.virtual_memory()
    add(f"Процессор: загрузка {cpu:.0f}% ({psutil.cpu_count()} потоков)")
    add(f"Память: занято {mem.percent:.0f}% ({mem.used / 2**30:.1f} из {mem.total / 2**30:.1f} ГБ)")
    if cpu > 85:
        issues.append(f"процессор загружен на {cpu:.0f} процентов")
    if mem.percent > 85:
        issues.append(f"оперативная память занята на {mem.percent:.0f} процентов")

    up = now - datetime.datetime.fromtimestamp(psutil.boot_time())
    add(f"Время работы без перезагрузки: {up.days} д {up.seconds // 3600} ч")
    if up.days >= 7:
        issues.append(f"компьютер не перезагружался {up.days} дней")

    bat = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
    if bat:
        add(f"Батарея: {bat.percent:.0f}% {'(заряжается)' if bat.power_plugged else ''}")

    add("\nДИСКИ:")
    for part in psutil.disk_partitions():
        if "cdrom" in part.opts or not part.fstype:
            continue
        try:
            u = psutil.disk_usage(part.mountpoint)
        except OSError:
            continue
        free_gb = u.free / 2**30
        add(f"  {part.mountpoint} {part.fstype}: свободно {free_gb:.1f} ГБ из {u.total / 2**30:.0f} ГБ ({100 - u.percent:.0f}%)")
        if u.percent > 90 or free_gb < 10:
            issues.append(f"на диске {part.mountpoint[0]} мало места — {free_gb:.0f} гигабайт")

    for d in ps_json("Get-PhysicalDisk | Select-Object FriendlyName,MediaType,HealthStatus,OperationalStatus"):
        add(f"  Накопитель {d.get('FriendlyName')}: здоровье {d.get('HealthStatus')}, состояние {d.get('OperationalStatus')}")
        if str(d.get("HealthStatus")) not in ("Healthy", "0"):
            issues.append(f"накопитель {d.get('FriendlyName')} сообщает о проблемах со здоровьем")

    tmp = os.environ.get("TEMP", "")
    if tmp:
        size = _dir_size(tmp) / 2**30
        add(f"  Временные файлы (%TEMP%): {size:.1f} ГБ")
        if size > 3:
            issues.append(f"временные файлы занимают {size:.0f} гигабайт")

    add("\nУСТРОЙСТВА С ОШИБКАМИ:")
    bad = ps_json("Get-PnpDevice -PresentOnly | Where-Object {$_.Status -eq 'Error'} | Select-Object FriendlyName,Class")
    for d in bad:
        add(f"  {d.get('FriendlyName')} ({d.get('Class')})")
    if not bad:
        add("  нет")
    else:
        issues.append(f"устройств с ошибкой драйвера: {len(bad)}")

    add("\nОШИБКИ В ЖУРНАЛАХ WINDOWS ЗА 24 ЧАСА (по источникам):")
    groups = ps_json("Get-WinEvent -FilterHashtable @{LogName='System','Application';Level=1,2;"
                     "StartTime=(Get-Date).AddDays(-1)} | Group-Object ProviderName | "
                     "Sort-Object Count -Descending | Select-Object -First 12 Count,Name")
    total_err = sum(int(g.get("Count", 0)) for g in groups)
    for g in groups:
        add(f"  {g.get('Count'):>4}  {g.get('Name')}")
    if not groups:
        add("  нет")
    if total_err > 30:
        issues.append(f"в журналах {total_err} ошибок за сутки")

    add("\nПОСЛЕДНИЕ ОШИБКИ:")
    for e in ps_json("Get-WinEvent -FilterHashtable @{LogName='System','Application';Level=1,2;"
                     "StartTime=(Get-Date).AddDays(-1)} -MaxEvents 8 | Select-Object "
                     "@{n='T';e={$_.TimeCreated.ToString('dd.MM HH:mm')}},ProviderName,Id,"
                     "@{n='M';e={if($_.Message){$_.Message.Substring(0,[Math]::Min(220,$_.Message.Length))}}}"):
        msg = re.sub(r"\s+", " ", str(e.get("M") or ""))
        add(f"  [{e.get('T')}] {e.get('ProviderName')} #{e.get('Id')}: {msg}")

    crashes = run_ps("(Get-WinEvent -FilterHashtable @{LogName='System';Id=41;"
                     "StartTime=(Get-Date).AddDays(-7)} | Measure-Object).Count")
    bsod = run_ps("(Get-WinEvent -FilterHashtable @{LogName='System';Id=1001;"
                  "ProviderName='Microsoft-Windows-WER-SystemErrorReporting';"
                  "StartTime=(Get-Date).AddDays(-7)} | Measure-Object).Count")
    crashes = int(crashes) if crashes.isdigit() else 0
    bsod = int(bsod) if bsod.isdigit() else 0
    add(f"\nАварийные выключения за 7 дней: {crashes}; синие экраны (BSOD): {bsod}")
    if crashes:
        issues.append(f"аварийных выключений за неделю: {crashes}")
    if bsod:
        issues.append(f"синих экранов за неделю: {bsod}")

    add("\nТОП ПРОЦЕССОВ ПО ПАМЯТИ:")
    procs = []
    for p in psutil.process_iter(["name", "memory_info"]):
        with contextlib.suppress(Exception):
            procs.append((p.info["memory_info"].rss, p.info["name"]))
    for rss, name in sorted(procs, reverse=True)[:8]:
        add(f"  {rss / 2**20:>7.0f} МБ  {name}")

    add("\nПРОГРАММЫ В АВТОЗАГРУЗКЕ:")
    for s in ps_json("Get-CimInstance Win32_StartupCommand | Select-Object Name,Location"):
        add(f"  {s.get('Name')}  [{s.get('Location')}]")

    add("\n" + "=" * 60)
    add("НАЙДЕННЫЕ ПРОБЛЕМЫ:" if issues else "Серьёзных проблем не найдено.")
    for i in issues:
        add(f"  • {i}")
    return issues, "\n".join(lines)
