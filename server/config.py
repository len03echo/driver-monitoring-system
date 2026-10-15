"""
智能驾驶员状态监测系统 - 服务端配置加载模块

负责从 YAML 文件加载配置，提供配置验证和默认值处理。
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from sqlalchemy.engine import URL


@dataclass
class DatabaseConfig:
    """数据库连接配置"""
    host: str
    port: int
    user: str
    password: str
    name: str


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str
    port: int
    debug: bool


@dataclass
class SnapshotConfig:
    """截图文件配置"""
    dir: str


@dataclass
class PaginationConfig:
    """分页配置"""
    default_page_size: int
    max_page_size: int


@dataclass
class CorsConfig:
    """CORS 配置"""
    allowed_origins: List[str]


@dataclass
class FlaskConfig:
    """Flask 服务端完整配置"""
    database: DatabaseConfig
    server: ServerConfig
    snapshot: SnapshotConfig
    pagination: PaginationConfig
    cors: CorsConfig


def load_config(config_path: Optional[str] = None) -> FlaskConfig:
    """
    从 YAML 文件加载服务端配置
    
    Args:
        config_path: 配置文件路径，默认为 None（自动定位到 server/config.yaml）
        
    Returns:
        FlaskConfig: 解析后的配置对象
        
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
        
        server_config = ServerConfig(
            host=os.getenv("SERVER_HOST") or config_data.get("server", {}).get("host", "127.0.0.1"),
            port=int(os.getenv("SERVER_PORT") or config_data.get("server", {}).get("port", 5000)),
            debug=(os.getenv("SERVER_DEBUG").lower() in ("1", "true", "yes"))
                  if os.getenv("SERVER_DEBUG") is not None
                  else config_data.get("server", {}).get("debug", False)
        )
        
        snapshot_config = SnapshotConfig(
            dir=_resolve_local_path(Path(__file__).parent.parent / "client", config_data.get("snapshot", {}).get("dir", "snapshots/"))
        )
        
        pagination_config = PaginationConfig(
            default_page_size=config_data.get("pagination", {}).get("default_page_size", 20),
            max_page_size=config_data.get("pagination", {}).get("max_page_size", 100)
        )
        
        cors_config = CorsConfig(
            allowed_origins=config_data.get("cors", {}).get("allowed_origins", ["http://127.0.0.1:3000", "http://localhost:3000"])
        )
        
        return FlaskConfig(
            database=database_config,
            server=server_config,
            snapshot=snapshot_config,
            pagination=pagination_config,
            cors=cors_config
        )
        
    except KeyError as e:
        raise ValueError(f"缺少必填字段: {e}")


def _resolve_local_path(base_dir: Path, value: str) -> str:
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


def validate_config(config: FlaskConfig) -> None:
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
    
    # 验证服务器端口范围
    if not (1 <= config.server.port <= 65535):
        raise ValueError(f"服务器端口必须在 1-65535 范围内: {config.server.port}")
    
    # 验证分页参数
    if config.pagination.default_page_size <= 0:
        raise ValueError(f"默认分页大小必须大于 0: {config.pagination.default_page_size}")
    
    if config.pagination.max_page_size <= 0:
        raise ValueError(f"最大分页大小必须大于 0: {config.pagination.max_page_size}")
    
    if config.pagination.default_page_size > config.pagination.max_page_size:
        raise ValueError(f"默认分页大小不能超过最大分页大小: {config.pagination.default_page_size} > {config.pagination.max_page_size}")
    
    # 验证截图目录路径
    if not config.snapshot.dir:
        raise ValueError("截图目录路径不能为空")
    
    # 验证 CORS 配置
    if not isinstance(config.cors.allowed_origins, list):
        raise ValueError("CORS 允许来源必须是列表格式")


def get_database_url(config: FlaskConfig) -> str:
    """
    生成数据库连接 URL
    
    Args:
        config: 配置对象
        
    Returns:
        数据库连接 URL 字符串
    """
    db_config = config.database
    # URL.create safely escapes special characters in a password (e.g. @, /, :).
    return URL.create(
        "mysql+pymysql", username=db_config.user, password=db_config.password or None,
        host=db_config.host, port=db_config.port, database=db_config.name,
    ).render_as_string(hide_password=False)


if __name__ == "__main__":
    # 测试配置加载
    try:
        config = load_config()
        validate_config(config)
        print("配置加载成功:")
        print(f"数据库: {config.database.host}:{config.database.port}/{config.database.name}")
        print(f"服务器: {config.server.host}:{config.server.port}")
        print(f"调试模式: {config.server.debug}")
        print(f"截图目录: {config.snapshot.dir}")
        print(f"分页配置: 默认 {config.pagination.default_page_size}，最大 {config.pagination.max_page_size}")
        print(f"CORS 来源: {config.cors.allowed_origins}")
        print("数据库 URL: [已省略凭据]")
    except Exception as e:
        print(f"配置加载失败: {e}")