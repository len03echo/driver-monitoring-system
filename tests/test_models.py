"""
SQLAlchemy 数据模型测试

测试 Driver、Session、AlertRecord 模型的字段、关系、约束。

依赖：
- pytest
- Flask
- SQLAlchemy
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
import numpy as np

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask
from server.models.models import db, Driver, Session, AlertRecord, AlertTypeEnum, SeverityEnum


@pytest.fixture
def app():
    """创建测试 Flask 应用"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # 使用内存数据库
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True
    
    # 初始化数据库
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def db_session(app):
    """获取数据库会话"""
    with app.app_context():
        yield db.session


class TestDriverModel:
    """测试 Driver 模型"""
    
    def test_create_driver(self, db_session):
        """测试创建驾驶员"""
        driver = Driver(
            name="张三",
            employee_id="EMP001"
        )
        db_session.add(driver)
        db_session.commit()
        
        assert driver.id is not None
        assert driver.name == "张三"
        assert driver.employee_id == "EMP001"
        assert driver.created_at is not None
        assert driver.face_feature is None
        assert driver.avatar_path is None
    
    def test_driver_unique_employee_id(self, db_session):
        """测试工号唯一约束"""
        driver1 = Driver(name="张三", employee_id="EMP001")
        db_session.add(driver1)
        db_session.commit()
        
        # 尝试创建相同工号的驾驶员
        driver2 = Driver(name="李四", employee_id="EMP001")
        db_session.add(driver2)
        
        with pytest.raises(Exception):  # 应该抛出唯一约束异常
            db_session.commit()
    
    def test_driver_with_face_feature(self, db_session):
        """测试带人脸特征的驾驶员"""
        # 模拟 512 维人脸特征向量
        face_feature = np.random.rand(512).astype(np.float32).tobytes()
        
        driver = Driver(
            name="王五",
            employee_id="EMP002",
            face_feature=face_feature,
            avatar_path="avatars/emp002.jpg"
        )
        db_session.add(driver)
        db_session.commit()
        
        assert driver.face_feature is not None
        assert len(driver.face_feature) == 512 * 4  # 512 个 float32
        assert driver.avatar_path == "avatars/emp002.jpg"
    
    def test_driver_to_dict(self, db_session):
        """测试 to_dict 方法"""
        driver = Driver(name="赵六", employee_id="EMP003")
        db_session.add(driver)
        db_session.commit()
        
        driver_dict = driver.to_dict()
        
        assert driver_dict['id'] == driver.id
        assert driver_dict['name'] == "赵六"
        assert driver_dict['employee_id'] == "EMP003"
        assert driver_dict['has_face_feature'] is False
        assert 'created_at' in driver_dict
    
    def test_driver_repr(self, db_session):
        """测试 __repr__ 方法"""
        driver = Driver(name="孙七", employee_id="EMP004")
        db_session.add(driver)
        db_session.commit()
        
        repr_str = repr(driver)
        assert "EMP004" in repr_str
        assert "孙七" in repr_str


class TestSessionModel:
    """测试 Session 模型"""
    
    def test_create_session(self, db_session):
        """测试创建会话"""
        # 先创建驾驶员
        driver = Driver(name="张三", employee_id="EMP001")
        db_session.add(driver)
        db_session.commit()
        
        # 创建会话
        session = Session(driver_id=driver.id)
        db_session.add(session)
        db_session.commit()
        
        assert session.id is not None
        assert session.driver_id == driver.id
        assert session.start_time is not None
        assert session.end_time is None
        assert session.total_alerts == 0
    
    def test_session_with_end_time(self, db_session):
        """测试带结束时间的会话"""
        driver = Driver(name="李四", employee_id="EMP002")
        db_session.add(driver)
        db_session.commit()
        
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=2)
        
        session = Session(
            driver_id=driver.id,
            start_time=start_time,
            end_time=end_time,
            total_alerts=5
        )
        db_session.add(session)
        db_session.commit()
        
        assert session.end_time is not None
        assert session.total_alerts == 5
    
    def test_session_driver_relationship(self, db_session):
        """测试会话与驾驶员的关系"""
        driver = Driver(name="王五", employee_id="EMP003")
        db_session.add(driver)
        db_session.commit()
        
        session = Session(driver_id=driver.id)
        db_session.add(session)
        db_session.commit()
        
        # 测试关系
        assert session.driver.name == "王五"
        assert driver.sessions[0].id == session.id
    
    def test_session_cascade_delete(self, db_session):
        """测试级联删除"""
        driver = Driver(name="赵六", employee_id="EMP004")
        db_session.add(driver)
        db_session.commit()
        
        session = Session(driver_id=driver.id)
        db_session.add(session)
        db_session.commit()
        
        session_id = session.id
        
        # 删除驾驶员
        db_session.delete(driver)
        db_session.commit()
        
        # 会话应该被级联删除
        deleted_session = db_session.get(Session, session_id)
        assert deleted_session is None
    
    def test_session_to_dict(self, db_session):
        """测试 to_dict 方法"""
        driver = Driver(name="孙七", employee_id="EMP005")
        db_session.add(driver)
        db_session.commit()
        
        session = Session(driver_id=driver.id, total_alerts=3)
        db_session.add(session)
        db_session.commit()
        
        session_dict = session.to_dict()
        
        assert session_dict['id'] == session.id
        assert session_dict['driver_id'] == driver.id
        assert session_dict['driver_name'] == "孙七"
        assert session_dict['total_alerts'] == 3
        assert session_dict['is_active'] is True  # end_time 为 None


class TestAlertRecordModel:
    """测试 AlertRecord 模型"""
    
    def test_create_alert_record(self, db_session):
        """测试创建告警记录"""
        # 创建驾驶员和会话
        driver = Driver(name="张三", employee_id="EMP001")
        db_session.add(driver)
        db_session.commit()
        
        session = Session(driver_id=driver.id)
        db_session.add(session)
        db_session.commit()
        
        # 创建告警记录
        alert = AlertRecord(
            driver_id=driver.id,
            session_id=session.id,
            alert_type=AlertTypeEnum.PHONE,
            severity=SeverityEnum.HIGH
        )
        db_session.add(alert)
        db_session.commit()
        
        assert alert.id is not None
        assert alert.driver_id == driver.id
        assert alert.session_id == session.id
        assert alert.alert_type == AlertTypeEnum.PHONE
        assert alert.severity == SeverityEnum.HIGH
        assert alert.created_at is not None
    
    def test_alert_all_types(self, db_session):
        """测试所有告警类型"""
        driver = Driver(name="李四", employee_id="EMP002")
        db_session.add(driver)
        db_session.commit()
        
        session = Session(driver_id=driver.id)
        db_session.add(session)
        db_session.commit()
        
        alert_types = [
            AlertTypeEnum.PHONE,
            AlertTypeEnum.CUP,
            AlertTypeEnum.SMOKING,
            AlertTypeEnum.EYE_CLOSED,
            AlertTypeEnum.YAWNING,
            AlertTypeEnum.HEAD_DOWN,
            AlertTypeEnum.UNKNOWN
        ]
        
        for alert_type in alert_types:
            alert = AlertRecord(
                driver_id=driver.id,
                session_id=session.id,
                alert_type=alert_type,
                severity=SeverityEnum.MEDIUM
            )
            db_session.add(alert)
        
        db_session.commit()
        
        # 验证所有告警都已创建
        alerts = db_session.query(AlertRecord).filter_by(session_id=session.id).all()
        assert len(alerts) == 7
    
    def test_alert_all_severities(self, db_session):
        """测试所有危险等级"""
        driver = Driver(name="王五", employee_id="EMP003")
        db_session.add(driver)
        db_session.commit()
        
        session = Session(driver_id=driver.id)
        db_session.add(session)
        db_session.commit()
        
        severities = [SeverityEnum.LOW, SeverityEnum.MEDIUM, SeverityEnum.HIGH]
        
        for severity in severities:
            alert = AlertRecord(
                driver_id=driver.id,
                session_id=session.id,
                alert_type=AlertTypeEnum.PHONE,
                severity=severity
            )
            db_session.add(alert)
        
        db_session.commit()
        
        alerts = db_session.query(AlertRecord).filter_by(session_id=session.id).all()
        assert len(alerts) == 3
    
    def test_alert_with_snapshot(self, db_session):
        """测试带截图的告警"""
        driver = Driver(name="赵六", employee_id="EMP004")
        db_session.add(driver)
        db_session.commit()
        
        session = Session(driver_id=driver.id)
        db_session.add(session)
        db_session.commit()
        
        alert = AlertRecord(
            driver_id=driver.id,
            session_id=session.id,
            alert_type=AlertTypeEnum.SMOKING,
            severity=SeverityEnum.HIGH,
            snapshot_path="snapshots/1_smoking_20240101120000.jpg"
        )
        db_session.add(alert)
        db_session.commit()
        
        assert alert.snapshot_path is not None
        assert "smoking" in alert.snapshot_path
    
    def test_alert_relationships(self, db_session):
        """测试告警记录的关系"""
        driver = Driver(name="孙七", employee_id="EMP005")
        db_session.add(driver)
        db_session.commit()
        
        session = Session(driver_id=driver.id)
        db_session.add(session)
        db_session.commit()
        
        alert = AlertRecord(
            driver_id=driver.id,
            session_id=session.id,
            alert_type=AlertTypeEnum.YAWNING,
            severity=SeverityEnum.MEDIUM
        )
        db_session.add(alert)
        db_session.commit()
        
        # 测试关系
        assert alert.driver.name == "孙七"
        assert alert.session.id == session.id
        assert driver.alert_records[0].id == alert.id
        assert session.alert_records[0].id == alert.id
    
    def test_alert_cascade_delete_driver(self, db_session):
        """测试删除驾驶员时级联删除告警"""
        driver = Driver(name="周八", employee_id="EMP006")
        db_session.add(driver)
        db_session.commit()
        
        session = Session(driver_id=driver.id)
        db_session.add(session)
        db_session.commit()
        
        alert = AlertRecord(
            driver_id=driver.id,
            session_id=session.id,
            alert_type=AlertTypeEnum.PHONE,
            severity=SeverityEnum.HIGH
        )
        db_session.add(alert)
        db_session.commit()
        
        alert_id = alert.id
        
        # 删除驾驶员
        db_session.delete(driver)
        db_session.commit()
        
        # 告警应该被级联删除
        deleted_alert = db_session.get(AlertRecord, alert_id)
        assert deleted_alert is None
    
    def test_alert_cascade_delete_session(self, db_session):
        """测试删除会话时级联删除告警"""
        driver = Driver(name="吴九", employee_id="EMP007")
        db_session.add(driver)
        db_session.commit()
        
        session = Session(driver_id=driver.id)
        db_session.add(session)
        db_session.commit()
        
        alert = AlertRecord(
            driver_id=driver.id,
            session_id=session.id,
            alert_type=AlertTypeEnum.CUP,
            severity=SeverityEnum.LOW
        )
        db_session.add(alert)
        db_session.commit()
        
        alert_id = alert.id
        
        # 删除会话
        db_session.delete(session)
        db_session.commit()
        
        # 告警应该被级联删除
        deleted_alert = db_session.get(AlertRecord, alert_id)
        assert deleted_alert is None
    
    def test_alert_to_dict(self, db_session):
        """测试 to_dict 方法"""
        driver = Driver(name="郑十", employee_id="EMP008")
        db_session.add(driver)
        db_session.commit()
        
        session = Session(driver_id=driver.id)
        db_session.add(session)
        db_session.commit()
        
        alert = AlertRecord(
            driver_id=driver.id,
            session_id=session.id,
            alert_type=AlertTypeEnum.HEAD_DOWN,
            severity=SeverityEnum.MEDIUM,
            snapshot_path="snapshots/test.jpg"
        )
        db_session.add(alert)
        db_session.commit()
        
        alert_dict = alert.to_dict()
        
        assert alert_dict['id'] == alert.id
        assert alert_dict['driver_id'] == driver.id
        assert alert_dict['driver_name'] == "郑十"
        assert alert_dict['session_id'] == session.id
        assert alert_dict['alert_type'] == 'head_down'
        assert alert_dict['severity'] == 'medium'
        assert alert_dict['snapshot_path'] == "snapshots/test.jpg"
        assert 'created_at' in alert_dict


class TestEnums:
    """测试枚举类型"""
    
    def test_alert_type_enum_values(self):
        """测试告警类型枚举值"""
        expected_values = ['phone', 'cup', 'smoking', 'eye_closed', 'yawning', 'head_down', 'unknown']
        actual_values = [e.value for e in AlertTypeEnum]
        
        assert set(actual_values) == set(expected_values)
    
    def test_severity_enum_values(self):
        """测试危险等级枚举值"""
        expected_values = ['low', 'medium', 'high']
        actual_values = [e.value for e in SeverityEnum]
        
        assert set(actual_values) == set(expected_values)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
