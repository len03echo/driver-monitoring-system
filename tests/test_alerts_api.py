"""
告警记录 API 测试

测试 /api/alerts 相关接口的功能。

依赖：
- pytest
- Flask
- SQLAlchemy
"""

import pytest
import sys
import os
import json
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from server.app import create_app
from server.models.models import db, Driver, Session, AlertRecord, AlertTypeEnum, SeverityEnum


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
def sample_data(app):
    """创建示例数据"""
    with app.app_context():
        # 创建驾驶员
        driver1 = Driver(name="张三", employee_id="EMP001")
        driver2 = Driver(name="李四", employee_id="EMP002")
        db.session.add(driver1)
        db.session.add(driver2)
        db.session.commit()
        
        # 创建会话
        session1 = Session(driver_id=driver1.id)
        session2 = Session(driver_id=driver2.id)
        db.session.add(session1)
        db.session.add(session2)
        db.session.commit()
        
        # 创建告警记录
        alerts = [
            AlertRecord(
                driver_id=driver1.id,
                session_id=session1.id,
                alert_type=AlertTypeEnum.PHONE,
                severity=SeverityEnum.MEDIUM,
                snapshot_path="1_phone_20240117142035.jpg",
                created_at=datetime.now() - timedelta(days=1)
            ),
            AlertRecord(
                driver_id=driver1.id,
                session_id=session1.id,
                alert_type=AlertTypeEnum.SMOKING,
                severity=SeverityEnum.HIGH,
                snapshot_path="1_smoking_20240117142136.jpg",
                created_at=datetime.now() - timedelta(hours=2)
            ),
            AlertRecord(
                driver_id=driver2.id,
                session_id=session2.id,
                alert_type=AlertTypeEnum.EYE_CLOSED,
                severity=SeverityEnum.HIGH,
                snapshot_path="2_eye_closed_20240117142237.jpg",
                created_at=datetime.now() - timedelta(hours=1)
            )
        ]
        
        for alert in alerts:
            db.session.add(alert)
        
        db.session.commit()
        
        # 返回ID而不是对象，避免DetachedInstanceError
        return {
            'driver_ids': [driver1.id, driver2.id],
            'session_ids': [session1.id, session2.id],
            'alert_ids': [alert.id for alert in alerts]
        }


class TestAlertsAPI:
    """测试告警记录 API"""
    
    def test_get_alerts_empty(self, client):
        """测试获取空告警记录列表"""
        response = client.get('/api/alerts')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['code'] == 200
        assert data['data']['total'] == 0
        assert data['data']['page'] == 1
        assert data['data']['page_size'] == 20
        assert data['data']['items'] == []
        assert data['msg'] == 'success'
    
    def test_get_alerts_with_data(self, client, sample_data):
        """测试获取告警记录列表"""
        response = client.get('/api/alerts')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['code'] == 200
        assert data['data']['total'] == 3
        assert data['data']['page'] == 1
        assert data['data']['page_size'] == 20
        assert len(data['data']['items']) == 3
        assert data['msg'] == 'success'
        
        # 验证数据结构
        alert_data = data['data']['items'][0]
        assert 'id' in alert_data
        assert 'driver_id' in alert_data
        assert 'driver_name' in alert_data
        assert 'session_id' in alert_data
        assert 'alert_type' in alert_data
        assert 'severity' in alert_data
        assert 'snapshot_path' in alert_data
        assert 'snapshot_url' in alert_data
        assert 'created_at' in alert_data
    
    def test_get_alerts_with_pagination(self, client, sample_data):
        """测试分页功能"""
        response = client.get('/api/alerts?page=1&page_size=2')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['code'] == 200
        assert data['data']['total'] == 3
        assert data['data']['page'] == 1
        assert data['data']['page_size'] == 2
        assert len(data['data']['items']) == 2
    
    def test_get_alerts_filter_by_alert_type(self, client, sample_data):
        """测试按告警类型筛选"""
        response = client.get('/api/alerts?alert_type=phone')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['code'] == 200
        assert data['data']['total'] == 1
        assert data['data']['items'][0]['alert_type'] == 'phone'
    
    def test_get_alerts_filter_by_severity(self, client, sample_data):
        """测试按危险等级筛选"""
        response = client.get('/api/alerts?severity=high')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['code'] == 200
        assert data['data']['total'] == 2
        
        # 验证所有返回的记录都是 high 等级
        for item in data['data']['items']:
            assert item['severity'] == 'high'
    
    def test_get_alerts_filter_by_driver_id(self, client, sample_data):
        """测试按驾驶员ID筛选"""
        driver_id = sample_data['driver_ids'][0]
        response = client.get(f'/api/alerts?driver_id={driver_id}')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['code'] == 200
        assert data['data']['total'] == 2
        
        # 验证所有返回的记录都属于指定驾驶员
        for item in data['data']['items']:
            assert item['driver_id'] == driver_id
    
    def test_get_alerts_filter_by_date_range(self, client, sample_data):
        """测试按日期范围筛选"""
        today = datetime.now().date()
        yesterday = (datetime.now() - timedelta(days=1)).date()
        
        response = client.get(f'/api/alerts?start_date={today}&end_date={today}')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['code'] == 200
        # 应该只返回今天的告警记录（2条）
        assert data['data']['total'] == 2
    
    def test_get_alerts_invalid_severity(self, client):
        """测试无效的危险等级参数"""
        response = client.get('/api/alerts?severity=invalid')
        
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert data['code'] == 400
        assert data['data'] is None
        assert 'severity 参数值非法' in data['msg']
    
    def test_get_alerts_invalid_date_format(self, client):
        """测试无效的日期格式"""
        response = client.get('/api/alerts?start_date=invalid-date')
        
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert data['code'] == 400
        assert data['data'] is None
        assert '无效的开始日期格式' in data['msg']
    
    def test_snapshot_url_generation(self, client, sample_data):
        """测试截图URL生成"""
        response = client.get('/api/alerts')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        alert_with_snapshot = None
        
        for item in data['data']['items']:
            if item['snapshot_path']:
                alert_with_snapshot = item
                break
        
        assert alert_with_snapshot is not None
        assert alert_with_snapshot['snapshot_url'] == f"/snapshots/{alert_with_snapshot['snapshot_path']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])