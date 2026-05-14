@echo off
cd /d "%~dp0"
echo 正在启动管理端，请勿关闭本窗口...
echo 若提示端口占用，请先看窗口里的报错。
call "%ProgramFiles%\nodejs\npm.cmd" run dev
if errorlevel 1 (
  echo.
  echo 若 npm 不在默认路径，请在本目录手动执行: npm run dev
  pause
)
