# 停止单机 mongod（按监听端口定位进程，避免误杀副本集节点）
$conn = Get-NetTCPConnection -LocalPort 27017 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    $procId = $conn.OwningProcess | Select-Object -First 1
    Stop-Process -Id $procId -Force
    Start-Sleep -Seconds 1
    Write-Host "[停止] 端口 27017 的 mongod 已关闭（PID $procId）"
} else {
    Write-Host "[提示] 端口 27017 无监听进程"
}
