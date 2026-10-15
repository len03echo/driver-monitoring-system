"""
基于 YOLOv8 的危险行为检测器

负责加载 YOLOv8 模型，对视频帧进行目标检测，维护各类别连续帧计数器，
达到阈值后触发告警信号。支持 smoke/phone/drink 三类检测。

依赖：
- ultralytics (YOLOv8)
- numpy
- opencv-python
"""

import os
import time
import logging
from typing import List, Dict, Tuple, Optional
import numpy as np

try:
    from ultralytics import YOLO
except ImportError:
    raise ImportError("请安装 ultralytics 库: pip install ultralytics")


class BehaviorDetector:
    """
    基于 YOLOv8 的危险行为检测器。
    依赖：ultralytics.YOLO
    """

    # 支持的检测类别及其危险等级映射
    # 类别映射：基于自定义训练的 YOLOv8 模型
    # class_id: 0=face, 1=smoke, 2=phone, 3=drink
    CLASS_ID_TO_NAME = {
        1: 'smoke',   # 吸烟
        2: 'phone',   # 使用手机
        3: 'drink'    # 喝水/饮料
        # 注意：class_id=0 (face) 会被过滤，不触发告警
    }
    
    CLASS_SEVERITY_MAP = {
        "smoke": "high",    # 吸烟 - 高危险
        "phone": "medium",  # 使用手机 - 中等危险
        "drink": "low"      # 喝水/饮料 - 低危险
    }

    def __init__(self, model_path: str, consecutive_threshold: int = 10, 
                 inference_size: int = 320, use_half: bool = False) -> None:
        """
        初始化检测器，加载 YOLOv8 模型。
        
        Args:
            model_path: YOLOv8 模型文件路径
            consecutive_threshold: 连续帧触发阈值，默认 N=10
            inference_size: 推理时的图像尺寸，默认 320（越小越快，但精度略降）
            use_half: 是否使用半精度推理（FP16），仅 GPU 支持
            
        Raises:
            FileNotFoundError: 模型文件不存在时抛出
            RuntimeError: 模型加载失败时抛出
        """
        self.model_path = model_path
        self.consecutive_threshold = consecutive_threshold
        self.inference_size = inference_size
        self.use_half = use_half
        
        # 设置日志（必须在 _load_model 之前初始化）
        self.logger = logging.getLogger(__name__)
        
        # 初始化连续帧计数器
        self.frame_counters: Dict[str, int] = {
            "smoke": 0,
            "phone": 0,
            "drink": 0
        }
        
        # 设备信息
        self.device = 'cpu'
        self.is_gpu_available = False
        
        # 加载模型
        self.model: Optional[YOLO] = None
        self._load_model()

    def _load_model(self) -> None:
        """
        加载 YOLOv8 模型。
        
        Raises:
            FileNotFoundError: 模型文件不存在时抛出
            RuntimeError: 模型加载失败时抛出
        """
        # 如果是相对路径且文件不存在，尝试让 ultralytics 自动下载
        model_path = self.model_path
        if not os.path.exists(model_path):
            # ultralytics 支持直接传入模型名称（如 yolov8n.pt）自动下载
            # 只有当路径包含目录分隔符时才认为是本地路径
            if os.sep in model_path or '/' in model_path:
                raise FileNotFoundError(f"YOLOv8 模型文件不存在: {model_path}")
            # 否则交给 ultralytics 处理（会自动下载官方模型）
            self.logger.info(f"模型文件 {model_path} 不存在，尝试自动下载...")
        
        try:
            # 先检查 GPU 可用性
            try:
                import torch
                gpu_available = torch.cuda.is_available()
                if gpu_available:
                    self.device = 'cuda'
                    self.is_gpu_available = True
                    self.logger.info(f"检测到 GPU: {torch.cuda.get_device_name(0)}")
                else:
                    self.device = 'cpu'
                    self.is_gpu_available = False
                    # CPU 不支持半精度，强制禁用
                    if self.use_half:
                        self.logger.warning("CPU 不支持半精度推理，已自动禁用")
                        self.use_half = False
                    self.logger.info(f"GPU 不可用，使用 CPU 推理")
            except Exception as e:
                self.device = 'cpu'
                self.is_gpu_available = False
                # 发生错误时也禁用半精度
                if self.use_half:
                    self.logger.warning("GPU 初始化失败，半精度已禁用")
                    self.use_half = False
                self.logger.warning(f"GPU 检测失败，使用 CPU 推理: {e}")
            
            # 加载模型时直接指定设备
            self.logger.info(f"正在加载 YOLOv8 模型到 {self.device.upper()}...")
            self.model = YOLO(model_path)
            
            # 如果是 GPU，进行额外配置
            if self.is_gpu_available:
                # 将模型移到 GPU
                self.model.to(self.device)
                
                # 记录半精度状态（不在这里转换模型，而是在推理时使用 half 参数）
                if self.use_half:
                    self.logger.info(f"YOLOv8 已启用 GPU 加速 (CUDA) + FP16 半精度")
                else:
                    self.logger.info(f"YOLOv8 已启用 GPU 加速 (CUDA)")
                
                # GPU 预热：运行一次推理以初始化 CUDA
                self.logger.info("正在预热 GPU...")
                dummy_frame = np.zeros((self.inference_size, self.inference_size, 3), dtype=np.uint8)
                # 预热时使用相同的参数
                _ = self.model(dummy_frame, imgsz=self.inference_size, verbose=False, half=self.use_half, device=self.device)
                self.logger.info("GPU 预热完成")
            
            self.logger.info(f"YOLOv8 模型加载成功: {model_path} (推理尺寸: {self.inference_size}, 设备: {self.device.upper()})")
        except Exception as e:
            raise RuntimeError(f"YOLOv8 模型加载失败: {e}")

    def detect(self, frame: np.ndarray) -> List[Dict]:
        """
        对单帧图像进行目标检测。
        
        Args:
            frame: BGR 格式的 numpy 数组（H×W×3）
            
        Returns:
            检测结果列表，每项包含 {"class": str, "confidence": float, "bbox": [x1,y1,x2,y2]}
        """
        if self.model is None:
            return []
        
        try:
            # 记录推理开始时间
            start_time = time.time()
            
            # 执行推理（使用优化参数）
            # imgsz: 推理时的图像尺寸，越小越快
            # half: 是否使用半精度（仅 GPU）
            # device: 指定设备
            results = self.model(
                frame, 
                imgsz=self.inference_size,
                verbose=False,
                half=self.use_half and self.is_gpu_available,
                device=self.device
            )
            
            # 记录推理耗时
            inference_time = (time.time() - start_time) * 1000  # 转换为毫秒
            if inference_time > 200:  # 超过200ms记录警告
                self.logger.warning(
                    f"YOLOv8 推理耗时过长: {inference_time:.1f}ms "
                    f"(设备: {self.device}, 尺寸: {self.inference_size}, "
                    f"半精度: {self.use_half and self.is_gpu_available})"
                )
            
            # 解析检测结果
            detections = []
            if results and len(results) > 0:
                result = results[0]  # 取第一个结果
                
                if result.boxes is not None:
                    boxes = result.boxes
                    
                    # 获取类别名称
                    names = result.names if hasattr(result, 'names') else {}
                    
                    # 调试：记录所有检测到的对象
                    all_detected = []
                    
                    for i in range(len(boxes)):
                        # 获取边界框坐标
                        bbox = boxes.xyxy[i].cpu().numpy()  # [x1, y1, x2, y2]
                        
                        # 获取置信度
                        confidence = float(boxes.conf[i].cpu().numpy())
                        
                        # 获取类别ID
                        class_id = int(boxes.cls[i].cpu().numpy())
                        
                        # 过滤掉 class_id=0 (face)，只处理 smoke/phone/drink
                        if class_id == 0:
                            continue
                        
                        # 使用自定义类别映射
                        class_name = self.CLASS_ID_TO_NAME.get(class_id, f"class_{class_id}")
                        
                        all_detected.append(f"{class_name}({confidence:.2f})")
                        
                        # 只保留我们关心的类别
                        if class_name in self.CLASS_SEVERITY_MAP:
                            detections.append({
                                "class": class_name,
                                "confidence": confidence,
                                "bbox": bbox.tolist()  # [x1, y1, x2, y2]
                            })
                    
                    # 调试日志：显示所有检测到的对象
                    if all_detected:
                        self.logger.info(f"YOLOv8 检测到: {', '.join(all_detected)} | 过滤后: {len(detections)} 个")
            
            return detections
            
        except Exception as e:
            self.logger.error(f"YOLOv8 推理失败: {e}")
            return []

    def update_counters(self, detections: List[Dict]) -> List[str]:
        """
        根据当前帧检测结果更新连续帧计数器。
        
        Args:
            detections: detect() 返回的检测结果列表
            
        Returns:
            本帧触发阈值的告警类别列表，如 ["phone"]
        """
        # 提取当前帧检测到的类别
        detected_classes = {detection["class"] for detection in detections}
        
        triggered_types = []
        
        for class_name in self.frame_counters:
            if class_name in detected_classes:
                # 检测到该类别，计数器加1
                self.frame_counters[class_name] += 1
                
                # 检查是否达到触发阈值
                if self.consecutive_threshold == 0 or self.frame_counters[class_name] == self.consecutive_threshold:
                    # 阈值为0时立即触发，或恰好达到阈值时触发（避免每帧都触发）
                    triggered_types.append(class_name)
                    # 触发后重置计数器，防止持续触发
                    self.frame_counters[class_name] = 0
                    self.logger.info(f"行为检测触发: {class_name} (连续 {self.consecutive_threshold} 帧)")
            else:
                # 未检测到该类别，重置计数器
                if self.frame_counters[class_name] > 0:
                    self.logger.debug(f"重置计数器: {class_name} (之前计数: {self.frame_counters[class_name]})")
                self.frame_counters[class_name] = 0
        
        return triggered_types

    def process_frame(self, frame: np.ndarray) -> Tuple[List[Dict], List[str]]:
        """
        对单帧执行检测并更新计数器，返回检测结果与触发的告警类别。
        
        Args:
            frame: BGR 格式的 numpy 数组
            
        Returns:
            (detections, triggered_types)
            detections: 检测结果列表
            triggered_types: 触发的告警类别列表
        """
        # 执行目标检测
        detections = self.detect(frame)
        
        # 更新连续帧计数器
        triggered_types = self.update_counters(detections)
        
        return detections, triggered_types

    def reset(self) -> None:
        """重置所有连续帧计数器（会话结束时调用）。"""
        for class_name in self.frame_counters:
            self.frame_counters[class_name] = 0
        self.logger.info("行为检测器计数器已重置")

    def get_severity(self, class_name: str) -> str:
        """
        获取指定类别的危险等级。
        
        Args:
            class_name: 类别名称
            
        Returns:
            危险等级字符串: "low", "medium", "high"
        """
        return self.CLASS_SEVERITY_MAP.get(class_name, "medium")

    def get_frame_counter(self, class_name: str) -> int:
        """
        获取指定类别的当前连续帧计数。
        
        Args:
            class_name: 类别名称
            
        Returns:
            当前连续帧计数
        """
        return self.frame_counters.get(class_name, 0)

    def get_all_counters(self) -> Dict[str, int]:
        """
        获取所有类别的连续帧计数器状态。
        
        Returns:
            计数器状态字典
        """
        return self.frame_counters.copy()

    def is_model_loaded(self) -> bool:
        """
        检查模型是否已成功加载。
        
        Returns:
            模型加载状态
        """
        return self.model is not None

    @property
    def supported_classes(self) -> List[str]:
        """
        获取支持的检测类别列表。
        
        Returns:
            支持的类别名称列表
        """
        return list(self.CLASS_SEVERITY_MAP.keys())

    @property
    def class_severity_map(self) -> Dict[str, str]:
        """
        获取类别到危险等级的映射。
        
        Returns:
            类别-危险等级映射字典
        """
        return self.CLASS_SEVERITY_MAP.copy()

    def close(self) -> None:
        """释放 YOLOv8 模型资源"""
        if self.model is not None:
            # YOLOv8 模型会自动管理资源，这里只需要清空引用
            self.model = None
            self.logger.info("YOLOv8 模型资源已释放")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()