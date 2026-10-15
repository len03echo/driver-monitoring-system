"""
告警弹窗

显示告警类型、危险等级、截图预览，提供确认按钮，支持自动关闭。

依赖：
- PyQt5
- opencv-python
"""

import logging
import os
from typing import Optional
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QGroupBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QFont


class AlertDialog(QDialog):
    """
    告警弹窗类。
    
    功能：
    - 显示告警类型和危险等级
    - 显示截图预览
    - 提供确认按钮
    - 支持自动关闭
    """
    
    # 告警类型中文映射
    ALERT_TYPE_MAP = {
        "phone": "使用手机",
        "cup": "持杯",
        "smoking": "抽烟",
        "eye_closed": "闭眼",
        "yawning": "哈欠",
        "head_down": "低头",
        "unknown": "未知"
    }
    
    # 危险等级中文映射
    SEVERITY_MAP = {
        "low": "低",
        "medium": "中",
        "high": "高"
    }
    
    # 危险等级颜色映射 - 使用新配色方案
    SEVERITY_COLOR_MAP = {
        "low": "#E65100",      # 警告状态
        "medium": "#E65100",   # 警告状态
        "high": "#B71C1C"      # 危险/报警状态
    }
    
    def __init__(self, alert_type: str, severity: str, 
                 snapshot_path: Optional[str] = None, 
                 auto_close_seconds: int = 5,
                 parent=None):
        """
        初始化告警弹窗。
        
        Args:
            alert_type: 告警类型（phone/cup/smoking/eye_closed/yawning/head_down）
            severity: 危险等级（low/medium/high）
            snapshot_path: 截图路径（可选）
            auto_close_seconds: 自动关闭秒数（0表示不自动关闭）
            parent: 父窗口
        """
        super().__init__(parent)
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 保存参数
        self.alert_type = alert_type
        self.severity = severity
        self.snapshot_path = snapshot_path
        self.auto_close_seconds = auto_close_seconds
        
        # UI组件
        self.confirm_button: Optional[QPushButton] = None
        self.snapshot_label: Optional[QLabel] = None
        
        # 初始化UI
        self.init_ui()
        
        # 设置自动关闭定时器
        if auto_close_seconds > 0:
            QTimer.singleShot(auto_close_seconds * 1000, self.accept)
        
        self.logger.info(f"告警弹窗初始化完成: {alert_type}, {severity}")
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("驾驶行为告警")
        self.setModal(True)
        self.setFixedSize(500, 600)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 告警信息区域
        info_group = self.create_info_group()
        main_layout.addWidget(info_group)
        
        # 截图预览区域
        if self.snapshot_path:
            snapshot_group = self.create_snapshot_group()
            main_layout.addWidget(snapshot_group)
        
        # 按钮区域
        button_layout = self.create_button_layout()
        main_layout.addLayout(button_layout)
        
        # 设置样式
        severity_color = self.SEVERITY_COLOR_MAP.get(self.severity, "#E65100")
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #F5F7FA;
            }}
            QGroupBox {{
                font-weight: bold;
                font-size: 13px;
                border: 2px solid {severity_color};
                border-radius: 8px;
                margin-top: 1ex;
                padding: 12px;
                padding-top: 20px;
                background-color: #FFFFFF;
                color: {severity_color};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 4px 8px;
                color: {severity_color};
                font-weight: bold;
            }}
            QLabel {{
                color: #212121;
            }}
            QPushButton {{
                background-color: {severity_color};
                border: none;
                color: white;
                padding: 10px 20px;
                text-align: center;
                font-size: 14px;
                font-weight: 500;
                border-radius: 6px;
                min-width: 100px;
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: {severity_color};
                filter: brightness(0.9);
            }}
        """)
    
    def create_info_group(self) -> QGroupBox:
        """创建告警信息组"""
        group = QGroupBox("告警信息")
        layout = QVBoxLayout(group)
        
        # 告警类型
        alert_type_cn = self.ALERT_TYPE_MAP.get(self.alert_type, self.alert_type)
        type_label = QLabel(f"告警类型：{alert_type_cn}")
        type_label.setFont(QFont("Arial", 16, QFont.Bold))
        type_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(type_label)
        
        # 危险等级
        severity_cn = self.SEVERITY_MAP.get(self.severity, self.severity)
        severity_color = self.SEVERITY_COLOR_MAP.get(self.severity, "#FFA500")
        severity_label = QLabel(f"危险等级：{severity_cn}")
        severity_label.setFont(QFont("Arial", 14, QFont.Bold))
        severity_label.setAlignment(Qt.AlignCenter)
        severity_label.setStyleSheet(f"color: {severity_color};")
        layout.addWidget(severity_label)
        
        # 提示信息
        warning_label = QLabel("⚠️ 请注意驾驶安全！")
        warning_label.setFont(QFont("Arial", 12))
        warning_label.setAlignment(Qt.AlignCenter)
        warning_label.setStyleSheet("color: #212121; margin-top: 10px;")
        layout.addWidget(warning_label)
        
        # 自动关闭提示
        if self.auto_close_seconds > 0:
            auto_close_label = QLabel(f"（{self.auto_close_seconds}秒后自动关闭）")
            auto_close_label.setFont(QFont("Arial", 10))
            auto_close_label.setAlignment(Qt.AlignCenter)
            auto_close_label.setStyleSheet("color: #757575;")
            layout.addWidget(auto_close_label)
        
        return group
    
    def create_snapshot_group(self) -> QGroupBox:
        """创建截图预览组"""
        group = QGroupBox("截图预览")
        layout = QVBoxLayout(group)
        
        # 截图标签
        self.snapshot_label = QLabel()
        self.snapshot_label.setFixedSize(460, 345)  # 4:3 比例
        self.snapshot_label.setStyleSheet("""
            QLabel {
                border: 2px solid #CFD8DC;
                background-color: #000000;
                color: #757575;
            }
        """)
        self.snapshot_label.setAlignment(Qt.AlignCenter)
        
        # 加载截图
        if self.snapshot_path and os.path.exists(self.snapshot_path):
            pixmap = QPixmap(self.snapshot_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    self.snapshot_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.snapshot_label.setPixmap(scaled_pixmap)
            else:
                self.snapshot_label.setText("截图加载失败")
        else:
            self.snapshot_label.setText("截图不可用")
        
        layout.addWidget(self.snapshot_label, alignment=Qt.AlignCenter)
        
        return group
    
    def create_button_layout(self) -> QHBoxLayout:
        """创建按钮布局"""
        layout = QHBoxLayout()
        layout.addStretch()
        
        # 确认按钮
        self.confirm_button = QPushButton("确认")
        self.confirm_button.clicked.connect(self.accept)
        layout.addWidget(self.confirm_button)
        
        layout.addStretch()
        
        return layout
    
    def get_alert_type_display(self) -> str:
        """获取告警类型显示文本"""
        return self.ALERT_TYPE_MAP.get(self.alert_type, self.alert_type)
    
    def get_severity_display(self) -> str:
        """获取危险等级显示文本"""
        return self.SEVERITY_MAP.get(self.severity, self.severity)


if __name__ == "__main__":
    # 测试告警弹窗
    import sys
    from PyQt5.QtWidgets import QApplication
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    app = QApplication(sys.argv)
    
    try:
        # 测试不同类型的告警
        dialog1 = AlertDialog(
            alert_type="phone",
            severity="medium",
            snapshot_path=None,
            auto_close_seconds=0
        )
        result = dialog1.exec_()
        
        print(f"对话框结果: {'接受' if result == QDialog.Accepted else '拒绝'}")
        
        sys.exit(0)
        
    except Exception as e:
        print(f"启动对话框失败: {e}")
        sys.exit(1)
