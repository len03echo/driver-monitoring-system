@echo off
echo ========================================
echo YOLOv8 性能测试工具
echo ========================================
echo.

cd /d "%~dp0"
python tests\test_yolo_performance.py

echo.
echo ========================================
echo 测试完成
echo ========================================
pause
