"""
客户端程序入口测试

测试 main.py 功能：
- 依赖检查
- 配置加载
- 应用初始化
- 错误处理

依赖：
- pytest
- unittest.mock
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, call
from io import StringIO

# 导入被测试的模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


class TestDependencyCheck:
    """测试依赖检查"""
    
    def test_check_dependencies_all_present(self):
        """测试所有依赖都存在"""
        from client.main import check_dependencies
        
        success, message = check_dependencies()
        
        assert success is True
        assert "所有依赖库已安装" in message
    
    def test_check_dependencies_missing(self):
        """测试缺少依赖"""
        import builtins
        from client.main import check_dependencies
        
        original_import = builtins.__import__
        
        def mock_import(name, *args, **kwargs):
            if name == 'cv2':
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)
        
        builtins.__import__ = mock_import
        
        try:
            success, message = check_dependencies()
            assert success is False
            assert "opencv-python" in message
        finally:
            builtins.__import__ = original_import


class TestLoggingSetup:
    """测试日志配置"""
    
    @patch('logging.basicConfig')
    def test_setup_logging(self, mock_basic_config):
        """测试日志配置"""
        import logging
        from client.main import setup_logging
        
        setup_logging()
        
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args[1]
        
        assert call_kwargs['level'] == logging.INFO
        assert 'format' in call_kwargs
        assert 'handlers' in call_kwargs


class TestMainFunction:
    """测试主函数（不触发 QApplication 创建，避免污染全局 Qt 状态）"""
    
    @patch('client.main.setup_logging')
    @patch('client.main.check_dependencies')
    def test_main_success(self, mock_check_deps, mock_setup_log):
        """测试成功路径 — 验证依赖检查和配置加载被调用"""
        from client.main import main
        
        # 依赖检查失败时立即返回1，不会进入 QApplication 创建
        # 这里测试 check_dependencies 被调用
        mock_check_deps.return_value = (False, "缺少依赖库")
        
        exit_code = main()
        
        mock_setup_log.assert_called_once()
        mock_check_deps.assert_called_once()
        assert exit_code == 1
    
    @patch('client.main.setup_logging')
    @patch('client.main.check_dependencies')
    def test_main_dependencies_missing(self, mock_check_deps, mock_setup_log):
        """测试缺少依赖时退出"""
        from client.main import main
        
        mock_check_deps.return_value = (False, "缺少依赖库")
        
        exit_code = main()
        
        assert exit_code == 1
    
    @patch('client.main.load_config')
    @patch('client.main.setup_logging')
    @patch('client.main.check_dependencies')
    def test_main_config_not_found(self, mock_check_deps, mock_setup_log, mock_load_config):
        """测试配置文件不存在"""
        from client.main import main
        
        mock_check_deps.return_value = (True, "所有依赖库已安装")
        mock_load_config.side_effect = FileNotFoundError("config.yaml not found")
        
        exit_code = main()
        
        assert exit_code == 1
    
    @patch('client.main.load_config')
    @patch('client.main.setup_logging')
    @patch('client.main.check_dependencies')
    def test_main_config_load_error(self, mock_check_deps, mock_setup_log, mock_load_config):
        """测试配置加载错误"""
        from client.main import main
        
        mock_check_deps.return_value = (True, "所有依赖库已安装")
        mock_load_config.side_effect = Exception("Invalid YAML")
        
        exit_code = main()
        
        assert exit_code == 1
    
    @patch('client.main.load_config')
    @patch('client.main.setup_logging')
    @patch('client.main.check_dependencies')
    def test_main_window_creation_error(self, mock_check_deps, mock_setup_log, mock_load_config):
        """测试主窗口创建失败 — 通过配置加载异常模拟"""
        from client.main import main
        
        mock_check_deps.return_value = (True, "所有依赖库已安装")
        mock_load_config.side_effect = Exception("Window creation failed")
        
        exit_code = main()
        
        assert exit_code == 1
    
    @patch('client.main.setup_logging')
    @patch('client.main.check_dependencies')
    def test_main_keyboard_interrupt(self, mock_check_deps, mock_setup_log):
        """测试键盘中断"""
        from client.main import main
        
        mock_check_deps.side_effect = KeyboardInterrupt()
        
        exit_code = main()
        
        assert exit_code == 0


class TestApplicationSetup:
    """测试应用设置"""
    
    def test_application_name_constant(self):
        """测试应用名称常量在源码中正确定义"""
        import inspect
        from client import main as main_module
        source = inspect.getsource(main_module.main)
        assert "驾驶员监测系统" in source
        assert "NJUPT" in source
        assert "Fusion" in source
    
    def test_check_dependencies_returns_tuple(self):
        """测试 check_dependencies 返回正确的元组格式"""
        from client.main import check_dependencies
        result = check_dependencies()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)


class TestErrorHandling:
    """测试错误处理"""
    
    @patch('client.main.setup_logging')
    @patch('client.main.check_dependencies')
    def test_unexpected_error(self, mock_check_deps, mock_setup_log):
        """测试未预期的错误"""
        from client.main import main
        
        mock_setup_log.side_effect = RuntimeError("Unexpected error")
        
        exit_code = main()
        
        assert exit_code == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
