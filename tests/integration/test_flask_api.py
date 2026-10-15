"""
Task-32：Flask API 集成测试

测试 Flask API 全部接口的端到端功能，使用 SQLite 内存数据库。
验证路由、服务层、数据库操作的完整链路。
"""

import pytest
import json
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from server.models.models import db, Driver, Session, AlertRecord, AlertTypeEnum, SeverityEnum


@pytest.fixture(scope='module')
def app():
    """创建集成测试 Flask 应用（模块级，所有测试共享）"""
    from flask import Flask
    from flask_cors import CORS
    from server.routes import drivers_bp, alerts_bp, stats_bp, snapshots_bp

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JSON_AS_ASCII'] = False

    db.init_app(app)
    CORS(app)
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
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app):
    """每个测试前清空数据库"""
    with app.app_context():
        db.session.query(AlertRecord).delete()
        db.session.query(Session).delete()
        db.session.query(Driver).delete()
        db.session.commit()
    yield


@pytest.fixture
def seed_data(app):
    """插入标准测试数据，返回 ID 字典"""
    with app.app_context():
        d1 = Driver(name="张三", employee_id="EMP001")
        d2 = Driver(name="李四", employee_id="EMP002")
        db.session.add_all([d1, d2])
        db.session.commit()

        s1 = Session(driver_id=d1.id, start_time=datetime.now())
        s2 = Session(driver_id=d2.id, start_time=datetime.now() - timedelta(days=1))
        db.session.add_all([s1, s2])
        db.session.commit()

        alerts = [
            AlertRecord(driver_id=d1.id, session_id=s1.id,
                        alert_type=AlertTypeEnum.PHONE, severity=SeverityEnum.MEDIUM,
                        snapshot_path="1_phone_20240117142035.jpg",
                        created_at=datetime.now()),
            AlertRecord(driver_id=d1.id, session_id=s1.id,
                        alert_type=AlertTypeEnum.SMOKING, severity=SeverityEnum.HIGH,
                        created_at=datetime.now()),
            AlertRecord(driver_id=d2.id, session_id=s2.id,
                        alert_type=AlertTypeEnum.EYE_CLOSED, severity=SeverityEnum.HIGH,
                        created_at=datetime.now() - timedelta(days=1)),
        ]
        db.session.add_all(alerts)
        db.session.commit()

        return {
            'driver1_id': d1.id,
            'driver2_id': d2.id,
            'session1_id': s1.id,
            'session2_id': s2.id,
        }


# ============================================================
# 驾驶员档案 API 集成测试
# ============================================================

class TestDriversAPIIntegration:
    """驾驶员档案 API 端到端测试"""

    def test_full_driver_lifecycle(self, client):
        """完整生命周期：创建 → 查询 → 删除"""
        # 1. 创建驾驶员
        resp = client.post('/api/drivers',
                           data=json.dumps({'name': '王五', 'employee_id': 'EMP003'}),
                           content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['code'] == 200
        driver_id = data['data']['id']

        # 2. 查询列表，确认存在
        resp = client.get('/api/drivers')
        data = json.loads(resp.data)
        assert data['code'] == 200
        ids = [d['id'] for d in data['data']]
        assert driver_id in ids

        # 3. 删除驾驶员
        resp = client.delete(f'/api/drivers/{driver_id}')
        data = json.loads(resp.data)
        assert data['code'] == 200

        # 4. 确认已删除
        resp = client.get('/api/drivers')
        data = json.loads(resp.data)
        ids = [d['id'] for d in data['data']]
        assert driver_id not in ids

    def test_duplicate_employee_id_rejected(self, client):
        """重复工号应被拒绝"""
        payload = {'name': '张三', 'employee_id': 'EMP_DUP'}
        client.post('/api/drivers', data=json.dumps(payload), content_type='application/json')
        resp = client.post('/api/drivers', data=json.dumps(payload), content_type='application/json')
        data = json.loads(resp.data)
        assert data['code'] == 400
        assert 'EMP_DUP' in data['msg']

    def test_delete_nonexistent_driver(self, client):
        """删除不存在的驾驶员应返回 404"""
        resp = client.delete('/api/drivers/99999')
        data = json.loads(resp.data)
        assert data['code'] == 404

    def test_create_driver_missing_fields(self, client):
        """缺少必填字段应返回 400"""
        resp = client.post('/api/drivers',
                           data=json.dumps({'name': '张三'}),
                           content_type='application/json')
        data = json.loads(resp.data)
        assert data['code'] == 400

    def test_get_drivers_returns_list(self, client, seed_data):
        """获取驾驶员列表应返回数组"""
        resp = client.get('/api/drivers')
        data = json.loads(resp.data)
        assert data['code'] == 200
        assert isinstance(data['data'], list)
        assert len(data['data']) == 2

    def test_driver_response_fields(self, client):
        """驾驶员响应应包含所有必要字段"""
        client.post('/api/drivers',
                    data=json.dumps({'name': '测试', 'employee_id': 'EMP_FIELD'}),
                    content_type='application/json')
        resp = client.get('/api/drivers')
        data = json.loads(resp.data)
        driver = data['data'][0]
        assert 'id' in driver
        assert 'name' in driver
        assert 'employee_id' in driver
        assert 'has_face_feature' in driver
        assert 'created_at' in driver
        assert driver['has_face_feature'] is False  # Web 端新增无人脸特征


# ============================================================
# 告警记录 API 集成测试
# ============================================================

class TestAlertsAPIIntegration:
    """告警记录 API 端到端测试"""

    def test_get_alerts_with_data(self, client, seed_data):
        """获取告警记录应返回正确数量"""
        resp = client.get('/api/alerts')
        data = json.loads(resp.data)
        assert data['code'] == 200
        assert data['data']['total'] == 3
        assert len(data['data']['items']) == 3

    def test_pagination_page1(self, client, seed_data):
        """第1页每页2条应返回2条"""
        resp = client.get('/api/alerts?page=1&page_size=2')
        data = json.loads(resp.data)
        assert data['code'] == 200
        assert data['data']['total'] == 3
        assert len(data['data']['items']) == 2

    def test_pagination_page2(self, client, seed_data):
        """第2页每页2条应返回1条"""
        resp = client.get('/api/alerts?page=2&page_size=2')
        data = json.loads(resp.data)
        assert data['code'] == 200
        assert len(data['data']['items']) == 1

    def test_filter_by_alert_type(self, client, seed_data):
        """按告警类型筛选"""
        resp = client.get('/api/alerts?alert_type=phone')
        data = json.loads(resp.data)
        assert data['code'] == 200
        assert data['data']['total'] == 1
        assert data['data']['items'][0]['alert_type'] == 'phone'

    def test_filter_by_severity(self, client, seed_data):
        """按危险等级筛选"""
        resp = client.get('/api/alerts?severity=high')
        data = json.loads(resp.data)
        assert data['code'] == 200
        assert data['data']['total'] == 2
        for item in data['data']['items']:
            assert item['severity'] == 'high'

    def test_filter_by_driver_id(self, client, seed_data):
        """按驾驶员 ID 筛选"""
        driver_id = seed_data['driver1_id']
        resp = client.get(f'/api/alerts?driver_id={driver_id}')
        data = json.loads(resp.data)
        assert data['code'] == 200
        assert data['data']['total'] == 2
        for item in data['data']['items']:
            assert item['driver_id'] == driver_id

    def test_filter_by_date_range(self, client, seed_data):
        """按日期范围筛选"""
        today = datetime.now().strftime('%Y-%m-%d')
        resp = client.get(f'/api/alerts?start_date={today}&end_date={today}')
        data = json.loads(resp.data)
        assert data['code'] == 200
        assert data['data']['total'] == 2  # 今日2条

    def test_invalid_severity_returns_400(self, client):
        """无效 severity 参数应返回 400"""
        resp = client.get('/api/alerts?severity=invalid')
        data = json.loads(resp.data)
        assert data['code'] == 400

    def test_alert_response_fields(self, client, seed_data):
        """告警记录响应应包含所有必要字段"""
        resp = client.get('/api/alerts')
        data = json.loads(resp.data)
        item = data['data']['items'][0]
        required_fields = ['id', 'driver_id', 'driver_name', 'session_id',
                           'alert_type', 'severity', 'snapshot_path',
                           'snapshot_url', 'created_at']
        for field in required_fields:
            assert field in item, f"响应缺少字段: {field}"

    def test_snapshot_url_format(self, client, seed_data):
        """有截图的告警记录 snapshot_url 格式应正确"""
        resp = client.get('/api/alerts')
        data = json.loads(resp.data)
        for item in data['data']['items']:
            if item['snapshot_path']:
                assert item['snapshot_url'] == f"/snapshots/{item['snapshot_path']}"


# ============================================================
# 统计数据 API 集成测试
# ============================================================

class TestStatsAPIIntegration:
    """统计数据 API 端到端测试"""

    def test_overview_empty(self, client):
        """空数据库概览统计应全为 0"""
        resp = client.get('/api/stats/overview')
        data = json.loads(resp.data)
        assert data['code'] == 200
        assert data['data']['today_alerts'] == 0
        assert data['data']['total_drivers'] == 0
        assert data['data']['today_sessions'] == 0

    def test_overview_with_data(self, client, seed_data):
        """有数据时概览统计应正确"""
        resp = client.get('/api/stats/overview')
        data = json.loads(resp.data)
        assert data['code'] == 200
        assert data['data']['total_drivers'] == 2
        assert data['data']['today_alerts'] == 2   # 今日2条
        assert data['data']['today_sessions'] == 1  # 今日1个会话

    def test_trend_returns_7_days(self, client):
        """趋势统计应固定返回7天数据"""
        resp = client.get('/api/stats/trend')
        data = json.loads(resp.data)
        assert data['code'] == 200
        assert len(data['data']) == 7

    def test_trend_sorted_ascending(self, client):
        """趋势数据应按日期升序排列"""
        resp = client.get('/api/stats/trend')
        data = json.loads(resp.data)
        dates = [item['date'] for item in data['data']]
        assert dates == sorted(dates), "趋势数据应按日期升序"

    def test_trend_has_required_fields(self, client):
        """趋势数据每条应包含 date 和 count 字段"""
        resp = client.get('/api/stats/trend')
        data = json.loads(resp.data)
        for item in data['data']:
            assert 'date' in item
            assert 'count' in item
            assert isinstance(item['count'], int)

    def test_type_distribution_empty(self, client):
        """空数据库类型分布应返回空列表"""
        resp = client.get('/api/stats/type')
        data = json.loads(resp.data)
        assert data['code'] == 200
        assert data['data'] == []

    def test_type_distribution_with_data(self, client, seed_data):
        """有数据时类型分布应正确"""
        resp = client.get('/api/stats/type')
        data = json.loads(resp.data)
        assert data['code'] == 200
        assert len(data['data']) > 0
        # 验证按数量降序
        counts = [item['count'] for item in data['data']]
        assert counts == sorted(counts, reverse=True)

    def test_type_distribution_fields(self, client, seed_data):
        """类型分布每条应包含 alert_type 和 count 字段"""
        resp = client.get('/api/stats/type')
        data = json.loads(resp.data)
        for item in data['data']:
            assert 'alert_type' in item
            assert 'count' in item
            assert item['count'] > 0


# ============================================================
# 跨模块集成测试
# ============================================================

class TestCrossModuleIntegration:
    """跨模块端到端集成测试"""

    def test_create_driver_then_query_alerts(self, client):
        """创建驾驶员后查询告警应返回空"""
        # 创建驾驶员
        resp = client.post('/api/drivers',
                           data=json.dumps({'name': '赵六', 'employee_id': 'EMP006'}),
                           content_type='application/json')
        driver_id = json.loads(resp.data)['data']['id']

        # 查询该驾驶员的告警
        resp = client.get(f'/api/alerts?driver_id={driver_id}')
        data = json.loads(resp.data)
        assert data['code'] == 200
        assert data['data']['total'] == 0

    def test_delete_driver_cascades(self, client, app):
        """删除驾驶员后相关告警记录应级联删除（通过 API 验证）"""
        # 创建驾驶员
        resp = client.post('/api/drivers',
                           data=json.dumps({'name': '级联测试', 'employee_id': 'EMP_CASCADE'}),
                           content_type='application/json')
        driver_id = json.loads(resp.data)['data']['id']

        # 在数据库中直接插入告警记录
        with app.app_context():
            session = Session(driver_id=driver_id)
            db.session.add(session)
            db.session.commit()
            alert = AlertRecord(
                driver_id=driver_id,
                session_id=session.id,
                alert_type=AlertTypeEnum.PHONE,
                severity=SeverityEnum.MEDIUM
            )
            db.session.add(alert)
            db.session.commit()

        # 确认告警存在
        resp = client.get(f'/api/alerts?driver_id={driver_id}')
        assert json.loads(resp.data)['data']['total'] == 1

        # 删除驾驶员
        client.delete(f'/api/drivers/{driver_id}')

        # 确认告警已级联删除
        resp = client.get(f'/api/alerts?driver_id={driver_id}')
        assert json.loads(resp.data)['data']['total'] == 0

    def test_stats_reflect_new_data(self, client, app):
        """新增数据后统计数据应实时更新"""
        # 初始状态
        resp = client.get('/api/stats/overview')
        initial_drivers = json.loads(resp.data)['data']['total_drivers']

        # 新增驾驶员
        client.post('/api/drivers',
                    data=json.dumps({'name': '统计测试', 'employee_id': 'EMP_STATS'}),
                    content_type='application/json')

        # 统计应更新
        resp = client.get('/api/stats/overview')
        new_drivers = json.loads(resp.data)['data']['total_drivers']
        assert new_drivers == initial_drivers + 1

    def test_response_format_consistency(self, client):
        """所有接口响应格式应一致"""
        endpoints = [
            '/api/drivers',
            '/api/alerts',
            '/api/stats/overview',
            '/api/stats/trend',
            '/api/stats/type',
        ]
        for endpoint in endpoints:
            resp = client.get(endpoint)
            data = json.loads(resp.data)
            assert 'code' in data, f"{endpoint} 缺少 code"
            assert 'data' in data, f"{endpoint} 缺少 data"
            assert 'msg' in data, f"{endpoint} 缺少 msg"
            assert data['code'] == 200, f"{endpoint} 应返回 200"
            assert data['msg'] == 'success', f"{endpoint} msg 应为 success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
