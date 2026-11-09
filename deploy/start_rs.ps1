# 启动副本集三节点（rs0:27021 / rs1:27022 / rs2:27023），可选加演练节点 rs3:27024
# 用法： powershell -ExecutionPolicy Bypass -File deploy\start_rs.ps1 [-ExtraNode] [-Clean]
param([switch]$ExtraNode, [switch]$Clean)

$root = Split-Path -Parent $PSScriptRoot
$mongod = "D:\MongoDB\mongodb\mongodb-win32-x86_64-windows-8.0.4\bin\mongod.exe"
Set-Location $root

$nodes = @(
  @{ conf = "rs0.conf"; dir = "db\rs0"; port = 27021 },
  @{ conf = "rs1.conf"; dir = "db\rs1"; port = 27022 },
  @{ conf = "rs2.conf"; dir = "db\rs2"; port = 27023 }
)
if ($ExtraNode) { $nodes += @{ conf = "rs3.conf"; dir = "db\rs3"; port = 27024 } }

foreach ($n in $nodes) {
  $dir = Join-Path $root $n.dir
  if ($Clean -and (Test-Path -LiteralPath $dir)) {
    # 只清理副本集自己的数据目录，且必须位于项目 db 目录内
    if ($dir.StartsWith((Join-Path $root "db"))) {
      Remove-Item -LiteralPath $dir -Recurse -Force -ErrorAction SilentlyContinue
    }
  }
  if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  $conf = Join-Path $PSScriptRoot $n.conf
  Start-Process -FilePath $mongod -ArgumentList "--config", $conf -WorkingDirectory $root -WindowStyle Hidden | Out-Null
  Write-Host "[启动] 节点 $(($n.port)) 配置 $($n.conf) 数据目录 $($n.dir)"
}
Start-Sleep -Seconds 4
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
  Where-Object { $_.LocalPort -in 27021, 27022, 27023, 27024 } |
  ForEach-Object { Write-Host "[监听] 127.0.0.1:$($_.LocalPort)" }
