@echo off
setlocal
cd /d "%~dp0"

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
echo 启动 catalog-service ...
"%~dp0catalog-service\catalog-service.exe"
endlocal
