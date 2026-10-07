# RAINMAN local loop — one-time setup on Josh's PC. Run from an elevated or normal PowerShell:
#   powershell -ExecutionPolicy Bypass -File C:\Users\jwlar\rainman\scripts\local\install.ps1
# 1) installs the Python packages the scripts use  2) registers a daily Task Scheduler job at 06:50 (local time)
#    that runs scripts\local\rainman.cmd whether or not you are logged in (the PC must be awake — enable "wake to run" below).
# Requires: Python 3 (py launcher) and Git for Windows on PATH. No credentials are stored by this script.
$repo = 'C:\Users\jwlar\rainman'
py -3 -m pip install --user --quiet --upgrade pandas numpy pyarrow beautifulsoup4 lxml openpyxl
$action  = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument "/c `"$repo\scripts\local\rainman.cmd`"" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Daily -At 06:50
$settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'RAINMAN local loop' -Action $action -Trigger $trigger -Settings $settings -Description 'RAINMAN daily data loop (no Claude): slate, NFL box/depth/props/Kalshi, NCAA, NBA/NHL/WNBA, rebuild, commit, push if credentials exist' -Force | Out-Null
Write-Host "Registered 'RAINMAN local loop' (daily 06:50). Test now with:  cd $repo; py -3 scripts\local\loop.py --dry"
Write-Host "To let it push to GitHub unattended, run ONE interactive push yourself (git push) so Git Credential Manager stores your login in Windows Credential Manager. Until then each run commits locally and skips the push."
