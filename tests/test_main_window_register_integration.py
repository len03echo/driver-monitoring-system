"""
MainWindow 与 RegisterDialog 集成测试

测试主窗口与注册对话框的集成：
- 打开注册对话框
- 注册成功后的处理
- 注册取消后的处理

依赖：
- pytest
- PyQt5
- unittest.mock
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from PyQt5.QtWidgets import QApplication, QDialog, QPushButton
from PyQt5.QtCore import QCoreApplication
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
    """模拟配置（使用 MagicMock 支持属性访问）"""
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


class TestMainWindowRegisterIntegration:
    """测试 MainWindow 与 RegisterDialog 集成"""

    @patch('client.ui.main_window.load_config')
    @patch('client.ui.main_window.DBClient')
    @patch('client.ui.main_window.DetectionThread')
    def test_open_register_dialog_success(self, mock_detection_thread,
                                          mock_db_client, mock_load_config, app, mock_config):
        """测试成功打开注册对话框"""
        mock_load_config.return_value = mock_config

        from client.ui.main_window import MainWindow
        window = MainWindow()

        # 模拟视频已打开（open_video_button 被禁用表示视频已打开）
        window.open_video_button.setEnabled(False)

        mock_dialog = Mock()
        # RegisterDialog 被 mock 后 RegisterDialog.Accepted 也是 Mock 对象
        # 让 exec_() 返回与 RegisterDialog.Accepted 相同的值（整数1）
        mock_dialog.exec_.return_value = QDialog.Accepted  # == 1

        with patch('client.ui.register_dialog.RegisterDialog') as mock_reg_cls:
            # 让 mock_reg_cls.Accepted == QDialog.Accepted（整数1），使判断匹配
            mock_reg_cls.Accepted = QDialog.Accepted
            mock_reg_cls.return_value = mock_dialog
            window.detection_thread = Mock()
            window.detection_thread.is_paused.return_value = False
            window.detection_thread.frame_ready = Mock()
            window.detection_thread.frame_ready.connect = Mock()
            window.detection_thread.frame_ready.disconnect = Mock()

            window.open_register_dialog()
            mock_reg_cls.assert_called_once()
            mock_dialog.exec_.assert_called_once()

        log_content = window.log_text.toPlainText()
        assert "注册成功" in log_content

        window.close()

    @patch('client.ui.main_window.load_config')
    @patch('client.ui.main_window.DBClient')
    @patch('client.ui.main_window.DetectionThread')
    def test_open_register_dialog_cancel(self, mock_detection_thread,
                                         mock_db_client, mock_load_config, app, mock_config):
        """测试取消注册对话框"""
        mock_load_config.return_value = mock_config

        from client.ui.main_window import MainWindow
        window = MainWindow()

        window.open_video_button.setEnabled(False)

        mock_dialog = Mock()
        mock_dialog.exec_.return_value = QDialog.Rejected

        with patch('client.ui.register_dialog.RegisterDialog', return_value=mock_dialog) as mock_reg_cls:
            window.detection_thread = Mock()
            window.detection_thread.is_paused.return_value = False
            window.detection_thread.frame_ready = Mock()
            window.detection_thread.frame_ready.connect = Mock()
            window.detection_thread.frame_ready.disconnect = Mock()

            window.open_register_dialog()
            mock_reg_cls.assert_called_once()
            mock_dialog.exec_.assert_called_once()

        log_content = window.log_text.toPlainText()
        assert "取消注册" in log_content

        window.close()

    @patch('client.ui.main_window.load_config')
    @patch('client.ui.main_window.DBClient')
    @patch('client.ui.main_window.DetectionThread')
    def test_register_button_exists(self, mock_detection_thread, mock_db_client,
                                    mock_load_config, app, mock_config):
        """测试注册按钮存在（实际文字含 '注册'）"""
        mock_load_config.return_value = mock_config

        from client.ui.main_window import MainWindow
        window = MainWindow()

        register_button = None
        for child in window.findChildren(QPushButton):
            if "注册" in child.text():
                register_button = child
                break

        assert register_button is not None
        assert register_button.isEnabled() is True

        window.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
