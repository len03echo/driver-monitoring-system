"""
主窗口 UI

驾驶员监测系统的主界面，包含视频显示区域、控制按钮、状态显示等。

依赖：
- PyQt5
"""

import sys
import os
import logging
import time
from typing import Optional, Dict, Any
import numpy as np
import cv2
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QLabel, QPushButton, QComboBox,
                            QGroupBox, QGridLayout, QTextEdit, QProgressBar,
                            QFileDialog, QStatusBar, QFrame,
                            QScrollArea)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QPixmap, QImage, QFont

# 导入核心模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from client.core.detection_thread import DetectionThread
from client.core.video_source import CameraSource, VideoFileSource
from client.core.behavior_detector import BehaviorDetector
from client.core.fatigue_detector import FatigueDetector
from client.core.face_recognizer import FaceRecognizer
from client.core.alert_engine import AlertEngine
from client.db.db_client import DBClient
from client.config import load_config


class MainWindow(QMainWindow):
    """
    主窗口类，驾驶员监测系统的主界面。
    
    功能：
    - 视频显示区域
    - 控制按钮（开始/停止/暂停）
    - 视频源选择（摄像头/视频文件）
    - 状态显示和日志
    - 人脸认证
    - 告警处理
    """
    
    def __init__(self, initialize_components: bool = True):
        super().__init__()
        
        # 设置全局字体
        from PyQt5.QtGui import QFont
        app_font = QFont()
        app_font.setPointSize(10)  # 设置全局字体大小
        self.setFont(app_font)
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 加载配置
        self.config = load_config()
        
        # 核心组件
        self.detection_thread: Optional[DetectionThread] = None
        self.db_client: Optional[DBClient] = None
        self.current_driver_id: Optional[int] = None
        self.current_driver_name: Optional[str] = None
        self.current_session_id: Optional[int] = None
        
        # UI组件
        self.video_label: Optional[QLabel] = None
        self.control_buttons: Dict[str, QPushButton] = {}
        self.status_label: Optional[QLabel] = None
        self.eye_status_label: Optional[QLabel] = None
        self.mouth_status_label: Optional[QLabel] = None
        self.head_status_label: Optional[QLabel] = None
        self.log_text: Optional[QTextEdit] = None
        
        # 状态变量
        self.is_authenticated = False
        self.is_monitoring = False
        
        # 统计变量
        self.blink_count = 0
        self.yawn_count = 0
        self.alert_count = 0
        
        # 累计统计变量（整个会话期间的总次数）
        self.total_blink_count = 0
        self.total_yawn_count = 0
        self.total_head_down_count = 0
        self.total_head_down_time = 0.0  # 低头总时间（秒）
        self.head_down_start_time = None  # 低头开始时间
        
        # 行为检测时间统计
        self.total_phone_time = 0.0  # 使用手机总时间（秒）
        self.phone_start_time = None  # 使用手机开始时间
        self.total_drink_time = 0.0  # 喝水总时间（秒）
        self.drink_start_time = None  # 喝水开始时间
        self.total_smoke_time = 0.0  # 抽烟总时间（秒）
        self.smoke_start_time = None  # 抽烟开始时间
        
        # 初始化UI
        self.init_ui()
        
        # UI 测试可禁用数据库和检测线程等外部组件
        if initialize_components:
            self.init_components()
        
        self.logger.info("主窗口初始化完成")
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("驾驶员监测系统 - Driver Monitor System")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 700)
        
        # 设置窗口图标
        self._set_window_icon()

        # 中央部件，背景与主窗口一致
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #F0F4F8;")
        self.setCentralWidget(central_widget)

        # 主布局：左右分栏，8px 间距，8px 四周边距
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # 左侧：视频显示区域
        video_group = self.create_video_group()
        main_layout.addWidget(video_group, 2)

        # 右侧：控制面板（滚动区域）
        control_group = self.create_control_group()
        control_group.setMinimumWidth(320)

        scroll_area = QScrollArea()
        scroll_area.setWidget(control_group)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setMinimumWidth(320)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                border-left: 2px solid #1565C0;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #F5F7FA;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #CFD8DC;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #B0BEC5;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        main_layout.addWidget(scroll_area, 1)
        self.create_status_bar()
        
        # 设置浅色专业风格样式
        self.setStyleSheet("""
            /* 主窗口背景 */
            QMainWindow {
                background-color: #F0F4F8;
            }
            QMainWindow::centralWidget {
                background-color: #F0F4F8;
            }

            /* 中央部件基础字体 */
            QWidget {
                color: #212121;
                font-family: 'Microsoft YaHei', 'Segoe UI', Arial;
                font-size: 21px;
            }

            /* 分组框 — 白色卡片 */
            QGroupBox {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                margin-top: 18px;
                padding-top: 14px;
                padding-left: 8px;
                padding-right: 8px;
                padding-bottom: 10px;
                font-weight: bold;
                font-size: 21px;
                color: #1565C0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                top: -9px;
                padding: 4px 12px;
                background-color: #E3F2FD;
                color: #1565C0;
                font-weight: bold;
                font-size: 21px;
                border-radius: 4px;
                border-left: 4px solid #1565C0;
            }

            /* 按钮基础样式（颜色由代码直接设置，此处只定义通用属性）*/
            QPushButton {
                border: none;
                color: white;
                padding: 6px 14px;
                font-size: 21px;
                font-weight: bold;
                border-radius: 6px;
                min-height: 38px;
            }

            /* 下拉框 */
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #CFD8DC;
                border-radius: 6px;
                padding: 4px 8px;
                color: #212121;
                font-size: 21px;
                min-height: 36px;
            }
            QComboBox:hover { border: 1px solid #1565C0; }
            QComboBox::drop-down { border: none; width: 30px; }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 8px solid #1565C0;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid #CFD8DC;
                selection-background-color: #E3F2FD;
                color: #212121;
                font-size: 21px;
            }

            /* 普通标签 */
            QLabel {
                color: #212121;
                font-size: 21px;
                background-color: transparent;
            }

            /* 日志文本框 */
            QTextEdit {
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 6px;
                color: #212121;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 18px;
            }

            /* 滚动条 */
            QScrollBar:vertical {
                background-color: #F5F7FA;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #CFD8DC;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover { background-color: #B0BEC5; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }

            /* 状态栏 */
            QStatusBar {
                background-color: #FFFFFF;
                color: #212121;
                border-top: 2px solid #1565C0;
            }

            /* 分隔线 */
            QFrame[frameShape="4"] {
                color: #E0E0E0;
                background-color: #E0E0E0;
            }
        """)
    
    def create_video_group(self) -> QWidget:
        """创建视频显示组"""
        container = QWidget()
        container.setStyleSheet("background-color: #F0F4F8;")
        layout = QVBoxLayout(container)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # 左上角标题栏 — 与控制面板标题风格一致
        title_bar = QWidget()
        title_bar.setStyleSheet("background-color: transparent;")
        title_bar.setFixedHeight(44)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(8, 6, 8, 6)

        title_label = QLabel("📹 实时视频监控")
        title_label.setStyleSheet("""
            color: #1565C0;
            font-size: 21px;
            font-weight: bold;
            background-color: #E3F2FD;
            border-left: 4px solid #1565C0;
            border-radius: 4px;
            padding: 2px 12px;
        """)
        title_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        title_label.setSizePolicy(title_label.sizePolicy().horizontalPolicy(), 
                                   title_label.sizePolicy().verticalPolicy())

        title_layout.addWidget(title_label)
        title_layout.addStretch()

        layout.addWidget(title_bar)

        self.video_label = QLabel()
        self.video_label.setMinimumSize(480, 360)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #F0F4F8;
                color: #90A4AE;
                font-size: 21px;
            }
        """)
        self.video_label.setText("⏸ 等待视频输入...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setScaledContents(False)

        layout.addWidget(self.video_label)
        return container
    
    def create_control_group(self) -> QGroupBox:
        """创建控制面板组"""
        group = QGroupBox("控制面板")
        layout = QVBoxLayout(group)
        layout.setSpacing(14)
        layout.setContentsMargins(8, 16, 8, 12)
        
        # 视频源选择区域
        source_group = self.create_source_group()
        layout.addWidget(source_group)
        
        # 身份认证区域
        auth_group = self.create_auth_group()
        layout.addWidget(auth_group)
        
        # 控制按钮区域
        button_group = self.create_button_group()
        layout.addWidget(button_group)
        
        # 状态显示区域
        status_group = self.create_status_group()
        layout.addWidget(status_group)
        
        # 日志显示区域
        log_group = self.create_log_group()
        layout.addWidget(log_group)
        
        return group
    
    def create_auth_group(self) -> QGroupBox:
        """创建身份认证组"""
        group = QGroupBox("🔐 身份认证")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 16, 8, 10)
        
        # 当前用户显示
        self.current_user_label = QLabel("✗ 未认证")
        self.current_user_label.setStyleSheet("""
            font-weight: bold; 
            color: #B71C1C;
            font-size: 18px;
            padding: 6px;
            background-color: #FFEBEE;
            border-radius: 6px;
            border: 1px solid #E53935;
            min-height: 28px;
        """)
        self.current_user_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.current_user_label)
        
        # 认证和注册按钮 - 使用网格布局
        button_layout = QGridLayout()
        button_layout.setSpacing(8)
        
        auth_button = QPushButton("👤 认证")
        auth_button.clicked.connect(self.start_face_authentication)
        self._style_button(auth_button, "blue")
        button_layout.addWidget(auth_button, 0, 0)
        
        register_button = QPushButton("➕ 注册")
        register_button.clicked.connect(self.open_register_dialog)
        self._style_button(register_button, "blue")
        button_layout.addWidget(register_button, 0, 1)
        
        layout.addLayout(button_layout)
        
        return group
    
    def create_source_group(self) -> QGroupBox:
        """创建视频源选择组"""
        group = QGroupBox("📷 视频源")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 16, 8, 10)
        
        # 视频源类型选择按钮
        source_button_layout = QHBoxLayout()
        source_button_layout.setSpacing(8)
        
        self.camera_source_button = QPushButton("📹 摄像头")
        self.camera_source_button.setCheckable(True)
        self.camera_source_button.setChecked(True)
        self.camera_source_button.clicked.connect(lambda: self.select_source_type("camera"))
        self._style_button(self.camera_source_button, "blue")
        source_button_layout.addWidget(self.camera_source_button)
        
        self.file_source_button = QPushButton("📁 视频文件")
        self.file_source_button.setCheckable(True)
        self.file_source_button.clicked.connect(lambda: self.select_source_type("file"))
        self._style_button(self.file_source_button, "blue")
        source_button_layout.addWidget(self.file_source_button)
        
        layout.addLayout(source_button_layout)
        
        # 摄像头ID选择
        self.camera_combo = QComboBox()
        self.camera_combo.addItems(["📹 摄像头 0", "📹 摄像头 1", "📹 摄像头 2"])
        layout.addWidget(self.camera_combo)
        
        # 视频文件选择
        self.file_button = QPushButton("📂 选择视频文件")
        self.file_button.clicked.connect(self.select_video_file)
        self.file_button.setVisible(False)
        self._style_button(self.file_button, "blue")
        layout.addWidget(self.file_button)
        
        self.file_path_label = QLabel("未选择文件")
        self.file_path_label.setWordWrap(True)
        self.file_path_label.setStyleSheet("""
            color: #757575; 
            font-size: 18px;
            padding: 6px;
            background-color: #F5F5F5;
            border-radius: 4px;
            border: 1px solid #E0E0E0;
        """)
        self.file_path_label.setVisible(False)
        layout.addWidget(self.file_path_label)
        
        # 视频控制按钮 - 使用网格布局更紧凑
        video_control_layout = QGridLayout()
        video_control_layout.setSpacing(8)
        
        self.open_video_button = QPushButton("▶ 打开")
        self.open_video_button.clicked.connect(self.open_video)
        self._style_button(self.open_video_button, "blue")
        video_control_layout.addWidget(self.open_video_button, 0, 0)
        
        self.pause_video_button = QPushButton("⏸ 暂停")
        self.pause_video_button.setObjectName("pause_video_button")
        self.pause_video_button.clicked.connect(self.pause_video)
        self.pause_video_button.setEnabled(False)
        self._style_button(self.pause_video_button, "orange")
        video_control_layout.addWidget(self.pause_video_button, 0, 1)
        
        self.close_video_button = QPushButton("⏹ 关闭")
        self.close_video_button.setObjectName("close_video_button")
        self.close_video_button.clicked.connect(self.close_video)
        self.close_video_button.setEnabled(False)
        self._style_button(self.close_video_button, "red")
        video_control_layout.addWidget(self.close_video_button, 0, 2)
        
        layout.addLayout(video_control_layout)
        
        return group
    
    def create_button_group(self) -> QGroupBox:
        """创建控制按钮组"""
        group = QGroupBox("🎮 监测控制")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 16, 8, 10)
        
        # 使用网格布局，2行3列排列
        button_grid = QGridLayout()
        button_grid.setSpacing(8)
        button_grid.setHorizontalSpacing(8)
        button_grid.setVerticalSpacing(8)
        
        # 第一行：开始、暂停、停止
        start_button = QPushButton("▶ 开始")
        start_button.clicked.connect(self.start_monitoring)
        start_button.setEnabled(False)
        self._style_button(start_button, "blue")
        self.control_buttons["start"] = start_button
        button_grid.addWidget(start_button, 0, 0)
        
        pause_button = QPushButton("⏸ 暂停")
        pause_button.setObjectName("pause_button")
        pause_button.clicked.connect(self.toggle_pause_monitoring)
        pause_button.setEnabled(False)
        self._style_button(pause_button, "orange")
        self.control_buttons["pause"] = pause_button
        button_grid.addWidget(pause_button, 0, 1)
        
        stop_button = QPushButton("⏹ 停止")
        stop_button.setObjectName("stop_button")
        stop_button.clicked.connect(self.stop_monitoring)
        stop_button.setEnabled(False)
        self._style_button(stop_button, "red")
        self.control_buttons["stop"] = stop_button
        button_grid.addWidget(stop_button, 0, 2)
        
        # 第二行：关键点按钮居中
        landmarks_button = QPushButton("👁 关键点")
        landmarks_button.setCheckable(True)
        landmarks_button.clicked.connect(self.toggle_landmarks)
        landmarks_button.setEnabled(False)
        self._style_button(landmarks_button, "blue")
        self.control_buttons["landmarks"] = landmarks_button
        button_grid.addWidget(landmarks_button, 1, 0, 1, 3)  # 跨3列
        
        layout.addLayout(button_grid)
        
        return group
    
    def create_status_group(self) -> QGroupBox:
        """创建状态显示组"""
        group = QGroupBox("📊 系统状态")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 16, 8, 10)
        
        # 监测状态
        self.status_label = QLabel("✅ 系统就绪")
        self.status_label.setStyleSheet("""
            font-weight: bold;
            font-size: 18px;
            padding: 6px 12px;
            background-color: #E8F5E9;
            border-radius: 14px;
            border: 1px solid #2E7D32;
            color: #1B5E20;
            min-height: 32px;
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 实时状态显示（眼睛、嘴巴、头部）- 横向排列
        status_layout = QHBoxLayout()
        status_layout.setSpacing(6)
        
        # 眼睛状态
        self.eye_status_label = QLabel("👁 眼睛: 正常")
        self.eye_status_label.setStyleSheet("""
            font-size: 18px; font-weight: bold; padding: 5px;
            background-color: #E8F5E9; border-radius: 4px;
            border: 1px solid #2E7D32; color: #1B5E20; min-height: 32px;
        """)
        self.eye_status_label.setAlignment(Qt.AlignCenter)
        self.eye_status_label.setMinimumWidth(70)
        status_layout.addWidget(self.eye_status_label)

        # 嘴巴状态
        self.mouth_status_label = QLabel("👄 嘴巴: 正常")
        self.mouth_status_label.setStyleSheet("""
            font-size: 18px; font-weight: bold; padding: 5px;
            background-color: #E8F5E9; border-radius: 4px;
            border: 1px solid #2E7D32; color: #1B5E20; min-height: 32px;
        """)
        self.mouth_status_label.setAlignment(Qt.AlignCenter)
        self.mouth_status_label.setMinimumWidth(70)
        status_layout.addWidget(self.mouth_status_label)

        # 头部状态
        self.head_status_label = QLabel("🧑 头部: 正常")
        self.head_status_label.setStyleSheet("""
            font-size: 18px; font-weight: bold; padding: 5px;
            background-color: #E8F5E9; border-radius: 4px;
            border: 1px solid #2E7D32; color: #1B5E20; min-height: 32px;
        """)
        self.head_status_label.setAlignment(Qt.AlignCenter)
        self.head_status_label.setMinimumWidth(70)
        status_layout.addWidget(self.head_status_label)
        
        layout.addLayout(status_layout)
        
        # 行为状态显示（Phone、Drink、Smoke）- 横向排列
        behavior_layout = QHBoxLayout()
        behavior_layout.setSpacing(6)
        
        # Phone 状态
        self.phone_status_label = QLabel("📱 手机: 正常")
        self.phone_status_label.setStyleSheet("""
            font-size: 18px; font-weight: bold; padding: 5px;
            background-color: #E8F5E9; border-radius: 4px;
            border: 1px solid #2E7D32; color: #1B5E20; min-height: 32px;
        """)
        self.phone_status_label.setAlignment(Qt.AlignCenter)
        self.phone_status_label.setMinimumWidth(70)
        behavior_layout.addWidget(self.phone_status_label)

        # Drink 状态
        self.drink_status_label = QLabel("🥤 喝水: 正常")
        self.drink_status_label.setStyleSheet("""
            font-size: 18px; font-weight: bold; padding: 5px;
            background-color: #E8F5E9; border-radius: 4px;
            border: 1px solid #2E7D32; color: #1B5E20; min-height: 32px;
        """)
        self.drink_status_label.setAlignment(Qt.AlignCenter)
        self.drink_status_label.setMinimumWidth(70)
        behavior_layout.addWidget(self.drink_status_label)

        # Smoke 状态
        self.smoke_status_label = QLabel("🚬 抽烟: 正常")
        self.smoke_status_label.setStyleSheet("""
            font-size: 18px; font-weight: bold; padding: 5px;
            background-color: #E8F5E9; border-radius: 4px;
            border: 1px solid #2E7D32; color: #1B5E20; min-height: 32px;
        """)
        self.smoke_status_label.setAlignment(Qt.AlignCenter)
        self.smoke_status_label.setMinimumWidth(70)
        behavior_layout.addWidget(self.smoke_status_label)
        
        layout.addLayout(behavior_layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # FPS和告警计数单独一行显示，字体加大到14px
        fps_alert_layout = QHBoxLayout()
        fps_alert_layout.setSpacing(8)
        
        # FPS显示
        self.fps_label = QLabel("⚡ FPS: --")
        self.fps_label.setStyleSheet("""
            font-size: 18px; font-weight: bold; padding: 5px;
            background-color: #F5F5F5; border-radius: 4px;
            color: #212121; border: 1px solid #E0E0E0;
        """)
        fps_alert_layout.addWidget(self.fps_label)

        # 告警计数
        self.alert_count_label = QLabel("⚠ 告警次数: 0")
        self.alert_count_label.setStyleSheet("""
            font-size: 18px; font-weight: bold; padding: 5px;
            background-color: #F5F5F5; border-radius: 4px;
            color: #2E7D32; border: 1px solid #E0E0E0;
        """)
        fps_alert_layout.addWidget(self.alert_count_label)
        
        layout.addLayout(fps_alert_layout)
        
        # 统计信息样式
        stat_style = """
            font-size: 18px;
            padding: 5px;
            background-color: #F5F5F5;
            border-radius: 4px;
            color: #212121;
            border: 1px solid #E0E0E0;
        """
        
        # 统计信息 - 两列布局
        stats_grid = QGridLayout()
        stats_grid.setSpacing(6)
        
        # 第一列
        self.blink_count_label = QLabel("😴 闭眼次数: 0")
        self.blink_count_label.setStyleSheet(stat_style)
        stats_grid.addWidget(self.blink_count_label, 0, 0)
        
        self.yawn_count_label = QLabel("🥱 打哈欠: 0")
        self.yawn_count_label.setStyleSheet(stat_style)
        stats_grid.addWidget(self.yawn_count_label, 1, 0)
        
        self.head_down_count_label = QLabel("⬇ 低头: 0秒")
        self.head_down_count_label.setStyleSheet(stat_style)
        stats_grid.addWidget(self.head_down_count_label, 2, 0)
        
        # 第二列
        self.phone_time_label = QLabel("📱 手机: 0秒")
        self.phone_time_label.setStyleSheet(stat_style)
        stats_grid.addWidget(self.phone_time_label, 0, 1)
        
        self.drink_time_label = QLabel("🥤 喝水: 0秒")
        self.drink_time_label.setStyleSheet(stat_style)
        stats_grid.addWidget(self.drink_time_label, 1, 1)
        
        self.smoke_time_label = QLabel("🚬 抽烟: 0秒")
        self.smoke_time_label.setStyleSheet(stat_style)
        stats_grid.addWidget(self.smoke_time_label, 2, 1)
        
        layout.addLayout(stats_grid)
        
        return group
    
    def create_log_group(self) -> QGroupBox:
        """创建日志显示组"""
        group = QGroupBox("📝 系统日志")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 16, 8, 10)
        
        self.log_text = QTextEdit()
        self.log_text.setMinimumHeight(120)
        self.log_text.setReadOnly(True)
        self.log_text.setAcceptRichText(True)
        layout.addWidget(self.log_text)
        
        # 清除日志按钮
        clear_button = QPushButton("🗑 清除日志")
        clear_button.setObjectName("clear_log_button")
        clear_button.clicked.connect(self.clear_log)
        self._style_button(clear_button, "outline")
        layout.addWidget(clear_button)
        
        return group
    
    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        from PyQt5.QtGui import QFont
        sb_font = QFont('Microsoft YaHei', 13)
        self.status_bar.setFont(sb_font)
        self.status_bar.setMinimumHeight(44)
        self.status_bar.setMaximumHeight(44)
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #FFFFFF;
                color: #212121;
                border-top: 2px solid #1565C0;
                padding: 0 12px;
            }
        """)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("系统就绪")
    
    def _set_window_icon(self):
        """生成并设置窗口图标（蓝色盾牌+眼睛，代表驾驶员安全监测）"""
        from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPainterPath
        from PyQt5.QtCore import QRectF, QPointF
        
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(0, 0, 0, 0))  # 透明背景
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制盾牌形状
        shield = QPainterPath()
        shield.moveTo(32, 4)
        shield.lineTo(58, 14)
        shield.lineTo(58, 34)
        shield.cubicTo(58, 50, 44, 58, 32, 62)
        shield.cubicTo(20, 58, 6, 50, 6, 34)
        shield.lineTo(6, 14)
        shield.closeSubpath()
        
        # 填充盾牌 — 深蓝色
        painter.setBrush(QBrush(QColor("#1565C0")))
        painter.setPen(QPen(QColor("#0D47A1"), 1.5))
        painter.drawPath(shield)
        
        # 绘制眼睛外轮廓（白色椭圆）
        painter.setBrush(QBrush(QColor("white")))
        painter.setPen(QPen(QColor("white"), 1))
        painter.drawEllipse(QRectF(13, 22, 38, 22))
        
        # 绘制瞳孔（深蓝色圆）
        painter.setBrush(QBrush(QColor("#1565C0")))
        painter.setPen(QPen(QColor("#0D47A1"), 1))
        painter.drawEllipse(QRectF(23, 25, 18, 16))
        
        # 绘制高光（白色小圆）
        painter.setBrush(QBrush(QColor("white")))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(27, 27, 6, 6))
        
        # 绘制眼睛轮廓线
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#E3F2FD"), 1.5))
        painter.drawEllipse(QRectF(13, 22, 38, 22))
        
        painter.end()
        
        self.setWindowIcon(QIcon(pixmap))

    def _style_button(self, btn: QPushButton, color: str = "blue"):
        """直接给按钮设置颜色，绕过样式表继承问题"""
        colors = {
            "blue":   ("background-color: #1976D2;", "background-color: #2196F3;", "background-color: #1565C0;", "background-color: #B0BEC5;"),
            "orange": ("background-color: #F57C00;", "background-color: #FF9800;", "background-color: #E65100;", "background-color: #B0BEC5;"),
            "red":    ("background-color: #E53935;", "background-color: #EF5350;", "background-color: #C62828;", "background-color: #B0BEC5;"),
            "outline":("background-color: #1565C0; border: 2px solid #1565C0; color: white;",
                       "background-color: #1976D2; border: 2px solid #1976D2; color: white;",
                       "background-color: #0D47A1; border: 2px solid #0D47A1; color: white;",
                       "background-color: #B0BEC5;"),
        }
        normal, hover, pressed, disabled = colors.get(color, colors["blue"])
        btn.setStyleSheet(f"""
            QPushButton {{
                {normal}
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 21px;
                font-weight: bold;
                min-height: 38px;
            }}
            QPushButton:hover {{ {hover} color: white; border: none; border-radius: 6px; }}
            QPushButton:pressed {{ {pressed} color: white; border: none; border-radius: 6px; }}
            QPushButton:disabled {{ {disabled} color: #78909C; border: none; border-radius: 6px; }}
        """)

    def init_components(self):
        """初始化核心组件"""
        try:
            # 初始化数据库客户端
            db_cfg = self.config.database
            self.db_client = DBClient(
                host=db_cfg.host,
                port=db_cfg.port,
                user=db_cfg.user,
                password=db_cfg.password,
                database=db_cfg.name
            )
            
            # 初始化检测线程
            self.detection_thread = DetectionThread()
            
            # 连接信号
            self.detection_thread.frame_ready.connect(self.on_frame_ready)
            self.detection_thread.detection_result.connect(self.on_detection_result)
            self.detection_thread.status_changed.connect(self.on_status_changed)
            self.detection_thread.error_occurred.connect(self.on_error_occurred)
            self.detection_thread.fps_updated.connect(self.on_fps_updated)
            self.detection_thread.video_ended.connect(self.on_video_ended)
            
            self.add_log("核心组件初始化完成")
            
        except Exception as e:
            self.logger.error(f"初始化核心组件失败: {e}")
            self.add_log(f"错误: 初始化失败 - {str(e)}")
            self.show_status_message(f"系统初始化失败：{str(e)}", 5000, "error")
    
    def add_log(self, message: str, level: str = "info"):
        """
        添加日志消息
        
        Args:
            message: 日志消息
            level: 日志级别 (info, warning, error, success)
        """
        if self.log_text:
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # 根据级别设置颜色 - 适配浅色主题
            color_map = {
                "info": "#1565C0",      # 主色调
                "warning": "#E65100",   # 警告状态
                "error": "#B71C1C",     # 危险/报警状态
                "success": "#2E7D32"    # 成功/正常状态
            }
            color = color_map.get(level, "#1565C0")
            
            # 添加带颜色的日志
            self.log_text.append(f'<span style="color: {color};">[{timestamp}] {message}</span>')
            
            # 自动滚动到底部
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def show_status_message(self, message: str, duration: int = 3000, level: str = "info"):
        """
        在状态栏显示临时消息
        
        Args:
            message: 消息内容
            duration: 显示时长（毫秒）
            level: 消息级别 (info, warning, error, success)
        """
        # 在状态栏显示消息
        self.status_bar.showMessage(message, duration)
        
        # 同时添加到日志
        self.add_log(message, level)
    
    def clear_log(self):
        """清除日志"""
        if self.log_text:
            self.log_text.clear()
    
    def select_source_type(self, source_type: str):
        """选择视频源类型"""
        if source_type == "camera":
            self.camera_source_button.setChecked(True)
            self.file_source_button.setChecked(False)
            self.camera_combo.setVisible(True)
            self.file_button.setVisible(False)
            self.file_path_label.setVisible(False)
            self.add_log("切换到摄像头模式")
        else:  # file
            self.camera_source_button.setChecked(False)
            self.file_source_button.setChecked(True)
            self.camera_combo.setVisible(False)
            self.file_button.setVisible(True)
            self.file_path_label.setVisible(True)
            self.add_log("切换到视频文件模式")
    
    @pyqtSlot(str)
    def on_source_type_changed(self, source_type: str):
        """视频源类型改变处理（保留用于兼容性）"""
        pass
    
    def select_video_file(self):
        """选择视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", 
            "视频文件 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*)"
        )
        if file_path:
            self.file_path_label.setText(os.path.basename(file_path))
            self.file_path_label.setProperty("full_path", file_path)
            self.add_log(f"选择视频文件: {file_path}")
    
    def open_video(self):
        """打开视频"""
        try:
            # 创建视频源
            video_source = self.create_video_source()
            if not video_source:
                return
            
            # 如果检测线程不存在，创建一个
            if not self.detection_thread:
                self.detection_thread = DetectionThread()
                self.detection_thread.frame_ready.connect(self.on_frame_ready)
                self.detection_thread.fps_updated.connect(self.on_fps_updated)
                self.detection_thread.video_ended.connect(self.on_video_ended)
            
            # 设置视频源
            self.detection_thread.set_video_source(video_source)
            
            # 只启动视频预览，不进行检测
            self.detection_thread.set_detection_config(
                enable_behavior=False,
                enable_fatigue=False,
                enable_face=False
            )
            
            # 启动视频
            self.detection_thread.start_detection()
            
            # 更新按钮状态
            self.open_video_button.setEnabled(False)
            self.pause_video_button.setEnabled(True)
            self.close_video_button.setEnabled(True)
            
            self.add_log("视频已打开")
            
        except Exception as e:
            self.logger.error(f"打开视频失败: {e}")
            self.add_log(f"错误: 打开视频失败 - {str(e)}")
            self.show_status_message(f"打开视频失败：{str(e)}", 5000, "error")
    
    def pause_video(self):
        """暂停/恢复视频"""
        if self.detection_thread:
            if self.detection_thread.is_paused():
                self.detection_thread.resume_detection()
                self.pause_video_button.setText("⏸ 暂停")
                self.add_log("视频已恢复")
            else:
                self.detection_thread.pause_detection()
                self.pause_video_button.setText("▶ 恢复")
                self.add_log("视频已暂停")
    
    def close_video(self):
        """关闭视频"""
        # 如果正在监测，不允许关闭视频
        if self.is_monitoring:
            self.show_status_message("监测进行中，无法关闭视频！请先停止监测。", 5000, "warning")
            return
        
        if self.detection_thread:
            self.detection_thread.stop_detection()
            
            # 清除视频显示
            self.video_label.clear()
            self.video_label.setText("⏸ 等待视频输入...")
            
            # 更新按钮状态
            self.open_video_button.setEnabled(True)
            self.pause_video_button.setEnabled(False)
            self.pause_video_button.setText("⏸ 暂停")
            self.close_video_button.setEnabled(False)
            
            self.add_log("视频已关闭")
    
    def toggle_landmarks(self):
        """切换关键点显示"""
        if self.detection_thread and self.is_monitoring:
            landmarks_enabled = self.control_buttons["landmarks"].isChecked()
            
            # 更新检测配置（保持当前的检测状态，只改变关键点显示）
            self.detection_thread.set_detection_config(
                enable_behavior=True,   # 保持行为检测启用
                enable_fatigue=True,    # 保持疲劳检测启用
                enable_face=False,
                draw_landmarks=landmarks_enabled
            )
            
            # 更新按钮文本
            if landmarks_enabled:
                self.control_buttons["landmarks"].setText("🙈 隐藏")
                self.add_log("已启用关键点显示")
            else:
                self.control_buttons["landmarks"].setText("👁 关键点")
                self.add_log("已禁用关键点显示")
    
    def start_face_authentication(self):
        """开始人脸认证"""
        if not self.is_authenticated:
            try:
                # 检查视频是否已打开（通过按钮状态判断）
                video_is_open = not self.open_video_button.isEnabled()
                
                # 如果没有视频源，提示用户先打开视频
                if not video_is_open:
                    self.show_status_message("请先打开视频源！人脸认证需要使用摄像头或视频文件。", 5000, "warning")
                    return
                
                # 如果视频暂停，自动恢复
                was_paused = False
                if self.detection_thread and self.detection_thread.is_paused():
                    self.detection_thread.resume_detection()
                    was_paused = True
                    self.add_log("自动恢复视频以进行人脸认证")
                
                # 导入人脸认证对话框
                from client.ui.face_auth_dialog import FaceAuthDialog
                
                # 创建人脸识别器
                from client.core.face_recognizer import FaceRecognizer
                face_recognizer = FaceRecognizer(
                    model_name=self.config.model.insightface_name
                )
                
                # 创建认证对话框（使用外部帧）
                dialog = FaceAuthDialog(
                    face_recognizer=face_recognizer,
                    db_client=self.db_client,
                    use_external_frames=True,  # 始终使用外部帧
                    parent=self
                )
                
                # 连接认证成功信号
                dialog.auth_success.connect(self.on_auth_success)
                
                # 连接帧信号
                self.detection_thread.frame_ready.connect(dialog.set_frame)
                
                # 显示对话框
                result = dialog.exec_()
                
                # 断开帧信号连接
                try:
                    self.detection_thread.frame_ready.disconnect(dialog.set_frame)
                except:
                    pass
                
                # 清理人脸识别器
                face_recognizer.close()
                
                # 如果之前是暂停状态，恢复暂停
                if was_paused and not self.is_monitoring:
                    self.detection_thread.pause_detection()
                    self.add_log("恢复视频暂停状态")
                
                if result != FaceAuthDialog.Accepted:
                    self.add_log("人脸认证已取消")
                
            except Exception as e:
                self.logger.error(f"人脸认证失败: {e}")
                self.add_log(f"错误: 人脸认证失败 - {str(e)}")
                self.show_status_message(f"人脸认证失败：{str(e)}", 5000, "error")
        else:
            # 注销
            self.is_authenticated = False
            self.current_driver_id = None
            self.current_driver_name = None
            self.current_user_label.setText("✗ 未认证")
            self.current_user_label.setStyleSheet("""
                font-weight: bold; 
                color: #B71C1C;
                font-size: 18px;
                padding: 6px;
                background-color: #FFEBEE;
                border-radius: 6px;
                border: 1px solid #E53935;
                min-height: 28px;
            """)
            self.control_buttons["start"].setEnabled(False)
            if self.is_monitoring:
                self.stop_monitoring()
            self.add_log("已注销")
            self.status_bar.showMessage("已注销")
    
    def on_auth_success(self, driver_info: dict):
        """
        人脸认证成功回调
        
        Args:
            driver_info: 驾驶员信息字典
        """
        self.is_authenticated = True
        self.current_driver_id = driver_info['id']
        self.current_driver_name = driver_info['name']
        
        # 更新UI
        self.current_user_label.setText(
            f"✓ 驾驶员: {driver_info['name']} (工号: {driver_info['employee_id']})"
        )
        self.current_user_label.setStyleSheet("""
            font-weight: bold; 
            color: #1B5E20;
            font-size: 18px;
            padding: 6px;
            background-color: #E8F5E9;
            border-radius: 6px;
            border: 1px solid #2E7D32;
            min-height: 28px;
        """)
        self.control_buttons["start"].setEnabled(True)
        
        self.add_log(f"人脸认证成功: {driver_info['name']} ({driver_info['employee_id']})", "success")
        self.show_status_message(f"认证成功，欢迎 {driver_info['name']}！", 5000, "success")
    
    def open_register_dialog(self):
        """打开注册对话框"""
        try:
            # 检查视频是否已打开（通过按钮状态判断）
            video_is_open = not self.open_video_button.isEnabled()
            
            # 如果没有视频源，提示用户先打开视频
            if not video_is_open:
                self.show_status_message("请先打开视频源！注册新用户需要使用摄像头或视频文件采集人脸照片。", 5000, "warning")
                return
            
            # 如果视频暂停，自动恢复
            was_paused = False
            if self.detection_thread and self.detection_thread.is_paused():
                self.detection_thread.resume_detection()
                was_paused = True
                self.add_log("自动恢复视频以进行用户注册")
            
            from client.ui.register_dialog import RegisterDialog
            
            # 创建注册对话框（使用外部帧）
            dialog = RegisterDialog(
                db_client=self.db_client,
                use_external_frames=True,
                parent=self
            )
            
            # 连接帧信号
            self.detection_thread.frame_ready.connect(dialog.set_frame)
            
            result = dialog.exec_()
            
            # 断开帧信号连接
            try:
                self.detection_thread.frame_ready.disconnect(dialog.set_frame)
            except:
                pass
            
            # 如果之前是暂停状态，恢复暂停
            if was_paused and not self.is_monitoring:
                self.detection_thread.pause_detection()
                self.add_log("恢复视频暂停状态")
            
            if result == RegisterDialog.Accepted:
                self.add_log("新驾驶员注册成功", "success")
                self.show_status_message("驾驶员注册成功！现在可以进行人脸认证了。", 5000, "success")
            else:
                self.add_log("取消注册")
                
        except Exception as e:
            self.logger.error(f"打开注册对话框失败: {e}")
            self.add_log(f"错误: 打开注册对话框失败 - {str(e)}")
            self.show_status_message(f"打开注册对话框失败：{str(e)}", 5000, "error")
    
    def start_monitoring(self):
        """开始监测"""
        if not self.is_authenticated:
            self.show_status_message("请先进行身份认证", 5000, "warning")
            return
        
        try:
            # 重置统计计数器
            self.total_blink_count = 0
            self.total_yawn_count = 0
            self.total_head_down_count = 0
            self.total_head_down_time = 0.0
            self.head_down_start_time = None
            self.blink_count_label.setText("😴 闭眼次数: 0")
            self.yawn_count_label.setText("🥱 打哈欠: 0")
            self.head_down_count_label.setText("⬇ 低头: 0秒")
            self.alert_count_label.setText("⚠ 告警次数: 0")
            
            # 重置告警计数颜色为绿色（正常状态）
            self.alert_count_label.setStyleSheet("""
                font-size: 18px;
                font-weight: bold;
                padding: 5px;
                background-color: #F5F5F5;
                border-radius: 4px;
                color: #2E7D32;
                border: 1px solid #E0E0E0;
            """)
            
            # 重置行为检测时间统计
            self.total_phone_time = 0.0
            self.phone_start_time = None
            self.total_drink_time = 0.0
            self.drink_start_time = None
            self.total_smoke_time = 0.0
            self.smoke_start_time = None
            self.phone_time_label.setText("📱 手机: 0秒")
            self.drink_time_label.setText("🥤 喝水: 0秒")
            self.smoke_time_label.setText("🚬 抽烟: 0秒")
            
            # 检查是否已经有视频源在运行
            if not self.detection_thread or not self.detection_thread.video_source:
                # 如果没有视频源，创建一个新的
                video_source = self.create_video_source()
                if not video_source:
                    return
                self.detection_thread.set_video_source(video_source)
            
            # 创建检测器
            detectors = self.create_detectors()
            
            # 创建预警引擎
            alert_engine = self.create_alert_engine()
            
            # 配置检测线程
            self.detection_thread.set_detectors(*detectors)
            self.detection_thread.set_alert_engine(alert_engine)
            self.detection_thread.db_client = self.db_client
            
            # 启用疲劳检测和行为检测
            self.detection_thread.set_detection_config(
                enable_behavior=True,   # 启用行为检测（YOLOv8）
                enable_fatigue=True,    # 启用疲劳检测
                enable_face=False,      # 禁用人脸识别（监测时不需要）
                draw_landmarks=False    # 默认不显示关键点
            )
            
            # 创建新会话
            self.create_new_session()
            
            # 如果检测线程没有运行，启动它
            if not self.detection_thread.is_running():
                self.detection_thread.start_detection()
            
            # 更新UI状态
            self.is_monitoring = True
            self.control_buttons["start"].setEnabled(False)
            self.control_buttons["pause"].setEnabled(True)
            self.control_buttons["stop"].setEnabled(True)
            self.control_buttons["landmarks"].setEnabled(True)  # 启用关键点按钮
            
            # 更新视频控制按钮状态
            self.open_video_button.setEnabled(False)
            self.pause_video_button.setEnabled(True)
            self.close_video_button.setEnabled(False)  # 监测时不允许关闭视频
            
            self.add_log("开始监测")
            
        except Exception as e:
            self.logger.error(f"启动监测失败: {e}")
            self.add_log(f"错误: 启动监测失败 - {str(e)}")
            self.show_status_message(f"启动监测失败：{str(e)}", 5000, "error")
    
    def create_video_source(self):
        """创建视频源"""
        # 判断当前选择的是摄像头还是视频文件
        if self.camera_source_button.isChecked():
            device_index = self.camera_combo.currentIndex()
            return CameraSource(device_index=device_index)
        else:  # 视频文件
            file_path = self.file_path_label.property("full_path")
            if not file_path:
                self.show_status_message("请先选择视频文件", 5000, "warning")
                return None
            return VideoFileSource(file_path=file_path)
    
    def create_detectors(self):
        """创建检测器"""
        # 启用行为检测器（YOLOv8）
        behavior_detector = BehaviorDetector(
            model_path=self.config.model.yolo_path,
            consecutive_threshold=self.config.detection.behavior_threshold,
            inference_size=self.config.yolo.inference_size,
            use_half=self.config.yolo.use_half
        )
        
        # 创建疲劳检测器，传入配置
        fatigue_detector = FatigueDetector(config=self.config)
        
        # 创建人脸识别器（监测时不需要，只在认证时使用）
        face_recognizer = None
        # face_recognizer = FaceRecognizer(
        #     model_name=self.config.model.insightface_name
        # )
        
        return behavior_detector, fatigue_detector, face_recognizer
    
    def create_alert_engine(self):
        """创建预警引擎"""
        snapshots_dir = self.config.alert.snapshot_dir
        alert_sound_path = self.config.alert.sound_path

        alert_engine = AlertEngine(
            snapshots_dir=snapshots_dir,
            alert_sound_path=alert_sound_path
        )
        
        # 设置会话信息
        if self.current_session_id and self.current_driver_id:
            alert_engine.set_session_info(self.current_session_id, self.current_driver_id)
        
        return alert_engine
    
    def create_new_session(self):
        """创建新的监测会话"""
        try:
            if self.db_client and self.current_driver_id:
                self.current_session_id = self.db_client.create_session(
                    driver_id=self.current_driver_id
                )
                self.add_log(f"创建新会话: ID={self.current_session_id}")
                
                # 设置 alert_engine 的会话信息
                if self.detection_thread and self.detection_thread.alert_engine:
                    self.detection_thread.alert_engine.set_session_info(
                        session_id=self.current_session_id,
                        driver_id=self.current_driver_id
                    )
        except Exception as e:
            self.logger.error(f"创建会话失败: {e}")
            self.add_log(f"警告: 创建会话失败 - {str(e)}")
    
    def toggle_pause_monitoring(self):
        """切换暂停/恢复监测"""
        if self.detection_thread and self.is_monitoring:
            if self.detection_thread.is_paused():
                self.detection_thread.resume_detection()
                self.control_buttons["pause"].setText("暂停监测")
                self.add_log("恢复监测")
            else:
                self.detection_thread.pause_detection()
                self.control_buttons["pause"].setText("恢复监测")
                self.add_log("暂停监测")
    
    def stop_monitoring(self):
        """停止监测"""
        if self.detection_thread and self.is_monitoring:
            # 结束会话
            self.end_current_session()
            
            # 停止检测功能，但保持视频预览
            self.detection_thread.set_detection_config(
                enable_behavior=False,
                enable_fatigue=False,
                enable_face=False,
                draw_landmarks=False
            )
            
            # 重置状态标签
            self.eye_status_label.setText("👁 眼睛: 正常")
            self.eye_status_label.setStyleSheet("""
                font-size: 18px; 
                font-weight: bold;
                padding: 5px;
                background-color: #E8F5E9;
                border-radius: 4px;
                border: 1px solid #2E7D32;
                color: #1B5E20;
                min-height: 28px;
            """)
            self.mouth_status_label.setText("👄 嘴巴: 正常")
            self.mouth_status_label.setStyleSheet("""
                font-size: 18px; 
                font-weight: bold;
                padding: 5px;
                background-color: #E8F5E9;
                border-radius: 4px;
                border: 1px solid #2E7D32;
                color: #1B5E20;
                min-height: 28px;
            """)
            self.head_status_label.setText("🧑 头部: 正常")
            self.head_status_label.setStyleSheet("""
                font-size: 18px; 
                font-weight: bold;
                padding: 5px;
                background-color: #E8F5E9;
                border-radius: 4px;
                border: 1px solid #2E7D32;
                color: #1B5E20;
                min-height: 28px;
            """)
            
            # 重置行为状态标签
            self.phone_status_label.setText("📱 手机: 正常")
            self.phone_status_label.setStyleSheet("""
                font-size: 18px; 
                font-weight: bold;
                padding: 5px;
                background-color: #E8F5E9;
                border-radius: 4px;
                border: 1px solid #2E7D32;
                color: #1B5E20;
                min-height: 28px;
            """)
            self.drink_status_label.setText("🥤 喝水: 正常")
            self.drink_status_label.setStyleSheet("""
                font-size: 18px; 
                font-weight: bold;
                padding: 5px;
                background-color: #E8F5E9;
                border-radius: 4px;
                border: 1px solid #2E7D32;
                color: #1B5E20;
                min-height: 28px;
            """)
            self.smoke_status_label.setText("🚬 抽烟: 正常")
            self.smoke_status_label.setStyleSheet("""
                font-size: 18px; 
                font-weight: bold;
                padding: 5px;
                background-color: #E8F5E9;
                border-radius: 4px;
                border: 1px solid #2E7D32;
                color: #1B5E20;
                min-height: 28px;
            """)
            
            # 如果正在低头，结束计时
            if self.head_down_start_time is not None:
                import time
                duration = time.time() - self.head_down_start_time
                self.total_head_down_time += duration
                self.head_down_start_time = None
                self.head_down_count_label.setText(f"⬇ 低头: {self.total_head_down_time:.0f}秒")
            
            # 如果正在使用手机/喝水/抽烟，结束计时
            import time
            current_time = time.time()
            
            if self.phone_start_time is not None:
                duration = current_time - self.phone_start_time
                self.total_phone_time += duration
                self.phone_start_time = None
                self.phone_time_label.setText(f"📱 手机: {self.total_phone_time:.0f}秒")
            
            if self.drink_start_time is not None:
                duration = current_time - self.drink_start_time
                self.total_drink_time += duration
                self.drink_start_time = None
                self.drink_time_label.setText(f"🥤 喝水: {self.total_drink_time:.0f}秒")
            
            if self.smoke_start_time is not None:
                duration = current_time - self.smoke_start_time
                self.total_smoke_time += duration
                self.smoke_start_time = None
                self.smoke_time_label.setText(f"🚬 抽烟: {self.total_smoke_time:.0f}秒")
            
            # 更新UI状态
            self.is_monitoring = False
            self.control_buttons["start"].setEnabled(True)
            self.control_buttons["pause"].setEnabled(False)
            self.control_buttons["pause"].setText("暂停监测")
            self.control_buttons["stop"].setEnabled(False)
            self.control_buttons["landmarks"].setEnabled(False)  # 禁用关键点按钮
            self.control_buttons["landmarks"].setChecked(False)  # 重置按钮状态
            
            # 恢复视频控制按钮状态
            self.open_video_button.setEnabled(False)  # 视频仍在运行
            self.pause_video_button.setEnabled(True)
            self.close_video_button.setEnabled(True)  # 允许关闭视频
            
            self.add_log("停止监测（视频预览继续）")
    
    def end_current_session(self):
        """结束当前会话"""
        try:
            if self.db_client and self.current_session_id:
                self.db_client.close_session(self.current_session_id, 0)
                self.add_log(f"结束会话: ID={self.current_session_id}")
                self.current_session_id = None
                
                # 清除 alert_engine 的会话信息
                if self.detection_thread and self.detection_thread.alert_engine:
                    self.detection_thread.alert_engine.clear_session_info()
        except Exception as e:
            self.logger.error(f"结束会话失败: {e}")
            self.add_log(f"警告: 结束会话失败 - {str(e)}")
    
    @pyqtSlot(np.ndarray)
    def on_frame_ready(self, frame: np.ndarray):
        """处理新帧"""
        try:
            # 根据配置决定是否镜像显示
            display_frame = frame
            if self.config.camera.mirror_display:
                # 水平翻转（镜像）
                display_frame = cv2.flip(frame, 1)
            
            # 转换为Qt图像格式
            # frame是BGR格式，需要转换为RGB
            height, width, channel = display_frame.shape
            bytes_per_line = 3 * width
            # 使用rgbSwapped()将BGR转换为RGB
            q_image = QImage(display_frame.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
            
            # 缩放图像以适应显示区域
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(
                self.video_label.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            
            self.video_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            self.logger.error(f"显示视频帧失败: {e}")
    
    @pyqtSlot(dict)
    def on_detection_result(self, result: Dict[str, Any]):
        """处理检测结果"""
        try:
            all_alerts = result.get("all_alerts", [])
            
            # 获取疲劳检测的详细数据
            fatigue_data = result.get("detections", {}).get("fatigue", {})
            if fatigue_data and "metrics" in fatigue_data:
                metrics = fatigue_data["metrics"]
                ear = metrics.get("ear", 0)
                mar = metrics.get("mar", 0)
                head_angle = metrics.get("head_angle", 0)
                face_detected = metrics.get("face_detected", False)
                
                # 更新实时状态显示
                if face_detected:
                    # 更新眼睛状态
                    if ear < self.detection_thread.fatigue_detector.EAR_THRESHOLD:
                        self.eye_status_label.setText("👁 眼睛: 闭眼")
                        self.eye_status_label.setStyleSheet("""
                            font-size: 18px; 
                            font-weight: bold;
                            padding: 5px;
                            background-color: #FFEBEE;
                            border-radius: 4px;
                            border: 1px solid #E53935;
                            color: #B71C1C;
                            min-height: 28px;
                        """)
                    else:
                        self.eye_status_label.setText("👁 眼睛: 正常")
                        self.eye_status_label.setStyleSheet("""
                            font-size: 18px; 
                            font-weight: bold;
                            padding: 5px;
                            background-color: #E8F5E9;
                            border-radius: 4px;
                            border: 1px solid #2E7D32;
                            color: #1B5E20;
                            min-height: 28px;
                        """)
                    
                    # 更新嘴巴状态
                    if mar > self.detection_thread.fatigue_detector.MAR_THRESHOLD:
                        self.mouth_status_label.setText("👄 嘴巴: 打哈欠")
                        self.mouth_status_label.setStyleSheet("""
                            font-size: 18px; 
                            font-weight: bold;
                            padding: 5px;
                            background-color: #FFEBEE;
                            border-radius: 4px;
                            border: 1px solid #E53935;
                            color: #B71C1C;
                            min-height: 28px;
                        """)
                    else:
                        self.mouth_status_label.setText("👄 嘴巴: 正常")
                        self.mouth_status_label.setStyleSheet("""
                            font-size: 18px; 
                            font-weight: bold;
                            padding: 5px;
                            background-color: #E8F5E9;
                            border-radius: 4px;
                            border: 1px solid #2E7D32;
                            color: #1B5E20;
                            min-height: 28px;
                        """)
                    
                    # 更新头部状态并计算低头时间
                    if head_angle > self.detection_thread.fatigue_detector.HEAD_DOWN_THRESHOLD:
                        self.head_status_label.setText("🧑 头部: 低头")
                        self.head_status_label.setStyleSheet("""
                            font-size: 18px; 
                            font-weight: bold;
                            padding: 5px;
                            background-color: #FFEBEE;
                            border-radius: 4px;
                            border: 1px solid #E53935;
                            color: #B71C1C;
                            min-height: 28px;
                        """)
                        
                        # 记录低头开始时间
                        if self.head_down_start_time is None:
                            import time
                            self.head_down_start_time = time.time()
                    else:
                        self.head_status_label.setText("🧑 头部: 正常")
                        self.head_status_label.setStyleSheet("""
                            font-size: 18px; 
                            font-weight: bold;
                            padding: 5px;
                            background-color: #E8F5E9;
                            border-radius: 4px;
                            border: 1px solid #2E7D32;
                            color: #1B5E20;
                            min-height: 28px;
                        """)
                        
                        # 如果之前在低头，计算低头持续时间
                        if self.head_down_start_time is not None:
                            import time
                            duration = time.time() - self.head_down_start_time
                            self.total_head_down_time += duration
                            self.head_down_start_time = None
                            # 更新显示
                            self.head_down_count_label.setText(f"⬇ 低头: {self.total_head_down_time:.0f}秒")
                else:
                    # 未检测到人脸，显示灰色
                    self.eye_status_label.setText("👁 眼睛: 未检测")
                    self.eye_status_label.setStyleSheet("""
                        font-size: 18px; 
                        font-weight: bold;
                        padding: 5px;
                        background-color: #F5F5F5;
                        border-radius: 4px;
                        border: 1px solid #BDBDBD;
                        color: #757575;
                        min-height: 28px;
                    """)
                    self.mouth_status_label.setText("👄 嘴巴: 未检测")
                    self.mouth_status_label.setStyleSheet("""
                        font-size: 18px; 
                        font-weight: bold;
                        padding: 5px;
                        background-color: #F5F5F5;
                        border-radius: 4px;
                        border: 1px solid #BDBDBD;
                        color: #757575;
                        min-height: 28px;
                    """)
                    self.head_status_label.setText("🧑 头部: 未检测")
                    self.head_status_label.setStyleSheet("""
                        font-size: 18px; 
                        font-weight: bold;
                        padding: 5px;
                        background-color: #F5F5F5;
                        border-radius: 4px;
                        border: 1px solid #BDBDBD;
                        color: #757575;
                        min-height: 28px;
                    """)
                    
                    # 如果之前在低头，结束计时
                    if self.head_down_start_time is not None:
                        import time
                        duration = time.time() - self.head_down_start_time
                        self.total_head_down_time += duration
                        self.head_down_start_time = None
                        self.head_down_count_label.setText(f"⬇ 低头: {self.total_head_down_time:.0f}秒")
                
                # 显示实时检测数据（每30帧显示一次，避免日志过多）
                if hasattr(self, '_debug_frame_count'):
                    self._debug_frame_count += 1
                else:
                    self._debug_frame_count = 0
                
                if self._debug_frame_count % 30 == 0 and face_detected:
                    self.add_log(f"实时数据 - EAR: {ear:.3f} (阈值<{self.detection_thread.fatigue_detector.EAR_THRESHOLD if self.detection_thread and self.detection_thread.fatigue_detector else 0.2}), MAR: {mar:.3f} (阈值>{self.detection_thread.fatigue_detector.MAR_THRESHOLD if self.detection_thread and self.detection_thread.fatigue_detector else 0.65})")
            
            # 更新行为检测状态（Phone、Drink、Smoke）
            behavior_data = result.get("detections", {}).get("behavior", {})
            if behavior_data and "objects" in behavior_data:
                objects = behavior_data["objects"]
                
                # 检查是否检测到各类行为（使用新模型的类别名称）
                has_phone = any(obj["class"] == "phone" for obj in objects)
                has_drink = any(obj["class"] == "drink" for obj in objects)
                has_smoke = any(obj["class"] == "smoke" for obj in objects)
                
                import time
                current_time = time.time()
                
                # 更新 Phone 状态和时间
                if has_phone:
                    self.phone_status_label.setText("📱 手机: 检测到")
                    self.phone_status_label.setStyleSheet("""
                        font-size: 18px; 
                        font-weight: bold;
                        padding: 5px;
                        background-color: #FFEBEE;
                        border-radius: 4px;
                        border: 1px solid #E53935;
                        color: #B71C1C;
                        min-height: 28px;
                    """)
                    # 记录开始时间
                    if self.phone_start_time is None:
                        self.phone_start_time = current_time
                else:
                    self.phone_status_label.setText("📱 手机: 正常")
                    self.phone_status_label.setStyleSheet("""
                        font-size: 18px; 
                        font-weight: bold;
                        padding: 5px;
                        background-color: #E8F5E9;
                        border-radius: 4px;
                        border: 1px solid #2E7D32;
                        color: #1B5E20;
                        min-height: 28px;
                    """)
                    # 如果之前在使用手机，计算持续时间
                    if self.phone_start_time is not None:
                        duration = current_time - self.phone_start_time
                        self.total_phone_time += duration
                        self.phone_start_time = None
                        self.phone_time_label.setText(f"📱 手机: {self.total_phone_time:.0f}秒")
                
                # 更新 Drink 状态和时间
                if has_drink:
                    self.drink_status_label.setText("🥤 喝水: 检测到")
                    self.drink_status_label.setStyleSheet("""
                        font-size: 18px; 
                        font-weight: bold;
                        padding: 5px;
                        background-color: #FFF3E0;
                        border-radius: 4px;
                        border: 1px solid #FB8C00;
                        color: #E65100;
                        min-height: 28px;
                    """)
                    # 记录开始时间
                    if self.drink_start_time is None:
                        self.drink_start_time = current_time
                else:
                    self.drink_status_label.setText("🥤 喝水: 正常")
                    self.drink_status_label.setStyleSheet("""
                        font-size: 18px; 
                        font-weight: bold;
                        padding: 5px;
                        background-color: #E8F5E9;
                        border-radius: 4px;
                        border: 1px solid #2E7D32;
                        color: #1B5E20;
                        min-height: 28px;
                    """)
                    # 如果之前在喝水，计算持续时间
                    if self.drink_start_time is not None:
                        duration = current_time - self.drink_start_time
                        self.total_drink_time += duration
                        self.drink_start_time = None
                        self.drink_time_label.setText(f"🥤 喝水: {self.total_drink_time:.0f}秒")
                
                # 更新 Smoke 状态和时间（暂时总是正常）
                if has_smoke:
                    self.smoke_status_label.setText("🚬 抽烟: 检测到")
                    self.smoke_status_label.setStyleSheet("""
                        font-size: 18px; 
                        font-weight: bold;
                        padding: 5px;
                        background-color: #FFEBEE;
                        border-radius: 4px;
                        border: 1px solid #E53935;
                        color: #B71C1C;
                        min-height: 28px;
                    """)
                    # 记录开始时间
                    if self.smoke_start_time is None:
                        self.smoke_start_time = current_time
                else:
                    self.smoke_status_label.setText("🚬 抽烟: 正常")
                    self.smoke_status_label.setStyleSheet("""
                        font-size: 18px; 
                        font-weight: bold;
                        padding: 5px;
                        background-color: #E8F5E9;
                        border-radius: 4px;
                        border: 1px solid #2E7D32;
                        color: #1B5E20;
                        min-height: 28px;
                    """)
                    # 如果之前在抽烟，计算持续时间
                    if self.smoke_start_time is not None:
                        duration = current_time - self.smoke_start_time
                        self.total_smoke_time += duration
                        self.smoke_start_time = None
                        self.smoke_time_label.setText(f"🚬 抽烟: {self.total_smoke_time:.0f}秒")
            else:
                # 未启用行为检测或无检测结果
                import time
                current_time = time.time()
                
                # 结束所有计时
                if self.phone_start_time is not None:
                    duration = current_time - self.phone_start_time
                    self.total_phone_time += duration
                    self.phone_start_time = None
                    self.phone_time_label.setText(f"📱 手机: {self.total_phone_time:.0f}秒")
                
                if self.drink_start_time is not None:
                    duration = current_time - self.drink_start_time
                    self.total_drink_time += duration
                    self.drink_start_time = None
                    self.drink_time_label.setText(f"🥤 喝水: {self.total_drink_time:.0f}秒")
                
                if self.smoke_start_time is not None:
                    duration = current_time - self.smoke_start_time
                    self.total_smoke_time += duration
                    self.smoke_start_time = None
                    self.smoke_time_label.setText(f"🚬 抽烟: {self.total_smoke_time:.0f}秒")
                
                self.phone_status_label.setText("📱 手机: 正常")
                self.phone_status_label.setStyleSheet("""
                    font-size: 18px; 
                    font-weight: bold;
                    padding: 5px;
                    background-color: #E8F5E9;
                    border-radius: 4px;
                    border: 1px solid #2E7D32;
                    color: #1B5E20;
                    min-height: 28px;
                """)
                self.drink_status_label.setText("🥤 喝水: 正常")
                self.drink_status_label.setStyleSheet("""
                    font-size: 18px; 
                    font-weight: bold;
                    padding: 5px;
                    background-color: #E8F5E9;
                    border-radius: 4px;
                    border: 1px solid #2E7D32;
                    color: #1B5E20;
                    min-height: 28px;
                """)
                self.smoke_status_label.setText("🚬 抽烟: 正常")
                self.smoke_status_label.setStyleSheet("""
                    font-size: 18px; 
                    font-weight: bold;
                    padding: 5px;
                    background-color: #E8F5E9;
                    border-radius: 4px;
                    border: 1px solid #2E7D32;
                    color: #1B5E20;
                    min-height: 28px;
                """)
            
            # 统计眨眼和打哈欠次数
            for alert_type in all_alerts:
                if alert_type == "eye_closed":
                    self.total_blink_count += 1
                    self.blink_count_label.setText(f"😴 闭眼次数: {self.total_blink_count}")
                    self.add_log(f"触发闭眼告警 - 当前EAR: {ear:.3f}")
                elif alert_type == "yawning":
                    self.total_yawn_count += 1
                    self.yawn_count_label.setText(f"🥱 打哈欠: {self.total_yawn_count}")
                    self.add_log(f"触发打哈欠告警 - 当前MAR: {mar:.3f}")
                elif alert_type == "head_down":
                    self.total_head_down_count += 1
                    # 低头时间在实时状态更新中计算，这里只记录次数用于日志
                    head_angle = metrics.get("head_angle", 0)
                    self.add_log(f"触发低头告警 - 当前角度: {head_angle:.1f}°")
            
            if all_alerts:
                # 不再显示弹窗，只更新告警计数和日志
                # 更新告警计数
                current_count = int(self.alert_count_label.text().split(": ")[1])
                new_count = current_count + len(all_alerts)
                self.alert_count_label.setText(f"⚠ 告警次数: {new_count}")
                
                # 动态更新告警计数颜色：0时用绿色，大于0时用红色
                if new_count > 0:
                    self.alert_count_label.setStyleSheet("""
                        font-size: 18px;
                        font-weight: bold;
                        padding: 5px;
                        background-color: #F5F5F5;
                        border-radius: 4px;
                        color: #B71C1C;
                        border: 1px solid #E0E0E0;
                    """)
                else:
                    self.alert_count_label.setStyleSheet("""
                        font-size: 18px;
                        font-weight: bold;
                        padding: 5px;
                        background-color: #F5F5F5;
                        border-radius: 4px;
                        color: #2E7D32;
                        border: 1px solid #E0E0E0;
                    """)
                
                self.add_log(f"检测到告警: {', '.join(all_alerts)}", "warning")
            
        except Exception as e:
            self.logger.error(f"处理检测结果失败: {e}")
    
    # 已移除弹窗警告功能，改为在系统状态中实时显示
    # def show_alert_dialog(self, alerts: list, detection_result: Dict[str, Any]):
    #     """显示告警对话框（已禁用）"""
    #     pass
    
    def get_alert_severity(self, alert_type: str) -> str:
        """获取告警类型对应的危险等级"""
        severity_map = {
            "smoking": "high",
            "phone": "medium",
            "cup": "low",
            "eye_closed": "high",
            "yawning": "medium",
            "head_down": "medium"
        }
        return severity_map.get(alert_type, "medium")
    
    @pyqtSlot(str)
    def on_status_changed(self, status: str):
        """处理状态变化"""
        status_map = {
            "starting": "正在启动...",
            "running": "🔵 监测中",
            "paused": "已暂停",
            "stopping": "正在停止...",
            "stopped": "已停止"
        }
        
        display_status = status_map.get(status, status)
        
        # 根据状态设置不同的样式
        if status == "running":
            self.status_label.setText(display_status)
            self.status_label.setStyleSheet("""
                font-weight: bold;
                font-size: 18px;
                padding: 6px 12px;
                background-color: #E3F2FD;
                border-radius: 14px;
                border: 1px solid #1565C0;
                color: #0D47A1;
                min-height: 28px;
            """)
        else:
            self.status_label.setText(f"✅ {display_status}" if status == "stopped" else display_status)
            self.status_label.setStyleSheet("""
                font-weight: bold;
                font-size: 18px;
                padding: 6px 12px;
                background-color: #E8F5E9;
                border-radius: 14px;
                border: 1px solid #2E7D32;
                color: #1B5E20;
                min-height: 28px;
            """)
        
        self.status_bar.showMessage(display_status)
    
    @pyqtSlot(str)
    def on_error_occurred(self, error: str):
        """处理错误"""
        self.add_log(f"错误: {error}")
        self.show_status_message(error, 5000, "error")
    
    @pyqtSlot(float)
    def on_fps_updated(self, fps: float):
        """更新FPS显示"""
        self.fps_label.setText(f"FPS: {fps:.1f}")
    
    @pyqtSlot()
    def on_video_ended(self):
        """视频播放结束"""
        self.add_log("视频播放结束", "warning")
        self.show_status_message("视频播放结束，监测已停止", 5000, "warning")
        self.stop_monitoring()
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 停止监测
            if self.is_monitoring:
                self.stop_monitoring()
            
            # 清理资源
            if self.detection_thread:
                self.detection_thread.cleanup()
            
            if self.db_client:
                self.db_client.close()
            
            self.logger.info("主窗口已关闭")
            event.accept()
            
        except Exception as e:
            self.logger.error(f"关闭窗口时出错: {e}")
            event.accept()


if __name__ == "__main__":
    # 测试主窗口
    import sys
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    app = QApplication(sys.argv)
    
    try:
        window = MainWindow()
        window.show()
        
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"启动主窗口失败: {e}")
        sys.exit(1)
