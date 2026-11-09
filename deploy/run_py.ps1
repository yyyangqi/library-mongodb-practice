# 运行 Python 脚本并把 stdout/stderr 以 UTF-8 追加到记录文件（避免 PowerShell 对 stderr 包装成报错）
# 用法： powershell -File deploy\run_py.ps1 -Script "src\tools\verify_permissions.py" -Log "records\x.txt" [-Args "--port 27023"]
param(
  [Parameter(Mandatory=$true)][string]$Script,
  [Parameter(Mandatory=$true)][string]$Log,
  [string]$ExtraArgs = "",
  [switch]$Clear
)
$env:PYTHONIOENCODING = "utf-8"
$o = [IO.Path]::GetTempFileName()
$e = [IO.Path]::GetTempFileName()
$argLine = '"' + $Script + '"'
if ($ExtraArgs) { $argLine = $argLine + " " + $ExtraArgs }
$p = Start-Process -FilePath "python" -ArgumentList ("-u " + $argLine) -NoNewWindow -PassThru `
     -RedirectStandardOutput $o -RedirectStandardError $e -WorkingDirectory (Get-Location)
$p.WaitForExit()
$outTxt = [IO.File]::ReadAllText($o, [Text.Encoding]::UTF8)
$errTxt = [IO.File]::ReadAllText($e, [Text.Encoding]::UTF8)
if ($Clear) {
  [IO.File]::WriteAllText($Log, $outTxt, (New-Object Text.UTF8Encoding $true))
} elseif (Test-Path -LiteralPath $Log) {
  Add-Content -LiteralPath $Log -Value $outTxt -Encoding utf8
} else {
  [IO.File]::WriteAllText($Log, $outTxt, (New-Object Text.UTF8Encoding $true))
}
if ($errTxt.Trim().Length -gt 0) {
  Add-Content -LiteralPath $Log -Value ("[stderr] " + $errTxt.Trim()) -Encoding utf8
}
Add-Content -LiteralPath $Log -Value ("[exit] " + $p.ExitCode) -Encoding utf8
Remove-Item -LiteralPath $o, $e -Force -ErrorAction SilentlyContinue
