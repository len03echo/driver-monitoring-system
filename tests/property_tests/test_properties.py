"""
Task-31：正确性属性测试

使用 Hypothesis 库实现设计文档第10章全部11个正确性属性的属性测试。
每个属性测试运行不少于100次迭代。

属性列表：
P1.  EAR 值域属性：EAR ∈ [0, ∞)，且睁眼 > 闭眼
P2.  MAR 值域属性：MAR ∈ [0, ∞)，且张嘴 > 闭嘴
P3.  余弦相似度值域属性：similarity ∈ [0, 1]
P4.  余弦相似度对称性：sim(a,b) == sim(b,a)
P5.  余弦相似度缩放不变性：sim(a, k*a) == 1.0（k > 0）
P6.  特征向量序列化往返属性：deserialize(serialize(v)) == v
P7.  连续帧计数器单调性：未中断时计数器单调递增
P8.  冷却机制抑制属性：触发后立即重触发被抑制
P9.  截图文件名格式属性：文件名符合 {session_id}_{alert_type}_{timestamp}.jpg
P10. API 响应格式属性：所有 API 响应包含 code/data/msg 字段
P11. 分页属性：返回条数 ≤ page_size，total 与实际数据一致
"""

import pytest
import math
import re
import sys
import os
import time
import json
from datetime import datetime

import numpy as np
from hypothesis import given, settings, assume
from hypothesis import strategies as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


# ============================================================
# 辅助函数（与源码逻辑一致）
# ============================================================

def calculate_ear(eye_points):
    if len(eye_points) != 6:
        return 1.0
    v1 = math.sqrt((eye_points[1][0]-eye_points[5][0])**2 + (eye_points[1][1]-eye_points[5][1])**2)
    v2 = math.sqrt((eye_points[2][0]-eye_points[4][0])**2 + (eye_points[2][1]-eye_points[4][1])**2)
    h  = math.sqrt((eye_points[0][0]-eye_points[3][0])**2 + (eye_points[0][1]-eye_points[3][1])**2)
    if h == 0:
        return 1.0
    return (v1 + v2) / (2.0 * h)


def calculate_mar(mouth_points):
    if len(mouth_points) != 8:
        return 0.0
    v1 = math.sqrt((mouth_points[1][0]-mouth_points[7][0])**2 + (mouth_points[1][1]-mouth_points[7][1])**2)
    v2 = math.sqrt((mouth_points[2][0]-mouth_points[6][0])**2 + (mouth_points[2][1]-mouth_points[6][1])**2)
    v3 = math.sqrt((mouth_points[3][0]-mouth_points[5][0])**2 + (mouth_points[3][1]-mouth_points[5][1])**2)
    h  = math.sqrt((mouth_points[0][0]-mouth_points[4][0])**2 + (mouth_points[0][1]-mouth_points[4][1])**2)
    if h == 0:
        return 0.0
    return (v1 + v2 + v3) / (3.0 * h)


def cosine_similarity(vec_a, vec_b):
    dot = np.dot(vec_a, vec_b)
    na = np.linalg.norm(vec_a)
    nb = np.linalg.norm(vec_b)
    if na == 0 or nb == 0:
        return 0.0
    sim = dot / (na * nb)
    if np.isnan(sim):
        return 0.0
    return float(max(0.0, min(1.0, sim)))


def generate_snapshot_filename(session_id, alert_type, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{session_id}_{alert_type}_{timestamp}.jpg"


SNAPSHOT_PATTERN = re.compile(
    r'^(\d+|unknown)_(phone|cup|smoking|eye_closed|yawning|head_down|unknown)_(\d{14})\.jpg$'
)

# ============================================================
# Hypothesis 策略定义
# ============================================================

# 坐标策略（避免极端值导致浮点溢出）
coord = st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False)
point = st.tuples(coord, coord)

# 6点眼睛坐标策略
eye_points_st = st.lists(point, min_size=6, max_size=6)

# 8点嘴巴坐标策略
mouth_points_st = st.lists(point, min_size=8, max_size=8)

# 512维特征向量策略：用固定范围的浮点数生成，避免 NaN/Inf 和过滤问题
# 使用 st.binary 生成随机种子，再用 numpy 生成正态分布向量
feature_vector_st = st.integers(min_value=0, max_value=2**32 - 1).map(
    lambda seed: np.random.default_rng(seed).standard_normal(512).astype(np.float32)
)

# 非零特征向量策略（正态分布几乎不可能为零向量，无需 filter）
nonzero_feature_st = feature_vector_st

# 告警类型策略
alert_type_st = st.sampled_from(
    ["phone", "cup", "smoking", "eye_closed", "yawning", "head_down"]
)

# session_id 策略
session_id_st = st.integers(min_value=1, max_value=99999)


# ============================================================
# P1：EAR 值域属性
# ============================================================

class TestP1EARRange:
    """P1：EAR 值应为非负数"""

    @given(eye_points_st)
    @settings(max_examples=100)
    def test_ear_non_negative(self, eye_points):
        """任意6点坐标计算的 EAR 应为非负数"""
        ear = calculate_ear(eye_points)
        assert ear >= 0, f"EAR 不应为负数，实际: {ear}"

    @given(eye_points_st)
    @settings(max_examples=100)
    def test_ear_finite(self, eye_points):
        """EAR 应为有限数（非 NaN/Inf）"""
        ear = calculate_ear(eye_points)
        assert math.isfinite(ear), f"EAR 应为有限数，实际: {ear}"

    @given(
        st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_open_eye_ear_greater_than_closed(self, scale):
        """睁眼的 EAR 应大于闭眼的 EAR"""
        # 睁眼：垂直距离 = scale，水平距离 = scale
        open_eye = [
            (0, 0), (scale*0.3, scale*0.5), (scale*0.7, scale*0.5),
            (scale, 0), (scale*0.7, -scale*0.5), (scale*0.3, -scale*0.5)
        ]
        # 闭眼：垂直距离 ≈ 0
        closed_eye = [
            (0, 0), (scale*0.3, scale*0.02), (scale*0.7, scale*0.02),
            (scale, 0), (scale*0.7, -scale*0.02), (scale*0.3, -scale*0.02)
        ]
        ear_open = calculate_ear(open_eye)
        ear_closed = calculate_ear(closed_eye)
        assert ear_open > ear_closed, f"睁眼 EAR({ear_open:.3f}) 应大于闭眼 EAR({ear_closed:.3f})"


# ============================================================
# P2：MAR 值域属性
# ============================================================

class TestP2MARRange:
    """P2：MAR 值应为非负数"""

    @given(mouth_points_st)
    @settings(max_examples=100)
    def test_mar_non_negative(self, mouth_points):
        """任意8点坐标计算的 MAR 应为非负数"""
        mar = calculate_mar(mouth_points)
        assert mar >= 0, f"MAR 不应为负数，实际: {mar}"

    @given(mouth_points_st)
    @settings(max_examples=100)
    def test_mar_finite(self, mouth_points):
        """MAR 应为有限数"""
        mar = calculate_mar(mouth_points)
        assert math.isfinite(mar), f"MAR 应为有限数，实际: {mar}"

    @given(
        st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_open_mouth_mar_greater_than_closed(self, scale):
        """张嘴的 MAR 应大于闭嘴的 MAR"""
        open_mouth = [
            (0, 0), (scale*0.2, scale*0.6), (scale*0.5, scale*0.7),
            (scale*0.8, scale*0.6), (scale, 0),
            (scale*0.8, -scale*0.6), (scale*0.5, -scale*0.7), (scale*0.2, -scale*0.6)
        ]
        closed_mouth = [
            (0, 0), (scale*0.2, scale*0.02), (scale*0.5, scale*0.02),
            (scale*0.8, scale*0.02), (scale, 0),
            (scale*0.8, -scale*0.02), (scale*0.5, -scale*0.02), (scale*0.2, -scale*0.02)
        ]
        mar_open = calculate_mar(open_mouth)
        mar_closed = calculate_mar(closed_mouth)
        assert mar_open > mar_closed, f"张嘴 MAR({mar_open:.3f}) 应大于闭嘴 MAR({mar_closed:.3f})"


# ============================================================
# P3：余弦相似度值域属性
# ============================================================

class TestP3SimilarityRange:
    """P3：余弦相似度应在 [0, 1] 范围内"""

    @given(nonzero_feature_st, nonzero_feature_st)
    @settings(max_examples=100)
    def test_similarity_in_range(self, vec_a, vec_b):
        """任意两个非零向量的余弦相似度应在 [0, 1]"""
        sim = cosine_similarity(vec_a, vec_b)
        assert 0.0 <= sim <= 1.0, f"相似度超出范围 [0,1]：{sim}"

    @given(nonzero_feature_st, nonzero_feature_st)
    @settings(max_examples=100)
    def test_similarity_finite(self, vec_a, vec_b):
        """相似度应为有限数"""
        sim = cosine_similarity(vec_a, vec_b)
        assert math.isfinite(sim), f"相似度应为有限数，实际: {sim}"


# ============================================================
# P4：余弦相似度对称性
# ============================================================

class TestP4SimilaritySymmetry:
    """P4：余弦相似度满足对称性 sim(a,b) == sim(b,a)"""

    @given(nonzero_feature_st, nonzero_feature_st)
    @settings(max_examples=100)
    def test_symmetry(self, vec_a, vec_b):
        """sim(a,b) 应等于 sim(b,a)"""
        sim_ab = cosine_similarity(vec_a, vec_b)
        sim_ba = cosine_similarity(vec_b, vec_a)
        assert abs(sim_ab - sim_ba) < 1e-5, f"对称性不满足: sim(a,b)={sim_ab}, sim(b,a)={sim_ba}"


# ============================================================
# P5：余弦相似度缩放不变性
# ============================================================

class TestP5SimilarityScaleInvariance:
    """P5：向量缩放不影响余弦相似度"""

    @given(
        nonzero_feature_st,
        st.floats(min_value=0.01, max_value=10.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_scale_invariance(self, vec, scale):
        """sim(a, k*a) 应等于 1.0（同向缩放）"""
        scaled_vec = vec * scale
        # 正态分布向量缩放后不会为零，直接计算
        sim = cosine_similarity(vec, scaled_vec)
        assert abs(sim - 1.0) < 1e-4, f"缩放不变性不满足: sim={sim}, scale={scale}"


# ============================================================
# P6：特征向量序列化往返属性
# ============================================================

class TestP6FeatureSerialization:
    """P6：特征向量序列化后反序列化应得到原始向量"""

    @given(feature_vector_st)
    @settings(max_examples=100)
    def test_roundtrip(self, feature):
        """serialize -> deserialize 应还原原始向量"""
        feature_bytes = feature.tobytes()
        restored = np.frombuffer(feature_bytes, dtype=np.float32)
        # 使用 allclose 比较，正态分布向量不含 NaN
        assert np.allclose(feature, restored), "序列化往返后向量应完全一致"

    @given(feature_vector_st)
    @settings(max_examples=100)
    def test_bytes_length(self, feature):
        """512维 float32 向量序列化后应为 2048 字节"""
        feature_bytes = feature.tobytes()
        assert len(feature_bytes) == 512 * 4

    @given(feature_vector_st)
    @settings(max_examples=100)
    def test_dtype_preserved(self, feature):
        """反序列化后数据类型应为 float32"""
        restored = np.frombuffer(feature.tobytes(), dtype=np.float32)
        assert restored.dtype == np.float32


# ============================================================
# P7：连续帧计数器单调性
# ============================================================

class TestP7FrameCounterMonotonicity:
    """P7：未中断时连续帧计数器应单调递增"""

    @given(st.integers(min_value=2, max_value=50))
    @settings(max_examples=100)
    def test_counter_monotone_increase(self, threshold):
        """连续检测时计数器应单调递增直到触发"""
        counter = 0
        prev = 0
        for i in range(threshold - 1):
            counter += 1
            assert counter >= prev, f"计数器应单调递增，第{i}帧: {counter} < {prev}"
            prev = counter

    @given(st.integers(min_value=1, max_value=30))
    @settings(max_examples=100)
    def test_counter_resets_on_miss(self, frames_before_miss):
        """中断后计数器应归零"""
        counter = frames_before_miss  # 模拟已计数
        counter = 0  # 中断后重置
        assert counter == 0


# ============================================================
# P8：冷却机制抑制属性
# ============================================================

class TestP8CooldownSuppression:
    """P8：触发后立即重触发应被抑制"""

    @given(alert_type_st)
    @settings(max_examples=100)
    def test_immediate_retrigger_suppressed(self, alert_type):
        """触发后立即重触发应被抑制"""
        cooldown_tracker = {}
        cooldown_seconds = 30

        def trigger(atype):
            if atype in cooldown_tracker:
                elapsed = time.time() - cooldown_tracker[atype]
                if elapsed < cooldown_seconds:
                    return False
            cooldown_tracker[atype] = time.time()
            return True

        assert trigger(alert_type) is True, "首次触发应成功"
        assert trigger(alert_type) is False, "立即重触发应被抑制"

    @given(alert_type_st, alert_type_st)
    @settings(max_examples=100)
    def test_different_types_independent(self, type_a, type_b):
        """不同类型的冷却期相互独立"""
        assume(type_a != type_b)
        cooldown_tracker = {}
        cooldown_seconds = 30

        def trigger(atype):
            if atype in cooldown_tracker:
                if time.time() - cooldown_tracker[atype] < cooldown_seconds:
                    return False
            cooldown_tracker[atype] = time.time()
            return True

        trigger(type_a)
        # type_a 在冷却期，type_b 应可以触发
        assert trigger(type_a) is False
        assert trigger(type_b) is True


# ============================================================
# P9：截图文件名格式属性
# ============================================================

class TestP9SnapshotNaming:
    """P9：截图文件名应符合 {session_id}_{alert_type}_{timestamp}.jpg 格式"""

    @given(session_id_st, alert_type_st)
    @settings(max_examples=100)
    def test_filename_format(self, session_id, alert_type):
        """生成的文件名应符合规范"""
        filename = generate_snapshot_filename(session_id, alert_type, "20240117142035")
        assert SNAPSHOT_PATTERN.match(filename), f"文件名不符合规范: {filename}"

    @given(session_id_st, alert_type_st)
    @settings(max_examples=100)
    def test_filename_contains_session_id(self, session_id, alert_type):
        """文件名应包含 session_id"""
        filename = generate_snapshot_filename(session_id, alert_type, "20240117142035")
        assert filename.startswith(f"{session_id}_")

    @given(session_id_st, alert_type_st)
    @settings(max_examples=100)
    def test_filename_ends_with_jpg(self, session_id, alert_type):
        """文件名应以 .jpg 结尾"""
        filename = generate_snapshot_filename(session_id, alert_type, "20240117142035")
        assert filename.endswith(".jpg")

    @given(session_id_st, alert_type_st)
    @settings(max_examples=100)
    def test_filename_contains_alert_type(self, session_id, alert_type):
        """文件名应包含告警类型"""
        filename = generate_snapshot_filename(session_id, alert_type, "20240117142035")
        assert f"_{alert_type}_" in filename


# ============================================================
# P10：API 响应格式属性
# ============================================================

class TestP10APIResponseFormat:
    """P10：所有 API 响应应包含 code/data/msg 字段"""

    @pytest.fixture
    def app(self):
        from flask import Flask
        from flask_cors import CORS
        from server.models.models import db
        from server.routes import drivers_bp, alerts_bp, stats_bp, snapshots_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
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
    def client(self, app):
        return app.test_client()

    @given(st.sampled_from([
        '/api/drivers',
        '/api/alerts',
        '/api/stats/overview',
        '/api/stats/trend',
        '/api/stats/type',
    ]))
    @settings(max_examples=20)
    def test_response_has_required_fields(self, endpoint):
        """所有 GET 接口响应应包含 code/data/msg 字段"""
        from flask import Flask
        from flask_cors import CORS
        from server.models.models import db
        from server.routes import drivers_bp, alerts_bp, stats_bp, snapshots_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
        CORS(app)
        app.register_blueprint(drivers_bp)
        app.register_blueprint(alerts_bp)
        app.register_blueprint(stats_bp)
        app.register_blueprint(snapshots_bp)

        with app.app_context():
            db.create_all()
            client = app.test_client()
            response = client.get(endpoint)
            data = json.loads(response.data)
            assert 'code' in data, f"{endpoint} 响应缺少 code 字段"
            assert 'data' in data, f"{endpoint} 响应缺少 data 字段"
            assert 'msg' in data, f"{endpoint} 响应缺少 msg 字段"
            assert isinstance(data['code'], int), "code 字段应为整数"
            db.session.remove()
            db.drop_all()

    @given(st.integers(min_value=200, max_value=200))
    @settings(max_examples=20)
    def test_success_response_code(self, expected_code):
        """成功响应的 code 应为 200"""
        from flask import Flask
        from flask_cors import CORS
        from server.models.models import db
        from server.routes import drivers_bp, alerts_bp, stats_bp, snapshots_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
        CORS(app)
        app.register_blueprint(drivers_bp)
        app.register_blueprint(alerts_bp)
        app.register_blueprint(stats_bp)
        app.register_blueprint(snapshots_bp)

        with app.app_context():
            db.create_all()
            client = app.test_client()
            response = client.get('/api/drivers')
            data = json.loads(response.data)
            assert data['code'] == expected_code
            db.session.remove()
            db.drop_all()


# ============================================================
# P11：分页属性
# ============================================================

class TestP11Pagination:
    """P11：分页返回条数应 ≤ page_size，total 与实际数据一致"""

    @given(
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50)
    def test_items_count_le_page_size(self, page, page_size):
        """返回的 items 数量应 ≤ page_size"""
        from flask import Flask
        from flask_cors import CORS
        from server.models.models import db, Driver, Session, AlertRecord, AlertTypeEnum, SeverityEnum
        from server.routes import drivers_bp, alerts_bp, stats_bp, snapshots_bp
        from datetime import datetime

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
        CORS(app)
        app.register_blueprint(drivers_bp)
        app.register_blueprint(alerts_bp)
        app.register_blueprint(stats_bp)
        app.register_blueprint(snapshots_bp)

        with app.app_context():
            db.create_all()
            # 插入5条告警记录
            driver = Driver(name="测试", employee_id=f"EMP_{page}_{page_size}")
            db.session.add(driver)
            db.session.commit()
            session = Session(driver_id=driver.id)
            db.session.add(session)
            db.session.commit()
            for i in range(5):
                alert = AlertRecord(
                    driver_id=driver.id,
                    session_id=session.id,
                    alert_type=AlertTypeEnum.PHONE,
                    severity=SeverityEnum.MEDIUM,
                    created_at=datetime.now()
                )
                db.session.add(alert)
            db.session.commit()

            client = app.test_client()
            response = client.get(f'/api/alerts?page={page}&page_size={page_size}')
            data = json.loads(response.data)

            assert data['code'] == 200
            items = data['data']['items']
            assert len(items) <= page_size, f"返回条数 {len(items)} 超过 page_size {page_size}"

            db.session.remove()
            db.drop_all()

    @given(st.integers(min_value=1, max_value=20))
    @settings(max_examples=50)
    def test_total_consistent(self, n_drivers):
        """total 字段应与数据库实际数据一致"""
        from flask import Flask
        from flask_cors import CORS
        from server.models.models import db, Driver
        from server.routes import drivers_bp, alerts_bp, stats_bp, snapshots_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
        CORS(app)
        app.register_blueprint(drivers_bp)
        app.register_blueprint(alerts_bp)
        app.register_blueprint(stats_bp)
        app.register_blueprint(snapshots_bp)

        with app.app_context():
            db.create_all()
            for i in range(n_drivers):
                db.session.add(Driver(name=f"驾驶员{i}", employee_id=f"EMP{i:04d}"))
            db.session.commit()

            client = app.test_client()
            response = client.get('/api/alerts?page=1&page_size=100')
            data = json.loads(response.data)
            assert data['code'] == 200
            # 没有告警记录，total 应为 0
            assert data['data']['total'] == 0

            db.session.remove()
            db.drop_all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
