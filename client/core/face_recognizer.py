"""
基于 InsightFace 的人脸识别器

使用 InsightFace 提取 512 维人脸特征向量，实现人脸注册和余弦相似度身份认证。
相似度阈值设为 0.5，支持与数据库的交互。

依赖：
- insightface
- numpy
- opencv-python
- onnxruntime
"""

import logging
import os
from typing import Optional, Tuple, List
import numpy as np
import cv2

try:
    import insightface
    from insightface.app import FaceAnalysis
except ImportError:
    raise ImportError("请安装 insightface 库: pip install insightface")


class FaceRecognizer:
    """
    基于 InsightFace 的人脸识别器。
    依赖：insightface, onnxruntime
    """

    # 相似度阈值
    SIMILARITY_THRESHOLD = 0.5
    
    # 特征向量维度
    FEATURE_DIM = 512

    def __init__(self, model_name: str = 'buffalo_l') -> None:
        """
        初始化人脸识别器，加载 InsightFace 模型。
        
        Args:
            model_name: InsightFace 模型名称，默认 'buffalo_l'
            
        Raises:
            RuntimeError: 模型加载失败时抛出
        """
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        self.model_name = model_name
        self.app: Optional[FaceAnalysis] = None
        
        # 加载模型
        self._load_model()
        
        self.logger.info(f"InsightFace 人脸识别器初始化成功，模型: {model_name}")

    def _load_model(self) -> None:
        """
        加载 InsightFace 模型。
        
        Raises:
            RuntimeError: 模型加载失败时抛出
        """
        try:
            # 创建 FaceAnalysis 应用
            self.app = FaceAnalysis(name=self.model_name, providers=['CPUExecutionProvider'])
            
            # 准备模型（下载模型文件如果不存在）
            self.app.prepare(ctx_id=0, det_size=(640, 640))
            
            self.logger.info(f"InsightFace 模型 {self.model_name} 加载成功")
            
        except Exception as e:
            error_msg = f"InsightFace 模型加载失败: {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

    def extract_feature(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        从图像中提取人脸特征向量。
        
        Args:
            frame: BGR 格式的 numpy 数组（H×W×3）
            
        Returns:
            512维特征向量 (float32)，未检测到人脸返回 None
        """
        if self.app is None:
            self.logger.error("InsightFace 模型未加载")
            return None
        
        try:
            # 检测人脸并提取特征
            faces = self.app.get(frame)
            
            if len(faces) == 0:
                self.logger.debug("未检测到人脸")
                return None
            
            if len(faces) > 1:
                self.logger.warning(f"检测到 {len(faces)} 张人脸，使用第一张")
            
            # 取第一张人脸的特征向量
            face = faces[0]
            feature = face.embedding
            
            # 确保特征向量维度正确
            if feature.shape[0] != self.FEATURE_DIM:
                self.logger.error(f"特征向量维度错误: {feature.shape[0]}, 期望: {self.FEATURE_DIM}")
                return None
            
            # 确保数据类型为 float32
            feature = feature.astype(np.float32)
            
            self.logger.debug(f"成功提取人脸特征，维度: {feature.shape}")
            return feature
            
        except Exception as e:
            self.logger.error(f"人脸特征提取失败: {e}")
            return None

    def calculate_similarity(self, feature1: np.ndarray, feature2: np.ndarray) -> float:
        """
        计算两个特征向量的余弦相似度。
        
        Args:
            feature1: 第一个特征向量 (512维)
            feature2: 第二个特征向量 (512维)
            
        Returns:
            余弦相似度值 [0, 1]，1表示完全相同
            
        Raises:
            ValueError: 特征向量维度不匹配时抛出
        """
        if feature1.shape != feature2.shape:
            raise ValueError(f"特征向量维度不匹配: {feature1.shape} vs {feature2.shape}")
        
        if feature1.shape[0] != self.FEATURE_DIM:
            raise ValueError(f"特征向量维度错误: {feature1.shape[0]}, 期望: {self.FEATURE_DIM}")
        
        try:
            # 计算余弦相似度
            # similarity = (A · B) / (||A|| * ||B||)
            dot_product = np.dot(feature1, feature2)
            norm1 = np.linalg.norm(feature1)
            norm2 = np.linalg.norm(feature2)
            
            # 避免除零
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            
            # 确保结果在 [0, 1] 范围内，并处理 NaN
            if np.isnan(similarity):
                similarity = 0.0
            else:
                similarity = max(0.0, min(1.0, similarity))
            
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"相似度计算失败: {e}")
            return 0.0

    def register_face(self, frame: np.ndarray, name: str, employee_id: str, 
                     db_client) -> Tuple[bool, str]:
        """
        注册人脸到数据库。
        
        Args:
            frame: BGR 格式的图像
            name: 驾驶员姓名
            employee_id: 驾驶员工号
            db_client: 数据库客户端实例
            
        Returns:
            (success, message) 元组
            success: 注册是否成功
            message: 结果消息
        """
        try:
            # 提取人脸特征
            feature = self.extract_feature(frame)
            if feature is None:
                return False, "未检测到人脸，请确保人脸清晰可见"
            
            # 将特征向量转换为字节数据
            feature_bytes = feature.tobytes()
            
            # 插入到数据库
            driver_id = db_client.insert_driver(
                name=name,
                employee_id=employee_id,
                face_feature=feature_bytes,
                avatar_path=None  # 暂不保存头像
            )
            
            self.logger.info(f"人脸注册成功: {name} ({employee_id}), 驾驶员ID: {driver_id}")
            return True, f"人脸注册成功，驾驶员ID: {driver_id}"
            
        except ValueError as e:
            # 工号已存在等业务错误
            error_msg = str(e)
            self.logger.warning(f"人脸注册失败: {error_msg}")
            return False, error_msg
            
        except Exception as e:
            error_msg = f"人脸注册失败: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def authenticate_face(self, frame: np.ndarray, db_client) -> Tuple[bool, Optional[dict], str]:
        """
        人脸身份认证。
        
        Args:
            frame: BGR 格式的图像
            db_client: 数据库客户端实例
            
        Returns:
            (success, driver_info, message) 元组
            success: 认证是否成功
            driver_info: 驾驶员信息字典（成功时）
            message: 结果消息
        """
        try:
            # 提取当前帧的人脸特征
            current_feature = self.extract_feature(frame)
            if current_feature is None:
                return False, None, "未检测到人脸，请确保人脸清晰可见"
            
            # 获取所有已注册的驾驶员
            drivers = db_client.get_all_drivers()
            if not drivers:
                return False, None, "数据库中没有已注册的驾驶员"
            
            best_similarity = 0.0
            best_match = None
            
            # 与每个已注册驾驶员进行比对
            for driver in drivers:
                if driver['face_feature'] is None:
                    continue  # 跳过没有人脸特征的驾驶员
                
                try:
                    # 将字节数据转换回特征向量
                    stored_feature = np.frombuffer(driver['face_feature'], dtype=np.float32)
                    
                    # 验证特征向量维度
                    if stored_feature.shape[0] != self.FEATURE_DIM:
                        self.logger.warning(f"驾驶员 {driver['name']} 的特征向量维度错误: {stored_feature.shape[0]}")
                        continue
                    
                    # 计算相似度
                    similarity = self.calculate_similarity(current_feature, stored_feature)
                    
                    self.logger.debug(f"与驾驶员 {driver['name']} 的相似度: {similarity:.3f}")
                    
                    # 更新最佳匹配
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = driver
                        
                except Exception as e:
                    self.logger.error(f"处理驾驶员 {driver['name']} 的特征向量时出错: {e}")
                    continue
            
            # 判断是否认证成功
            if best_similarity >= self.SIMILARITY_THRESHOLD:
                self.logger.info(f"身份认证成功: {best_match['name']} ({best_match['employee_id']}), 相似度: {best_similarity:.3f}")
                return True, best_match, f"身份认证成功，欢迎 {best_match['name']}"
            else:
                self.logger.info(f"身份认证失败，最高相似度: {best_similarity:.3f} < {self.SIMILARITY_THRESHOLD}")
                return False, None, f"身份认证失败，未找到匹配的驾驶员"
                
        except Exception as e:
            error_msg = f"身份认证过程出错: {e}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def update_face_feature(self, frame: np.ndarray, driver_id: int, 
                           db_client) -> Tuple[bool, str]:
        """
        更新驾驶员的人脸特征。
        
        Args:
            frame: BGR 格式的图像
            driver_id: 驾驶员ID
            db_client: 数据库客户端实例
            
        Returns:
            (success, message) 元组
        """
        try:
            # 提取人脸特征
            feature = self.extract_feature(frame)
            if feature is None:
                return False, "未检测到人脸，请确保人脸清晰可见"
            
            # 将特征向量转换为字节数据
            feature_bytes = feature.tobytes()
            
            # 更新数据库
            success = db_client.update_driver_face_feature(driver_id, feature_bytes)
            
            if success:
                self.logger.info(f"驾驶员 {driver_id} 的人脸特征更新成功")
                return True, "人脸特征更新成功"
            else:
                return False, "驾驶员不存在"
                
        except Exception as e:
            error_msg = f"人脸特征更新失败: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def validate_feature_vector(self, feature: np.ndarray) -> bool:
        """
        验证特征向量的有效性。
        
        Args:
            feature: 特征向量
            
        Returns:
            是否有效
        """
        if not isinstance(feature, np.ndarray):
            return False
        
        if feature.dtype != np.float32:
            return False
        
        if feature.shape != (self.FEATURE_DIM,):
            return False
        
        # 检查是否为零向量
        if np.allclose(feature, 0):
            return False
        
        # 检查是否包含 NaN 或 Inf
        if not np.isfinite(feature).all():
            return False
        
        return True

    def get_similarity_threshold(self) -> float:
        """
        获取相似度阈值。
        
        Returns:
            相似度阈值
        """
        return self.SIMILARITY_THRESHOLD

    def set_similarity_threshold(self, threshold: float) -> None:
        """
        设置相似度阈值。
        
        Args:
            threshold: 新的相似度阈值 [0, 1]
            
        Raises:
            ValueError: 阈值超出有效范围时抛出
        """
        if not 0 <= threshold <= 1:
            raise ValueError(f"相似度阈值必须在 [0, 1] 范围内，当前值: {threshold}")
        
        old_threshold = self.SIMILARITY_THRESHOLD
        self.SIMILARITY_THRESHOLD = threshold
        self.logger.info(f"相似度阈值已更新: {old_threshold} -> {threshold}")

    def is_model_loaded(self) -> bool:
        """
        检查模型是否已成功加载。
        
        Returns:
            模型加载状态
        """
        return self.app is not None

    @property
    def feature_dimension(self) -> int:
        """
        获取特征向量维度。
        
        Returns:
            特征向量维度
        """
        return self.FEATURE_DIM

    def close(self) -> None:
        """释放 InsightFace 资源"""
        if self.app is not None:
            # InsightFace 没有显式的 close 方法，设为 None 即可
            self.app = None
        self.logger.info("InsightFace 资源已释放")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


# ---- 工具函数 ----

def feature_to_bytes(feature: np.ndarray) -> bytes:
    """
    将特征向量转换为字节数据（用于存储到数据库）。
    
    Args:
        feature: numpy 特征向量
        
    Returns:
        字节数据
    """
    return feature.tobytes()


def bytes_to_feature(feature_bytes: bytes) -> np.ndarray:
    """
    将字节数据转换为特征向量（从数据库读取）。
    
    Args:
        feature_bytes: 字节数据
        
    Returns:
        numpy 特征向量 (float32)
    """
    return np.frombuffer(feature_bytes, dtype=np.float32)


if __name__ == "__main__":
    # 测试人脸识别器
    import sys
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # 创建人脸识别器
        recognizer = FaceRecognizer()
        
        print("人脸识别器初始化成功！")
        print(f"模型名称: {recognizer.model_name}")
        print(f"特征向量维度: {recognizer.feature_dimension}")
        print(f"相似度阈值: {recognizer.get_similarity_threshold()}")
        
        # 测试空白图像
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        feature = recognizer.extract_feature(test_frame)
        print(f"测试结果: {feature is not None}")
        
        recognizer.close()
        
    except Exception as e:
        print(f"人脸识别器测试失败: {e}")
        sys.exit(1)