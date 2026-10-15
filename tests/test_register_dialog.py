"""
RegisterDialog 模块单元测试

测试人脸注册对话框功能：
- UI初始化
- 摄像头启动
- 输入验证
- 人脸注册
- 资源清理

依赖：
- pytest
- PyQt5
- unittest.mock
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, call
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtCore import QCoreApplication, Qt
from PyQt5.QtTest import QTest
import numpy as np

# 导入被测试的模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def app():
    """创建 QApplication 实例"""
    if not QCoreApplication.instance():
        app = QApplication([])
    else:
        app = QCoreApplication.instance()
    yield app


@pytest.fixture
def mock_db_client():
    """模拟数据库客户端"""
    return Mock()


@pytest.fixture
def mock_camera():
    """模拟摄像头"""
    camera = Mock()
    camera.isOpened.return_value = True
    camera.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
    return camera


class TestRegisterDialogInit:
    """测试 RegisterDialog 初始化"""
    
    @patch('client.ui.register_dialog.FaceRecognizer')
    @patch('client.ui.register_dialog.cv2.VideoCapture')
    def test_init_success(self, mock_video_capture, mock_face_recognizer, app, mock_db_client, mock_camera):
        """测试成功初始化"""
        mock_video_capture.return_value = mock_camera
        
        from client.ui.register_dialog import RegisterDialog
        
        dialog = RegisterDialog(db_client=mock_db_client)
        
        # 检查基本属性
        assert dialog.db_client == mock_db_client
        assert dialog.face_recognizer is not None
        assert dialog.camera is not None
        assert dialog.camera_timer is not None
        
        # 检查UI组件
        assert dialog.name_input is not None
        assert dialog.employee_id_input is not None
        assert dialog.preview_label is not None
        assert dialog.capture_button is not None
        assert dialog.cancel_button is not None
        
        # 检查窗口属性
        assert dialog.windowTitle() == "驾驶员人脸注册"
        assert dialog.isModal() is True
        
        # 检查按钮状态
        assert dialog.capture_button.isEnabled() is True  # 摄像头启动后应启用
        
        dialog.cleanup()
        dialog.close()
    
    @patch('client.ui.register_dialog.FaceRecognizer')
    @patch('client.ui.register_dialog.cv2.VideoCapture')
    def test_init_ui_components(self, mock_video_capture, mock_face_recognizer, app, mock_db_client, mock_camera):
        """测试UI组件初始化"""
        mock_video_capture.return_value = mock_camera
        
        from client.ui.register_dialog import RegisterDialog
        
        dialog = RegisterDialog(db_client=mock_db_client)
        
        # 检查输入框
        assert dialog.name_input.placeholderText() == "请输入驾驶员姓名"
        assert dialog.name_input.maxLength() == 50
        assert dialog.employee_id_input.placeholderText() == "请输入驾驶员工号"
        assert dialog.employee_id_input.maxLength() == 30
        
        # 检查预览标签
        assert dialog.preview_label.width() == 640
        assert dialog.preview_label.height() == 480
        
        # 检查按钮文本
        assert dialog.capture_button.text() == "拍摄并注册"
        assert dialog.cancel_button.text() == "取消"
        
        dialog.cleanup()
        dialog.close()
    
    @patch('client.ui.register_dialog.FaceRecognizer')
    @patch('client.ui.register_dialog.cv2.VideoCapture')
    @patch('client.ui.register_dialog.QMessageBox')
    def test_init_camera_failure(self, mock_msg_box, mock_video_capture, mock_face_recognizer, app, mock_db_client):
        """测试摄像头启动失败"""
        # 模拟摄像头打开失败
        mock_camera = Mock()
        mock_camera.isOpened.return_value = False
        mock_video_capture.return_value = mock_camera
        
        from client.ui.register_dialog import RegisterDialog
        
        dialog = RegisterDialog(db_client=mock_db_client)
        
        # 检查错误处理
        mock_msg_box.critical.assert_called_once()
        assert dialog.capture_button.isEnabled() is False
        
        dialog.cleanup()
        dialog.close()


class TestRegisterDialogCamera:
    """测试摄像头功能"""
    
    @patch('client.ui.register_dialog.FaceRecognizer')
    @patch('client.ui.register_dialog.cv2.VideoCapture')
    def test_start_camera_success(self, mock_video_capture, mock_face_recognizer, app, mock_db_client, mock_camera):
        """测试成功启动摄像头"""
        mock_video_capture.return_value = mock_camera
        
        from client.ui.register_dialog import RegisterDialog
        
        dialog = RegisterDialog(db_client=mock_db_client)
        
        # 检查摄像头启动
        assert dialog.camera is not None
        assert dialog.camera.isOpened() is True
        assert dialog.camera_timer is not None
        assert dialog.camera_timer.isActive() is True
        assert dialog.capture_button.isEnabled() is True
        
        dialog.cleanup()
        dialog.close()
    
    @patch('client.ui.register_dialog.FaceRecognizer')
    @patch('client.ui.register_dialog.cv2.VideoCapture')
    def test_update_preview(self, mock_video_capture, mock_face_recognizer, app, mock_db_client, mock_camera):
        """测试更新预览"""
        # 创建测试帧
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.read.return_value = (True, test_frame)
        mock_video_capture.return_value = mock_camera
        
        from client.ui.register_dialog import RegisterDialog
        
        dialog = RegisterDialog(db_client=mock_db_client)
        
        # 显示对话框以确保Qt事件处理
        dialog.show()
        app.processEvents()
        
        # 手动调用更新预览
        dialog.update_preview()
        app.processEvents()
        
        # 检查当前帧已保存
        assert dialog.current_frame is not None
        assert dialog.current_frame.shape == (480, 640, 3)
        
        # 检查预览标签已更新
        assert dialog.preview_label.pixmap() is not None
        
        dialog.cleanup()
        dialog.close()
    
    @patch('client.ui.register_dialog.FaceRecognizer')
    @patch('client.ui.register_dialog.cv2.VideoCapture')
    def test_update_preview_read_failure(self, mock_video_capture, mock_face_recognizer, app, mock_db_client, mock_camera):
        """测试读取帧失败"""
        # 模拟读取失败
        mock_camera.read.return_value = (False, None)
        mock_video_capture.return_value = mock_camera
        
        from client.ui.register_dialog import RegisterDialog
        
        dialog = RegisterDialog(db_client=mock_db_client)
        
        # 调用更新预览（不应崩溃）
        dialog.update_preview()
        
        # 当前帧应为None
        assert dialog.current_frame is None
        
        dialog.cleanup()
        dialog.close()


class TestRegisterDialogValidation:
    """测试输入验证"""
    
    @patch('client.ui.register_dialog.FaceRecognizer')
    @patch('client.ui.register_dialog.cv2.VideoCapture')
    @patch('client.ui.register_dialog.QMessageBox')
    def test_capture_empty_name(self, mock_msg_box, mock_video_capture, mock_face_recognizer, app, mock_db_client, mock_camera):
        """测试姓名为空"""
        mock_video_capture.return_value = mock_camera
        
        from client.ui.register_dialog import RegisterDialog
        
        dialog = RegisterDialog(db_client=mock_db_client)
        dialog.current_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 设置空姓名
        dialog.name_input.setText("")
        dialog.employee_id_input.setText("D001")
        
        # 尝试注册
        dialog.capture_and_register()
        
        # 应显示警告
        mock_msg_box.warning.assert_called_once()
        assert "姓名" in str(mock_msg_box.warning.call_args)
        
        dialog.cleanup()
        dialog.close()
    
    @patch('client.ui.register_dialog.FaceRecognizer')
    @patch('client.ui.register_dialog.cv2.VideoCapture')
    @patch('client.ui.register_dialog.QMessageBox')
    def test_capture_empty_employee_id(self, mock_msg_box, mock_video_capture, mock_face_recognizer, app, mock_db_client, mock_camera):
        """测试工号为空"""
        mock_video_capture.return_value = mock_camera
        
        from client.ui.register_dialog import RegisterDialog
        
        dialog = RegisterDialog(db_client=mock_db_client)
        dialog.current_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 设置空工号
        dialog.name_input.setText("张三")
        dialog.employee_id_input.setText("")
        
        # 尝试注册
        dialog.capture_and_register()
        
        # 应显示警告
        mock_msg_box.warning.assert_called_once()
        assert "工号" in str(mock_msg_box.warning.call_args)
        
        dialog.cleanup()
        dialog.close()
    
    @patch('client.ui.register_dialog.FaceRecognizer')
    @patch('client.ui.register_dialog.cv2.VideoCapture')
    @patch('client.ui.register_dialog.QMessageBox')
    def test_capture_no_frame(self, mock_msg_box, mock_video_capture, mock_face_recognizer, app, mock_db_client, mock_camera):
        """测试未获取到帧"""
        mock_video_capture.return_value = mock_camera
        
        from client.ui.register_dialog import RegisterDialog
        
        dialog = RegisterDialog(db_client=mock_db_client)
        dialog.current_frame = None  # 未获取到帧
        
        # 设置有效输入
        dialog.name_input.setText("张三")
        dialog.employee_id_input.setText("D001")
        
        # 尝试注册
        dialog.capture_and_register()
        
        # 应显示警告
        mock_msg_box.warning.assert_called_once()
        assert "摄像头" in str(mock_msg_box.warning.call_args)
        
        dialog.cleanup()
        dialog.close()


class TestRegisterDialogRegistration:
    """测试人脸注册"""
    
    @patch('client.ui.register_dialog.FaceRecognizer')
    @patch('client.ui.register_dialog.cv2.VideoCapture')
    @patch('client.ui.register_dialog.QMessageBox')
    def test_register_success(self, mock_msg_box, mock_video_capture, mock_face_recognizer_class, app, mock_db_client, mock_camera):
        """测试注册成功"""
        mock_video_capture.return_value = mock_camera
        
        # 模拟人脸识别器
        mock_face_recognizer = Mock()
        mock_face_recognizer.register_face.return_value = (True, "注册成功")
        mock_face_recognizer_class.return_value = mock_face_recognizer
        
        from client.ui.register_dialog import RegisterDialog
        
        dialog = RegisterDialog(db_client=mock_db_client)
        dialog.current_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 设置有效输入
        dialog.name_input.setText("张三")
        dialog.employee_id_input.setText("D001")
        
        # 执行注册
        dialog.capture_and_register()
        
        # 检查调用
        mock_face_recognizer.register_face.assert_called_once()
        call_args = mock_face_recognizer.register_face.call_args
        assert call_args[1]['name'] == "张三"
        assert call_args[1]['employee_id'] == "D001"
        assert call_args[1]['db_client'] == mock_db_client
        
        # 应显示成功消息
        mock_msg_box.information.assert_called_once()
        
        dialog.cleanup()
        dialog.close()
    
    @patch('client.ui.register_dialog.FaceRecognizer')
    @patch('client.ui.register_dialog.cv2.VideoCapture')
    @patch('client.ui.register_dialog.QMessageBox')
    def test_register_no_face_detected(self, mock_msg_box, mock_video_capture, mock_face_recognizer_class, app, mock_db_client, mock_camera):
        """测试未检测到人脸"""
        mock_video_capture.return_value = mock_camera
        
        # 模拟人脸识别器返回失败
        mock_face_recognizer = Mock()
        mock_face_recognizer.register_face.return_value = (False, "未检测到人脸，请确保人脸清晰可见")
        mock_face_recognizer_class.return_value = mock_face_recognizer
        
        from client.ui.register_dialog import RegisterDialog
        
        dialog = RegisterDialog(db_client=mock_db_client)
        dialog.current_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 设置有效输入
        dialog.name_input.setText("张三")
        dialog.employee_id_input.setText("D001")
        
        # 执行注册
        dialog.capture_and_register()
        
        # 应显示警告消息
        mock_msg_box.warning.assert_called_once()
        assert "未检测到人脸" in str(mock_msg_box.warning.call_args)
        
        # 按钮应重新启用
        assert dialog.capture_button.isEnabled() is True
        assert dialog.cancel_button.isEnabled() is True
        
        dialog.cleanup()
        dialog.close()
    
    @patch('client.ui.register_dialog.FaceRecognizer')
    @patch('client.ui.register_dialog.cv2.VideoCapture')
    @patch('client.ui.register_dialog.QMessageBox')
    def test_register_duplicate_employee_id(self, mock_msg_box, mock_video_capture, mock_face_recognizer_class, app, mock_db_client, mock_camera):
        """测试工号重复"""
        mock_video_capture.return_value = mock_camera
        
        # 模拟人脸识别器返回工号重复错误
        mock_face_recognizer = Mock()
        mock_face_recognizer.register_face.return_value = (False, "工号已存在")
        mock_face_recognizer_class.return_value = mock_face_recognizer
        
        from client.ui.register_dialog import RegisterDialog
        
        dialog = RegisterDialog(db_client=mock_db_client)
        dialog.current_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 设置有效输入
        dialog.name_input.setText("张三")
        dialog.employee_id_input.setText("D001")
        
        # 执行注册
        dialog.capture_and_register()
        
        # 应显示警告消息
        mock_msg_box.warning.assert_called_once()
        assert "工号已存在" in str(mock_msg_box.warning.call_args)
        
        # 按钮应重新启用
        assert dialog.capture_button.isEnabled() is True
        assert dialog.cancel_button.isEnabled() is True
        
        dialog.cleanup()
        dialog.close()


class TestRegisterDialogCleanup:
    """测试资源清理"""
    
    @patch('client.ui.register_dialog.FaceRecognizer')
    @patch('client.ui.register_dialog.cv2.VideoCapture')
    def test_cleanup(self, mock_video_capture, mock_face_recognizer_class, app, mock_db_client, mock_camera):
        """测试资源清理"""
        mock_video_capture.return_value = mock_camera
        
        mock_face_recognizer = Mock()
        mock_face_recognizer_class.return_value = mock_face_recognizer
        
        from client.ui.register_dialog import RegisterDialog
        
        dialog = RegisterDialog(db_client=mock_db_client)
        
        # 执行清理
        dialog.cleanup()
        
        # 检查资源释放
        assert dialog.camera_timer is None
        assert dialog.camera is None
        assert dialog.face_recognizer is None
        
        # 检查摄像头释放调用
        mock_camera.release.assert_called_once()
        
        # 检查人脸识别器关闭调用
        mock_face_recognizer.close.assert_called_once()
        
        dialog.close()
    
    @patch('client.ui.register_dialog.FaceRecognizer')
    @patch('client.ui.register_dialog.cv2.VideoCapture')
    def test_close_event(self, mock_video_capture, mock_face_recognizer_class, app, mock_db_client, mock_camera):
        """测试窗口关闭事件"""
        mock_video_capture.return_value = mock_camera
        
        mock_face_recognizer = Mock()
        mock_face_recognizer_class.return_value = mock_face_recognizer
        
        from client.ui.register_dialog import RegisterDialog
        
        dialog = RegisterDialog(db_client=mock_db_client)
        
        # 关闭对话框
        dialog.close()
        
        # 资源应已清理
        mock_camera.release.assert_called_once()
        mock_face_recognizer.close.assert_called_once()


class TestRegisterDialogIntegration:
    """测试集成场景"""
    
    @patch('client.ui.register_dialog.FaceRecognizer')
    @patch('client.ui.register_dialog.cv2.VideoCapture')
    def test_cancel_button(self, mock_video_capture, mock_face_recognizer, app, mock_db_client, mock_camera):
        """测试取消按钮"""
        mock_video_capture.return_value = mock_camera
        
        from client.ui.register_dialog import RegisterDialog
        
        dialog = RegisterDialog(db_client=mock_db_client)
        
        # 点击取消按钮
        dialog.cancel_button.click()
        
        # 对话框应被拒绝
        assert dialog.result() == QDialog.Rejected
        
        dialog.cleanup()
        dialog.close()
    
    @patch('client.ui.register_dialog.FaceRecognizer')
    @patch('client.ui.register_dialog.cv2.VideoCapture')
    def test_input_max_length(self, mock_video_capture, mock_face_recognizer, app, mock_db_client, mock_camera):
        """测试输入框最大长度限制"""
        mock_video_capture.return_value = mock_camera
        
        from client.ui.register_dialog import RegisterDialog
        
        dialog = RegisterDialog(db_client=mock_db_client)
        
        # 测试姓名最大长度
        long_name = "A" * 100
        dialog.name_input.setText(long_name)
        assert len(dialog.name_input.text()) == 50  # 应被截断为50
        
        # 测试工号最大长度
        long_id = "B" * 100
        dialog.employee_id_input.setText(long_id)
        assert len(dialog.employee_id_input.text()) == 30  # 应被截断为30
        
        dialog.cleanup()
        dialog.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
