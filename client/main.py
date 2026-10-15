"""
客户端程序入口

初始化 QApplication，加载配置，创建主窗口，处理启动异常。

依赖：
- PyQt5
"""

import sys
import os
import logging
import ctypes
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client.ui.main_window import MainWindow
from client.config import load_config


def setup_logging():
    """配置日志系统"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Path(__file__).resolve().parent / 'driver_monitor.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def check_dependencies():
    """检查必要的依赖库"""
    required_modules = [
        ('cv2', 'opencv-python'),
        ('PyQt5', 'PyQt5'),
        ('yaml', 'PyYAML'),
        ('pymysql', 'pymysql'),
        ('numpy', 'numpy')
    ]
    
    missing_modules = []
    
    for module_name, package_name in required_modules:
        try:
            __import__(module_name)
        except ImportError:
            missing_modules.append(package_name)
    
    if missing_modules:
        error_msg = f"缺少必要的依赖库：\n" + "\n".join(f"  - {pkg}" for pkg in missing_modules)
        error_msg += f"\n\n请运行以下命令安装：\npip install {' '.join(missing_modules)}"
        return False, error_msg
    
    return True, "所有依赖库已安装"


def main():
    """主函数"""
    logger = logging.getLogger(__name__)
    
    try:
        # 配置日志
        setup_logging()
        logger.info("=" * 60)
        logger.info("驾驶员监测系统启动")
        logger.info("=" * 60)
        
        # 检查依赖
        logger.info("检查依赖库...")
        deps_ok, deps_msg = check_dependencies()
        if not deps_ok:
            logger.error(deps_msg)
            print(f"\n错误：{deps_msg}")
            return 1
        logger.info("依赖库检查通过")
        
        # 加载配置
        logger.info("加载配置文件...")
        try:
            config = load_config()
            logger.info("配置文件加载成功")
        except FileNotFoundError as e:
            error_msg = f"配置文件不存在：{e}\n请确保 client/config.yaml 文件存在"
            logger.error(error_msg)
            print(f"\n错误：{error_msg}")
            return 1
        except Exception as e:
            error_msg = f"配置文件加载失败：{e}"
            logger.error(error_msg)
            print(f"\n错误：{error_msg}")
            return 1
        
        # 创建 QApplication
        logger.info("初始化 Qt 应用...")
        app = QApplication(sys.argv)
        app.setApplicationName("驾驶员监测系统")
        app.setOrganizationName("NJUPT")
        
        # Fusion 风格让样式表在 Windows 上正常渲染
        app.setStyle("Fusion")
        
        # Windows 任务栏图标：设置 AppUserModelID，让任务栏显示独立图标
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "NJUPT.DriverMonitorSystem.1.0"
            )
        except Exception:
            pass
        
        # 生成图标并设置到 QApplication（同步到任务栏）
        try:
            from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPainterPath
            from PyQt5.QtCore import QRectF
            size = 64
            pixmap = QPixmap(size, size)
            pixmap.fill(QColor(0, 0, 0, 0))
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            shield = QPainterPath()
            shield.moveTo(32, 4)
            shield.lineTo(58, 14)
            shield.lineTo(58, 34)
            shield.cubicTo(58, 50, 44, 58, 32, 62)
            shield.cubicTo(20, 58, 6, 50, 6, 34)
            shield.lineTo(6, 14)
            shield.closeSubpath()
            painter.setBrush(QBrush(QColor("#1565C0")))
            painter.setPen(QPen(QColor("#0D47A1"), 1.5))
            painter.drawPath(shield)
            painter.setBrush(QBrush(QColor("white")))
            painter.setPen(QPen(QColor("white"), 1))
            painter.drawEllipse(QRectF(13, 22, 38, 22))
            painter.setBrush(QBrush(QColor("#1565C0")))
            painter.setPen(QPen(QColor("#0D47A1"), 1))
            painter.drawEllipse(QRectF(23, 25, 18, 16))
            painter.setBrush(QBrush(QColor("white")))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QRectF(27, 27, 6, 6))
            painter.end()
            app_icon = QIcon(pixmap)
            app.setWindowIcon(app_icon)
        except Exception:
            pass  # 测试环境或无显示器时静默跳过图标绘制
        
        # 创建主窗口
        logger.info("创建主窗口...")
        try:
            window = MainWindow()
            window.show()
            logger.info("主窗口创建成功")
        except Exception as e:
            error_msg = f"主窗口创建失败：{e}"
            logger.error(error_msg, exc_info=True)
            
            # 显示错误对话框
            QMessageBox.critical(
                None,
                "启动错误",
                f"系统启动失败：\n\n{str(e)}\n\n请查看日志文件 driver_monitor.log 获取详细信息。"
            )
            return 1
        
        # 启动事件循环
        logger.info("系统启动完成，进入事件循环")
        exit_code = app.exec_()
        
        logger.info(f"系统退出，退出码: {exit_code}")
        return exit_code
        
    except KeyboardInterrupt:
        logger.info("用户中断程序")
        return 0
        
    except Exception as e:
        logger.error(f"未预期的错误: {e}", exc_info=True)
        print(f"\n严重错误：{e}")
        print("请查看日志文件 driver_monitor.log 获取详细信息")
        return 1


if __name__ == "__main__":
    sys.exit(main())
