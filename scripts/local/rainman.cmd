@echo off
rem RAINMAN local loop — run by Windows Task Scheduler (see install.ps1). Logs to notes\local_runs.log and notes\local_loop.out
cd /d C:\Users\jwlar\rainman
py -3 scripts\local\loop.py %* >> notes\local_loop.out 2>&1
