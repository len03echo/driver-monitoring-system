"""
预警引擎

汇总检测结果，执行 30 秒冷却判断，触发音效和视觉报警，保存截图，
写入数据库告警记录。支持多种告警类型的统一处理。

依赖：
- pygame (音效播放)
- opencv-python (截图保存)
- numpy
"""

import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import cv2

try:
    import pygame
    pygame.mixer.init()
except ImportError:
    raise ImportError("请安装 pygame 库: pip install pygame")


class AlertEngine:
    """
    预警引擎，负责汇总检测结果并触发告警。
    """

    # 告警冷却时间（秒）
    COOLDOWN_SECONDS = 30
    
    # 告警类型到危险等级的映射
    ALERT_SEVERITY_MAP = {
        # 行为检测
        "phone": "medium",
        "cup": "low", 
        "smoking": "high",
        # 疲劳检测
        "eye_closed": "high",
        "yawning": "medium",
        "head_down": "medium"
    }

    def __init__(self, snapshots_dir: str = "snapshots", 
                 alert_sound_path: Optional[str] = None) -> None:
        """
        初始化预警引擎。
        
        Args:
            snapshots_dir: 截图保存目录
            alert_sound_path: 告警音效文件路径
        """
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 截图保存目录
        self.snapshots_dir = snapshots_dir
        self._ensure_snapshots_dir()
        
        # 告警音效
        self.alert_sound_path = alert_sound_path
        self.alert_sound = None
        self._load_alert_sound()
        
        # 冷却状态跟踪 {alert_type: last_trigger_time}
        self.cooldown_tracker: Dict[str, float] = {}
        
        # 当前会话信息
        self.current_session_id: Optional[int] = None
        self.current_driver_id: Optional[int] = None
        
        self.logger.info(f"预警引擎初始化成功，截图目录: {self.snapshots_dir}")

    def _ensure_snapshots_dir(self) -> None:
        """确保截图目录存在"""
        try:
            os.makedirs(self.snapshots_dir, exist_ok=True)
            self.logger.debug(f"截图目录已准备: {self.snapshots_dir}")
        except Exception as e:
            self.logger.error(f"创建截图目录失败: {e}")
            raise

    def _load_alert_sound(self) -> None:
        """加载告警音效"""
        if self.alert_sound_path and os.path.exists(self.alert_sound_path):
            try:
                self.alert_sound = pygame.mixer.Sound(self.alert_sound_path)
                self.logger.info(f"告警音效加载成功: {self.alert_sound_path}")
            except Exception as e:
                self.logger.warning(f"告警音效加载失败: {e}")
                self.alert_sound = None
        else:
            self.logger.info("未配置告警音效或文件不存在")

    def set_session_info(self, session_id: int, driver_id: int) -> None:
        """
        设置当前会话信息。
        
        Args:
            session_id: 会话ID
            driver_id: 驾驶员ID
        """
        self.current_session_id = session_id
        self.current_driver_id = driver_id
        self.logger.info(f"设置会话信息: 会话ID={session_id}, 驾驶员ID={driver_id}")

    def clear_session_info(self) -> None:
        """清除当前会话信息"""
        self.current_session_id = None
        self.current_driver_id = None
        self.logger.info("会话信息已清除")

    def reset_cooldown(self) -> None:
        """重置所有告警类型的冷却状态（会话开始时调用）"""
        self.cooldown_tracker.clear()
        self.logger.info("告警冷却状态已重置")

    def _is_in_cooldown(self, alert_type: str) -> bool:
        """
        检查指定告警类型是否在冷却期内。
        
        Args:
            alert_type: 告警类型
            
        Returns:
            是否在冷却期内
        """
        if alert_type not in self.cooldown_tracker:
            return False
        
        last_trigger_time = self.cooldown_tracker[alert_type]
        current_time = time.time()
        
        return (current_time - last_trigger_time) < self.COOLDOWN_SECONDS

    def _update_cooldown(self, alert_type: str) -> None:
        """
        更新指定告警类型的冷却时间。
        
        Args:
            alert_type: 告警类型
        """
        self.cooldown_tracker[alert_type] = time.time()

    def _generate_snapshot_filename(self, alert_type: str) -> str:
        """
        生成截图文件名。
        
        格式: {session_id}_{alert_type}_{timestamp}.jpg
        
        Args:
            alert_type: 告警类型
            
        Returns:
            截图文件名
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        session_id = self.current_session_id or "unknown"
        filename = f"{session_id}_{alert_type}_{timestamp}.jpg"
        return filename

    def _save_snapshot(self, frame: np.ndarray, alert_type: str) -> Optional[str]:
        """
        保存告警截图。
        
        Args:
            frame: BGR 格式的图像帧
            alert_type: 告警类型
            
        Returns:
            截图文件路径，保存失败返回 None
        """
        try:
            filename = self._generate_snapshot_filename(alert_type)
            filepath = os.path.join(self.snapshots_dir, filename)
            
            # 保存图像
            success = cv2.imwrite(filepath, frame)
            
            if success:
                self.logger.info(f"截图保存成功: {filepath}")
                return filepath
            else:
                self.logger.error(f"截图保存失败: {filepath}")
                return None
                
        except Exception as e:
            self.logger.error(f"保存截图时出错: {e}")
            return None

    def _play_alert_sound(self) -> None:
        """播放告警音效"""
        if self.alert_sound:
            try:
                self.alert_sound.play()
                self.logger.debug("告警音效播放")
            except Exception as e:
                self.logger.warning(f"告警音效播放失败: {e}")
        else:
            self.logger.debug("未配置告警音效，跳过播放")

    def _write_alert_record(self, alert_type: str, severity: str, 
                           snapshot_path: Optional[str], db_client) -> bool:
        """
        写入告警记录到数据库。
        
        Args:
            alert_type: 告警类型
            severity: 危险等级
            snapshot_path: 截图路径
            db_client: 数据库客户端
            
        Returns:
            写入是否成功
        """
        if not self.current_session_id or not self.current_driver_id:
            self.logger.error("会话信息未设置，无法写入告警记录")
            return False
        
        try:
            # 只保存文件名，不包含完整路径
            snapshot_filename = None
            if snapshot_path:
                snapshot_filename = os.path.basename(snapshot_path)
            
            alert_id = db_client.insert_alert(
                driver_id=self.current_driver_id,
                session_id=self.current_session_id,
                alert_type=alert_type,
                severity=severity,
                snapshot_path=snapshot_filename
            )
            
            # 更新会话的告警计数
            db_client.increment_session_alerts(self.current_session_id)
            
            self.logger.info(f"告警记录写入成功: ID={alert_id}, 类型={alert_type}, 等级={severity}")
            return True
            
        except Exception as e:
            self.logger.error(f"写入告警记录失败: {e}")
            return False

    def get_alert_severity(self, alert_type: str) -> str:
        """
        获取告警类型的危险等级。
        
        Args:
            alert_type: 告警类型
            
        Returns:
            危险等级: "low", "medium", "high"
        """
        return self.ALERT_SEVERITY_MAP.get(alert_type, "medium")

    def process_alerts(self, frame: np.ndarray, triggered_alerts: List[str], 
                      db_client) -> List[Dict[str, Any]]:
        """
        处理触发的告警列表。
        
        Args:
            frame: 当前视频帧
            triggered_alerts: 触发的告警类型列表
            db_client: 数据库客户端
            
        Returns:
            实际处理的告警信息列表
        """
        processed_alerts = []
        
        for alert_type in triggered_alerts:
            # 检查冷却状态
            if self._is_in_cooldown(alert_type):
                remaining_time = self.COOLDOWN_SECONDS - (time.time() - self.cooldown_tracker[alert_type])
                self.logger.debug(f"告警类型 {alert_type} 在冷却期内，剩余 {remaining_time:.1f} 秒")
                continue
            
            # 获取危险等级
            severity = self.get_alert_severity(alert_type)
            
            # 保存截图
            snapshot_path = self._save_snapshot(frame, alert_type)
            
            # 播放告警音效
            self._play_alert_sound()
            
            # 写入数据库
            db_success = self._write_alert_record(alert_type, severity, snapshot_path, db_client)
            
            # 更新冷却状态
            self._update_cooldown(alert_type)
            
            # 记录处理结果
            alert_info = {
                "type": alert_type,
                "severity": severity,
                "timestamp": datetime.now(),
                "snapshot_path": snapshot_path,
                "db_recorded": db_success
            }
            processed_alerts.append(alert_info)
            
            self.logger.warning(f"告警触发: {alert_type} ({severity})")
        
        return processed_alerts

    def get_cooldown_status(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有告警类型的冷却状态。
        
        Returns:
            冷却状态字典: {alert_type: {"in_cooldown": bool, "remaining_time": float}}
        """
        current_time = time.time()
        status = {}
        
        for alert_type in self.ALERT_SEVERITY_MAP.keys():
            if alert_type in self.cooldown_tracker:
                last_trigger_time = self.cooldown_tracker[alert_type]
                elapsed_time = current_time - last_trigger_time
                remaining_time = max(0, self.COOLDOWN_SECONDS - elapsed_time)
                in_cooldown = remaining_time > 0
            else:
                remaining_time = 0
                in_cooldown = False
            
            status[alert_type] = {
                "in_cooldown": in_cooldown,
                "remaining_time": remaining_time
            }
        
        return status

    def force_trigger_alert(self, frame: np.ndarray, alert_type: str, 
                           db_client) -> Dict[str, Any]:
        """
        强制触发告警（忽略冷却期，用于测试）。
        
        Args:
            frame: 当前视频帧
            alert_type: 告警类型
            db_client: 数据库客户端
            
        Returns:
            告警信息字典
        """
        self.logger.info(f"强制触发告警: {alert_type}")
        
        # 临时清除该类型的冷却状态
        if alert_type in self.cooldown_tracker:
            del self.cooldown_tracker[alert_type]
        
        # 处理告警
        processed_alerts = self.process_alerts(frame, [alert_type], db_client)
        
        return processed_alerts[0] if processed_alerts else {}

    @property
    def supported_alert_types(self) -> List[str]:
        """
        获取支持的告警类型列表。
        
        Returns:
            支持的告警类型列表
        """
        return list(self.ALERT_SEVERITY_MAP.keys())

    @property
    def cooldown_seconds(self) -> int:
        """
        获取冷却时间（秒）。
        
        Returns:
            冷却时间
        """
        return self.COOLDOWN_SECONDS

    def close(self) -> None:
        """释放资源"""
        try:
            if pygame.mixer.get_init():
                pygame.mixer.quit()
            self.logger.info("预警引擎资源已释放")
        except Exception as e:
            self.logger.warning(f"释放预警引擎资源时出错: {e}")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


if __name__ == "__main__":
    # 测试预警引擎
    import sys
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # 创建预警引擎
        engine = AlertEngine()
        
        print("预警引擎初始化成功！")
        print(f"支持的告警类型: {engine.supported_alert_types}")
        print(f"冷却时间: {engine.cooldown_seconds} 秒")
        print(f"截图目录: {engine.snapshots_dir}")
        
        # 测试冷却状态
        status = engine.get_cooldown_status()
        print(f"冷却状态: {len(status)} 个告警类型")
        
        # 测试截图文件名生成
        engine.set_session_info(123, 456)
        filename = engine._generate_snapshot_filename("phone")
        print(f"截图文件名示例: {filename}")
        
        engine.close()
        
    except Exception as e:
        print(f"预警引擎测试失败: {e}")
        sys.exit(1)