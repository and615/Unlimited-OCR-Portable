@echo off
echo ========================================
echo    Unlimited-OCR 启动脚本
echo ========================================
echo.

echo [1/3] 检查Python环境...
if not exist python\python.exe (
    echo [ERROR] 未找到内嵌Python
    pause
    exit /b 1
)
echo Python环境已就绪
echo.

echo [2/3] 检查模型文件...
if not exist models\Unlimited-OCR (
    echo [提示] 未找到模型文件
    echo.
    pause
    exit /b 1
)
echo 模型文件已就绪
echo.

echo [3/3] 启动Web界面...
echo 启动后请在浏览器中打开: http://127.0.0.1:7860
echo.
python\python.exe webui.py

pause
