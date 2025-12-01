@echo off
title Modal Manager
echo ========================================
echo   Modal Manager - 启动中...
echo ========================================
echo.

cd /d "%~dp0"

:: 检查 wails 是否安装
where wails >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到 wails，请先安装 Wails CLI
    echo 安装命令: go install github.com/wailsapp/wails/v2/cmd/wails@latest
    pause
    exit /b 1
)

:: 启动开发模式
echo [启动] wails dev
wails dev

pause
