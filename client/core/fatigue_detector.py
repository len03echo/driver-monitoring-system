"""
基于 MediaPipe 的疲劳检测器

使用 MediaPipe Face Mesh 提取面部关键点，计算 EAR（眼睛纵横比）、MAR（嘴巴纵横比）
及头部姿态角度，维护连续帧计数器，支持 eye_closed/yawning/head_down 检测。

依赖：
- mediapipe
- numpy
- opencv-python
"""

import logging
import math
from typing import List, Dict, Tuple, Optional
import numpy as np
import cv2

try:
    import mediapipe as mp
except ImportError:
    raise ImportError("请安装 mediapipe 库: pip install mediapipe")


class FatigueDetector:
    """
    基于 MediaPipe Face Mesh 的疲劳检测器。
    依赖：mediapipe
    """

    # MediaPipe Face Mesh 关键点索引
    # 左眼关键点 (6个点)
    LEFT_EYE_POINTS = [362, 385, 387, 263, 373, 380]
    # 右眼关键点 (6个点)  
    RIGHT_EYE_POINTS = [33, 160, 158, 133, 153, 144]
    
    # 嘴巴关键点 (用于MAR计算的8个关键点)
    # MediaPipe Face Mesh 标准嘴巴关键点索引：
    # 左嘴角: 61, 右嘴角: 291
    # 上唇: 13(上), 14(中上), 312(中上右)
    # 下唇: 17(中), 18(中下), 200(下)
    # MAR计算需要：左嘴角、上唇3点、右嘴角、下唇3点（共8点）
    MOUTH_POINTS = [61, 13, 14, 312, 291, 17, 18, 200]
    
    # MediaPipe Face Mesh 标准嘴巴轮廓关键点
    # 嘴巴外轮廓（上唇）- 从左到右
    UPPER_LIP_POINTS = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291]
    # 嘴巴外轮廓（下唇）- 从右到左
    LOWER_LIP_POINTS = [291, 375, 321, 405, 314, 17, 84, 181, 91, 146, 61]
    
    # 完整嘴巴轮廓（顺时针，形成闭合轮廓）
    MOUTH_OUTER_POINTS = [
        61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291,  # 上唇（左到右）
        375, 321, 405, 314, 17, 84, 181, 91, 146  # 下唇（右到左，不重复61）
    ]
    # 鼻尖和下巴关键点
    NOSE_TIP = 1
    CHIN = 18

    def __init__(self, config=None) -> None:
        """
        初始化疲劳检测器，加载 MediaPipe Face Mesh 模型。
        
        Args:
            config: 配置对象，包含检测阈值参数
        """
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 设置检测阈值（使用配置或默认值）
        if config and hasattr(config, 'detection'):
            self.EAR_THRESHOLD = config.detection.ear_threshold
            self.MAR_THRESHOLD = config.detection.mar_threshold
            self.HEAD_DOWN_THRESHOLD = config.detection.head_down_angle
            self.EYE_CLOSED_FRAMES = config.detection.eye_closed_frames
            self.YAWNING_FRAMES = config.detection.yawning_frames
        else:
            # 默认阈值
            self.EAR_THRESHOLD = 0.25      # 眼睛纵横比阈值
            self.MAR_THRESHOLD = 0.8       # 嘴巴纵横比阈值（提高默认值）
            self.HEAD_DOWN_THRESHOLD = 30  # 低头角度阈值（度）
            self.EYE_CLOSED_FRAMES = 20    # 闭眼连续帧数
            self.YAWNING_FRAMES = 15       # 哈欠连续帧数
        
        # 连续帧阈值（保持不变）
        self.HEAD_DOWN_FRAMES = 10     # 低头连续帧数
        
        # 初始化 MediaPipe Face Mesh
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # 初始化连续帧计数器
        self.frame_counters: Dict[str, int] = {
            "eye_closed": 0,
            "yawning": 0,
            "head_down": 0
        }
        
        self.logger.info(f"MediaPipe Face Mesh 疲劳检测器初始化成功 - EAR阈值: {self.EAR_THRESHOLD}, MAR阈值: {self.MAR_THRESHOLD}")

    def _calculate_ear(self, eye_points: List[Tuple[float, float]]) -> float:
        """
        计算眼睛纵横比 (Eye Aspect Ratio)
        
        EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)
        
        Args:
            eye_points: 眼睛6个关键点坐标列表 [(x,y), ...]
            
        Returns:
            眼睛纵横比值
        """
        if len(eye_points) != 6:
            return 1.0  # 默认值，表示眼睛睁开
        
        # 计算垂直距离
        vertical_1 = math.sqrt((eye_points[1][0] - eye_points[5][0])**2 + 
                              (eye_points[1][1] - eye_points[5][1])**2)
        vertical_2 = math.sqrt((eye_points[2][0] - eye_points[4][0])**2 + 
                              (eye_points[2][1] - eye_points[4][1])**2)
        
        # 计算水平距离
        horizontal = math.sqrt((eye_points[0][0] - eye_points[3][0])**2 + 
                              (eye_points[0][1] - eye_points[3][1])**2)
        
        # 避免除零
        if horizontal == 0:
            return 1.0
        
        # 计算 EAR
        ear = (vertical_1 + vertical_2) / (2.0 * horizontal)
        return ear

    def _calculate_mar(self, mouth_points: List[Tuple[float, float]]) -> float:
        """
        计算嘴巴纵横比 (Mouth Aspect Ratio)
        
        MAR = (|p2-p8| + |p3-p7| + |p4-p6|) / (3 * |p1-p5|)
        
        Args:
            mouth_points: 嘴巴8个关键点坐标列表 [(x,y), ...]
            
        Returns:
            嘴巴纵横比值
        """
        if len(mouth_points) != 8:
            return 0.0  # 默认值，表示嘴巴闭合
        
        # 计算垂直距离
        vertical_1 = math.sqrt((mouth_points[1][0] - mouth_points[7][0])**2 + 
                              (mouth_points[1][1] - mouth_points[7][1])**2)
        vertical_2 = math.sqrt((mouth_points[2][0] - mouth_points[6][0])**2 + 
                              (mouth_points[2][1] - mouth_points[6][1])**2)
        vertical_3 = math.sqrt((mouth_points[3][0] - mouth_points[5][0])**2 + 
                              (mouth_points[3][1] - mouth_points[5][1])**2)
        
        # 计算水平距离
        horizontal = math.sqrt((mouth_points[0][0] - mouth_points[4][0])**2 + 
                              (mouth_points[0][1] - mouth_points[4][1])**2)
        
        # 避免除零
        if horizontal == 0:
            return 0.0
        
        # 计算 MAR
        mar = (vertical_1 + vertical_2 + vertical_3) / (3.0 * horizontal)
        return mar

    def _calculate_head_angle(self, nose_tip: Tuple[float, float], 
                             chin: Tuple[float, float]) -> float:
        """
        计算头部低头角度
        
        Args:
            nose_tip: 鼻尖坐标 (x, y)
            chin: 下巴坐标 (x, y)
            
        Returns:
            低头角度（度），正值表示低头
        """
        # 计算鼻尖到下巴的向量
        dx = chin[0] - nose_tip[0]
        dy = chin[1] - nose_tip[1]
        
        # 计算与垂直方向的夹角
        angle_rad = math.atan2(abs(dx), dy)
        angle_deg = math.degrees(angle_rad)
        
        return angle_deg

    def detect(self, frame: np.ndarray, draw_landmarks: bool = False) -> Dict[str, float]:
        """
        对单帧图像进行疲劳检测。
        
        Args:
            frame: BGR 格式的 numpy 数组（H×W×3）
            draw_landmarks: 是否在帧上绘制关键点
            
        Returns:
            检测结果字典: {
                "ear": float,           # 眼睛纵横比
                "mar": float,           # 嘴巴纵横比  
                "head_angle": float,    # 头部角度
                "face_detected": bool,  # 是否检测到人脸
                "annotated_frame": np.ndarray  # 带标注的帧（如果draw_landmarks=True）
            }
        """
        # 转换为 RGB 格式
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 执行人脸检测
        results = self.face_mesh.process(rgb_frame)
        
        # 初始化返回值
        detection_result = {
            "ear": 1.0,           # 默认眼睛睁开
            "mar": 0.0,           # 默认嘴巴闭合
            "head_angle": 0.0,    # 默认头部正常
            "face_detected": False
        }
        
        # 复制原始帧用于绘制
        annotated_frame = frame.copy() if draw_landmarks else None
        
        if results.multi_face_landmarks:
            # 取第一个检测到的人脸
            face_landmarks = results.multi_face_landmarks[0]
            
            # 获取图像尺寸
            h, w = frame.shape[:2]
            
            # 提取关键点坐标
            landmarks = []
            for landmark in face_landmarks.landmark:
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                landmarks.append((x, y))
            
            # 提取眼睛关键点
            left_eye = [landmarks[i] for i in self.LEFT_EYE_POINTS]
            right_eye = [landmarks[i] for i in self.RIGHT_EYE_POINTS]
            
            # 计算双眼 EAR 的平均值
            left_ear = self._calculate_ear(left_eye)
            right_ear = self._calculate_ear(right_eye)
            avg_ear = (left_ear + right_ear) / 2.0
            
            # 提取嘴巴关键点并计算 MAR
            mouth = [landmarks[i] for i in self.MOUTH_POINTS]
            mar = self._calculate_mar(mouth)
            
            # 提取鼻尖和下巴点并计算头部角度
            nose_tip = landmarks[self.NOSE_TIP]
            chin = landmarks[self.CHIN]
            head_angle = self._calculate_head_angle(nose_tip, chin)
            
            # 更新检测结果
            detection_result.update({
                "ear": avg_ear,
                "mar": mar,
                "head_angle": head_angle,
                "face_detected": True
            })
            
            # 绘制关键点
            if draw_landmarks and annotated_frame is not None:
                # 绘制眼睛关键点（绿色）
                for point in left_eye + right_eye:
                    cv2.circle(annotated_frame, point, 2, (0, 255, 0), -1)
                
                # 绘制鼻尖和下巴（红色）
                cv2.circle(annotated_frame, nose_tip, 3, (0, 0, 255), -1)
                cv2.circle(annotated_frame, chin, 3, (0, 0, 255), -1)
                
                # 绘制眼睛轮廓
                left_eye_np = np.array(left_eye, dtype=np.int32)
                right_eye_np = np.array(right_eye, dtype=np.int32)
                cv2.polylines(annotated_frame, [left_eye_np], True, (0, 255, 0), 2)
                cv2.polylines(annotated_frame, [right_eye_np], True, (0, 255, 0), 2)
                
                # 绘制完整嘴巴轮廓
                mouth_outer = [landmarks[i] for i in self.MOUTH_OUTER_POINTS]
                
                # 绘制嘴巴关键点（蓝色）
                for point in mouth_outer:
                    cv2.circle(annotated_frame, point, 2, (255, 0, 0), -1)
                
                # 绘制嘴巴轮廓（闭合多边形）
                mouth_outer_np = np.array(mouth_outer, dtype=np.int32)
                cv2.polylines(annotated_frame, [mouth_outer_np], True, (255, 0, 0), 2)
                
                # 显示数值
                cv2.putText(annotated_frame, f"EAR: {avg_ear:.3f}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(annotated_frame, f"MAR: {mar:.3f}", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                cv2.putText(annotated_frame, f"Head: {head_angle:.1f}°", (10, 90), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # 显示阈值状态
                ear_status = "CLOSED" if avg_ear < self.EAR_THRESHOLD else "OPEN"
                mar_status = "YAWNING" if mar > self.MAR_THRESHOLD else "NORMAL"
                head_status = "DOWN" if head_angle > self.HEAD_DOWN_THRESHOLD else "NORMAL"
                
                cv2.putText(annotated_frame, f"Eyes: {ear_status}", (10, 120), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if ear_status == "OPEN" else (0, 0, 255), 2)
                cv2.putText(annotated_frame, f"Mouth: {mar_status}", (10, 145), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0) if mar_status == "NORMAL" else (0, 0, 255), 2)
                cv2.putText(annotated_frame, f"Head: {head_status}", (10, 170), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255) if head_status == "NORMAL" else (0, 255, 255), 2)
            
            self.logger.debug(f"疲劳检测结果: EAR={avg_ear:.3f}, MAR={mar:.3f}, 头部角度={head_angle:.1f}°")
        
        # 添加标注帧到结果中
        if draw_landmarks:
            detection_result["annotated_frame"] = annotated_frame
        
        return detection_result

    def update_counters(self, detection_result: Dict[str, float]) -> List[str]:
        """
        根据检测结果更新连续帧计数器。
        
        Args:
            detection_result: detect() 返回的检测结果字典
            
        Returns:
            本帧触发阈值的疲劳类型列表，如 ["eye_closed", "yawning"]
        """
        if not detection_result["face_detected"]:
            # 未检测到人脸，重置所有计数器
            for fatigue_type in self.frame_counters:
                if self.frame_counters[fatigue_type] > 0:
                    self.logger.debug(f"未检测到人脸，重置计数器: {fatigue_type}")
                self.frame_counters[fatigue_type] = 0
            return []
        
        triggered_types = []
        
        # 检查闭眼状态
        if detection_result["ear"] < self.EAR_THRESHOLD:
            self.frame_counters["eye_closed"] += 1
            if self.frame_counters["eye_closed"] == self.EYE_CLOSED_FRAMES:
                triggered_types.append("eye_closed")
                self.frame_counters["eye_closed"] = 0  # 重置防止重复触发
                self.logger.info(f"疲劳检测触发: eye_closed (连续 {self.EYE_CLOSED_FRAMES} 帧)")
        else:
            if self.frame_counters["eye_closed"] > 0:
                self.logger.debug(f"重置计数器: eye_closed (之前计数: {self.frame_counters['eye_closed']})")
            self.frame_counters["eye_closed"] = 0
        
        # 检查哈欠状态
        if detection_result["mar"] > self.MAR_THRESHOLD:
            self.frame_counters["yawning"] += 1
            if self.frame_counters["yawning"] == self.YAWNING_FRAMES:
                triggered_types.append("yawning")
                self.frame_counters["yawning"] = 0  # 重置防止重复触发
                self.logger.info(f"疲劳检测触发: yawning (连续 {self.YAWNING_FRAMES} 帧)")
        else:
            if self.frame_counters["yawning"] > 0:
                self.logger.debug(f"重置计数器: yawning (之前计数: {self.frame_counters['yawning']})")
            self.frame_counters["yawning"] = 0
        
        # 检查低头状态
        if detection_result["head_angle"] > self.HEAD_DOWN_THRESHOLD:
            self.frame_counters["head_down"] += 1
            if self.frame_counters["head_down"] == self.HEAD_DOWN_FRAMES:
                triggered_types.append("head_down")
                self.frame_counters["head_down"] = 0  # 重置防止重复触发
                self.logger.info(f"疲劳检测触发: head_down (连续 {self.HEAD_DOWN_FRAMES} 帧)")
        else:
            if self.frame_counters["head_down"] > 0:
                self.logger.debug(f"重置计数器: head_down (之前计数: {self.frame_counters['head_down']})")
            self.frame_counters["head_down"] = 0
        
        return triggered_types

    def process_frame(self, frame: np.ndarray, draw_landmarks: bool = False) -> Tuple[Dict[str, float], List[str]]:
        """
        对单帧执行疲劳检测并更新计数器，返回检测结果与触发的疲劳类型。
        
        Args:
            frame: BGR 格式的 numpy 数组
            draw_landmarks: 是否在帧上绘制关键点
            
        Returns:
            (detection_result, triggered_types)
            detection_result: 检测结果字典
            triggered_types: 触发的疲劳类型列表
        """
        # 执行疲劳检测
        detection_result = self.detect(frame, draw_landmarks)
        
        # 更新连续帧计数器
        triggered_types = self.update_counters(detection_result)
        
        return detection_result, triggered_types

    def reset(self) -> None:
        """重置所有连续帧计数器（会话结束时调用）。"""
        for fatigue_type in self.frame_counters:
            self.frame_counters[fatigue_type] = 0
        self.logger.info("疲劳检测器计数器已重置")

    def get_severity(self, fatigue_type: str) -> str:
        """
        获取指定疲劳类型的危险等级。
        
        Args:
            fatigue_type: 疲劳类型名称
            
        Returns:
            危险等级字符串: "low", "medium", "high"
        """
        severity_map = {
            "eye_closed": "high",    # 闭眼 - 高危险
            "yawning": "medium",     # 哈欠 - 中等危险
            "head_down": "medium"    # 低头 - 中等危险
        }
        return severity_map.get(fatigue_type, "medium")

    def get_frame_counter(self, fatigue_type: str) -> int:
        """
        获取指定疲劳类型的当前连续帧计数。
        
        Args:
            fatigue_type: 疲劳类型名称
            
        Returns:
            当前连续帧计数
        """
        return self.frame_counters.get(fatigue_type, 0)

    def get_all_counters(self) -> Dict[str, int]:
        """
        获取所有疲劳类型的连续帧计数器状态。
        
        Returns:
            计数器状态字典
        """
        return self.frame_counters.copy()

    @property
    def supported_fatigue_types(self) -> List[str]:
        """
        获取支持的疲劳检测类型列表。
        
        Returns:
            支持的疲劳类型名称列表
        """
        return list(self.frame_counters.keys())

    def close(self) -> None:
        """释放 MediaPipe 资源"""
        if hasattr(self, 'face_mesh'):
            self.face_mesh.close()
        self.logger.info("MediaPipe Face Mesh 资源已释放")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


if __name__ == "__main__":
    # 测试疲劳检测器
    import sys
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # 创建疲劳检测器
        detector = FatigueDetector()
        
        print("疲劳检测器初始化成功！")
        print(f"支持的疲劳类型: {detector.supported_fatigue_types}")
        print(f"EAR 阈值: {detector.EAR_THRESHOLD}")
        print(f"MAR 阈值: {detector.MAR_THRESHOLD}")
        print(f"低头角度阈值: {detector.HEAD_DOWN_THRESHOLD}°")
        
        # 测试空白图像
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result, triggered = detector.process_frame(test_frame)
        print(f"测试结果: {result}")
        print(f"触发类型: {triggered}")
        
        detector.close()
        
    except Exception as e:
        print(f"疲劳检测器测试失败: {e}")
        sys.exit(1)