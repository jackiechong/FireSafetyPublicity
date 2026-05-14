# 使用 18080 端口，避开 Windows 对部分端口（如 8000）的权限/保留限制
Set-Location $PSScriptRoot
$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
  & $python.Source -m uvicorn app.main:app --reload --host 127.0.0.1 --port 18080
  exit $LASTEXITCODE
}

$knownPython = "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe"
if (Test-Path $knownPython) {
  & $knownPython -m uvicorn app.main:app --reload --host 127.0.0.1 --port 18080
  exit $LASTEXITCODE
}

Write-Host "未找到 Python，请先安装 Python 或把 python 加入 PATH。"
exit 1
