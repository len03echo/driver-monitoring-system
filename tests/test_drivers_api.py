"""
驾驶员档案 API 测试

测试 /api/drivers 相关接口的功能。

依赖：
- pytest
- Flask
- SQLAlchemy
"""

import pytest
import sys
import os
import json
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from server.app import create_app
from server.models.models import db, Driver


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
def sample_drivers(app):
    """创建示例驾驶员数据"""
    with app.app_context():
        drivers = [
            Driver(name="张三", employee_id="EMP001"),
            Driver(name="李四", employee_id="EMP002"),
            Driver(name="王五", employee_id="EMP003")
        ]
        
        for driver in drivers:
            db.session.add(driver)
        
        db.session.commit()
        
        # 返回驾驶员ID列表而不是对象，避免DetachedInstanceError
        return [driver.id for driver in drivers]


class TestDriversAPI:
    """测试驾驶员档案 API"""
    
    def test_get_drivers_empty(self, client):
        """测试获取空驾驶员列表"""
        response = client.get('/api/drivers')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['code'] == 200
        assert data['data'] == []
        assert data['msg'] == 'success'
    
    def test_get_drivers_with_data(self, client, sample_drivers):
        """测试获取驾驶员列表"""
        response = client.get('/api/drivers')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['code'] == 200
        assert len(data['data']) == 3
        assert data['msg'] == 'success'
        
        # 验证数据结构
        driver_data = data['data'][0]
        assert 'id' in driver_data
        assert 'name' in driver_data
        assert 'employee_id' in driver_data
        assert 'has_face_feature' in driver_data
        assert 'created_at' in driver_data
    
    def test_create_driver_success(self, client):
        """测试成功创建驾驶员"""
        driver_data = {
            'name': '赵六',
            'employee_id': 'EMP004'
        }
        
        response = client.post('/api/drivers', 
                             data=json.dumps(driver_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['code'] == 200
        assert data['data']['name'] == '赵六'
        assert data['data']['employee_id'] == 'EMP004'
        assert data['data']['has_face_feature'] is False
        assert data['msg'] == 'success'
    
    def test_create_driver_missing_name(self, client):
        """测试创建驾驶员缺少姓名"""
        driver_data = {
            'employee_id': 'EMP005'
        }
        
        response = client.post('/api/drivers',
                             data=json.dumps(driver_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert data['code'] == 400
        assert data['data'] is None
        assert '缺少必填字段：name' in data['msg']
    
    def test_create_driver_missing_employee_id(self, client):
        """测试创建驾驶员缺少工号"""
        driver_data = {
            'name': '孙七'
        }
        
        response = client.post('/api/drivers',
                             data=json.dumps(driver_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert data['code'] == 400
        assert data['data'] is None
        assert '缺少必填字段：employee_id' in data['msg']
    
    def test_create_driver_duplicate_employee_id(self, client, sample_drivers):
        """测试创建重复工号的驾驶员"""
        driver_data = {
            'name': '新张三',
            'employee_id': 'EMP001'  # 重复工号
        }
        
        response = client.post('/api/drivers',
                             data=json.dumps(driver_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert data['code'] == 400
        assert data['data'] is None
        assert 'EMP001 已存在' in data['msg']
    
    def test_create_driver_invalid_json(self, client):
        """测试创建驾驶员时提供无效JSON"""
        response = client.post('/api/drivers',
                             data='invalid json',
                             content_type='application/json')
        
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert data['code'] == 400
        assert data['data'] is None
        assert '请求体格式错误' in data['msg']
    
    def test_delete_driver_success(self, client, sample_drivers):
        """测试成功删除驾驶员"""
        driver_id = sample_drivers[0]
        
        response = client.delete(f'/api/drivers/{driver_id}')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['code'] == 200
        assert data['data'] is None
        assert data['msg'] == '删除成功'
    
    def test_delete_driver_not_found(self, client):
        """测试删除不存在的驾驶员"""
        response = client.delete('/api/drivers/999')
        
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert data['code'] == 404
        assert data['data'] is None
        assert '驾驶员 ID 999 不存在' in data['msg']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])