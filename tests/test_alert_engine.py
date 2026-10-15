"""
AlertEngine 模块单元测试

测试预警引擎功能：
- 初始化和配置
- 冷却机制
- 截图保存
- 音效播放
- 数据库记录
- 告警处理流程
- 错误处理

依赖：
- pytest
- numpy
- unittest.mock
"""

import pytest
import numpy as np
import os
import tempfile
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

# 导入被测试的模块
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from client.core.alert_engine import AlertEngine


class TestAlertEngineInit:
    """测试 AlertEngine 初始化"""
    
    @patch('client.core.alert_engine.pygame')
    def test_init_success(self, mock_pygame):
        """测试成功初始化"""
        # pygame.mixer.init 在模块导入时就被调用了，这里不需要验证
        mock_pygame.mixer.init.return_value = None
        
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = AlertEngine(snapshots_dir=temp_dir)
            
            assert engine.snapshots_dir == temp_dir
            assert engine.alert_sound_path is None
            assert engine.alert_sound is None
            assert engine.current_session_id is None
            assert engine.current_driver_id is None
            assert engine.cooldown_tracker == {}
    
    @patch('client.core.alert_engine.pygame')
    def test_init_with_sound(self, mock_pygame):
        """测试带音效文件的初始化"""
        mock_pygame.mixer.init.return_value = None
        mock_sound = Mock()
        mock_pygame.mixer.Sound.return_value = mock_sound
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建一个临时音效文件
            sound_file = os.path.join(temp_dir, "alert.wav")
            with open(sound_file, 'w') as f:
                f.write("dummy")
            
            engine = AlertEngine(snapshots_dir=temp_dir, alert_sound_path=sound_file)
            
            assert engine.alert_sound_path == sound_file
            assert engine.alert_sound == mock_sound
            mock_pygame.mixer.Sound.assert_called_once_with(sound_file)
    
    @patch('client.core.alert_engine.pygame')
    def test_init_sound_load_failure(self, mock_pygame):
        """测试音效加载失败"""
        mock_pygame.mixer.init.return_value = None
        mock_pygame.mixer.Sound.side_effect = Exception("音效加载失败")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            sound_file = os.path.join(temp_dir, "alert.wav")
            with open(sound_file, 'w') as f:
                f.write("dummy")
            
            engine = AlertEngine(snapshots_dir=temp_dir, alert_sound_path=sound_file)
            
            # 验证音效加载失败后的状态
            assert engine.alert_sound is None
            assert engine.alert_sound_path == sound_file
    
    @patch('client.core.alert_engine.pygame')
    def test_init_nonexistent_sound_file(self, mock_pygame):
        """测试不存在的音效文件"""
        mock_pygame.mixer.init.return_value = None
        
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = AlertEngine(snapshots_dir=temp_dir, alert_sound_path="nonexistent.wav")
            
            assert engine.alert_sound is None
    
    @patch('client.core.alert_engine.pygame')
    @patch('os.makedirs')
    def test_init_snapshots_dir_creation_failure(self, mock_makedirs, mock_pygame):
        """测试截图目录创建失败"""
        mock_pygame.mixer.init.return_value = None
        mock_makedirs.side_effect = Exception("目录创建失败")
        
        with pytest.raises(Exception, match="目录创建失败"):
            AlertEngine(snapshots_dir="/invalid/path")


class TestAlertEngineSessionManagement:
    """测试会话管理"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.alert_engine.pygame'), \
             tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            self.engine = AlertEngine(snapshots_dir=temp_dir)
    
    def test_set_session_info(self):
        """测试设置会话信息"""
        self.engine.set_session_info(123, 456)
        
        assert self.engine.current_session_id == 123
        assert self.engine.current_driver_id == 456
    
    def test_clear_session_info(self):
        """测试清除会话信息"""
        self.engine.set_session_info(123, 456)
        self.engine.clear_session_info()
        
        assert self.engine.current_session_id is None
        assert self.engine.current_driver_id is None
    
    def test_reset_cooldown(self):
        """测试重置冷却状态"""
        # 设置一些冷却状态
        self.engine.cooldown_tracker = {"phone": time.time(), "smoking": time.time()}
        
        self.engine.reset_cooldown()
        
        assert self.engine.cooldown_tracker == {}


class TestAlertEngineCooldown:
    """测试冷却机制"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.alert_engine.pygame'), \
             tempfile.TemporaryDirectory() as temp_dir:
            self.engine = AlertEngine(snapshots_dir=temp_dir)
    
    def test_is_in_cooldown_no_history(self):
        """测试没有历史记录时不在冷却期"""
        assert self.engine._is_in_cooldown("phone") is False
    
    def test_is_in_cooldown_within_period(self):
        """测试在冷却期内"""
        current_time = time.time()
        self.engine.cooldown_tracker["phone"] = current_time - 10  # 10秒前触发
        
        assert self.engine._is_in_cooldown("phone") is True
    
    def test_is_in_cooldown_outside_period(self):
        """测试超出冷却期"""
        current_time = time.time()
        self.engine.cooldown_tracker["phone"] = current_time - 40  # 40秒前触发
        
        assert self.engine._is_in_cooldown("phone") is False
    
    def test_update_cooldown(self):
        """测试更新冷却时间"""
        before_time = time.time()
        self.engine._update_cooldown("phone")
        after_time = time.time()
        
        assert "phone" in self.engine.cooldown_tracker
        trigger_time = self.engine.cooldown_tracker["phone"]
        assert before_time <= trigger_time <= after_time
    
    def test_get_cooldown_status(self):
        """测试获取冷却状态"""
        # 设置一个在冷却期内的告警
        current_time = time.time()
        self.engine.cooldown_tracker["phone"] = current_time - 10
        
        status = self.engine.get_cooldown_status()
        
        assert isinstance(status, dict)
        assert "phone" in status
        assert status["phone"]["in_cooldown"] is True
        assert 15 < status["phone"]["remaining_time"] < 25  # 大约20秒剩余
        
        # 检查未触发的告警类型
        assert "smoking" in status
        assert status["smoking"]["in_cooldown"] is False
        assert status["smoking"]["remaining_time"] == 0


class TestAlertEngineSnapshot:
    """测试截图功能"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.alert_engine.pygame'):
            self.temp_dir = tempfile.mkdtemp()
            self.engine = AlertEngine(snapshots_dir=self.temp_dir)
            self.engine.set_session_info(123, 456)
    
    def teardown_method(self):
        """清理测试环境"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_generate_snapshot_filename(self):
        """测试生成截图文件名"""
        filename = self.engine._generate_snapshot_filename("phone")
        
        # 检查文件名格式: {session_id}_{alert_type}_{timestamp}.jpg
        parts = filename.split('_')
        assert len(parts) == 3
        assert parts[0] == "123"  # session_id
        assert parts[1] == "phone"  # alert_type
        assert parts[2].endswith(".jpg")  # timestamp.jpg
        assert len(parts[2]) == 18  # 14位时间戳 + ".jpg"
    
    def test_generate_snapshot_filename_no_session(self):
        """测试没有会话ID时的文件名生成"""
        self.engine.clear_session_info()
        filename = self.engine._generate_snapshot_filename("phone")
        
        assert filename.startswith("unknown_phone_")
    
    @patch('cv2.imwrite')
    def test_save_snapshot_success(self, mock_imwrite):
        """测试成功保存截图"""
        mock_imwrite.return_value = True
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        filepath = self.engine._save_snapshot(frame, "phone")
        
        assert filepath is not None
        assert filepath.endswith(".jpg")
        assert "123_phone_" in os.path.basename(filepath)
        mock_imwrite.assert_called_once()
    
    @patch('cv2.imwrite')
    def test_save_snapshot_failure(self, mock_imwrite):
        """测试截图保存失败"""
        mock_imwrite.return_value = False
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        filepath = self.engine._save_snapshot(frame, "phone")
        
        assert filepath is None
    
    @patch('cv2.imwrite')
    def test_save_snapshot_exception(self, mock_imwrite):
        """测试截图保存异常"""
        mock_imwrite.side_effect = Exception("保存失败")
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        with patch.object(self.engine.logger, 'error') as mock_error:
            filepath = self.engine._save_snapshot(frame, "phone")
            
            assert filepath is None
            mock_error.assert_called_once()


class TestAlertEngineSound:
    """测试音效播放"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.alert_engine.pygame'), \
             tempfile.TemporaryDirectory() as temp_dir:
            self.engine = AlertEngine(snapshots_dir=temp_dir)
    
    def test_play_alert_sound_with_sound(self):
        """测试播放音效（有音效文件）"""
        mock_sound = Mock()
        self.engine.alert_sound = mock_sound
        
        self.engine._play_alert_sound()
        
        mock_sound.play.assert_called_once()
    
    def test_play_alert_sound_no_sound(self):
        """测试播放音效（无音效文件）"""
        self.engine.alert_sound = None
        
        with patch.object(self.engine.logger, 'debug') as mock_debug:
            self.engine._play_alert_sound()
            mock_debug.assert_called_once()
    
    def test_play_alert_sound_exception(self):
        """测试播放音效异常"""
        mock_sound = Mock()
        mock_sound.play.side_effect = Exception("播放失败")
        self.engine.alert_sound = mock_sound
        
        with patch.object(self.engine.logger, 'warning') as mock_warning:
            self.engine._play_alert_sound()
            mock_warning.assert_called_once()


class TestAlertEngineDatabase:
    """测试数据库操作"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.alert_engine.pygame'), \
             tempfile.TemporaryDirectory() as temp_dir:
            self.engine = AlertEngine(snapshots_dir=temp_dir)
            self.engine.set_session_info(123, 456)
            self.mock_db_client = Mock()
    
    def test_write_alert_record_success(self):
        """测试成功写入告警记录"""
        self.mock_db_client.insert_alert.return_value = 789
        self.mock_db_client.increment_session_alerts.return_value = True
        
        success = self.engine._write_alert_record(
            alert_type="phone",
            severity="medium",
            snapshot_path="/path/to/snapshot.jpg",
            db_client=self.mock_db_client
        )
        
        assert success is True
        self.mock_db_client.insert_alert.assert_called_once_with(
            driver_id=456,
            session_id=123,
            alert_type="phone",
            severity="medium",
            snapshot_path="snapshot.jpg"  # 只保存文件名
        )
        self.mock_db_client.increment_session_alerts.assert_called_once_with(123)
    
    def test_write_alert_record_no_session(self):
        """测试没有会话信息时写入失败"""
        self.engine.clear_session_info()
        
        success = self.engine._write_alert_record(
            alert_type="phone",
            severity="medium",
            snapshot_path=None,
            db_client=self.mock_db_client
        )
        
        assert success is False
        self.mock_db_client.insert_alert.assert_not_called()
    
    def test_write_alert_record_database_error(self):
        """测试数据库写入错误"""
        self.mock_db_client.insert_alert.side_effect = Exception("数据库错误")
        
        with patch.object(self.engine.logger, 'error') as mock_error:
            success = self.engine._write_alert_record(
                alert_type="phone",
                severity="medium",
                snapshot_path=None,
                db_client=self.mock_db_client
            )
            
            assert success is False
            mock_error.assert_called_once()


class TestAlertEngineProcessing:
    """测试告警处理流程"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.alert_engine.pygame'), \
             tempfile.TemporaryDirectory() as temp_dir:
            self.engine = AlertEngine(snapshots_dir=temp_dir)
            self.engine.set_session_info(123, 456)
            self.mock_db_client = Mock()
    
    @patch('cv2.imwrite')
    def test_process_alerts_success(self, mock_imwrite):
        """测试成功处理告警"""
        mock_imwrite.return_value = True
        self.mock_db_client.insert_alert.return_value = 789
        self.mock_db_client.increment_session_alerts.return_value = True
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        triggered_alerts = ["phone", "smoking"]
        
        with patch.object(self.engine, '_play_alert_sound') as mock_play_sound:
            processed_alerts = self.engine.process_alerts(frame, triggered_alerts, self.mock_db_client)
            
            assert len(processed_alerts) == 2
            
            # 检查第一个告警
            alert1 = processed_alerts[0]
            assert alert1["type"] == "phone"
            assert alert1["severity"] == "medium"
            assert alert1["db_recorded"] is True
            assert alert1["snapshot_path"] is not None
            
            # 检查第二个告警
            alert2 = processed_alerts[1]
            assert alert2["type"] == "smoking"
            assert alert2["severity"] == "high"
            
            # 验证音效播放次数
            assert mock_play_sound.call_count == 2
    
    def test_process_alerts_with_cooldown(self):
        """测试冷却期内的告警处理"""
        # 设置phone在冷却期内
        self.engine.cooldown_tracker["phone"] = time.time() - 10
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        triggered_alerts = ["phone", "smoking"]
        
        with patch.object(self.engine, '_save_snapshot', return_value="test.jpg"), \
             patch.object(self.engine, '_play_alert_sound'), \
             patch.object(self.engine, '_write_alert_record', return_value=True):
            
            processed_alerts = self.engine.process_alerts(frame, triggered_alerts, self.mock_db_client)
            
            # 只有smoking应该被处理，phone在冷却期内
            assert len(processed_alerts) == 1
            assert processed_alerts[0]["type"] == "smoking"
    
    def test_process_alerts_empty_list(self):
        """测试空告警列表"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        triggered_alerts = []
        
        processed_alerts = self.engine.process_alerts(frame, triggered_alerts, self.mock_db_client)
        
        assert processed_alerts == []
    
    @patch('cv2.imwrite')
    def test_force_trigger_alert(self, mock_imwrite):
        """测试强制触发告警"""
        mock_imwrite.return_value = True
        self.mock_db_client.insert_alert.return_value = 789
        self.mock_db_client.increment_session_alerts.return_value = True
        
        # 设置phone在冷却期内
        self.engine.cooldown_tracker["phone"] = time.time() - 10
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        with patch.object(self.engine, '_play_alert_sound'):
            alert_info = self.engine.force_trigger_alert(frame, "phone", self.mock_db_client)
            
            assert alert_info["type"] == "phone"
            assert alert_info["severity"] == "medium"
            assert "phone" in self.engine.cooldown_tracker  # 应该重新设置冷却时间


class TestAlertEngineUtilityMethods:
    """测试工具方法"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.alert_engine.pygame'), \
             tempfile.TemporaryDirectory() as temp_dir:
            self.engine = AlertEngine(snapshots_dir=temp_dir)
    
    def test_get_alert_severity(self):
        """测试获取告警危险等级"""
        assert self.engine.get_alert_severity("phone") == "medium"
        assert self.engine.get_alert_severity("smoking") == "high"
        assert self.engine.get_alert_severity("cup") == "low"
        assert self.engine.get_alert_severity("eye_closed") == "high"
        assert self.engine.get_alert_severity("unknown") == "medium"  # 默认值
    
    def test_supported_alert_types(self):
        """测试支持的告警类型"""
        types = self.engine.supported_alert_types
        expected_types = {"phone", "cup", "smoking", "eye_closed", "yawning", "head_down"}
        assert set(types) == expected_types
    
    def test_cooldown_seconds_property(self):
        """测试冷却时间属性"""
        assert self.engine.cooldown_seconds == 30
    
    @patch('client.core.alert_engine.pygame')
    def test_close(self, mock_pygame):
        """测试资源释放"""
        mock_pygame.mixer.get_init.return_value = True
        
        with patch.object(self.engine.logger, 'info') as mock_info:
            self.engine.close()
            
            mock_pygame.mixer.quit.assert_called_once()
            mock_info.assert_called_once()
    
    @patch('client.core.alert_engine.pygame')
    def test_close_exception(self, mock_pygame):
        """测试资源释放异常"""
        mock_pygame.mixer.quit.side_effect = Exception("释放失败")
        
        with patch.object(self.engine.logger, 'warning') as mock_warning:
            self.engine.close()
            mock_warning.assert_called_once()
    
    def test_context_manager(self):
        """测试上下文管理器"""
        with patch.object(self.engine, 'close') as mock_close:
            with self.engine as engine:
                assert engine == self.engine
            mock_close.assert_called_once()


class TestAlertEngineConstants:
    """测试常量和配置"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.alert_engine.pygame'), \
             tempfile.TemporaryDirectory() as temp_dir:
            self.engine = AlertEngine(snapshots_dir=temp_dir)
    
    def test_cooldown_seconds_constant(self):
        """测试冷却时间常量"""
        assert AlertEngine.COOLDOWN_SECONDS == 30
    
    def test_alert_severity_map(self):
        """测试告警严重程度映射"""
        expected_map = {
            "phone": "medium",
            "cup": "low",
            "smoking": "high",
            "eye_closed": "high",
            "yawning": "medium",
            "head_down": "medium"
        }
        assert AlertEngine.ALERT_SEVERITY_MAP == expected_map


if __name__ == "__main__":
    pytest.main([__file__])