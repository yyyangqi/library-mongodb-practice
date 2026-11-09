# 停止副本集节点（按端口对应的 mongod 进程命令行匹配，只停本项目 db\rs* 数据目录的进程）
# 用法： powershell -ExecutionPolicy Bypass -File deploy\stop_rs.ps1
$root = Split-Path -Parent $PSScriptRoot
$confNames = @("rs0.conf", "rs1.conf", "rs2.conf", "rs3.conf")
$procs = Get-CimInstance Win32_Process -Filter "Name='mongod.exe'" | Where-Object {
  $cl = $_.CommandLine
  ($confNames | Where-Object { $cl -like ("*" + $_) }).Count -gt 0
}
foreach ($p in $procs) {
  Write-Host "[停止] PID $($p.ProcessId) -> $($p.CommandLine)"
  Stop-Process -Id $p.ProcessId -Force
}
Start-Sleep -Seconds 2
$left = (Get-CimInstance Win32_Process -Filter "Name='mongod.exe'" | Where-Object {
  $cl = $_.CommandLine; ($confNames | Where-Object { $cl -like ("*" + $_) }).Count -gt 0 })
if ($left) { Write-Host "[警告] 仍有副本集进程存活" } else { Write-Host "[完成] 副本集进程已全部停止" }
