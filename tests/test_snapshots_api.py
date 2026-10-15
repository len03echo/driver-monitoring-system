"""
截图静态文件 API 测试

测试 /snapshots/<filename> 接口的功能。

依赖：
- pytest
- Flask
"""

import pytest
import sys
import os
import json
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from server.app import create_app


@pytest.fixture
def app():
    """创建测试 Flask 应用"""
    from flask import Flask
    from flask_cors import CORS
    from server.models.models import db
    from server.routes import drivers_bp, alerts_bp, stats_bp, snapshots_bp
    
    # 直接创建Flask应用，不使用create_app()以避免加载配置文件
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JSON_AS_ASCII'] = False
    
    # 初始化数据库
    db.init_app(app)
    
    # 配置CORS
    CORS(app)
    
    # 注册蓝图
    app.register_blueprint(drivers_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(snapshots_bp)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """获取测试客户端"""
    return app.test_client()


@pytest.fixture
def temp_snapshots_dir():
    """创建临时截图目录"""
    with tempfile.TemporaryDirectory() as temp_dir:
        snapshots_dir = Path(temp_dir) / 'snapshots'
        snapshots_dir.mkdir()
        
        # 创建测试图片文件
        test_image = snapshots_dir / '1_phone_20240117142035.jpg'
        test_image.write_bytes(b'fake image content')
        
        # 创建子目录和文件
        sub_dir = snapshots_dir / '2024' / '01'
        sub_dir.mkdir(parents=True)
        sub_image = sub_dir / '2_smoking_20240117142136.jpg'
        sub_image.write_bytes(b'fake sub image content')
        
        # 临时修改 SNAPSHOTS_DIR
        from server.routes import snapshots
        original_dir = snapshots.SNAPSHOTS_DIR
        snapshots.SNAPSHOTS_DIR = snapshots_dir
        
        yield snapshots_dir
        
        # 恢复原始目录
        snapshots.SNAPSHOTS_DIR = original_dir


class TestSnapshotsAPI:
    """测试截图静态文件 API"""
    
    def test_get_snapshot_success(self, client, temp_snapshots_dir):
        """测试成功获取截图文件"""
        response = client.get('/snapshots/1_phone_20240117142035.jpg')
        
        assert response.status_code == 200
        assert response.mimetype == 'image/jpeg'
        assert response.data == b'fake image content'
    
    def test_get_snapshot_with_subdirectory(self, client, temp_snapshots_dir):
        """测试获取子目录中的截图文件"""
        response = client.get('/snapshots/2024/01/2_smoking_20240117142136.jpg')
        
        assert response.status_code == 200
        assert response.mimetype == 'image/jpeg'
        assert response.data == b'fake sub image content'
    
    def test_get_snapshot_not_found(self, client, temp_snapshots_dir):
        """测试获取不存在的截图文件"""
        response = client.get('/snapshots/nonexistent.jpg')
        
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert data['code'] == 404
        assert data['data'] is None
        assert data['msg'] == '截图文件不存在'
    
    def test_get_snapshot_path_traversal_attack(self, client, temp_snapshots_dir):
        """测试路径遍历攻击防护"""
        # 尝试访问上级目录
        response = client.get('/snapshots/../../../etc/passwd')
        
        assert response.status_code == 403
        
        data = json.loads(response.data)
        assert data['code'] == 403
        assert data['data'] is None
        assert data['msg'] == '非法的文件路径'
    
    def test_get_snapshot_directory_not_exists(self, client):
        """测试截图目录不存在的情况"""
        # 临时修改为不存在的目录
        from server.routes import snapshots
        original_dir = snapshots.SNAPSHOTS_DIR
        snapshots.SNAPSHOTS_DIR = Path('/nonexistent/directory')
        
        try:
            response = client.get('/snapshots/test.jpg')
            
            assert response.status_code == 404
            
            data = json.loads(response.data)
            assert data['code'] == 404
            assert data['data'] is None
            assert data['msg'] == '截图文件不存在'
        
        finally:
            # 恢复原始目录
            snapshots.SNAPSHOTS_DIR = original_dir
    
    def test_get_snapshot_filename_validation(self, client, temp_snapshots_dir):
        """测试文件名验证"""
        # 测试空文件名
        response = client.get('/snapshots/')
        assert response.status_code == 404  # Flask会返回404
        
        # 测试特殊字符
        response = client.get('/snapshots/test<script>.jpg')
        assert response.status_code == 404  # 文件不存在


class TestSnapshotsIntegration:
    """测试截图API集成功能"""
    
    def test_snapshot_url_format(self, client, temp_snapshots_dir):
        """测试截图URL格式"""
        # 测试标准格式的截图文件名
        test_files = [
            '1_phone_20240117142035.jpg',
            '2_smoking_20240117142136.jpg',
            '3_eye_closed_20240117142237.jpg',
            '4_yawning_20240117142338.jpg',
            '5_head_down_20240117142439.jpg',
            '6_cup_20240117142540.jpg'
        ]
        
        for filename in test_files:
            # 创建测试文件
            test_file = temp_snapshots_dir / filename
            test_file.write_bytes(f'content for {filename}'.encode())
            
            # 测试访问
            response = client.get(f'/snapshots/{filename}')
            assert response.status_code == 200
            assert response.data == f'content for {filename}'.encode()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])