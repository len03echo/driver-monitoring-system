"""
AlertDialog 模块单元测试

测试告警弹窗功能：
- UI初始化
- 告警信息显示
- 截图预览
- 自动关闭
- 按钮功能

依赖：
- pytest
- PyQt5
- unittest.mock
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtCore import QCoreApplication, QTimer
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt

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


class TestAlertDialogInit:
    """测试 AlertDialog 初始化"""
    
    def test_init_basic(self, app):
        """测试基本初始化"""
        from client.ui.alert_dialog import AlertDialog
        
        dialog = AlertDialog(
            alert_type="phone",
            severity="medium",
            snapshot_path=None,
            auto_close_seconds=0
        )
        
        # 检查基本属性
        assert dialog.alert_type == "phone"
        assert dialog.severity == "medium"
        assert dialog.snapshot_path is None
        assert dialog.auto_close_seconds == 0
        
        # 检查窗口属性
        assert dialog.windowTitle() == "驾驶行为告警"
        assert dialog.isModal() is True
        
        dialog.close()
    
    def test_init_with_snapshot(self, app, tmp_path):
        """测试带截图初始化"""
        from client.ui.alert_dialog import AlertDialog
        
        # 创建临时截图文件
        snapshot_file = tmp_path / "test_snapshot.jpg"
        snapshot_file.write_bytes(b"fake image data")
        
        dialog = AlertDialog(
            alert_type="smoking",
            severity="high",
            snapshot_path=str(snapshot_file),
            auto_close_seconds=0
        )
        
        assert dialog.snapshot_path == str(snapshot_file)
        assert dialog.snapshot_label is not None
        
        dialog.close()
    
    def test_init_all_alert_types(self, app):
        """测试所有告警类型"""
        from client.ui.alert_dialog import AlertDialog
        
        alert_types = ["phone", "cup", "smoking", "eye_closed", "yawning", "head_down", "unknown"]
        
        for alert_type in alert_types:
            dialog = AlertDialog(
                alert_type=alert_type,
                severity="medium",
                auto_close_seconds=0
            )
            
            assert dialog.alert_type == alert_type
            assert dialog.get_alert_type_display() is not None
            
            dialog.close()
    
    def test_init_all_severity_levels(self, app):
        """测试所有危险等级"""
        from client.ui.alert_dialog import AlertDialog
        
        severity_levels = ["low", "medium", "high"]
        
        for severity in severity_levels:
            dialog = AlertDialog(
                alert_type="phone",
                severity=severity,
                auto_close_seconds=0
            )
            
            assert dialog.severity == severity
            assert dialog.get_severity_display() is not None
            
            dialog.close()


class TestAlertDialogDisplay:
    """测试告警信息显示"""
    
    def test_alert_type_display(self, app):
        """测试告警类型显示"""
        from client.ui.alert_dialog import AlertDialog
        
        dialog = AlertDialog(
            alert_type="phone",
            severity="medium",
            auto_close_seconds=0
        )
        
        # 检查中文映射
        assert dialog.get_alert_type_display() == "使用手机"
        
        dialog.close()
    
    def test_severity_display(self, app):
        """测试危险等级显示"""
        from client.ui.alert_dialog import AlertDialog
        
        dialog = AlertDialog(
            alert_type="phone",
            severity="high",
            auto_close_seconds=0
        )
        
        # 检查中文映射
        assert dialog.get_severity_display() == "高"
        
        dialog.close()
    
    def test_severity_colors(self, app):
        """测试危险等级颜色"""
        from client.ui.alert_dialog import AlertDialog
        
        # 测试不同等级的颜色（与实际代码 SEVERITY_COLOR_MAP 一致）
        severities = {
            "low": "#E65100",
            "medium": "#E65100",
            "high": "#B71C1C"
        }
        
        for severity, expected_color in severities.items():
            dialog = AlertDialog(
                alert_type="phone",
                severity=severity,
                auto_close_seconds=0
            )
            
            assert AlertDialog.SEVERITY_COLOR_MAP[severity] == expected_color
            
            dialog.close()


class TestAlertDialogSnapshot:
    """测试截图预览"""
    
    def test_snapshot_not_provided(self, app):
        """测试未提供截图"""
        from client.ui.alert_dialog import AlertDialog
        
        dialog = AlertDialog(
            alert_type="phone",
            severity="medium",
            snapshot_path=None,
            auto_close_seconds=0
        )
        
        # 未提供截图时，snapshot_label 应为 None
        assert dialog.snapshot_label is None
        
        dialog.close()
    
    def test_snapshot_file_not_exists(self, app):
        """测试截图文件不存在"""
        from client.ui.alert_dialog import AlertDialog
        
        dialog = AlertDialog(
            alert_type="phone",
            severity="medium",
            snapshot_path="/nonexistent/path/image.jpg",
            auto_close_seconds=0
        )
        
        # 文件不存在时应显示提示
        assert dialog.snapshot_label is not None
        assert dialog.snapshot_label.text() == "截图不可用"
        
        dialog.close()
    
    def test_snapshot_load_success(self, app, tmp_path):
        """测试截图加载成功"""
        from client.ui.alert_dialog import AlertDialog
        from PyQt5.QtGui import QPixmap, QImage
        
        # 创建一个真实的测试图片（1x1像素的黑色图片）
        snapshot_file = tmp_path / "test_snapshot.jpg"
        
        # 创建一个简单的图片
        image = QImage(100, 100, QImage.Format_RGB888)
        image.fill(0)  # 填充黑色
        pixmap = QPixmap.fromImage(image)
        pixmap.save(str(snapshot_file), "JPG")
        
        dialog = AlertDialog(
            alert_type="phone",
            severity="medium",
            snapshot_path=str(snapshot_file),
            auto_close_seconds=0
        )
        
        # 检查截图标签
        assert dialog.snapshot_label is not None
        assert dialog.snapshot_label.pixmap() is not None
        
        dialog.close()


class TestAlertDialogAutoClose:
    """测试自动关闭功能"""
    
    @patch('client.ui.alert_dialog.QTimer')
    def test_auto_close_enabled(self, mock_timer, app):
        """测试启用自动关闭"""
        from client.ui.alert_dialog import AlertDialog
        
        dialog = AlertDialog(
            alert_type="phone",
            severity="medium",
            auto_close_seconds=5
        )
        
        # 检查定时器被调用
        mock_timer.singleShot.assert_called_once()
        call_args = mock_timer.singleShot.call_args
        assert call_args[0][0] == 5000  # 5秒 = 5000毫秒
        
        dialog.close()
    
    @patch('client.ui.alert_dialog.QTimer')
    def test_auto_close_disabled(self, mock_timer, app):
        """测试禁用自动关闭"""
        from client.ui.alert_dialog import AlertDialog
        
        dialog = AlertDialog(
            alert_type="phone",
            severity="medium",
            auto_close_seconds=0
        )
        
        # 自动关闭为0时不应调用定时器
        mock_timer.singleShot.assert_not_called()
        
        dialog.close()


class TestAlertDialogButtons:
    """测试按钮功能"""
    
    def test_confirm_button_exists(self, app):
        """测试确认按钮存在"""
        from client.ui.alert_dialog import AlertDialog
        
        dialog = AlertDialog(
            alert_type="phone",
            severity="medium",
            auto_close_seconds=0
        )
        
        assert dialog.confirm_button is not None
        assert dialog.confirm_button.text() == "确认"
        assert dialog.confirm_button.isEnabled() is True
        
        dialog.close()
    
    def test_confirm_button_click(self, app):
        """测试点击确认按钮"""
        from client.ui.alert_dialog import AlertDialog
        
        dialog = AlertDialog(
            alert_type="phone",
            severity="medium",
            auto_close_seconds=0
        )
        
        # 点击确认按钮
        dialog.confirm_button.click()
        
        # 对话框应被接受
        assert dialog.result() == QDialog.Accepted
        
        dialog.close()


class TestAlertDialogIntegration:
    """测试集成场景"""
    
    def test_complete_workflow(self, app):
        """测试完整工作流程"""
        from client.ui.alert_dialog import AlertDialog
        
        # 创建对话框
        dialog = AlertDialog(
            alert_type="smoking",
            severity="high",
            snapshot_path=None,
            auto_close_seconds=0
        )
        
        # 显示对话框
        dialog.show()
        app.processEvents()
        
        # 检查显示状态
        assert dialog.isVisible() is True
        
        # 点击确认
        dialog.confirm_button.click()
        
        # 检查结果
        assert dialog.result() == QDialog.Accepted
        
        dialog.close()
    
    def test_multiple_dialogs(self, app):
        """测试多个对话框"""
        from client.ui.alert_dialog import AlertDialog
        
        dialogs = []
        
        # 创建多个不同类型的对话框
        for alert_type in ["phone", "smoking", "eye_closed"]:
            dialog = AlertDialog(
                alert_type=alert_type,
                severity="medium",
                auto_close_seconds=0
            )
            dialogs.append(dialog)
        
        # 检查所有对话框
        for dialog in dialogs:
            assert dialog.alert_type in ["phone", "smoking", "eye_closed"]
            dialog.close()


class TestAlertDialogMapping:
    """测试映射字典"""
    
    def test_alert_type_map_complete(self, app):
        """测试告警类型映射完整性"""
        from client.ui.alert_dialog import AlertDialog
        
        expected_types = ["phone", "cup", "smoking", "eye_closed", "yawning", "head_down", "unknown"]
        
        for alert_type in expected_types:
            assert alert_type in AlertDialog.ALERT_TYPE_MAP
            assert isinstance(AlertDialog.ALERT_TYPE_MAP[alert_type], str)
            assert len(AlertDialog.ALERT_TYPE_MAP[alert_type]) > 0
    
    def test_severity_map_complete(self, app):
        """测试危险等级映射完整性"""
        from client.ui.alert_dialog import AlertDialog
        
        expected_severities = ["low", "medium", "high"]
        
        for severity in expected_severities:
            assert severity in AlertDialog.SEVERITY_MAP
            assert isinstance(AlertDialog.SEVERITY_MAP[severity], str)
            assert len(AlertDialog.SEVERITY_MAP[severity]) > 0
    
    def test_severity_color_map_complete(self, app):
        """测试危险等级颜色映射完整性"""
        from client.ui.alert_dialog import AlertDialog
        
        expected_severities = ["low", "medium", "high"]
        
        for severity in expected_severities:
            assert severity in AlertDialog.SEVERITY_COLOR_MAP
            color = AlertDialog.SEVERITY_COLOR_MAP[severity]
            assert isinstance(color, str)
            assert color.startswith("#")
            assert len(color) == 7  # #RRGGBB 格式


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
