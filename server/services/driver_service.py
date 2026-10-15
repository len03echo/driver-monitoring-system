"""
驾驶员档案业务逻辑服务

提供驾驶员档案的增删查改操作。

依赖：
- SQLAlchemy
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.exc import IntegrityError
from server.models.models import db, Driver


class DriverService:
    """驾驶员档案服务类"""
    
    @staticmethod
    def get_all_drivers() -> List[Driver]:
        """
        获取所有驾驶员列表
        
        Returns:
            驾驶员列表
        """
        return db.session.query(Driver).order_by(Driver.created_at.desc()).all()
    
    @staticmethod
    def get_driver_by_id(driver_id: int) -> Optional[Driver]:
        """
        根据 ID 获取驾驶员
        
        Args:
            driver_id: 驾驶员 ID
            
        Returns:
            驾驶员对象，不存在则返回 None
        """
        return db.session.get(Driver, driver_id)
    
    @staticmethod
    def get_driver_by_employee_id(employee_id: str) -> Optional[Driver]:
        """
        根据工号获取驾驶员
        
        Args:
            employee_id: 工号
            
        Returns:
            驾驶员对象，不存在则返回 None
        """
        return db.session.query(Driver).filter_by(employee_id=employee_id).first()
    
    @staticmethod
    def create_driver(name: str, employee_id: str) -> Driver:
        """
        创建新驾驶员档案（仅基础档案，不包含人脸特征）
        
        Args:
            name: 驾驶员姓名
            employee_id: 工号
            
        Returns:
            创建的驾驶员对象
            
        Raises:
            ValueError: 参数验证失败或工号重复
        """
        # 参数验证
        if not name or not name.strip():
            raise ValueError("驾驶员姓名不能为空")
        
        if not employee_id or not employee_id.strip():
            raise ValueError("工号不能为空")
        
        if len(name) > 50:
            raise ValueError("驾驶员姓名长度不能超过 50 个字符")
        
        if len(employee_id) > 30:
            raise ValueError("工号长度不能超过 30 个字符")
        
        # 检查工号是否已存在
        existing_driver = DriverService.get_driver_by_employee_id(employee_id)
        if existing_driver:
            raise ValueError(f"工号 {employee_id} 已存在")
        
        # 创建驾驶员（face_feature 为 NULL）
        driver = Driver(
            name=name.strip(),
            employee_id=employee_id.strip(),
            face_feature=None,
            avatar_path=None
        )
        
        try:
            db.session.add(driver)
            db.session.commit()
            return driver
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"工号 {employee_id} 已存在") from e
    
    @staticmethod
    def delete_driver(driver_id: int) -> bool:
        """
        删除驾驶员档案
        
        Args:
            driver_id: 驾驶员 ID
            
        Returns:
            删除成功返回 True，驾驶员不存在返回 False
        """
        driver = DriverService.get_driver_by_id(driver_id)
        if not driver:
            return False
        
        db.session.delete(driver)
        db.session.commit()
        return True
    
    @staticmethod
    def get_driver_count() -> int:
        """
        获取驾驶员总数
        
        Returns:
            驾驶员总数
        """
        return db.session.query(Driver).count()


if __name__ == "__main__":
    print("DriverService 业务逻辑服务")
    print("提供驾驶员档案的增删查改操作")
