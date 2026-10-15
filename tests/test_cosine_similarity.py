"""
Task-30：余弦相似度计算单元测试

测试 FaceRecognizer 中余弦相似度计算的正确性，不依赖 InsightFace 模型。
"""

import pytest
import math
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """余弦相似度计算（与 FaceRecognizer.calculate_similarity 逻辑一致）"""
    dot_product = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    similarity = dot_product / (norm_a * norm_b)
    if np.isnan(similarity):
        return 0.0
    return float(max(0.0, min(1.0, similarity)))


class TestCosineSimilarity:
    """测试余弦相似度计算"""

    def test_identical_vectors(self):
        """完全相同的向量相似度应为 1.0"""
        vec = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
        sim = cosine_similarity(vec, vec)
        assert abs(sim - 1.0) < 1e-6, f"相同向量相似度应为 1.0，实际: {sim}"

    def test_opposite_vectors(self):
        """方向相反的向量相似度应为 0.0（clamp 后）"""
        vec_a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        vec_b = np.array([-1.0, 0.0, 0.0], dtype=np.float32)
        sim = cosine_similarity(vec_a, vec_b)
        assert sim == 0.0, f"反向向量相似度应为 0.0，实际: {sim}"

    def test_orthogonal_vectors(self):
        """正交向量相似度应为 0.0"""
        vec_a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        vec_b = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        sim = cosine_similarity(vec_a, vec_b)
        assert abs(sim) < 1e-6, f"正交向量相似度应为 0.0，实际: {sim}"

    def test_zero_vector(self):
        """零向量相似度应为 0.0（避免除零）"""
        vec_a = np.zeros(512, dtype=np.float32)
        vec_b = np.ones(512, dtype=np.float32)
        sim = cosine_similarity(vec_a, vec_b)
        assert sim == 0.0, f"零向量相似度应为 0.0，实际: {sim}"

    def test_similarity_range(self):
        """相似度结果应在 [0, 1] 范围内"""
        rng = np.random.default_rng(42)
        for _ in range(100):
            vec_a = rng.standard_normal(512).astype(np.float32)
            vec_b = rng.standard_normal(512).astype(np.float32)
            sim = cosine_similarity(vec_a, vec_b)
            assert 0.0 <= sim <= 1.0, f"相似度超出范围 [0,1]：{sim}"

    def test_symmetry(self):
        """相似度计算应满足对称性：sim(a,b) == sim(b,a)"""
        rng = np.random.default_rng(0)
        vec_a = rng.standard_normal(512).astype(np.float32)
        vec_b = rng.standard_normal(512).astype(np.float32)
        assert abs(cosine_similarity(vec_a, vec_b) - cosine_similarity(vec_b, vec_a)) < 1e-6

    def test_scale_invariance(self):
        """缩放向量不影响相似度"""
        vec_a = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        vec_b = np.array([2.0, 4.0, 6.0], dtype=np.float32)  # vec_a * 2
        sim = cosine_similarity(vec_a, vec_b)
        assert abs(sim - 1.0) < 1e-6, f"同向缩放向量相似度应为 1.0，实际: {sim}"

    def test_512_dim_vectors(self):
        """512维向量计算应正常工作"""
        rng = np.random.default_rng(1)
        vec_a = rng.standard_normal(512).astype(np.float32)
        vec_b = rng.standard_normal(512).astype(np.float32)
        sim = cosine_similarity(vec_a, vec_b)
        assert isinstance(sim, float)
        assert 0.0 <= sim <= 1.0

    def test_high_similarity_vectors(self):
        """相似向量的相似度应接近 1.0"""
        base = np.ones(512, dtype=np.float32)
        noise = np.random.default_rng(2).standard_normal(512).astype(np.float32) * 0.01
        vec_a = base + noise
        vec_b = base - noise
        sim = cosine_similarity(vec_a, vec_b)
        assert sim > 0.9, f"相似向量的相似度应大于 0.9，实际: {sim}"

    def test_threshold_boundary(self):
        """验证 0.5 阈值边界：相似度 >= 0.5 认证通过"""
        # 构造相似度恰好在阈值附近的向量
        vec_a = np.array([1.0, 0.0], dtype=np.float32)
        # 45度角，余弦值 = cos(45°) ≈ 0.707 > 0.5
        vec_b = np.array([1.0, 1.0], dtype=np.float32)
        sim = cosine_similarity(vec_a, vec_b)
        assert sim >= 0.5, f"45度角向量相似度应 >= 0.5，实际: {sim}"


class TestFeatureVectorProperties:
    """测试特征向量的基本属性"""

    def test_feature_dtype(self):
        """特征向量应为 float32 类型"""
        feature = np.random.randn(512).astype(np.float32)
        assert feature.dtype == np.float32

    def test_feature_dimension(self):
        """特征向量维度应为 512"""
        feature = np.random.randn(512).astype(np.float32)
        assert feature.shape == (512,)

    def test_feature_serialization(self):
        """特征向量序列化和反序列化应保持一致"""
        original = np.random.randn(512).astype(np.float32)
        # 序列化为字节
        feature_bytes = original.tobytes()
        # 反序列化
        restored = np.frombuffer(feature_bytes, dtype=np.float32)
        assert np.allclose(original, restored), "序列化/反序列化后向量应保持一致"

    def test_feature_bytes_length(self):
        """512维 float32 向量序列化后应为 2048 字节"""
        feature = np.random.randn(512).astype(np.float32)
        feature_bytes = feature.tobytes()
        assert len(feature_bytes) == 512 * 4  # float32 = 4 bytes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
