@echo off
title RiseAI P91 - one-shot session (P94 hardened)
setlocal
chcp 65001 >nul

set "GAME=D:\Monster Hunter Generations Ultimate Recomp"
set "PROJ=D:\MHGU mod maker"
set "OUT=%PROJ%\02_Workspace\game_p91_oneshot.txt"
set "PLUG=%GAME%\mods\RiseAI_EntryProbe\romfs\nativeNX\plugins\rai_entrylocator_probe.nro"
set "REF=%PROJ%\04_RiseAI\out\rai_p90_probe.nro"
set "CFG=%GAME%\mods\forge\romfs\nativeNX\forge\config.ini"
set "BACKUP=%PROJ%\04_RiseAI\out\P94_forge_config_backup_20261116.ini"
set "STATUS=%PROJ%\04_RiseAI\out\P91_watch_status.txt"
set "PY=C:\Users\RongLynn\.workbuddy\binaries\python\versions\3.13.12\python.exe"
set "PREP=%PROJ%\04_RiseAI\tools\prepare_p91_env.py"
set "WATCH=%PROJ%\04_RiseAI\tools\watch_p91_log.py"
set "TOOL=%PROJ%\04_RiseAI\tools\analyze_p91_session.py"
set "TOOL2=%PROJ%\04_RiseAI\tools\analyze_p90_f0.py"
set "TOOL3=%PROJ%\04_RiseAI\tools\check_log_integrity.py"
set "REP=%PROJ%\04_RiseAI\out\P91_session_report"
set "PYTHONIOENCODING=utf-8"

echo === P94 PREFLIGHT : NRO / FORGE LOG LEVEL / LOG ROTATION ===
"%PY%" "%PREP%" "%CFG%" "%PLUG%" "%REF%" "%OUT%" "%STATUS%" "%BACKUP%"
if errorlevel 1 (
  echo.
  echo [x] PREFLIGHT FAILED. DO NOT PLAY. Tell the agent.
  pause
  exit /b 1
)

echo.
echo === HOW TO PLAY THIS ONE SESSION ===
echo   [P93] Goal A (P87 tired-gap) is CLOSED by P92.
echo   No need to chase tiredness / area change / feeding any more.
echo   Just play normally for ONE normal session (~30 min), with TWO
echo   different new large monsters (NOT 0020 / 0050 / 0052 / 0051 / 0047).
echo   Switching quests is fine; quitting the game is NOT.
echo   NEVER press F9. NEVER use instant quest completion.
echo   Quit the game NORMALLY at the end (the log flushes on exit).
echo   Do not touch mods, load_order, or any other task's scripts.
echo.
echo   A background watcher will pop up a WARNING WINDOW within 150 s
echo   if the [rai] banner does not appear. If you see it, quit at once.
echo.
echo   Log file: %OUT%
echo.
pause

start "P91 LOG WATCH" /min "%PY%" "%WATCH%" "%OUT%" "%STATUS%" 150
cd /d "%GAME%"
mhgurecomp.exe > "%OUT%" 2>&1

echo.
echo === POST-RUN SELF CHECK ===
findstr /C:"P90 PROBE" "%OUT%" >nul 2>&1
if errorlevel 1 (
  echo [X] NO [rai] BANNER IN THIS LOG - THIS SESSION HAS NO PLUGIN DATA.
  echo     Do NOT treat it as a valid session. Tell the agent.
) else (
  echo [ok] P90 banner present - plugin logging confirmed.
)
if exist "%STATUS%" type "%STATUS%"
echo.

echo [analysing] ...
"%PY%" "%TOOL%" "%OUT%" --md "%REP%.md" --json "%REP%.json" > "%REP%.console.txt" 2>&1
type "%REP%.console.txt"
echo.
"%PY%" "%TOOL2%" "%OUT%" > "%PROJ%\04_RiseAI\out\P91_f0_detail.txt" 2>&1
"%PY%" "%TOOL3%" "%OUT%" --md "%PROJ%\04_RiseAI\out\P91_log_integrity.md" > "%PROJ%\04_RiseAI\out\P91_integrity_console.txt" 2>&1

echo.
echo [done] main report : %REP%.md
echo [done] F0 detail   : %PROJ%\04_RiseAI\out\P91_f0_detail.txt
echo [done] integrity   : %PROJ%\04_RiseAI\out\P91_log_integrity.md
echo [done] raw log     : %OUT%
echo.
echo Send the raw log path to the agent. Do NOT delete or rename it.
pause
