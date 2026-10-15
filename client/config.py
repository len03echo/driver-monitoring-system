"""
智能驾驶员状态监测系统 - 客户端配置加载模块

负责从 YAML 文件加载配置，提供配置验证和默认值处理。
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """数据库连接配置"""
    host: str
    port: int
    user: str
    password: str
    name: str


@dataclass
class CameraConfig:
    """摄像头配置"""
    device_index: int
    fps_min: int
    mirror_display: bool


@dataclass
class ModelConfig:
    """模型配置"""
    yolo_path: str
    insightface_name: str


@dataclass
class DetectionConfig:
    """检测参数配置"""
    behavior_threshold: int
    ear_threshold: float
    mar_threshold: float
    head_down_angle: float
    eye_closed_frames: int
    yawning_frames: int
    face_similarity_threshold: float


@dataclass
class AlertConfig:
    """告警配置"""
    cooldown_seconds: int
    sound_path: str
    snapshot_dir: str


@dataclass
class YoloConfig:
    """YOLOv8 性能配置"""
    inference_timeout_ms: int
    inference_size: int
    use_half: bool


@dataclass
class ClientConfig:
    """客户端完整配置"""
    database: DatabaseConfig
    camera: CameraConfig
    model: ModelConfig
    detection: DetectionConfig
    alert: AlertConfig
    yolo: YoloConfig


def load_config(config_path: Optional[str] = None) -> ClientConfig:
    """
    从 YAML 文件加载客户端配置
    
    Args:
        config_path: 配置文件路径，默认为 None（自动定位到 client/config.yaml）
        
    Returns:
        ClientConfig: 解析后的配置对象
        
    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置文件格式错误或缺少必填字段
        yaml.YAMLError: YAML 解析错误
    """
    # 如果未指定路径，使用相对于本文件的路径
    if config_path is None:
        config_path = Path(__file__).parent / "config.yaml"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    try:
        with open(str(config_path), 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"配置文件 YAML 格式错误: {e}")
    
    # Respect environment variables provided by the caller and load local .env only as defaults.
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

    if not isinstance(config_data, dict):
        raise ValueError("配置文件根节点必须是字典格式")
    
    # 验证必填字段并创建配置对象
    try:
        database_config = DatabaseConfig(
            host=os.getenv("DB_HOST") or _get_required_field(config_data, "database.host"),
            port=int(os.getenv("DB_PORT") or _get_required_field(config_data, "database.port")),
            user=os.getenv("DB_USER") or _get_required_field(config_data, "database.user"),
            password=os.getenv("DB_PASSWORD") or config_data.get("database", {}).get("password", ""),
            name=os.getenv("DB_NAME") or _get_required_field(config_data, "database.name")
        )
        
        camera_config = CameraConfig(
            device_index=config_data.get("camera", {}).get("device_index", 0),
            fps_min=config_data.get("camera", {}).get("fps_min", 15),
            mirror_display=config_data.get("camera", {}).get("mirror_display", False)
        )
        
        model_config = ModelConfig(
            yolo_path=_resolve_local_path(config_path.parent, _get_required_field(config_data, "model.yolo_path")),
            insightface_name=config_data.get("model", {}).get("insightface_name", "buffalo_l")
        )
        
        detection_config = DetectionConfig(
            behavior_threshold=config_data.get("detection", {}).get("behavior_threshold", 10),
            ear_threshold=config_data.get("detection", {}).get("ear_threshold", 0.25),
            mar_threshold=config_data.get("detection", {}).get("mar_threshold", 0.6),
            head_down_angle=config_data.get("detection", {}).get("head_down_angle", 30.0),
            eye_closed_frames=config_data.get("detection", {}).get("eye_closed_frames", 20),
            yawning_frames=config_data.get("detection", {}).get("yawning_frames", 15),
            face_similarity_threshold=config_data.get("detection", {}).get("face_similarity_threshold", 0.5)
        )
        
        alert_config = AlertConfig(
            cooldown_seconds=config_data.get("alert", {}).get("cooldown_seconds", 30),
            sound_path=_resolve_local_path(config_path.parent, config_data.get("alert", {}).get("sound_path", "assets/alert.wav")),
            snapshot_dir=_resolve_local_path(config_path.parent, config_data.get("alert", {}).get("snapshot_dir", "snapshots/"))
        )
        
        yolo_config = YoloConfig(
            inference_timeout_ms=config_data.get("yolo", {}).get("inference_timeout_ms", 200),
            inference_size=config_data.get("yolo", {}).get("inference_size", 320),
            use_half=config_data.get("yolo", {}).get("use_half", False)
        )
        
        return ClientConfig(
            database=database_config,
            camera=camera_config,
            model=model_config,
            detection=detection_config,
            alert=alert_config,
            yolo=yolo_config
        )
        
    except KeyError as e:
        raise ValueError(f"缺少必填字段: {e}")


def _resolve_local_path(base_dir: Path, value: str) -> str:
    """Interpret relative resources beside the YAML file, independent of the current working directory."""
    path = Path(value).expanduser()
    return str(path if path.is_absolute() else (base_dir / path).resolve())


def _get_required_field(config_data: Dict[str, Any], field_path: str) -> Any:
    """
    获取必填配置字段
    
    Args:
        config_data: 配置数据字典
        field_path: 字段路径，如 "database.host"
        
    Returns:
        字段值
        
    Raises:
        KeyError: 字段不存在
    """
    keys = field_path.split('.')
    value = config_data
    
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise KeyError(field_path)
        value = value[key]
    
    return value


def validate_config(config: ClientConfig) -> None:
    """
    验证配置参数的合理性
    
    Args:
        config: 配置对象
        
    Raises:
        ValueError: 配置参数不合理
    """
    # 验证数据库端口范围
    if not (1 <= config.database.port <= 65535):
        raise ValueError(f"数据库端口必须在 1-65535 范围内: {config.database.port}")
    
    # 验证摄像头设备索引
    if config.camera.device_index < 0:
        raise ValueError(f"摄像头设备索引不能为负数: {config.camera.device_index}")
    
    # 验证帧率
    if config.camera.fps_min <= 0:
        raise ValueError(f"最低帧率必须大于 0: {config.camera.fps_min}")
    
    # 验证检测阈值范围
    if not (0.0 <= config.detection.ear_threshold <= 1.0):
        raise ValueError(f"EAR 阈值必须在 0.0-1.0 范围内: {config.detection.ear_threshold}")
    
    if not (0.0 <= config.detection.mar_threshold <= 2.0):
        raise ValueError(f"MAR 阈值必须在 0.0-2.0 范围内: {config.detection.mar_threshold}")
    
    if not (0.0 <= config.detection.head_down_angle <= 90.0):
        raise ValueError(f"低头角度阈值必须在 0.0-90.0 度范围内: {config.detection.head_down_angle}")
    
    if not (0.0 <= config.detection.face_similarity_threshold <= 1.0):
        raise ValueError(f"人脸相似度阈值必须在 0.0-1.0 范围内: {config.detection.face_similarity_threshold}")
    
    # 验证连续帧数
    if config.detection.behavior_threshold <= 0:
        raise ValueError(f"行为检测连续帧阈值必须大于 0: {config.detection.behavior_threshold}")
    
    if config.detection.eye_closed_frames <= 0:
        raise ValueError(f"闭眼连续帧阈值必须大于 0: {config.detection.eye_closed_frames}")
    
    if config.detection.yawning_frames <= 0:
        raise ValueError(f"哈欠连续帧阈值必须大于 0: {config.detection.yawning_frames}")
    
    # 验证冷却时间
    if config.alert.cooldown_seconds <= 0:
        raise ValueError(f"告警冷却时间必须大于 0 秒: {config.alert.cooldown_seconds}")
    
    # 验证 YOLOv8 配置
    if config.yolo.inference_size not in [320, 416, 640]:
        raise ValueError(f"YOLOv8 推理尺寸必须是 320, 416 或 640: {config.yolo.inference_size}")
    
    if not isinstance(config.yolo.use_half, bool):
        raise ValueError(f"YOLOv8 use_half 必须是布尔值: {config.yolo.use_half}")


if __name__ == "__main__":
    # 测试配置加载
    try:
        config = load_config()
        validate_config(config)
        print("配置加载成功:")
        print(f"数据库: {config.database.host}:{config.database.port}/{config.database.name}")
        print(f"摄像头设备: {config.camera.device_index}")
        print(f"YOLOv8 模型: {config.model.yolo_path}")
        print(f"行为检测阈值: {config.detection.behavior_threshold} 帧")
        print(f"EAR 阈值: {config.detection.ear_threshold}")
        print(f"告警冷却: {config.alert.cooldown_seconds} 秒")
        print(f"YOLOv8 推理尺寸: {config.yolo.inference_size}")
        print(f"YOLOv8 半精度: {config.yolo.use_half}")
    except Exception as e:
        print(f"配置加载失败: {e}")