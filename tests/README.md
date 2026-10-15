# 测试文件说明

## 📋 测试结构

```
tests/
├── README.md                              # 测试说明（本文档）
├── test_system_integration.py             # 🔥 系统集成测试（推荐运行）
├── integration/                           # 集成测试
│   └── test_flask_api.py                 # Flask API 集成测试
├── property_tests/                        # 属性测试
├── test_*.py                              # 单元测试文件
└── __pycache__/                          # Python 缓存
```

## 🚀 快速开始

### 运行系统集成测试（推荐）

```bash
# 从项目根目录运行
python tests/test_system_integration.py
```

这个测试会检查：
- ✅ 人脸识别器初始化
- ✅ 数据库连接
- ✅ 人脸特征提取
- ✅ 摄像头访问
- ✅ 相似度计算

### 运行所有单元测试

```bash
# 使用 pytest
pytest tests/

# 运行特定测试文件
pytest tests/test_face_recognizer.py

# 显示详细输出
pytest tests/ -v

# 生成覆盖率报告
pytest tests/ --cov=client --cov=server
```

## 📝 测试文件说明

### 核心功能测试

| 文件 | 说明 | 状态 |
|------|------|------|
| `test_system_integration.py` | 系统集成测试 | ✅ 推荐 |
| `test_face_recognizer.py` | 人脸识别器单元测试 | ✅ |
| `test_behavior_detector.py` | 行为检测器单元测试 | ✅ |
| `test_fatigue_detector.py` | 疲劳检测器单元测试 | ✅ |
| `test_alert_engine.py` | 告警引擎单元测试 | ✅ |
| `test_detection_thread.py` | 检测线程单元测试 | ✅ |
| `test_video_source.py` | 视频源单元测试 | ✅ |

### UI 测试

| 文件 | 说明 | 状态 |
|------|------|------|
| `test_main_window.py` | 主窗口单元测试 | ✅ |
| `test_register_dialog.py` | 注册对话框单元测试 | ✅ |
| `test_alert_dialog.py` | 告警对话框单元测试 | ✅ |

### API 测试

| 文件 | 说明 | 状态 |
|------|------|------|
| `test_flask_app.py` | Flask 应用测试 | ✅ |
| `test_drivers_api.py` | 驾驶员 API 测试 | ✅ |
| `test_alerts_api.py` | 告警 API 测试 | ✅ |
| `test_stats_api.py` | 统计 API 测试 | ✅ |
| `test_snapshots_api.py` | 截图 API 测试 | ✅ |

### 算法测试

| 文件 | 说明 | 状态 |
|------|------|------|
| `test_cosine_similarity.py` | 余弦相似度测试 | ✅ |
| `test_ear_mar.py` | EAR/MAR 计算测试 | ✅ |
| `test_frame_counter.py` | 帧计数器测试 | ✅ |
| `test_cooldown.py` | 冷却机制测试 | ✅ |

### 集成测试

| 文件 | 说明 | 状态 |
|------|------|------|
| `integration/test_flask_api.py` | Flask API 集成测试 | ✅ |
| `test_main_window_register_integration.py` | 主窗口注册集成测试 | ✅ |

## 🎯 测试场景

### 场景 1: 首次安装后测试

```bash
# 1. 运行系统集成测试
python tests/test_system_integration.py

# 2. 如果通过，启动客户端
python client/main.py
```

### 场景 2: 开发过程中测试

```bash
# 运行相关的单元测试
pytest tests/test_face_recognizer.py -v
pytest tests/test_fatigue_detector.py -v
```

### 场景 3: 提交代码前测试

```bash
# 运行所有测试
pytest tests/ -v

# 检查覆盖率
pytest tests/ --cov=client --cov=server --cov-report=html
```

## 📊 测试覆盖率

查看测试覆盖率报告：

```bash
# 生成 HTML 报告
pytest tests/ --cov=client --cov=server --cov-report=html

# 打开报告
# Windows: start htmlcov/index.html
# Linux: xdg-open htmlcov/index.html
# macOS: open htmlcov/index.html
```

## 🐛 测试失败处理

### 常见问题

1. **数据库连接失败**
   ```
   错误: 数据库连接失败
   解决: 检查 MySQL 是否启动，密码是否正确
   ```

2. **摄像头访问失败**
   ```
   错误: 无法打开摄像头 0
   解决: 检查摄像头是否被占用，尝试更换索引
   ```

3. **模型加载失败**
   ```
   错误: InsightFace 模型加载失败
   解决: 检查网络连接，模型会自动下载
   ```

4. **导入错误**
   ```
   错误: ModuleNotFoundError
   解决: 确保已安装所有依赖 pip install -r requirements.txt
   ```

## 📝 编写新测试

### 单元测试模板

```python
"""
测试模块说明
"""

import pytest
from client.core.xxx import XXX


class TestXXX:
    """XXX 测试类"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        self.xxx = XXX()
    
    def teardown_method(self):
        """每个测试方法后执行"""
        self.xxx.close()
    
    def test_功能名称(self):
        """测试功能说明"""
        # Arrange (准备)
        input_data = ...
        
        # Act (执行)
        result = self.xxx.method(input_data)
        
        # Assert (断言)
        assert result == expected_value
```

### 集成测试模板

```python
"""
集成测试说明
"""

import pytest


def test_集成场景():
    """测试集成场景说明"""
    # 1. 准备环境
    ...
    
    # 2. 执行操作
    ...
    
    # 3. 验证结果
    assert ...
    
    # 4. 清理环境
    ...
```

## 🔧 测试配置

### pytest 配置

在项目根目录创建 `pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

### 覆盖率配置

在项目根目录创建 `.coveragerc`:

```ini
[run]
source = client,server
omit = 
    */tests/*
    */venv/*
    */__pycache__/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
```

## 📚 相关文档

- [pytest 文档](https://docs.pytest.org/)
- [pytest-cov 文档](https://pytest-cov.readthedocs.io/)
- [项目文档](../docs/000-INDEX.md)

---

**更新日期**: 2026-05-18  
**维护者**: NJUPT 项目组
