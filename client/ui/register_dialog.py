"""
人脸注册对话框

提供驾驶员人脸注册功能，包含姓名和工号输入框、摄像头预览、拍摄按钮。

依赖：
- PyQt5
- opencv-python
- FaceRecognizer
"""

import logging
import sys
import os
from typing import Optional
import cv2
import numpy as np
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QGroupBox, QFormLayout,
                            QMessageBox, QApplication)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QPixmap, QImage

# 导入核心模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from client.core.face_recognizer import FaceRecognizer
from client.db.db_client import DBClient


class RegisterDialog(QDialog):
    """
    人脸注册对话框类。
    
    功能：
    - 姓名和工号输入
    - 摄像头实时预览
    - 拍摄并注册人脸
    - 显示注册结果
    """
    
    def __init__(self, db_client: DBClient, use_external_frames=False, parent=None):
        super().__init__(parent)
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 核心组件
        self.db_client = db_client
        self.face_recognizer: Optional[FaceRecognizer] = None
        
        # 视频帧模式
        self.use_external_frames = use_external_frames
        
        # 摄像头相关（仅在不使用外部帧时使用）
        self.camera: Optional[cv2.VideoCapture] = None
        self.camera_timer: Optional[QTimer] = None
        self.current_frame: Optional[np.ndarray] = None
        
        # UI组件
        self.name_input: Optional[QLineEdit] = None
        self.employee_id_input: Optional[QLineEdit] = None
        self.preview_label: Optional[QLabel] = None
        self.capture_button: Optional[QPushButton] = None
        self.cancel_button: Optional[QPushButton] = None
        
        # 初始化UI
        self.init_ui()
        
        # 初始化核心组件
        self.init_components()
        
        # 启动摄像头或定时器
        if not use_external_frames:
            self.start_camera()
        else:
            # 使用外部帧时，只启动定时器用于更新UI
            self.camera_timer = QTimer(self)
            self.camera_timer.timeout.connect(self.update_preview)
            self.camera_timer.start(30)
            self.capture_button.setEnabled(True)
            self.preview_label.setText("等待视频帧...")
        
        self.logger.info("人脸注册对话框初始化完成")
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("驾驶员人脸注册")
        self.setModal(True)
        self.setFixedSize(700, 600)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 信息输入区域
        info_group = self.create_info_group()
        main_layout.addWidget(info_group)
        
        # 摄像头预览区域
        preview_group = self.create_preview_group()
        main_layout.addWidget(preview_group)
        
        # 按钮区域
        button_layout = self.create_button_layout()
        main_layout.addLayout(button_layout)
        
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F7FA;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #CFD8DC;
                border-radius: 8px;
                margin-top: 1ex;
                padding: 12px;
                padding-top: 20px;
                background-color: #FFFFFF;
                color: #1565C0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 4px 8px;
                color: #1565C0;
                font-weight: bold;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #CFD8DC;
                border-radius: 6px;
                font-size: 14px;
                background-color: #FFFFFF;
                color: #212121;
            }
            QLineEdit:focus {
                border: 1px solid #1565C0;
            }
            QPushButton {
                background-color: #1565C0;
                border: none;
                color: white;
                padding: 10px 20px;
                text-align: center;
                font-size: 14px;
                font-weight: 500;
                border-radius: 6px;
                min-width: 100px;
                min-height: 36px;
            }
            QPushButton:hover {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #CFD8DC;
                color: #757575;
            }
            QPushButton#cancel_button {
                background-color: #B71C1C;
            }
            QPushButton#cancel_button:hover {
                background-color: #8B0000;
            }
        """)
    
    def create_info_group(self) -> QGroupBox:
        """创建信息输入组"""
        group = QGroupBox("驾驶员信息")
        layout = QFormLayout(group)
        
        # 姓名输入
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入驾驶员姓名")
        self.name_input.setMaxLength(50)
        layout.addRow("姓名：", self.name_input)
        
        # 工号输入
        self.employee_id_input = QLineEdit()
        self.employee_id_input.setPlaceholderText("请输入驾驶员工号")
        self.employee_id_input.setMaxLength(30)
        layout.addRow("工号：", self.employee_id_input)
        
        return group
    
    def create_preview_group(self) -> QGroupBox:
        """创建摄像头预览组"""
        group = QGroupBox("摄像头预览")
        layout = QVBoxLayout(group)
        
        # 预览标签
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(640, 480)
        self.preview_label.setStyleSheet("""
            QLabel {
                border: 2px solid #CFD8DC;
                background-color: #000000;
                color: #757575;
                text-align: center;
            }
        """)
        self.preview_label.setText("正在启动摄像头...")
        self.preview_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.preview_label, alignment=Qt.AlignCenter)
        
        return group
    
    def create_button_layout(self) -> QHBoxLayout:
        """创建按钮布局"""
        layout = QHBoxLayout()
        layout.addStretch()
        
        # 拍摄注册按钮
        self.capture_button = QPushButton("拍摄并注册")
        self.capture_button.clicked.connect(self.capture_and_register)
        self.capture_button.setEnabled(False)  # 默认禁用，摄像头启动后启用
        layout.addWidget(self.capture_button)
        
        # 取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setObjectName("cancel_button")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)
        
        layout.addStretch()
        
        return layout
    
    def init_components(self):
        """初始化核心组件"""
        try:
            # 初始化人脸识别器
            self.face_recognizer = FaceRecognizer()
            self.logger.info("人脸识别器初始化成功")
            
        except Exception as e:
            self.logger.error(f"初始化人脸识别器失败: {e}")
            QMessageBox.critical(self, "初始化错误", f"人脸识别器初始化失败：\n{str(e)}")
            self.reject()
    
    def start_camera(self):
        """启动摄像头"""
        try:
            # 打开默认摄像头
            self.camera = cv2.VideoCapture(0)
            
            if not self.camera.isOpened():
                raise RuntimeError("无法打开摄像头")
            
            # 设置摄像头分辨率
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # 创建定时器更新预览
            self.camera_timer = QTimer(self)
            self.camera_timer.timeout.connect(self.update_preview)
            self.camera_timer.start(30)  # 约30fps
            
            # 启用拍摄按钮
            self.capture_button.setEnabled(True)
            
            self.logger.info("摄像头启动成功")
            
        except Exception as e:
            self.logger.error(f"启动摄像头失败: {e}")
            self.preview_label.setText(f"摄像头启动失败\n{str(e)}")
            QMessageBox.critical(self, "摄像头错误", f"无法启动摄像头：\n{str(e)}")
    
    @pyqtSlot()
    def update_preview(self):
        """更新摄像头预览"""
        frame = None
        
        # 获取视频帧
        if self.use_external_frames:
            # 使用外部传入的帧
            if self.current_frame is None:
                return
            frame = self.current_frame.copy()
        else:
            # 从摄像头读取帧
            if self.camera is None or not self.camera.isOpened():
                return
            
            ret, frame = self.camera.read()
            if not ret or frame is None:
                self.logger.warning("读取摄像头帧失败")
                return
            
            # 保存当前帧
            self.current_frame = frame.copy()
        
        try:
            # 转换为RGB格式（OpenCV使用BGR）
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 转换为Qt图像格式
            height, width, channel = frame_rgb.shape
            bytes_per_line = 3 * width
            q_image = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            # 显示图像
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(
                self.preview_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            self.logger.error(f"更新预览失败: {e}")
    
    def set_frame(self, frame: np.ndarray):
        """
        设置外部视频帧（用于外部帧模式）
        
        Args:
            frame: BGR格式的numpy数组（从detection_thread的frame_ready信号传来）
        """
        if self.use_external_frames:
            # 直接使用BGR格式的帧
            self.current_frame = frame
    
    @pyqtSlot()
    def capture_and_register(self):
        """拍摄并注册人脸"""
        # 验证输入
        name = self.name_input.text().strip()
        employee_id = self.employee_id_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "输入错误", "请输入驾驶员姓名")
            self.name_input.setFocus()
            return
        
        if not employee_id:
            QMessageBox.warning(self, "输入错误", "请输入驾驶员工号")
            self.employee_id_input.setFocus()
            return
        
        if self.current_frame is None:
            QMessageBox.warning(self, "摄像头错误", "未获取到摄像头画面，请稍后重试")
            return
        
        # 禁用按钮，防止重复点击
        self.capture_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        
        try:
            # 调用人脸识别器注册
            success, message = self.face_recognizer.register_face(
                frame=self.current_frame,
                name=name,
                employee_id=employee_id,
                db_client=self.db_client
            )
            
            if success:
                self.logger.info(f"人脸注册成功: {name} ({employee_id})")
                QMessageBox.information(self, "注册成功", message)
                self.accept()  # 关闭对话框
            else:
                self.logger.warning(f"人脸注册失败: {message}")
                QMessageBox.warning(self, "注册失败", message)
                # 重新启用按钮
                self.capture_button.setEnabled(True)
                self.cancel_button.setEnabled(True)
                
        except Exception as e:
            self.logger.error(f"注册过程出错: {e}")
            QMessageBox.critical(self, "注册错误", f"注册过程出错：\n{str(e)}")
            # 重新启用按钮
            self.capture_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        self.cleanup()
        event.accept()
    
    def cleanup(self):
        """清理资源"""
        try:
            # 停止定时器
            if self.camera_timer:
                self.camera_timer.stop()
                self.camera_timer = None
            
            # 释放摄像头
            if self.camera:
                self.camera.release()
                self.camera = None
            
            # 释放人脸识别器
            if self.face_recognizer:
                self.face_recognizer.close()
                self.face_recognizer = None
            
            self.logger.info("资源清理完成")
            
        except Exception as e:
            self.logger.error(f"清理资源时出错: {e}")


if __name__ == "__main__":
    # 测试人脸注册对话框
    import sys
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    app = QApplication(sys.argv)
    
    try:
        # 创建模拟数据库客户端
        from unittest.mock import Mock
        mock_db_client = Mock(spec=DBClient)
        
        dialog = RegisterDialog(db_client=mock_db_client)
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            print("注册成功")
        else:
            print("注册取消")
        
        sys.exit(0)
        
    except Exception as e:
        print(f"启动对话框失败: {e}")
        sys.exit(1)
