"""
检测线程

在独立线程中运行视频检测循环，协调 VideoSource 读帧与三路检测器调用，
通过 Qt 信号向主线程传递帧画面与状态信息。

依赖：
- PyQt5
- numpy
- opencv-python
"""

import logging
import time
from typing import Optional, Dict, Any, List
import numpy as np
import cv2
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker

from .video_source import VideoSource
from .behavior_detector import BehaviorDetector
from .fatigue_detector import FatigueDetector
from .face_recognizer import FaceRecognizer
from .alert_engine import AlertEngine


class DetectionThread(QThread):
    """
    检测线程，在独立线程中运行视频检测循环。
    """
    
    # Qt 信号定义
    frame_ready = pyqtSignal(np.ndarray)  # 新帧准备就绪
    detection_result = pyqtSignal(dict)   # 检测结果
    status_changed = pyqtSignal(str)      # 状态变化
    error_occurred = pyqtSignal(str)      # 错误发生
    fps_updated = pyqtSignal(float)       # FPS 更新
    video_ended = pyqtSignal()            # 视频播放结束
    
    def __init__(self, parent=None):
        """
        初始化检测线程。
        
        Args:
            parent: 父对象
        """
        super().__init__(parent)
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 线程控制
        self._running = False
        self._paused = False
        self._mutex = QMutex()
        
        # 组件实例
        self.video_source: Optional[VideoSource] = None
        self.behavior_detector: Optional[BehaviorDetector] = None
        self.fatigue_detector: Optional[FatigueDetector] = None
        self.face_recognizer: Optional[FaceRecognizer] = None
        self.alert_engine: Optional[AlertEngine] = None
        self.db_client = None  # 数据库客户端（用于预警引擎写入告警记录）
        
        # 性能统计
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.target_fps = 30  # 目标 FPS
        self.frame_interval = 1.0 / self.target_fps
        
        # 检测配置
        self.enable_behavior_detection = True
        self.enable_fatigue_detection = True
        self.enable_face_recognition = True
        self.draw_landmarks = False  # 是否绘制关键点
        
        self.logger.info("检测线程初始化完成")
    
    def set_video_source(self, video_source: VideoSource) -> None:
        """
        设置视频源。
        
        Args:
            video_source: 视频源实例
        """
        with QMutexLocker(self._mutex):
            self.video_source = video_source
            self.logger.info(f"设置视频源: {type(video_source).__name__}")
    
    def set_detectors(self, behavior_detector: Optional[BehaviorDetector] = None,
                     fatigue_detector: Optional[FatigueDetector] = None,
                     face_recognizer: Optional[FaceRecognizer] = None) -> None:
        """
        设置检测器。
        
        Args:
            behavior_detector: 行为检测器
            fatigue_detector: 疲劳检测器
            face_recognizer: 人脸识别器
        """
        with QMutexLocker(self._mutex):
            if behavior_detector is not None:
                self.behavior_detector = behavior_detector
                self.logger.info("设置行为检测器")
            
            if fatigue_detector is not None:
                self.fatigue_detector = fatigue_detector
                self.logger.info("设置疲劳检测器")
            
            if face_recognizer is not None:
                self.face_recognizer = face_recognizer
                self.logger.info("设置人脸识别器")
    
    def set_alert_engine(self, alert_engine: AlertEngine) -> None:
        """
        设置预警引擎。
        
        Args:
            alert_engine: 预警引擎实例
        """
        with QMutexLocker(self._mutex):
            self.alert_engine = alert_engine
            self.logger.info("设置预警引擎")
    
    def set_detection_config(self, enable_behavior: bool = True,
                           enable_fatigue: bool = True,
                           enable_face: bool = True,
                           draw_landmarks: bool = False) -> None:
        """
        设置检测配置。
        
        Args:
            enable_behavior: 是否启用行为检测
            enable_fatigue: 是否启用疲劳检测
            enable_face: 是否启用人脸识别
            draw_landmarks: 是否绘制关键点
        """
        with QMutexLocker(self._mutex):
            self.enable_behavior_detection = enable_behavior
            self.enable_fatigue_detection = enable_fatigue
            self.enable_face_recognition = enable_face
            self.draw_landmarks = draw_landmarks
            
            self.logger.info(f"检测配置更新: 行为={enable_behavior}, 疲劳={enable_fatigue}, 人脸={enable_face}, 绘制关键点={draw_landmarks}")
    
    def set_target_fps(self, fps: float) -> None:
        """
        设置目标 FPS。
        
        Args:
            fps: 目标帧率
        """
        with QMutexLocker(self._mutex):
            self.target_fps = max(1, min(60, fps))  # 限制在 1-60 FPS
            self.frame_interval = 1.0 / self.target_fps
            self.logger.info(f"设置目标 FPS: {self.target_fps}")
    
    def start_detection(self) -> None:
        """开始检测"""
        if not self.video_source:
            self.error_occurred.emit("未设置视频源")
            return
        
        with QMutexLocker(self._mutex):
            self._running = True
            self._paused = False
        
        self.status_changed.emit("starting")
        self.start()  # 启动线程
        self.logger.info("开始检测")
    
    def stop_detection(self) -> None:
        """停止检测"""
        with QMutexLocker(self._mutex):
            self._running = False
            self._paused = False
        
        self.status_changed.emit("stopping")
        self.wait()  # 等待线程结束
        self.logger.info("停止检测")
    
    def pause_detection(self) -> None:
        """暂停检测"""
        with QMutexLocker(self._mutex):
            self._paused = True
        
        self.status_changed.emit("paused")
        self.logger.info("暂停检测")
    
    def resume_detection(self) -> None:
        """恢复检测"""
        with QMutexLocker(self._mutex):
            self._paused = False
        
        self.status_changed.emit("running")
        self.logger.info("恢复检测")
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        with QMutexLocker(self._mutex):
            return self._running
    
    def is_paused(self) -> bool:
        """检查是否已暂停"""
        with QMutexLocker(self._mutex):
            return self._paused
    
    def run(self) -> None:
        """线程主循环"""
        try:
            self.status_changed.emit("running")
            self.logger.info("检测线程开始运行")

            # 打开视频源
            if not self.video_source or not self.video_source.open():
                self.logger.error("视频源打开失败")
                self.error_occurred.emit("视频源打开失败，请检查摄像头或视频文件")
                return
            
            # 重置性能计数器
            self.fps_counter = 0
            self.fps_start_time = time.time()
            
            while True:
                # 检查停止标志
                with QMutexLocker(self._mutex):
                    if not self._running:
                        break
                    
                    # 检查暂停状态
                    if self._paused:
                        self.msleep(50)  # 暂停时短暂休眠
                        continue
                
                # 记录帧开始时间
                frame_start_time = time.time()
                
                # 读取视频帧
                success, frame = self._read_frame()
                if not success:
                    if frame is None:  # 视频结束
                        self.video_ended.emit()
                        break
                    else:  # 读取错误
                        continue
                
                # 执行检测
                detection_results = self._process_frame(frame)
                
                # 决定发送哪个帧（原始帧还是带标注的帧）
                display_frame = frame.copy()
                
                # 绘制 YOLOv8 检测结果
                if detection_results and self.enable_behavior_detection:
                    behavior_data = detection_results.get("detections", {}).get("behavior", {})
                    if "objects" in behavior_data and behavior_data["objects"]:
                        display_frame = self._draw_yolo_detections(display_frame, behavior_data["objects"])
                
                # 绘制疲劳检测关键点（如果启用）
                if detection_results and self.draw_landmarks:
                    fatigue_data = detection_results.get("detections", {}).get("fatigue", {})
                    if "metrics" in fatigue_data and "annotated_frame" in fatigue_data["metrics"]:
                        display_frame = fatigue_data["metrics"]["annotated_frame"]
                
                # 发送显示帧
                self.frame_ready.emit(display_frame)
                
                # 发送检测结果
                if detection_results:
                    self.detection_result.emit(detection_results)
                
                # 更新 FPS
                self._update_fps()
                
                # 控制帧率
                self._control_frame_rate(frame_start_time)
            
        except Exception as e:
            self.logger.error(f"检测线程运行错误: {e}")
            self.error_occurred.emit(f"检测线程错误: {str(e)}")
        
        finally:
            self.status_changed.emit("stopped")
            self.logger.info("检测线程已停止")
    
    def _read_frame(self) -> tuple:
        """
        读取视频帧。
        
        Returns:
            (成功标志, 帧数据)
        """
        try:
            if not self.video_source:
                return False, None
            
            # video_source.read() 返回 (success, frame) 元组
            success, frame = self.video_source.read()
            if not success or frame is None:
                return False, None  # 视频结束或读取失败
            
            return True, frame
            
        except Exception as e:
            self.logger.error(f"读取视频帧失败: {e}")
            self.error_occurred.emit(f"读取视频帧失败: {str(e)}")
            return False, None
    
    def _process_frame(self, frame: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        处理单帧检测。
        
        Args:
            frame: 输入帧
            
        Returns:
            检测结果字典
        """
        try:
            results = {
                "timestamp": time.time(),
                "frame_shape": frame.shape,
                "detections": {}
            }
            
            # 行为检测
            if self.enable_behavior_detection and self.behavior_detector:
                try:
                    detections, triggered = self.behavior_detector.process_frame(frame)
                    results["detections"]["behavior"] = {
                        "objects": detections,
                        "triggered_alerts": triggered
                    }
                    # 调试日志：记录检测到的对象
                    if detections:
                        self.logger.debug(f"行为检测: 检测到 {len(detections)} 个对象 - {[d['class'] for d in detections]}")
                except Exception as e:
                    self.logger.warning(f"行为检测失败: {e}")
                    results["detections"]["behavior"] = {"objects": [], "triggered_alerts": []}
            
            # 疲劳检测
            if self.enable_fatigue_detection and self.fatigue_detector:
                try:
                    fatigue_result, triggered = self.fatigue_detector.process_frame(frame, self.draw_landmarks)
                    results["detections"]["fatigue"] = {
                        "metrics": fatigue_result,
                        "triggered_alerts": triggered
                    }
                except Exception as e:
                    self.logger.warning(f"疲劳检测失败: {e}")
                    results["detections"]["fatigue"] = {"triggered_alerts": []}
            
            # 人脸识别
            if self.enable_face_recognition and self.face_recognizer:
                try:
                    # 在监测过程中只做特征提取，不做完整认证（避免每帧都查数据库）
                    feature = self.face_recognizer.extract_feature(frame)
                    results["detections"]["face"] = {
                        "face_detected": feature is not None,
                        "feature": feature
                    }
                except Exception as e:
                    self.logger.warning(f"人脸识别失败: {e}")
                    results["detections"]["face"] = {"face_detected": False}
            
            # 汇总告警
            all_alerts = []
            for detection_type, detection_result in results["detections"].items():
                if "triggered_alerts" in detection_result:
                    all_alerts.extend(detection_result["triggered_alerts"])
            
            results["all_alerts"] = all_alerts

            # 通过预警引擎处理告警（写数据库、截图、播放音效）
            if all_alerts and self.alert_engine and self.db_client:
                try:
                    self.alert_engine.process_alerts(frame, all_alerts, self.db_client)
                except Exception as e:
                    self.logger.warning(f"预警引擎处理失败: {e}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"处理帧检测失败: {e}")
            return None
    
    def _update_fps(self) -> None:
        """更新 FPS 统计"""
        self.fps_counter += 1
        
        # 每秒更新一次 FPS
        current_time = time.time()
        if current_time - self.fps_start_time >= 1.0:
            fps = self.fps_counter / (current_time - self.fps_start_time)
            self.fps_updated.emit(fps)
            
            # 重置计数器
            self.fps_counter = 0
            self.fps_start_time = current_time
    
    def _control_frame_rate(self, frame_start_time: float) -> None:
        """
        控制帧率。
        
        Args:
            frame_start_time: 帧处理开始时间
        """
        frame_process_time = time.time() - frame_start_time
        sleep_time = self.frame_interval - frame_process_time
        
        if sleep_time > 0:
            self.msleep(int(sleep_time * 1000))  # 转换为毫秒
    
    def _draw_yolo_detections(self, frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """
        在帧上绘制 YOLOv8 检测结果。
        
        Args:
            frame: 输入帧
            detections: 检测结果列表，每项包含 {"class": str, "confidence": float, "bbox": [x1,y1,x2,y2]}
            
        Returns:
            绘制后的帧
        """
        # 类别颜色映射（使用新模型的类别）
        class_colors = {
            "smoke": (0, 0, 255),      # 红色 - 高危
            "phone": (0, 165, 255),    # 橙色 - 中危
            "drink": (0, 255, 255),    # 黄色 - 低危
        }
        
        # 类别中文标签映射
        class_labels = {
            "smoke": "Smoking",
            "phone": "Phone",
            "drink": "Drinking",
        }
        
        annotated_frame = frame.copy()
        
        for detection in detections:
            class_name = detection["class"]
            confidence = detection["confidence"]
            bbox = detection["bbox"]  # [x1, y1, x2, y2]
            
            # 获取颜色
            color = class_colors.get(class_name, (0, 255, 0))
            
            # 绘制边界框
            x1, y1, x2, y2 = map(int, bbox)
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            
            # 准备标签文本（使用英文）
            label_text = class_labels.get(class_name, class_name)
            label = f"{label_text} {confidence:.2f}"
            
            # 计算文本大小
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 2
            (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            
            # 绘制文本背景
            cv2.rectangle(annotated_frame, 
                         (x1, y1 - text_height - baseline - 5), 
                         (x1 + text_width, y1), 
                         color, -1)
            
            # 绘制文本
            cv2.putText(annotated_frame, label, 
                       (x1, y1 - baseline - 5), 
                       font, font_scale, (255, 255, 255), thickness)
        
        return annotated_frame
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取线程状态信息。
        
        Returns:
            状态信息字典
        """
        with QMutexLocker(self._mutex):
            return {
                "running": self._running,
                "paused": self._paused,
                "target_fps": self.target_fps,
                "has_video_source": self.video_source is not None,
                "has_behavior_detector": self.behavior_detector is not None,
                "has_fatigue_detector": self.fatigue_detector is not None,
                "has_face_recognizer": self.face_recognizer is not None,
                "has_alert_engine": self.alert_engine is not None,
                "detection_config": {
                    "behavior": self.enable_behavior_detection,
                    "fatigue": self.enable_fatigue_detection,
                    "face": self.enable_face_recognition
                }
            }
    
    def cleanup(self) -> None:
        """清理资源"""
        try:
            # 停止检测
            if self.is_running():
                self.stop_detection()
            
            # 清理组件
            with QMutexLocker(self._mutex):
                # 清理视频源
                if self.video_source:
                    try:
                        self.video_source.release()
                    except Exception as e:
                        self.logger.warning(f"释放视频源时出错: {e}")
                    finally:
                        self.video_source = None
                
                # 清理行为检测器
                if self.behavior_detector:
                    try:
                        self.behavior_detector.close()
                    except Exception as e:
                        self.logger.warning(f"关闭行为检测器时出错: {e}")
                    finally:
                        self.behavior_detector = None
                
                # 清理疲劳检测器
                if self.fatigue_detector:
                    try:
                        self.fatigue_detector.close()
                    except Exception as e:
                        self.logger.warning(f"关闭疲劳检测器时出错: {e}")
                    finally:
                        self.fatigue_detector = None
                
                # 清理人脸识别器
                if self.face_recognizer:
                    try:
                        self.face_recognizer.close()
                    except Exception as e:
                        self.logger.warning(f"关闭人脸识别器时出错: {e}")
                    finally:
                        self.face_recognizer = None
                
                # 清理预警引擎
                if self.alert_engine:
                    try:
                        self.alert_engine.close()
                    except Exception as e:
                        self.logger.warning(f"关闭预警引擎时出错: {e}")
                    finally:
                        self.alert_engine = None
            
            self.logger.info("检测线程资源清理完成")
            
        except Exception as e:
            self.logger.error(f"清理检测线程资源时出错: {e}")
    
    def __del__(self):
        """析构函数"""
        self.cleanup()


if __name__ == "__main__":
    # 测试检测线程
    import sys
    from PyQt5.QtWidgets import QApplication
    from .video_source import Camera
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    app = QApplication(sys.argv)
    
    try:
        # 创建检测线程
        thread = DetectionThread()
        
        # 设置视频源
        camera = Camera(camera_id=0)
        thread.set_video_source(camera)
        
        # 连接信号
        def on_frame_ready(frame):
            print(f"收到帧: {frame.shape}")
        
        def on_detection_result(result):
            print(f"检测结果: {len(result.get('all_alerts', []))} 个告警")
        
        def on_status_changed(status):
            print(f"状态变化: {status}")
        
        def on_error_occurred(error):
            print(f"错误: {error}")
        
        def on_fps_updated(fps):
            print(f"FPS: {fps:.1f}")
        
        thread.frame_ready.connect(on_frame_ready)
        thread.detection_result.connect(on_detection_result)
        thread.status_changed.connect(on_status_changed)
        thread.error_occurred.connect(on_error_occurred)
        thread.fps_updated.connect(on_fps_updated)
        
        print("检测线程测试启动...")
        print(f"状态: {thread.get_status()}")
        
        # 启动检测（需要在实际应用中调用）
        # thread.start_detection()
        
        print("检测线程测试完成！")
        
    except Exception as e:
        print(f"检测线程测试失败: {e}")
        sys.exit(1)
    
    finally:
        app.quit()