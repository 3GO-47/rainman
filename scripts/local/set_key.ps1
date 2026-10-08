# Writes ODDS_API_KEY into .env at the repo root (git-ignored). Run from anywhere:
#   powershell -ExecutionPolicy Bypass -File C:\Users\jwlar\rainman\scripts\local\set_key.ps1
# The key is typed into a hidden prompt and never echoed, logged or committed.
$root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$env_path = Join-Path $root '.env'
$sec = Read-Host -AsSecureString 'Paste your The Odds API key (input hidden)'
$key = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)).Trim()
if (-not $key) { Write-Host 'nothing entered — .env unchanged'; exit 1 }
$lines = @()
if (Test-Path $env_path) { $lines = Get-Content $env_path | Where-Object { $_ -notmatch '^ODDS_API_KEY=' } }
$lines += "ODDS_API_KEY=$key"
Set-Content -Path $env_path -Value $lines -Encoding ascii
Write-Host "wrote $env_path ($($key.Length) chars). Test it with:  python scripts\fetch_odds_api.py --leagues nfl"
