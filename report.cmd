@echo off
chcp 65001 >nul
rem ASCII ONLY -- do not put Korean text in this file.
rem cmd.exe re-reads a batch file by byte offset, so non-ASCII bytes plus chcp shift
rem the parser and make comment fragments run as commands. Verified failure, not a
rem precaution. Korean messages and the ordering logic live in tools\report.py.
rem
rem   report.cmd              score the newest ZIP in artifacts\inbox, then serve
rem   report.cmd --all        rebuild every registered run, then serve
rem   report.cmd --run <id>   that run only
rem
rem Korean walkthrough: web\README.md . macOS uses report.command.

setlocal
cd /d "%~dp0"

set "PY=py -3"
where py >nul 2>nul || set "PY=python"

%PY% -X utf8 tools\report.py %*
if errorlevel 1 pause
