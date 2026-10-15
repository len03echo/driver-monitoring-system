"""
人脸认证对话框

实时显示摄像头画面，进行人脸识别认证。

依赖：
- PyQt5
- OpenCV
- numpy
"""

import logging
import cv2
import numpy as np
from typing import Optional, Dict
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QFont


class FaceAuthDialog(QDialog):
    """
    人脸认证对话框
    
    实时显示摄像头画面，自动进行人脸识别认证
    """
    
    # 认证成功信号
    auth_success = pyqtSignal(dict)  # 传递驾驶员信息
    
    def __init__(self, face_recognizer, db_client, use_external_frames=False, parent=None):
        """
        初始化人脸认证对话框
        
        Args:
            face_recognizer: 人脸识别器实例
            db_client: 数据库客户端实例
            use_external_frames: 是否使用外部视频帧（True时不打开摄像头）
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        
        # 保存参数
        self.face_recognizer = face_recognizer
        self.db_client = db_client
        self.use_external_frames = use_external_frames
        
        # 摄像头（仅在不使用外部帧时使用）
        self.camera = None
        
        # 当前帧（用于外部帧模式）
        self.current_frame = None
        
        # 认证状态
        self.is_authenticated = False
        self.driver_info = None
        self.auth_attempts = 0
        self.max_attempts = 30  # 最多尝试30次（约3秒）
        
        # 定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        
        # 初始化UI
        self.init_ui()
        
        # 启动摄像头或定时器
        if not use_external_frames:
            self.start_camera()
        else:
            # 使用外部帧时，只启动定时器
            self.timer.start(100)
            self.status_label.setText("等待视频帧...")
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("人脸认证")
        self.setModal(True)
        self.setFixedSize(700, 600)
        
        # 主布局
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("人脸身份认证")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 视频显示区域
        self.video_label = QLabel()
        self.video_label.setFixedSize(640, 480)
        self.video_label.setStyleSheet("""
            QLabel {
                border: 3px solid #4CAF50;
                background-color: #000000;
                border-radius: 10px;
            }
        """)
        self.video_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.video_label, alignment=Qt.AlignCenter)
        
        # 状态标签
        self.status_label = QLabel("正在初始化...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 13px; padding: 5px;")
        layout.addWidget(self.status_label)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 确认按钮（认证成功后显示）
        self.ok_button = QPushButton("确认并关闭")
        self.ok_button.setObjectName("ok_button")
        self.ok_button.clicked.connect(self.on_ok_clicked)
        self.ok_button.setVisible(False)  # 默认隐藏
        button_layout.addWidget(self.ok_button)
        
        # 继续认证按钮（认证成功后显示）
        self.continue_button = QPushButton("继续认证其他人")
        self.continue_button.setObjectName("continue_button")
        self.continue_button.clicked.connect(self.continue_auth)
        self.continue_button.setVisible(False)  # 默认隐藏
        button_layout.addWidget(self.continue_button)
        
        # 重试按钮（认证失败后显示）
        self.retry_button = QPushButton("重试")
        self.retry_button.clicked.connect(self.retry_auth)
        self.retry_button.setEnabled(False)
        self.retry_button.setVisible(False)  # 默认隐藏
        button_layout.addWidget(self.retry_button)
        
        # 取消按钮（始终显示）
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 10px 24px;
                font-size: 14px;
                border-radius: 5px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QPushButton#ok_button {
                background-color: #2196F3;
            }
            QPushButton#ok_button:hover {
                background-color: #0b7dda;
            }
            QPushButton#continue_button {
                background-color: #FF9800;
            }
            QPushButton#continue_button:hover {
                background-color: #e68900;
            }
        """)
    
    def start_camera(self):
        """启动摄像头"""
        try:
            self.camera = cv2.VideoCapture(self.camera_index)
            
            if not self.camera.isOpened():
                raise RuntimeError(f"无法打开摄像头 {self.camera_index}")
            
            # 设置摄像头参数
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            # 启动定时器（每100ms更新一次）
            self.timer.start(100)
            
            self.status_label.setText("摄像头已就绪，开始识别...")
            self.logger.info("摄像头启动成功")
            
        except Exception as e:
            self.logger.error(f"启动摄像头失败: {e}")
            self.status_label.setText(f"错误: {str(e)}")
            QMessageBox.critical(self, "错误", f"无法启动摄像头：\n{str(e)}")
            self.reject()
    
    def update_frame(self):
        """更新视频帧并进行人脸识别"""
        frame = None
        
        # 获取视频帧
        if self.use_external_frames:
            # 使用外部传入的帧
            if self.current_frame is None:
                return
            frame = self.current_frame.copy()
        else:
            # 从摄像头读取帧
            if not self.camera or not self.camera.isOpened():
                return
            
            ret, frame = self.camera.read()
            if not ret or frame is None:
                self.status_label.setText("读取摄像头失败")
                return
        
        try:
            # 转换为RGB（用于显示）
            display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 如果还未认证成功，进行人脸识别
            if not self.is_authenticated and self.auth_attempts < self.max_attempts:
                self.auth_attempts += 1
                
                # 进行人脸认证
                success, driver_info, message = self.face_recognizer.authenticate_face(
                    frame, self.db_client
                )
                
                if success:
                    # 认证成功
                    self.is_authenticated = True
                    self.driver_info = driver_info
                    
                    self.status_label.setText(f"✓ 认证成功！欢迎 {driver_info['name']}")
                    self.status_label.setStyleSheet("color: green; font-size: 20px; font-weight: bold; padding: 10px;")
                    
                    self.logger.info(f"人脸认证成功: {driver_info['name']} ({driver_info['employee_id']})")
                    
                    # 停止定时器
                    self.timer.stop()
                    
                    # 显示确认和继续按钮，隐藏取消按钮
                    self.ok_button.setVisible(True)
                    self.continue_button.setVisible(True)
                    self.cancel_button.setVisible(False)
                    
                else:
                    # 认证失败，继续尝试
                    self.status_label.setText(f"识别中... ({self.auth_attempts}/{self.max_attempts})")
            
            elif self.auth_attempts >= self.max_attempts and not self.is_authenticated:
                # 达到最大尝试次数仍未成功
                self.timer.stop()
                self.status_label.setText("✗ 认证失败，未找到匹配的驾驶员，请重试或注册新用户")
                self.status_label.setStyleSheet("color: red; font-size: 20px; font-weight: bold; padding: 10px;")
                self.retry_button.setEnabled(True)
                self.retry_button.setVisible(True)
            
            # 显示帧
            self.display_frame(display_frame)
            
        except Exception as e:
            self.logger.error(f"更新帧时出错: {e}")
            self.status_label.setText(f"错误: {str(e)}")
    
    def set_frame(self, frame: np.ndarray):
        """
        设置外部视频帧（用于外部帧模式）
        
        Args:
            frame: BGR格式的numpy数组（从detection_thread的frame_ready信号传来）
        """
        if self.use_external_frames:
            # 直接使用BGR格式的帧
            self.current_frame = frame
    
    def display_frame(self, frame: np.ndarray):
        """
        显示视频帧
        
        Args:
            frame: RGB格式的numpy数组
        """
        try:
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            # 缩放以适应显示区域
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(
                self.video_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            self.video_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            self.logger.error(f"显示帧失败: {e}")
    
    def retry_auth(self):
        """重试认证"""
        self.auth_attempts = 0
        self.is_authenticated = False
        self.driver_info = None
        self.status_label.setText("正在重新识别...")
        self.status_label.setStyleSheet("font-size: 13px; padding: 5px;")
        
        # 隐藏所有操作按钮，只显示取消按钮
        self.retry_button.setEnabled(False)
        self.retry_button.setVisible(False)
        self.ok_button.setVisible(False)
        self.continue_button.setVisible(False)
        self.cancel_button.setVisible(True)
        
        # 重新启动定时器
        if not self.timer.isActive():
            self.timer.start(100)
        
        self.logger.info("重试人脸认证")
    
    def continue_auth(self):
        """继续认证（保持对话框打开，重新开始识别）"""
        self.logger.info("继续人脸认证")
        
        # 重置状态但保留已认证的驾驶员信息
        authenticated_driver = self.driver_info
        
        # 重置认证状态
        self.auth_attempts = 0
        self.is_authenticated = False
        self.driver_info = None
        self.status_label.setText("正在识别...")
        self.status_label.setStyleSheet("font-size: 13px; padding: 5px;")
        
        # 隐藏操作按钮，显示取消按钮
        self.ok_button.setVisible(False)
        self.continue_button.setVisible(False)
        self.cancel_button.setVisible(True)
        
        # 重新启动定时器
        if not self.timer.isActive():
            self.timer.start(100)
        
        # 提示上次认证的驾驶员
        if authenticated_driver:
            self.add_log(f"上次认证: {authenticated_driver['name']} ({authenticated_driver['employee_id']})")
    
    def on_ok_clicked(self):
        """点击确认按钮"""
        if self.is_authenticated and self.driver_info:
            self.on_auth_success()
        else:
            self.reject()
    
    def add_log(self, message: str):
        """添加日志（如果需要的话）"""
        self.logger.info(message)
    
    def on_auth_success(self):
        """认证成功处理"""
        # 发送信号
        self.auth_success.emit(self.driver_info)
        
        # 关闭对话框
        self.accept()
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        self.cleanup()
        event.accept()
    
    def cleanup(self):
        """清理资源"""
        try:
            # 停止定时器
            if self.timer.isActive():
                self.timer.stop()
            
            # 释放摄像头
            if self.camera and self.camera.isOpened():
                self.camera.release()
                self.camera = None
            
            self.logger.info("人脸认证对话框资源已清理")
            
        except Exception as e:
            self.logger.error(f"清理资源时出错: {e}")
    
    def reject(self):
        """取消对话框"""
        self.cleanup()
        super().reject()
    
    def accept(self):
        """接受对话框"""
        self.cleanup()
        super().accept()


if __name__ == "__main__":
    # 测试人脸认证对话框
    import sys
    from PyQt5.QtWidgets import QApplication
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    app = QApplication(sys.argv)
    
    try:
        # 这里需要实际的 face_recognizer 和 db_client 实例
        # dialog = FaceAuthDialog(face_recognizer, db_client)
        # result = dialog.exec_()
        
        print("人脸认证对话框测试完成")
        
    except Exception as e:
        print(f"测试失败: {e}")
        sys.exit(1)
