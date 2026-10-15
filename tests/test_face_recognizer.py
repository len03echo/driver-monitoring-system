"""
FaceRecognizer 模块单元测试

测试基于 InsightFace 的人脸识别器功能：
- InsightFace 初始化
- 人脸特征提取
- 余弦相似度计算
- 人脸注册功能
- 身份认证功能
- 特征向量验证
- 错误处理

依赖：
- pytest
- numpy
- unittest.mock
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from typing import Optional, Tuple

# 导入被测试的模块
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from client.core.face_recognizer import FaceRecognizer, feature_to_bytes, bytes_to_feature


class TestFaceRecognizerInit:
    """测试 FaceRecognizer 初始化"""
    
    @patch('client.core.face_recognizer.FaceAnalysis')
    def test_init_success(self, mock_face_analysis):
        """测试成功初始化"""
        mock_app = Mock()
        mock_face_analysis.return_value = mock_app
        
        recognizer = FaceRecognizer(model_name='buffalo_l')
        
        assert recognizer.model_name == 'buffalo_l'
        assert recognizer.app == mock_app
        assert recognizer.SIMILARITY_THRESHOLD == 0.5
        assert recognizer.FEATURE_DIM == 512
        
        mock_face_analysis.assert_called_once_with(name='buffalo_l', providers=['CPUExecutionProvider'])
        mock_app.prepare.assert_called_once_with(ctx_id=0, det_size=(640, 640))
    
    @patch('client.core.face_recognizer.FaceAnalysis')
    def test_init_default_model(self, mock_face_analysis):
        """测试默认模型名称"""
        mock_face_analysis.return_value = Mock()
        
        recognizer = FaceRecognizer()
        
        assert recognizer.model_name == 'buffalo_l'
        mock_face_analysis.assert_called_once_with(name='buffalo_l', providers=['CPUExecutionProvider'])
    
    @patch('client.core.face_recognizer.FaceAnalysis')
    def test_init_model_load_failure(self, mock_face_analysis):
        """测试模型加载失败"""
        mock_face_analysis.side_effect = Exception("模型加载错误")
        
        with pytest.raises(RuntimeError, match="InsightFace 模型加载失败"):
            FaceRecognizer()


class TestFaceRecognizerFeatureExtraction:
    """测试人脸特征提取"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.face_recognizer.FaceAnalysis') as mock_face_analysis:
            self.mock_app = Mock()
            mock_face_analysis.return_value = self.mock_app
            self.recognizer = FaceRecognizer()
    
    def test_extract_feature_success(self):
        """测试成功提取特征"""
        # 创建模拟的人脸对象
        mock_face = Mock()
        mock_face.embedding = np.random.rand(512).astype(np.float32)
        
        self.mock_app.get.return_value = [mock_face]
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        feature = self.recognizer.extract_feature(frame)
        
        assert feature is not None
        assert feature.shape == (512,)
        assert feature.dtype == np.float32
        np.testing.assert_array_equal(feature, mock_face.embedding)
    
    def test_extract_feature_no_face(self):
        """测试未检测到人脸"""
        self.mock_app.get.return_value = []
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        feature = self.recognizer.extract_feature(frame)
        
        assert feature is None
    
    def test_extract_feature_multiple_faces(self):
        """测试检测到多张人脸"""
        # 创建两个模拟的人脸对象
        mock_face1 = Mock()
        mock_face1.embedding = np.random.rand(512).astype(np.float32)
        mock_face2 = Mock()
        mock_face2.embedding = np.random.rand(512).astype(np.float32)
        
        self.mock_app.get.return_value = [mock_face1, mock_face2]
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        with patch.object(self.recognizer.logger, 'warning') as mock_warning:
            feature = self.recognizer.extract_feature(frame)
            
            assert feature is not None
            np.testing.assert_array_equal(feature, mock_face1.embedding)  # 应该使用第一张人脸
            mock_warning.assert_called_once()
    
    def test_extract_feature_wrong_dimension(self):
        """测试特征向量维度错误"""
        mock_face = Mock()
        mock_face.embedding = np.random.rand(256).astype(np.float32)  # 错误维度
        
        self.mock_app.get.return_value = [mock_face]
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        feature = self.recognizer.extract_feature(frame)
        
        assert feature is None
    
    def test_extract_feature_no_model(self):
        """测试模型未加载"""
        self.recognizer.app = None
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        feature = self.recognizer.extract_feature(frame)
        
        assert feature is None
    
    def test_extract_feature_exception(self):
        """测试提取过程中的异常"""
        self.mock_app.get.side_effect = Exception("提取异常")
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        with patch.object(self.recognizer.logger, 'error') as mock_error:
            feature = self.recognizer.extract_feature(frame)
            
            assert feature is None
            mock_error.assert_called_once()


class TestFaceRecognizerSimilarity:
    """测试相似度计算"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.face_recognizer.FaceAnalysis'):
            self.recognizer = FaceRecognizer()
    
    def test_calculate_similarity_identical(self):
        """测试相同特征向量的相似度"""
        feature = np.random.rand(512).astype(np.float32)
        
        similarity = self.recognizer.calculate_similarity(feature, feature)
        
        assert abs(similarity - 1.0) < 1e-6  # 应该接近 1.0
    
    def test_calculate_similarity_orthogonal(self):
        """测试正交特征向量的相似度"""
        feature1 = np.zeros(512, dtype=np.float32)
        feature1[0] = 1.0
        
        feature2 = np.zeros(512, dtype=np.float32)
        feature2[1] = 1.0
        
        similarity = self.recognizer.calculate_similarity(feature1, feature2)
        
        assert abs(similarity - 0.0) < 1e-6  # 应该接近 0.0
    
    def test_calculate_similarity_opposite(self):
        """测试相反特征向量的相似度"""
        feature1 = np.ones(512, dtype=np.float32)
        feature2 = -np.ones(512, dtype=np.float32)
        
        similarity = self.recognizer.calculate_similarity(feature1, feature2)
        
        assert abs(similarity - 0.0) < 1e-6  # 余弦相似度为-1，但被限制到0
    
    def test_calculate_similarity_dimension_mismatch(self):
        """测试维度不匹配"""
        feature1 = np.random.rand(512).astype(np.float32)
        feature2 = np.random.rand(256).astype(np.float32)
        
        with pytest.raises(ValueError, match="特征向量维度不匹配"):
            self.recognizer.calculate_similarity(feature1, feature2)
    
    def test_calculate_similarity_wrong_dimension(self):
        """测试错误的特征向量维度"""
        feature1 = np.random.rand(256).astype(np.float32)
        feature2 = np.random.rand(256).astype(np.float32)
        
        with pytest.raises(ValueError, match="特征向量维度错误"):
            self.recognizer.calculate_similarity(feature1, feature2)
    
    def test_calculate_similarity_zero_vector(self):
        """测试零向量的相似度"""
        feature1 = np.zeros(512, dtype=np.float32)
        feature2 = np.random.rand(512).astype(np.float32)
        
        similarity = self.recognizer.calculate_similarity(feature1, feature2)
        
        assert similarity == 0.0
    
    def test_calculate_similarity_exception(self):
        """测试计算过程中的异常"""
        # 创建会导致异常的特征向量（包含 NaN）
        feature1 = np.full(512, np.nan, dtype=np.float32)
        feature2 = np.random.rand(512).astype(np.float32)
        
        # NaN 值会导致计算结果为 NaN，但我们的代码会处理这种情况
        similarity = self.recognizer.calculate_similarity(feature1, feature2)
        
        # NaN 的余弦相似度应该被处理为无效值
        assert np.isnan(similarity) or similarity == 0.0


class TestFaceRecognizerRegistration:
    """测试人脸注册功能"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.face_recognizer.FaceAnalysis'):
            self.recognizer = FaceRecognizer()
        
        # 创建模拟的数据库客户端
        self.mock_db_client = Mock()
    
    def test_register_face_success(self):
        """测试成功注册人脸"""
        # 模拟成功提取特征
        mock_feature = np.random.rand(512).astype(np.float32)
        with patch.object(self.recognizer, 'extract_feature', return_value=mock_feature):
            self.mock_db_client.insert_driver.return_value = 123
            
            success, message = self.recognizer.register_face(
                frame=np.zeros((480, 640, 3), dtype=np.uint8),
                name="张三",
                employee_id="EMP001",
                db_client=self.mock_db_client
            )
            
            assert success is True
            assert "123" in message
            self.mock_db_client.insert_driver.assert_called_once()
    
    def test_register_face_no_face_detected(self):
        """测试未检测到人脸"""
        with patch.object(self.recognizer, 'extract_feature', return_value=None):
            success, message = self.recognizer.register_face(
                frame=np.zeros((480, 640, 3), dtype=np.uint8),
                name="张三",
                employee_id="EMP001",
                db_client=self.mock_db_client
            )
            
            assert success is False
            assert "未检测到人脸" in message
            self.mock_db_client.insert_driver.assert_not_called()
    
    def test_register_face_duplicate_employee_id(self):
        """测试工号重复"""
        mock_feature = np.random.rand(512).astype(np.float32)
        with patch.object(self.recognizer, 'extract_feature', return_value=mock_feature):
            self.mock_db_client.insert_driver.side_effect = ValueError("工号 EMP001 已存在")
            
            success, message = self.recognizer.register_face(
                frame=np.zeros((480, 640, 3), dtype=np.uint8),
                name="张三",
                employee_id="EMP001",
                db_client=self.mock_db_client
            )
            
            assert success is False
            assert "工号 EMP001 已存在" in message
    
    def test_register_face_database_error(self):
        """测试数据库错误"""
        mock_feature = np.random.rand(512).astype(np.float32)
        with patch.object(self.recognizer, 'extract_feature', return_value=mock_feature):
            self.mock_db_client.insert_driver.side_effect = Exception("数据库连接失败")
            
            success, message = self.recognizer.register_face(
                frame=np.zeros((480, 640, 3), dtype=np.uint8),
                name="张三",
                employee_id="EMP001",
                db_client=self.mock_db_client
            )
            
            assert success is False
            assert "数据库连接失败" in message


class TestFaceRecognizerAuthentication:
    """测试身份认证功能"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.face_recognizer.FaceAnalysis'):
            self.recognizer = FaceRecognizer()
        
        self.mock_db_client = Mock()
    
    def test_authenticate_face_success(self):
        """测试成功认证"""
        # 创建当前帧特征
        current_feature = np.random.rand(512).astype(np.float32)
        
        # 创建数据库中的驾驶员（相同特征）
        stored_feature = current_feature.copy()
        mock_driver = {
            'id': 1,
            'name': '张三',
            'employee_id': 'EMP001',
            'face_feature': stored_feature.tobytes()
        }
        
        with patch.object(self.recognizer, 'extract_feature', return_value=current_feature):
            self.mock_db_client.get_all_drivers.return_value = [mock_driver]
            
            success, driver_info, message = self.recognizer.authenticate_face(
                frame=np.zeros((480, 640, 3), dtype=np.uint8),
                db_client=self.mock_db_client
            )
            
            assert success is True
            assert driver_info == mock_driver
            assert "张三" in message
    
    def test_authenticate_face_no_face_detected(self):
        """测试未检测到人脸"""
        with patch.object(self.recognizer, 'extract_feature', return_value=None):
            success, driver_info, message = self.recognizer.authenticate_face(
                frame=np.zeros((480, 640, 3), dtype=np.uint8),
                db_client=self.mock_db_client
            )
            
            assert success is False
            assert driver_info is None
            assert "未检测到人脸" in message
    
    def test_authenticate_face_no_registered_drivers(self):
        """测试没有已注册驾驶员"""
        current_feature = np.random.rand(512).astype(np.float32)
        
        with patch.object(self.recognizer, 'extract_feature', return_value=current_feature):
            self.mock_db_client.get_all_drivers.return_value = []
            
            success, driver_info, message = self.recognizer.authenticate_face(
                frame=np.zeros((480, 640, 3), dtype=np.uint8),
                db_client=self.mock_db_client
            )
            
            assert success is False
            assert driver_info is None
            assert "没有已注册的驾驶员" in message
    
    def test_authenticate_face_low_similarity(self):
        """测试相似度过低"""
        # 创建确保相似度很低的特征向量
        current_feature = np.zeros(512, dtype=np.float32)
        current_feature[0] = 1.0  # 单位向量
        
        stored_feature = np.zeros(512, dtype=np.float32)
        stored_feature[1] = 1.0  # 正交的单位向量，相似度为0
        
        mock_driver = {
            'id': 1,
            'name': '张三',
            'employee_id': 'EMP001',
            'face_feature': stored_feature.tobytes()
        }
        
        with patch.object(self.recognizer, 'extract_feature', return_value=current_feature):
            self.mock_db_client.get_all_drivers.return_value = [mock_driver]
            
            success, driver_info, message = self.recognizer.authenticate_face(
                frame=np.zeros((480, 640, 3), dtype=np.uint8),
                db_client=self.mock_db_client
            )
            
            assert success is False
            assert driver_info is None
            assert "身份认证失败" in message
    
    def test_authenticate_face_skip_no_feature(self):
        """测试跳过没有人脸特征的驾驶员"""
        current_feature = np.random.rand(512).astype(np.float32)
        
        mock_drivers = [
            {'id': 1, 'name': '张三', 'employee_id': 'EMP001', 'face_feature': None},
            {'id': 2, 'name': '李四', 'employee_id': 'EMP002', 'face_feature': current_feature.tobytes()}
        ]
        
        with patch.object(self.recognizer, 'extract_feature', return_value=current_feature):
            self.mock_db_client.get_all_drivers.return_value = mock_drivers
            
            success, driver_info, message = self.recognizer.authenticate_face(
                frame=np.zeros((480, 640, 3), dtype=np.uint8),
                db_client=self.mock_db_client
            )
            
            assert success is True
            assert driver_info['name'] == '李四'
    
    def test_authenticate_face_wrong_feature_dimension(self):
        """测试错误的特征向量维度"""
        current_feature = np.random.rand(512).astype(np.float32)
        wrong_feature = np.random.rand(256).astype(np.float32)  # 错误维度
        
        mock_driver = {
            'id': 1,
            'name': '张三',
            'employee_id': 'EMP001',
            'face_feature': wrong_feature.tobytes()
        }
        
        with patch.object(self.recognizer, 'extract_feature', return_value=current_feature):
            self.mock_db_client.get_all_drivers.return_value = [mock_driver]
            
            with patch.object(self.recognizer.logger, 'warning') as mock_warning:
                success, driver_info, message = self.recognizer.authenticate_face(
                    frame=np.zeros((480, 640, 3), dtype=np.uint8),
                    db_client=self.mock_db_client
                )
                
                assert success is False
                mock_warning.assert_called_once()


class TestFaceRecognizerUtilityMethods:
    """测试工具方法"""
    
    def setup_method(self):
        """设置测试环境"""
        with patch('client.core.face_recognizer.FaceAnalysis'):
            self.recognizer = FaceRecognizer()
    
    def test_update_face_feature_success(self):
        """测试成功更新人脸特征"""
        mock_feature = np.random.rand(512).astype(np.float32)
        mock_db_client = Mock()
        mock_db_client.update_driver_face_feature.return_value = True
        
        with patch.object(self.recognizer, 'extract_feature', return_value=mock_feature):
            success, message = self.recognizer.update_face_feature(
                frame=np.zeros((480, 640, 3), dtype=np.uint8),
                driver_id=123,
                db_client=mock_db_client
            )
            
            assert success is True
            assert "更新成功" in message
            mock_db_client.update_driver_face_feature.assert_called_once()
    
    def test_update_face_feature_no_face(self):
        """测试未检测到人脸"""
        mock_db_client = Mock()
        
        with patch.object(self.recognizer, 'extract_feature', return_value=None):
            success, message = self.recognizer.update_face_feature(
                frame=np.zeros((480, 640, 3), dtype=np.uint8),
                driver_id=123,
                db_client=mock_db_client
            )
            
            assert success is False
            assert "未检测到人脸" in message
            mock_db_client.update_driver_face_feature.assert_not_called()
    
    def test_validate_feature_vector_valid(self):
        """测试有效的特征向量"""
        feature = np.random.rand(512).astype(np.float32)
        
        assert self.recognizer.validate_feature_vector(feature) is True
    
    def test_validate_feature_vector_wrong_type(self):
        """测试错误的数据类型"""
        feature = [1, 2, 3]  # 不是 numpy 数组
        
        assert self.recognizer.validate_feature_vector(feature) is False
    
    def test_validate_feature_vector_wrong_dtype(self):
        """测试错误的数据类型"""
        feature = np.random.rand(512).astype(np.float64)  # 不是 float32
        
        assert self.recognizer.validate_feature_vector(feature) is False
    
    def test_validate_feature_vector_wrong_shape(self):
        """测试错误的形状"""
        feature = np.random.rand(256).astype(np.float32)  # 错误维度
        
        assert self.recognizer.validate_feature_vector(feature) is False
    
    def test_validate_feature_vector_zero_vector(self):
        """测试零向量"""
        feature = np.zeros(512, dtype=np.float32)
        
        assert self.recognizer.validate_feature_vector(feature) is False
    
    def test_validate_feature_vector_nan(self):
        """测试包含 NaN 的向量"""
        feature = np.random.rand(512).astype(np.float32)
        feature[0] = np.nan
        
        assert self.recognizer.validate_feature_vector(feature) is False
    
    def test_validate_feature_vector_inf(self):
        """测试包含 Inf 的向量"""
        feature = np.random.rand(512).astype(np.float32)
        feature[0] = np.inf
        
        assert self.recognizer.validate_feature_vector(feature) is False
    
    def test_similarity_threshold_operations(self):
        """测试相似度阈值操作"""
        # 测试获取阈值
        assert self.recognizer.get_similarity_threshold() == 0.5
        
        # 测试设置有效阈值
        self.recognizer.set_similarity_threshold(0.7)
        assert self.recognizer.get_similarity_threshold() == 0.7
        
        # 测试设置无效阈值
        with pytest.raises(ValueError, match="相似度阈值必须在"):
            self.recognizer.set_similarity_threshold(1.5)
        
        with pytest.raises(ValueError, match="相似度阈值必须在"):
            self.recognizer.set_similarity_threshold(-0.1)
    
    def test_is_model_loaded(self):
        """测试模型加载状态检查"""
        assert self.recognizer.is_model_loaded() is True
        
        self.recognizer.app = None
        assert self.recognizer.is_model_loaded() is False
    
    def test_feature_dimension_property(self):
        """测试特征向量维度属性"""
        assert self.recognizer.feature_dimension == 512
    
    def test_close(self):
        """测试资源释放"""
        with patch.object(self.recognizer.logger, 'info') as mock_info:
            self.recognizer.close()
            
            assert self.recognizer.app is None
            mock_info.assert_called_once()
    
    def test_context_manager(self):
        """测试上下文管理器"""
        with patch.object(self.recognizer, 'close') as mock_close:
            with self.recognizer as recognizer:
                assert recognizer == self.recognizer
            mock_close.assert_called_once()


class TestUtilityFunctions:
    """测试工具函数"""
    
    def test_feature_to_bytes(self):
        """测试特征向量转字节"""
        feature = np.random.rand(512).astype(np.float32)
        
        feature_bytes = feature_to_bytes(feature)
        
        assert isinstance(feature_bytes, bytes)
        assert len(feature_bytes) == 512 * 4  # float32 = 4 bytes
    
    def test_bytes_to_feature(self):
        """测试字节转特征向量"""
        original_feature = np.random.rand(512).astype(np.float32)
        feature_bytes = original_feature.tobytes()
        
        restored_feature = bytes_to_feature(feature_bytes)
        
        assert restored_feature.dtype == np.float32
        assert restored_feature.shape == (512,)
        np.testing.assert_array_equal(original_feature, restored_feature)
    
    def test_feature_bytes_roundtrip(self):
        """测试特征向量与字节的往返转换"""
        original_feature = np.random.rand(512).astype(np.float32)
        
        # 转换为字节再转换回来
        feature_bytes = feature_to_bytes(original_feature)
        restored_feature = bytes_to_feature(feature_bytes)
        
        np.testing.assert_array_equal(original_feature, restored_feature)


if __name__ == "__main__":
    pytest.main([__file__])