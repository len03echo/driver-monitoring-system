"""
MainWindow 模块单元测试

测试主窗口功能：
- UI初始化
- 组件创建
- 视频源选择
- 监测控制
- 信号处理
- 状态管理

依赖：
- pytest
- PyQt5
- unittest.mock
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtTest import QTest, QSignalSpy
from PyQt5.QtCore import Qt
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
def mock_config():
    """模拟配置（使用 Mock 对象模拟 ClientConfig 属性访问）"""
    config = MagicMock()
    config.database.host = "localhost"
    config.database.port = 3306
    config.database.user = "test_user"
    config.database.password = "test_pass"
    config.database.name = "test_db"
    config.alert.snapshot_dir = "test_snapshots"
    config.alert.sound_path = "test_alert.wav"
    config.alert.cooldown_seconds = 30
    config.detection.behavior_threshold = 10
    config.detection.ear_threshold = 0.25
    config.detection.mar_threshold = 0.6
    config.model.yolo_path = "test_model.pt"
    config.model.insightface_name = "buffalo_l"
    return config


class TestMainWindowInit:
    """测试 MainWindow 初始化"""
    
    @patch('client.ui.main_window.load_config')
    @patch('client.ui.main_window.DBClient')
    @patch('client.ui.main_window.DetectionThread')
    def test_init_success(self, mock_detection_thread, mock_db_client, mock_load_config, app, mock_config):
        """测试成功初始化"""
        mock_load_config.return_value = mock_config
        
        from client.ui.main_window import MainWindow
        
        window = MainWindow()
        
        # 检查基本属性
        assert window.config == mock_config
        assert window.is_authenticated is False
        assert window.is_monitoring is False
        assert window.current_driver_id is None
        assert window.current_session_id is None
        
        # 检查UI组件
        assert window.video_label is not None
        assert window.status_label is not None
        assert window.log_text is not None
        assert len(window.control_buttons) >= 3  # start, pause, stop (landmarks也在其中)
        
        # 检查核心组件初始化
        mock_db_client.assert_called_once()
        mock_detection_thread.assert_called_once()
        
        window.close()
    
    @patch('client.ui.main_window.load_config')
    def test_init_ui_components(self, mock_load_config, app, mock_config):
        """测试UI组件初始化"""
        mock_load_config.return_value = mock_config
        
        with patch('client.ui.main_window.DBClient'), \
             patch('client.ui.main_window.DetectionThread'):
            
            from client.ui.main_window import MainWindow
            window = MainWindow()
            
            # 检查窗口属性
            assert "驾驶员监测系统" in window.windowTitle()
            # 窗口尺寸在显示前可能不精确，检查最小尺寸
            assert window.minimumWidth() >= 1200
            assert window.minimumHeight() >= 700
            
            # 检查控制按钮
            assert "start" in window.control_buttons
            assert "pause" in window.control_buttons
            assert "stop" in window.control_buttons
            
            # 检查初始按钮状态
            assert window.control_buttons["start"].isEnabled() is False  # 需要先认证
            assert window.control_buttons["pause"].isEnabled() is False
            assert window.control_buttons["stop"].isEnabled() is False
            
            window.close()


class TestMainWindowVideoSource:
    """测试视频源选择"""
    
    @patch('client.ui.main_window.load_config')
    def test_source_type_changed_camera(self, mock_load_config, app, mock_config):
        """测试切换到摄像头"""
        mock_load_config.return_value = mock_config
        
        with patch('client.ui.main_window.DBClient'), \
             patch('client.ui.main_window.DetectionThread'):
            
            from client.ui.main_window import MainWindow
            window = MainWindow()
            
            window.show()
            app.processEvents()
            
            # 先切到视频文件模式
            window.select_source_type("file")
            app.processEvents()
            
            # 再切回摄像头模式
            window.select_source_type("camera")
            app.processEvents()
            
            assert window.camera_combo.isVisible() is True
            assert window.file_button.isVisible() is False
            assert window.file_path_label.isVisible() is False
            
            window.close()
    
    @patch('client.ui.main_window.load_config')
    def test_source_type_changed_video_file(self, mock_load_config, app, mock_config):
        """测试切换到视频文件"""
        mock_load_config.return_value = mock_config
        
        with patch('client.ui.main_window.DBClient'), \
             patch('client.ui.main_window.DetectionThread'):
            
            from client.ui.main_window import MainWindow
            window = MainWindow()
            
            window.show()
            app.processEvents()
            
            # 实际方法名是 select_source_type，参数是 "file"
            window.select_source_type("file")
            app.processEvents()
            
            assert window.camera_combo.isVisible() is False
            assert window.file_button.isVisible() is True
            assert window.file_path_label.isVisible() is True
            
            window.close()
    
    @patch('client.ui.main_window.load_config')
    @patch('client.ui.main_window.CameraSource')
    def test_create_video_source_camera(self, mock_camera, mock_load_config, app, mock_config):
        """测试创建摄像头视频源"""
        mock_load_config.return_value = mock_config
        
        with patch('client.ui.main_window.DBClient'), \
             patch('client.ui.main_window.DetectionThread'):
            
            from client.ui.main_window import MainWindow
            window = MainWindow()
            
            # 实际代码用 camera_source_button（checkable）判断摄像头模式
            window.camera_source_button.setChecked(True)
            window.camera_combo.setCurrentIndex(1)
            
            video_source = window.create_video_source()
            
            mock_camera.assert_called_once_with(device_index=1)
            assert video_source is not None
            
            window.close()
    
    @patch('client.ui.main_window.load_config')
    @patch('client.ui.main_window.VideoFileSource')
    def test_create_video_source_file(self, mock_video_file, mock_load_config, app, mock_config):
        """测试创建视频文件源"""
        mock_load_config.return_value = mock_config
        
        with patch('client.ui.main_window.DBClient'), \
             patch('client.ui.main_window.DetectionThread'):
            
            from client.ui.main_window import MainWindow
            window = MainWindow()
            
            # 切换到视频文件模式
            window.select_source_type("file")
            window.file_path_label.setProperty("full_path", "/path/to/video.mp4")
            
            video_source = window.create_video_source()
            
            mock_video_file.assert_called_once_with(file_path="/path/to/video.mp4")
            assert video_source is not None
            
            window.close()


class TestMainWindowAuthentication:
    """测试身份认证"""
    
    @patch('client.ui.main_window.load_config')
    def test_face_authentication_success(self, mock_load_config, app, mock_config):
        """测试人脸认证成功（直接设置认证状态模拟成功）"""
        mock_load_config.return_value = mock_config
        
        with patch('client.ui.main_window.DBClient'), \
             patch('client.ui.main_window.DetectionThread'):
            
            from client.ui.main_window import MainWindow
            window = MainWindow()
            
            # 直接模拟认证成功回调
            driver_info = {
                'id': 1,
                'name': '张三',
                'employee_id': 'EMP001'
            }
            window.on_auth_success(driver_info)
            
            assert window.is_authenticated is True
            assert window.current_driver_id == 1
            assert window.control_buttons["start"].isEnabled() is True
            assert "张三" in window.current_user_label.text()
            
            window.close()
    
    @patch('client.ui.main_window.load_config')
    def test_face_authentication_logout(self, mock_load_config, app, mock_config):
        """测试注销"""
        mock_load_config.return_value = mock_config
        
        with patch('client.ui.main_window.DBClient'), \
             patch('client.ui.main_window.DetectionThread'):
            
            from client.ui.main_window import MainWindow
            window = MainWindow()
            
            # 先通过 on_auth_success 设置认证状态
            driver_info = {'id': 1, 'name': '张三', 'employee_id': 'EMP001'}
            window.on_auth_success(driver_info)
            assert window.is_authenticated is True
            
            # 调用 start_face_authentication 时已认证则触发注销逻辑
            window.start_face_authentication()
            
            assert window.is_authenticated is False
            assert window.current_driver_id is None
            assert window.control_buttons["start"].isEnabled() is False
            assert "未认证" in window.current_user_label.text()
            
            window.close()


class TestMainWindowMonitoring:
    """测试监测控制"""
    
    @patch('client.ui.main_window.load_config')
    def test_start_monitoring_not_authenticated(self, mock_load_config, app, mock_config):
        """测试未认证时启动监测（实际通过 show_status_message 提示，不用 QMessageBox.warning）"""
        mock_load_config.return_value = mock_config
        
        with patch('client.ui.main_window.DBClient'), \
             patch('client.ui.main_window.DetectionThread'):
            
            from client.ui.main_window import MainWindow
            window = MainWindow()
            
            # 尝试启动监测
            window.start_monitoring()
            
            # 未认证时不应该开始监测
            assert window.is_monitoring is False
            
            window.close()
    
    @patch('client.ui.main_window.load_config')
    def test_start_monitoring_success(self, mock_load_config, app, mock_config):
        """测试成功启动监测"""
        mock_load_config.return_value = mock_config
        
        with patch('client.ui.main_window.DBClient') as mock_db_client, \
             patch('client.ui.main_window.DetectionThread') as mock_detection_thread, \
             patch('client.ui.main_window.CameraSource'), \
             patch('client.ui.main_window.BehaviorDetector'), \
             patch('client.ui.main_window.FatigueDetector'), \
             patch('client.ui.main_window.AlertEngine'):
            
            from client.ui.main_window import MainWindow
            window = MainWindow()
            
            window.is_authenticated = True
            window.current_driver_id = 1
            
            mock_db_client_instance = Mock()
            mock_db_client_instance.create_session.return_value = 123
            window.db_client = mock_db_client_instance
            
            mock_detection_thread_instance = Mock()
            mock_detection_thread_instance.video_source = Mock()  # 模拟已有视频源
            mock_detection_thread_instance.is_running.return_value = False
            mock_detection_thread_instance.alert_engine = None
            window.detection_thread = mock_detection_thread_instance
            
            window.start_monitoring()
            
            assert window.is_monitoring is True
            assert window.current_session_id == 123
            assert window.control_buttons["start"].isEnabled() is False
            assert window.control_buttons["pause"].isEnabled() is True
            assert window.control_buttons["stop"].isEnabled() is True
            
            window.close()
    
    @patch('client.ui.main_window.load_config')
    def test_stop_monitoring(self, mock_load_config, app, mock_config):
        """测试停止监测"""
        mock_load_config.return_value = mock_config
        
        with patch('client.ui.main_window.DBClient') as mock_db_client, \
             patch('client.ui.main_window.DetectionThread'):
            
            from client.ui.main_window import MainWindow
            window = MainWindow()
            
            # 设置监测状态
            window.is_monitoring = True
            window.current_session_id = 123
            
            mock_detection_thread_instance = Mock()
            window.detection_thread = mock_detection_thread_instance
            
            mock_db_client_instance = Mock()
            window.db_client = mock_db_client_instance
            
            # 停止监测
            window.stop_monitoring()
            
            # 检查状态
            assert window.is_monitoring is False
            assert window.current_session_id is None
            assert window.control_buttons["start"].isEnabled() is True
            assert window.control_buttons["pause"].isEnabled() is False
            assert window.control_buttons["stop"].isEnabled() is False
            
            # 检查调用：stop_monitoring 调用 set_detection_config 停止检测（保持视频预览）
            mock_detection_thread_instance.set_detection_config.assert_called()
            mock_db_client_instance.close_session.assert_called()
            
            window.close()


class TestMainWindowSignalHandling:
    """测试信号处理"""
    
    @patch('client.ui.main_window.load_config')
    def test_on_frame_ready(self, mock_load_config, app, mock_config):
        """测试帧准备信号处理"""
        mock_load_config.return_value = mock_config
        
        with patch('client.ui.main_window.DBClient'), \
             patch('client.ui.main_window.DetectionThread'):
            
            from client.ui.main_window import MainWindow
            window = MainWindow()
            
            # 创建测试帧
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            
            # 处理帧
            window.on_frame_ready(frame)
            
            # 检查视频标签是否更新
            assert window.video_label.pixmap() is not None
            
            window.close()
    
    @patch('client.ui.main_window.load_config')
    def test_on_detection_result_with_alerts(self, mock_load_config, app, mock_config):
        """测试检测结果信号处理（有告警）"""
        mock_load_config.return_value = mock_config
        
        with patch('client.ui.main_window.DBClient'), \
             patch('client.ui.main_window.DetectionThread'), \
             patch('client.ui.main_window.QTimer'):
            
            from client.ui.main_window import MainWindow
            window = MainWindow()
            
            # 创建检测结果
            result = {
                "all_alerts": ["phone", "smoking"],
                "timestamp": 1234567890
            }
            
            # 处理检测结果
            window.on_detection_result(result)
            
            # 检查告警计数更新（2条告警）
            assert "2" in window.alert_count_label.text()
            
            window.close()
    
    @patch('client.ui.main_window.load_config')
    def test_on_status_changed(self, mock_load_config, app, mock_config):
        """测试状态变化信号处理"""
        mock_load_config.return_value = mock_config
        
        with patch('client.ui.main_window.DBClient'), \
             patch('client.ui.main_window.DetectionThread'):
            
            from client.ui.main_window import MainWindow
            window = MainWindow()
            
            # 处理状态变化
            window.on_status_changed("running")
            
            # 检查状态显示
            assert "监测中" in window.status_label.text()
            assert "监测中" in window.status_bar.currentMessage()
            
            window.close()
    
    @patch('client.ui.main_window.load_config')
    def test_on_fps_updated(self, mock_load_config, app, mock_config):
        """测试FPS更新信号处理"""
        mock_load_config.return_value = mock_config
        
        with patch('client.ui.main_window.DBClient'), \
             patch('client.ui.main_window.DetectionThread'):
            
            from client.ui.main_window import MainWindow
            window = MainWindow()
            
            # 更新FPS
            window.on_fps_updated(30.5)
            
            # 检查FPS显示
            assert "30.5" in window.fps_label.text()
            
            window.close()


class TestMainWindowUtility:
    """测试工具方法"""
    
    @patch('client.ui.main_window.load_config')
    def test_add_log(self, mock_load_config, app, mock_config):
        """测试添加日志"""
        mock_load_config.return_value = mock_config
        
        with patch('client.ui.main_window.DBClient'), \
             patch('client.ui.main_window.DetectionThread'):
            
            from client.ui.main_window import MainWindow
            window = MainWindow()
            
            # 添加日志
            window.add_log("测试日志消息")
            
            # 检查日志文本
            log_content = window.log_text.toPlainText()
            assert "测试日志消息" in log_content
            
            window.close()
    
    @patch('client.ui.main_window.load_config')
    def test_clear_log(self, mock_load_config, app, mock_config):
        """测试清除日志"""
        mock_load_config.return_value = mock_config
        
        with patch('client.ui.main_window.DBClient'), \
             patch('client.ui.main_window.DetectionThread'):
            
            from client.ui.main_window import MainWindow
            window = MainWindow()
            
            # 添加日志然后清除
            window.add_log("测试日志")
            window.clear_log()
            
            # 检查日志已清空
            assert window.log_text.toPlainText() == ""
            
            window.close()


if __name__ == "__main__":
    pytest.main([__file__])
