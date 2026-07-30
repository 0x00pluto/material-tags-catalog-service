@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul

if not exist ".env" (
  if exist ".env.example" (
    copy /Y ".env.example" ".env" >nul
    echo 已从 .env.example 复制出 .env，请先编辑 CATALOG_ROOT 后再启动。
    notepad ".env"
    exit /b 1
  )
  echo 缺少 .env，请复制 .env.example 为 .env 并设置 CATALOG_ROOT。
  exit /b 1
)

copy /Y ".env" "catalog-service\.env" >nul

REM 关闭本窗口快速编辑，避免鼠标点选导致服务假死（失败时提示，仍继续启动；进程内会再关一次）
powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-Type -Name CQE -Namespace W -MemberDefinition '[DllImport(\"kernel32.dll\",SetLastError=true)]public static extern System.IntPtr GetStdHandle(int n);[DllImport(\"kernel32.dll\")]public static extern bool GetConsoleMode(System.IntPtr h, out uint m);[DllImport(\"kernel32.dll\")]public static extern bool SetConsoleMode(System.IntPtr h, uint m);public static int Disable(){var h=GetStdHandle(-10);uint m;if(!GetConsoleMode(h,out m)){return 1;}m&=~(uint)0x40;m|=(uint)0x80;return SetConsoleMode(h,m)?0:2;}' -ErrorAction Stop; exit [W.CQE]::Disable()" 2>nul
if errorlevel 1 (
  echo 警告: 未能关闭本窗口快速编辑，请勿用鼠标点选黑窗；服务进程内会再尝试关闭。
)

echo 启动 catalog-service ...
"%~dp0catalog-service\catalog-service.exe"
endlocal
