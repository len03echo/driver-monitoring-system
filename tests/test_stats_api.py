"""
统计数据 API 测试

测试 /api/stats/* 相关接口的功能。

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
def sample_stats_data(app):
    """创建统计测试数据"""
    with app.app_context():
        # 创建驾驶员
        drivers = [
            Driver(name="张三", employee_id="EMP001"),
            Driver(name="李四", employee_id="EMP002"),
            Driver(name="王五", employee_id="EMP003")
        ]
        
        for driver in drivers:
            db.session.add(driver)
        db.session.commit()
        
        # 创建会话（今日和昨日）
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        sessions = [
            # 今日会话
            Session(driver_id=drivers[0].id, start_time=today),
            Session(driver_id=drivers[1].id, start_time=today),
            # 昨日会话
            Session(driver_id=drivers[2].id, start_time=yesterday)
        ]
        
        for session in sessions:
            db.session.add(session)
        db.session.commit()
        
        # 创建告警记录（不同类型和时间）
        alerts = [
            # 今日告警
            AlertRecord(
                driver_id=drivers[0].id,
                session_id=sessions[0].id,
                alert_type=AlertTypeEnum.PHONE,
                severity=SeverityEnum.MEDIUM,
                created_at=today
            ),
            AlertRecord(
                driver_id=drivers[0].id,
                session_id=sessions[0].id,
                alert_type=AlertTypeEnum.PHONE,
                severity=SeverityEnum.HIGH,
                created_at=today
            ),
            AlertRecord(
                driver_id=drivers[1].id,
                session_id=sessions[1].id,
                alert_type=AlertTypeEnum.SMOKING,
                severity=SeverityEnum.HIGH,
                created_at=today
            ),
            # 昨日告警
            AlertRecord(
                driver_id=drivers[2].id,
                session_id=sessions[2].id,
                alert_type=AlertTypeEnum.EYE_CLOSED,
                severity=SeverityEnum.HIGH,
                created_at=yesterday
            ),
            AlertRecord(
                driver_id=drivers[2].id,
                session_id=sessions[2].id,
                alert_type=AlertTypeEnum.YAWNING,
                severity=SeverityEnum.MEDIUM,
                created_at=yesterday
            ),
            # 前天告警
            AlertRecord(
                driver_id=drivers[0].id,
                session_id=sessions[0].id,
                alert_type=AlertTypeEnum.CUP,
                severity=SeverityEnum.LOW,
                created_at=today - timedelta(days=2)
            )
        ]
        
        for alert in alerts:
            db.session.add(alert)
        db.session.commit()
        
        return {
            'drivers': drivers,
            'sessions': sessions,
            'alerts': alerts
        }


class TestStatsAPI:
    """测试统计数据 API"""
    
    def test_get_overview_empty(self, client):
        """测试获取空概览统计"""
        response = client.get('/api/stats/overview')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['code'] == 200
        assert data['data']['today_alerts'] == 0
        assert data['data']['total_drivers'] == 0
        assert data['data']['today_sessions'] == 0
        assert data['msg'] == 'success'
    
    def test_get_overview_with_data(self, client, sample_stats_data):
        """测试获取概览统计"""
        response = client.get('/api/stats/overview')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['code'] == 200
        assert data['data']['today_alerts'] == 3  # 今日告警数
        assert data['data']['total_drivers'] == 3  # 总驾驶员数
        assert data['data']['today_sessions'] == 2  # 今日会话数
        assert data['msg'] == 'success'
    
    def test_get_trend_empty(self, client):
        """测试获取空趋势统计"""
        response = client.get('/api/stats/trend')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['code'] == 200
        assert len(data['data']) == 7  # 固定返回7天数据
        assert data['msg'] == 'success'
        
        # 验证数据结构
        for item in data['data']:
            assert 'date' in item
            assert 'count' in item
            assert item['count'] == 0  # 空数据时count为0
    
    def test_get_trend_with_data(self, client, sample_stats_data):
        """测试获取趋势统计"""
        response = client.get('/api/stats/trend')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['code'] == 200
        assert len(data['data']) == 7  # 固定返回7天数据
        assert data['msg'] == 'success'
        
        # 验证数据按日期升序排列
        dates = [item['date'] for item in data['data']]
        assert dates == sorted(dates)
        
        # 验证今日和昨日有数据
        today_str = datetime.now().strftime('%Y-%m-%d')
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        today_data = next((item for item in data['data'] if item['date'] == today_str), None)
        yesterday_data = next((item for item in data['data'] if item['date'] == yesterday_str), None)
        
        assert today_data is not None
        assert today_data['count'] == 3  # 今日3条告警
        
        assert yesterday_data is not None
        assert yesterday_data['count'] == 2  # 昨日2条告警
    
    def test_get_type_distribution_empty(self, client):
        """测试获取空类型分布统计"""
        response = client.get('/api/stats/type')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['code'] == 200
        assert data['data'] == []  # 空数据时返回空列表
        assert data['msg'] == 'success'
    
    def test_get_type_distribution_with_data(self, client, sample_stats_data):
        """测试获取类型分布统计"""
        response = client.get('/api/stats/type')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['code'] == 200
        assert len(data['data']) > 0
        assert data['msg'] == 'success'
        
        # 验证数据结构
        for item in data['data']:
            assert 'alert_type' in item
            assert 'count' in item
            assert isinstance(item['count'], int)
            assert item['count'] > 0
        
        # 验证按数量降序排列
        counts = [item['count'] for item in data['data']]
        assert counts == sorted(counts, reverse=True)
        
        # 验证具体数据
        phone_data = next((item for item in data['data'] if item['alert_type'] == 'phone'), None)
        assert phone_data is not None
        assert phone_data['count'] == 2  # phone类型有2条记录
    
    def test_stats_api_error_handling(self, client):
        """测试统计API错误处理"""
        # 这里可以通过模拟数据库错误来测试错误处理
        # 由于使用内存数据库，暂时跳过此测试
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])