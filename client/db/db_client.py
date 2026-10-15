"""
智能驾驶员状态监测系统 - 客户端数据库操作类

封装所有 pymysql 数据库操作，提供驾驶员查询、会话管理、告警写入等方法，
统一异常处理与日志记录。
"""

import pymysql
import logging
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import contextmanager


class DBClient:
    """
    数据库操作封装类，使用 pymysql 直连 MySQL 8.0
    """
    
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        """
        初始化数据库连接
        
        Args:
            host: MySQL 服务器地址
            port: MySQL 端口
            user: 数据库用户名
            password: 数据库密码
            database: 数据库名称
            
        Raises:
            ConnectionError: 连接失败时抛出
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection: Optional[pymysql.connections.Connection] = None
        
        # 配置日志
        self.logger = logging.getLogger(__name__)
        
        # 建立数据库连接
        self._connect()
    
    def _connect(self) -> None:
        """
        建立数据库连接
        
        Raises:
            ConnectionError: 连接失败时抛出
        """
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                autocommit=True,  # 自动提交事务
                connect_timeout=10,  # 连接超时 10 秒
                read_timeout=30,  # 读取超时 30 秒
                write_timeout=30  # 写入超时 30 秒
            )
            self.logger.info(f"数据库连接成功: {self.host}:{self.port}/{self.database}")
        except pymysql.Error as e:
            error_msg = f"数据库连接失败: {e}"
            self.logger.error(error_msg)
            raise ConnectionError(error_msg)
    
    @contextmanager
    def _get_cursor(self):
        """
        获取数据库游标的上下文管理器
        
        Yields:
            pymysql.cursors.Cursor: 数据库游标
            
        Raises:
            ConnectionError: 连接断开时抛出
        """
        if not self.connection or not self.connection.open:
            self._connect()
        
        cursor = None
        try:
            cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            yield cursor
        except pymysql.Error as e:
            self.logger.error(f"数据库操作错误: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
    
    # ---- 驾驶员相关操作 ----
    
    def get_all_drivers(self) -> List[Dict[str, Any]]:
        """
        查询所有驾驶员档案（含 face_feature 字节数据）
        
        Returns:
            List[Dict]: 驾驶员字典列表
            
        Raises:
            Exception: 数据库查询失败时抛出
        """
        try:
            with self._get_cursor() as cursor:
                sql = """
                SELECT id, name, employee_id, face_feature, avatar_path, created_at
                FROM drivers
                ORDER BY created_at DESC
                """
                cursor.execute(sql)
                drivers = cursor.fetchall()
                
                self.logger.info(f"查询到 {len(drivers)} 个驾驶员档案")
                return drivers
                
        except Exception as e:
            self.logger.error(f"查询驾驶员列表失败: {e}")
            raise
    
    def get_driver_by_employee_id(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """
        按工号查询驾驶员
        
        Args:
            employee_id: 驾驶员工号
            
        Returns:
            Optional[Dict]: 驾驶员信息字典，不存在返回 None
            
        Raises:
            Exception: 数据库查询失败时抛出
        """
        try:
            with self._get_cursor() as cursor:
                sql = """
                SELECT id, name, employee_id, face_feature, avatar_path, created_at
                FROM drivers
                WHERE employee_id = %s
                """
                cursor.execute(sql, (employee_id,))
                driver = cursor.fetchone()
                
                if driver:
                    self.logger.info(f"找到驾驶员: {driver['name']} ({employee_id})")
                else:
                    self.logger.info(f"未找到工号为 {employee_id} 的驾驶员")
                
                return driver
                
        except Exception as e:
            self.logger.error(f"按工号查询驾驶员失败: {e}")
            raise
    
    def get_driver_by_id(self, driver_id: int) -> Optional[Dict[str, Any]]:
        """
        按 ID 查询驾驶员
        
        Args:
            driver_id: 驾驶员 ID
            
        Returns:
            Optional[Dict]: 驾驶员信息字典，不存在返回 None
        """
        try:
            with self._get_cursor() as cursor:
                sql = """
                SELECT id, name, employee_id, face_feature, avatar_path, created_at
                FROM drivers
                WHERE id = %s
                """
                cursor.execute(sql, (driver_id,))
                return cursor.fetchone()
                
        except Exception as e:
            self.logger.error(f"按 ID 查询驾驶员失败: {e}")
            raise
    
    def insert_driver(
        self,
        name: str,
        employee_id: str,
        face_feature: Optional[bytes],
        avatar_path: Optional[str]
    ) -> int:
        """
        插入驾驶员档案
        
        Args:
            name: 驾驶员姓名
            employee_id: 驾驶员工号
            face_feature: 人脸特征向量字节数据（可为 None）
            avatar_path: 头像路径（可为 None）
            
        Returns:
            int: 新插入记录的 id
            
        Raises:
            ValueError: 工号已存在时抛出
            Exception: 数据库操作失败时抛出
        """
        try:
            # 检查工号是否已存在
            existing_driver = self.get_driver_by_employee_id(employee_id)
            if existing_driver:
                raise ValueError(f"工号 {employee_id} 已存在")
            
            with self._get_cursor() as cursor:
                sql = """
                INSERT INTO drivers (name, employee_id, face_feature, avatar_path)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (name, employee_id, face_feature, avatar_path))
                driver_id = cursor.lastrowid
                
                self.logger.info(f"成功插入驾驶员: {name} ({employee_id}), ID: {driver_id}")
                return driver_id
                
        except ValueError:
            raise  # 重新抛出 ValueError
        except Exception as e:
            self.logger.error(f"插入驾驶员档案失败: {e}")
            raise
    
    def update_driver_face_feature(self, driver_id: int, face_feature: bytes) -> bool:
        """
        更新驾驶员人脸特征向量
        
        Args:
            driver_id: 驾驶员 ID
            face_feature: 人脸特征向量字节数据
            
        Returns:
            bool: 更新成功返回 True
        """
        try:
            with self._get_cursor() as cursor:
                sql = """
                UPDATE drivers
                SET face_feature = %s
                WHERE id = %s
                """
                affected_rows = cursor.execute(sql, (face_feature, driver_id))
                
                if affected_rows > 0:
                    self.logger.info(f"成功更新驾驶员 {driver_id} 的人脸特征")
                    return True
                else:
                    self.logger.warning(f"驾驶员 ID {driver_id} 不存在")
                    return False
                    
        except Exception as e:
            self.logger.error(f"更新驾驶员人脸特征失败: {e}")
            raise
    
    def delete_driver(self, driver_id: int) -> bool:
        """
        删除驾驶员档案（级联删除会话与告警记录）
        
        Args:
            driver_id: 驾驶员 ID
            
        Returns:
            bool: 删除成功返回 True
            
        Raises:
            Exception: 数据库操作失败时抛出
        """
        try:
            with self._get_cursor() as cursor:
                sql = "DELETE FROM drivers WHERE id = %s"
                affected_rows = cursor.execute(sql, (driver_id,))
                
                if affected_rows > 0:
                    self.logger.info(f"成功删除驾驶员 ID: {driver_id}")
                    return True
                else:
                    self.logger.warning(f"驾驶员 ID {driver_id} 不存在")
                    return False
                    
        except Exception as e:
            self.logger.error(f"删除驾驶员档案失败: {e}")
            raise
    
    # ---- 会话相关操作 ----
    
    def create_session(self, driver_id: int) -> int:
        """
        创建新的监测会话
        
        Args:
            driver_id: 驾驶员 ID
            
        Returns:
            int: 新会话的 id
            
        Raises:
            Exception: 数据库操作失败时抛出
        """
        try:
            with self._get_cursor() as cursor:
                sql = """
                INSERT INTO sessions (driver_id, start_time)
                VALUES (%s, %s)
                """
                start_time = datetime.now()
                cursor.execute(sql, (driver_id, start_time))
                session_id = cursor.lastrowid
                
                self.logger.info(f"创建新会话: 驾驶员 {driver_id}, 会话 ID: {session_id}")
                return session_id
                
        except Exception as e:
            self.logger.error(f"创建监测会话失败: {e}")
            raise
    
    def close_session(self, session_id: int, total_alerts: int) -> bool:
        """
        更新会话的 end_time 与 total_alerts
        
        Args:
            session_id: 会话 ID
            total_alerts: 总告警次数
            
        Returns:
            bool: 更新成功返回 True
            
        Raises:
            Exception: 数据库操作失败时抛出
        """
        try:
            with self._get_cursor() as cursor:
                sql = """
                UPDATE sessions
                SET end_time = %s, total_alerts = %s
                WHERE id = %s
                """
                end_time = datetime.now()
                affected_rows = cursor.execute(sql, (end_time, total_alerts, session_id))
                
                if affected_rows > 0:
                    self.logger.info(f"成功关闭会话 {session_id}, 总告警数: {total_alerts}")
                    return True
                else:
                    self.logger.warning(f"会话 ID {session_id} 不存在")
                    return False
                    
        except Exception as e:
            self.logger.error(f"关闭监测会话失败: {e}")
            raise
    
    def increment_session_alerts(self, session_id: int) -> bool:
        """
        将指定会话的 total_alerts 加 1
        
        Args:
            session_id: 会话 ID
            
        Returns:
            bool: 更新成功返回 True
            
        Raises:
            Exception: 数据库操作失败时抛出
        """
        try:
            with self._get_cursor() as cursor:
                sql = """
                UPDATE sessions
                SET total_alerts = total_alerts + 1
                WHERE id = %s
                """
                affected_rows = cursor.execute(sql, (session_id,))
                
                if affected_rows > 0:
                    self.logger.debug(f"会话 {session_id} 告警计数 +1")
                    return True
                else:
                    self.logger.warning(f"会话 ID {session_id} 不存在")
                    return False
                    
        except Exception as e:
            self.logger.error(f"更新会话告警计数失败: {e}")
            raise
    
    # ---- 告警记录相关操作 ----
    
    def insert_alert(
        self,
        driver_id: int,
        session_id: int,
        alert_type: str,
        severity: str,
        snapshot_path: Optional[str]
    ) -> int:
        """
        插入告警记录
        
        Args:
            driver_id: 驾驶员 ID
            session_id: 会话 ID
            alert_type: 告警类型
            severity: 危险等级
            snapshot_path: 截图路径（可为 None）
            
        Returns:
            int: 新插入记录的 id
            
        Raises:
            Exception: 数据库操作失败时抛出
        """
        try:
            with self._get_cursor() as cursor:
                sql = """
                INSERT INTO alert_records (driver_id, session_id, alert_type, severity, snapshot_path)
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (driver_id, session_id, alert_type, severity, snapshot_path))
                alert_id = cursor.lastrowid
                
                self.logger.info(f"插入告警记录: 类型 {alert_type}, 等级 {severity}, ID: {alert_id}")
                return alert_id
                
        except Exception as e:
            self.logger.error(f"插入告警记录失败: {e}")
            raise
    
    def get_alerts_by_session(self, session_id: int) -> List[Dict[str, Any]]:
        """
        查询指定会话的所有告警记录
        
        Args:
            session_id: 会话 ID
            
        Returns:
            List[Dict]: 告警记录列表
        """
        try:
            with self._get_cursor() as cursor:
                sql = """
                SELECT id, driver_id, session_id, alert_type, severity, snapshot_path, created_at
                FROM alert_records
                WHERE session_id = %s
                ORDER BY created_at DESC
                """
                cursor.execute(sql, (session_id,))
                alerts = cursor.fetchall()
                
                self.logger.info(f"会话 {session_id} 共有 {len(alerts)} 条告警记录")
                return alerts
                
        except Exception as e:
            self.logger.error(f"查询会话告警记录失败: {e}")
            raise
    
    # ---- 连接管理 ----
    
    def close(self) -> None:
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.logger.info("数据库连接已关闭")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


# ---- 工具函数 ----

def numpy_to_bytes(feature_vector: np.ndarray) -> bytes:
    """
    将 numpy 数组转换为字节数据（用于存储到 BLOB 字段）
    
    Args:
        feature_vector: numpy 数组
        
    Returns:
        bytes: 序列化后的字节数据
    """
    return feature_vector.tobytes()


def bytes_to_numpy(feature_bytes: bytes, dtype: np.dtype = np.float32) -> np.ndarray:
    """
    将字节数据转换为 numpy 数组（从 BLOB 字段读取）
    
    Args:
        feature_bytes: 字节数据
        dtype: 数据类型，默认 float32
        
    Returns:
        np.ndarray: 反序列化后的 numpy 数组
    """
    return np.frombuffer(feature_bytes, dtype=dtype)


if __name__ == "__main__":
    # 测试数据库连接
    import sys
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # 使用默认配置测试连接
        db_client = DBClient(
            host="127.0.0.1",
            port=3306,
            user="root",
            password="",
            database="driver_monitor"
        )
        
        print("数据库连接测试成功！")
        
        # 测试查询驾驶员列表
        drivers = db_client.get_all_drivers()
        print(f"当前数据库中有 {len(drivers)} 个驾驶员档案")
        
        db_client.close()
        
    except Exception as e:
        print(f"数据库连接测试失败: {e}")
        sys.exit(1)