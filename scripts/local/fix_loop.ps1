# RAINMAN — diagnose and repair the "RAINMAN local loop" (daily 06:50) and "RAINMAN markets" (6-hourly) scheduled tasks.
# Run in an ADMIN PowerShell:  Win+X -> "Terminal (Admin)" -> paste:
#   powershell -ExecutionPolicy Bypass -File C:\Users\jwlar\rainman\scripts\local\fix_loop.ps1
# What it does: shows each task's state / last result / next run / settings, pulls the last Task Scheduler events for them
# (the "why" when a run never started), then re-applies the settings that let a sleeping or logged-off PC still run them
# (wake-to-run, start-when-available, run on battery, run whether logged on or not), allows wake timers in the power plan,
# fires the daily loop once right now and watches the log for it. Nothing here touches the repo, .env or git.
$ErrorActionPreference = 'Continue'
$repo = 'C:\Users\jwlar\rainman'
$tasks = @('RAINMAN local loop', 'RAINMAN markets')

function Show-Task($name) {
    $t = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if (-not $t) { Write-Host "  [$name] NOT REGISTERED" -ForegroundColor Red; return $null }
    $i = $t | Get-ScheduledTaskInfo
    $res = $i.LastTaskResult
    $why = switch ($res) { 0 {'ok'} 1 {'generic failure (script exited 1)'} 267009 {'still running'} 267011 {'has not run yet'} 267014 {'terminated by user / time limit'} 2147942402 {'file not found (cmd/py/rainman.cmd?)'} 2147943645 {'service not available / tried to run while not logged on'} default {"0x{0:X}" -f $res} }
    Write-Host ("  [{0}]  state={1}  enabled={2}" -f $name, $t.State, $t.Settings.Enabled) -ForegroundColor Cyan
    Write-Host ("     last run {0}  result {1} ({2})  next run {3}  missed runs {4}" -f $i.LastRunTime, $res, $why, $i.NextRunTime, $i.NumberOfMissedRuns)
    $s = $t.Settings
    Write-Host ("     wakeToRun={0} startWhenAvailable={1} disallowOnBattery={2} stopOnBattery={3} networkOnly={4} limit={5} multi={6}" -f $s.WakeToRun, $s.StartWhenAvailable, $s.DisallowStartIfOnBatteries, $s.StopIfGoingOnBatteries, $s.RunOnlyIfNetworkAvailable, $s.ExecutionTimeLimit, $s.MultipleInstances)
    Write-Host ("     principal: user={0} logon={1} runLevel={2}" -f $t.Principal.UserId, $t.Principal.LogonType, $t.Principal.RunLevel)
    foreach ($tr in $t.Triggers) { Write-Host ("     trigger: {0}  start {1}  enabled={2}  repeat={3}" -f $tr.CimClass.CimClassName.Replace('MSFT_Task',''), $tr.StartBoundary, $tr.Enabled, $tr.Repetition.Interval) }
    return $t
}

Write-Host "`n== TASKS (before) ==" -ForegroundColor Yellow
$before = @{}; foreach ($n in $tasks) { $before[$n] = Show-Task $n }

Write-Host "`n== TASK SCHEDULER EVENTS, last 4 days (why a run did or did not happen) ==" -ForegroundColor Yellow
try {
    $ev = Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-TaskScheduler/Operational'; StartTime=(Get-Date).AddDays(-4)} -ErrorAction Stop |
          Where-Object { $_.Message -match 'RAINMAN' } | Select-Object -First 40
    if (-not $ev) { Write-Host "  no events mention RAINMAN — the Operational log may be disabled (Event Viewer > Task Scheduler > Operational > Enable Log)" -ForegroundColor DarkYellow }
    foreach ($e in $ev) { Write-Host ("  {0:yyyy-MM-dd HH:mm}  id {1,-4} {2}" -f $e.TimeCreated, $e.Id, ($e.Message -replace '\s+',' ').Substring(0, [Math]::Min(150, ($e.Message -replace '\s+',' ').Length))) }
    Write-Host "  (id 100/102 = started/finished · 129 = process launched · 200/201 = action start/end · 322 = skipped, previous still running · 324 = queued · 327 = stopped (battery) · 329 = killed (time limit) · 332 = launch condition not met, e.g. not logged on · 109 = missed, will run when available · 141 = task deleted)" -ForegroundColor DarkGray
} catch { Write-Host "  could not read the event log: $($_.Exception.Message)" -ForegroundColor DarkYellow }

Write-Host "`n== POWER: can the PC wake itself? ==" -ForegroundColor Yellow
try { powercfg /waketimers 2>&1 | Select-Object -First 12 | ForEach-Object { Write-Host "  $_" } } catch {}
Write-Host "  allowing wake timers on AC and battery for the current power plan (needs admin; harmless if already on)"
powercfg /setacvalueindex SCHEME_CURRENT SUB_SLEEP RTCWAKE 1 2>$null
powercfg /setdcvalueindex SCHEME_CURRENT SUB_SLEEP RTCWAKE 1 2>$null
powercfg /setactive SCHEME_CURRENT 2>$null

Write-Host "`n== REPAIR ==" -ForegroundColor Yellow
$common = @{ AllowStartIfOnBatteries = $true; DontStopIfGoingOnBatteries = $true; StartWhenAvailable = $true; MultipleInstances = 'IgnoreNew'; RunOnlyIfNetworkAvailable = $false }
foreach ($n in $tasks) {
    $t = $before[$n]; if (-not $t) { continue }
    $limit = if ($n -eq 'RAINMAN local loop') { New-TimeSpan -Hours 2 } else { New-TimeSpan -Minutes 30 }
    $settings = New-ScheduledTaskSettingsSet @common -WakeToRun -ExecutionTimeLimit $limit
    # S4U = run whether the user is logged on or not, no password stored; the task keeps running through the lock screen and after logoff
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited
    try {
        Set-ScheduledTask -TaskName $n -Settings $settings -Principal $principal -ErrorAction Stop | Out-Null
        Enable-ScheduledTask -TaskName $n -ErrorAction Stop | Out-Null
        Write-Host "  [$n] settings re-applied, enabled" -ForegroundColor Green
    } catch { Write-Host "  [$n] could not update: $($_.Exception.Message)  (run this window as Administrator)" -ForegroundColor Red }
}
# a safety-net second daily trigger at 12:10: if 06:50 is missed while the PC is off, the noon pass still gets the day's data
try {
    $t = Get-ScheduledTask -TaskName 'RAINMAN local loop'
    $has = $t.Triggers | Where-Object { $_.StartBoundary -match 'T12:10' }
    if (-not $has) {
        $trg = @($t.Triggers) + (New-ScheduledTaskTrigger -Daily -At 12:10)
        Set-ScheduledTask -TaskName 'RAINMAN local loop' -Trigger $trg | Out-Null
        Write-Host "  [RAINMAN local loop] added a second daily trigger at 12:10 (loop.py only pulls what is still due, so a second pass is cheap)" -ForegroundColor Green
    } else { Write-Host "  [RAINMAN local loop] 12:10 safety trigger already present" }
} catch { Write-Host "  could not add the 12:10 trigger: $($_.Exception.Message)" -ForegroundColor Red }

Write-Host "`n== TASKS (after) ==" -ForegroundColor Yellow
foreach ($n in $tasks) { Show-Task $n | Out-Null }

Write-Host "`n== TEST: starting the daily loop now and watching notes\local_runs.log for 90 s ==" -ForegroundColor Yellow
$log = Join-Path $repo 'notes\local_runs.log'
$mark = (Get-Date).ToString('yyyy-MM-dd HH:mm')
Start-ScheduledTask -TaskName 'RAINMAN local loop'
$seen = $false
for ($i = 0; $i -lt 18; $i++) {
    Start-Sleep -Seconds 5
    $tail = Get-Content $log -Tail 5 -ErrorAction SilentlyContinue
    if ($tail -match '=== local loop' -and ($tail -join ' ') -match $mark.Substring(0, 13)) { $seen = $true; break }
}
if ($seen) { Write-Host "  the loop started and is logging — let it finish (box scores, depth, odds, rebuild, push; ~10-20 min)" -ForegroundColor Green }
else { Write-Host "  no new '=== local loop' line in 90 s. Last lines of the log:" -ForegroundColor Red; Get-Content $log -Tail 5 | ForEach-Object { Write-Host "    $_" }; Write-Host "  and the task's last result:"; Show-Task 'RAINMAN local loop' | Out-Null }
Write-Host "`nDone. Send me the output of this window." -ForegroundColor Yellow
