# 启动单机 mongod（自定义数据目录 db/standalone，端口 27017）
# 用法： powershell -ExecutionPolicy Bypass -File deploy\start_standalone.ps1 [-Auth]
param([switch]$Auth)

$root = Split-Path -Parent $PSScriptRoot
$mongod = "D:\MongoDB\mongodb\mongodb-win32-x86_64-windows-8.0.4\bin\mongod.exe"
$conf = Join-Path $PSScriptRoot "standalone.conf"
Set-Location $root

$p = Get-Process mongod -ErrorAction SilentlyContinue
if ($p) { Write-Host "[提示] 已有 mongod 进程在运行（PID $($p.Id)），请先 stop_standalone.ps1" ; exit 0 }

$mongoArgs = @("--config", $conf)
if ($Auth) { $mongoArgs += "--auth" }
Start-Process -FilePath $mongod -ArgumentList $mongoArgs -WindowStyle Hidden -PassThru | Out-Null
Start-Sleep -Seconds 3
Write-Host "[启动] mongod 端口 27017，数据目录 db/standalone，认证：$(if($Auth){'已开启'}else{'未开启'})"
