"""
告警记录业务逻辑服务

提供告警记录的查询、筛选、分页操作。

依赖：
- SQLAlchemy
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy import and_, or_
from server.models.models import db, AlertRecord, Driver, Session, AlertTypeEnum, SeverityEnum


class AlertService:
    """告警记录服务类"""
    
    @staticmethod
    def get_alerts_with_filters(
        page: int = 1,
        page_size: int = 20,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
        driver_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Tuple[List[AlertRecord], int]:
        """
        获取告警记录列表（支持分页和筛选）
        
        Args:
            page: 页码（从 1 开始）
            page_size: 每页数量
            alert_type: 告警类型筛选（可选）
            severity: 危险等级筛选（可选）
            driver_id: 驾驶员 ID 筛选（可选）
            start_date: 开始日期筛选（可选）
            end_date: 结束日期筛选（可选）
            
        Returns:
            (告警记录列表, 总数)
            
        Raises:
            ValueError: 参数验证失败
        """
        # 参数验证
        if page < 1:
            raise ValueError("页码必须大于等于 1")
        
        if page_size < 1:
            raise ValueError("每页数量必须大于等于 1")
        
        if page_size > 100:
            raise ValueError("每页数量不能超过 100")
        
        # 构建查询
        query = db.session.query(AlertRecord)
        
        # 应用筛选条件
        filters = []
        
        # 告警类型筛选
        if alert_type:
            try:
                alert_type_enum = AlertTypeEnum(alert_type)
                filters.append(AlertRecord.alert_type == alert_type_enum)
            except ValueError:
                raise ValueError(f"无效的告警类型: {alert_type}")
        
        # 危险等级筛选
        if severity:
            valid_severities = ['low', 'medium', 'high']
            if severity not in valid_severities:
                raise ValueError(f"severity 参数值非法，允许值：{', '.join(valid_severities)}")
            try:
                severity_enum = SeverityEnum(severity)
                filters.append(AlertRecord.severity == severity_enum)
            except ValueError:
                raise ValueError(f"severity 参数值非法，允许值：{', '.join(valid_severities)}")
        
        # 驾驶员筛选
        if driver_id is not None:
            filters.append(AlertRecord.driver_id == driver_id)
        
        # 日期范围筛选
        if start_date:
            filters.append(AlertRecord.created_at >= start_date)
        
        if end_date:
            filters.append(AlertRecord.created_at <= end_date)
        
        # 应用所有筛选条件
        if filters:
            query = query.filter(and_(*filters))
        
        # 获取总数
        total = query.count()
        
        # 排序（按创建时间降序）
        query = query.order_by(AlertRecord.created_at.desc())
        
        # 分页
        offset = (page - 1) * page_size
        alerts = query.offset(offset).limit(page_size).all()
        
        return alerts, total
    
    @staticmethod
    def get_alert_by_id(alert_id: int) -> Optional[AlertRecord]:
        """
        根据 ID 获取告警记录
        
        Args:
            alert_id: 告警记录 ID
            
        Returns:
            告警记录对象，不存在则返回 None
        """
        return db.session.get(AlertRecord, alert_id)
    
    @staticmethod
    def create_alert(
        driver_id: int,
        session_id: int,
        alert_type: str,
        severity: str,
        snapshot_path: Optional[str] = None
    ) -> AlertRecord:
        """
        创建告警记录
        
        Args:
            driver_id: 驾驶员 ID
            session_id: 会话 ID
            alert_type: 告警类型
            severity: 危险等级
            snapshot_path: 截图路径（可选）
            
        Returns:
            创建的告警记录对象
            
        Raises:
            ValueError: 参数验证失败
        """
        # 验证告警类型
        try:
            alert_type_enum = AlertTypeEnum(alert_type)
        except ValueError:
            raise ValueError(f"无效的告警类型: {alert_type}")
        
        # 验证危险等级
        try:
            severity_enum = SeverityEnum(severity)
        except ValueError:
            raise ValueError(f"无效的危险等级: {severity}")
        
        # 验证驾驶员存在
        driver = db.session.get(Driver, driver_id)
        if not driver:
            raise ValueError(f"驾驶员 ID {driver_id} 不存在")
        
        # 验证会话存在
        session = db.session.get(Session, session_id)
        if not session:
            raise ValueError(f"会话 ID {session_id} 不存在")
        
        # 创建告警记录
        alert = AlertRecord(
            driver_id=driver_id,
            session_id=session_id,
            alert_type=alert_type_enum,
            severity=severity_enum,
            snapshot_path=snapshot_path
        )
        
        db.session.add(alert)
        
        # 更新会话的告警计数
        session.total_alerts += 1
        
        db.session.commit()
        return alert
    
    @staticmethod
    def get_alert_count() -> int:
        """
        获取告警记录总数
        
        Returns:
            告警记录总数
        """
        return db.session.query(AlertRecord).count()
    
    @staticmethod
    def get_alert_count_by_type() -> Dict[str, int]:
        """
        获取各类型告警的数量统计
        
        Returns:
            字典，键为告警类型，值为数量
        """
        from sqlalchemy import func
        
        results = db.session.query(
            AlertRecord.alert_type,
            func.count(AlertRecord.id)
        ).group_by(AlertRecord.alert_type).all()
        
        return {
            alert_type.value if isinstance(alert_type, AlertTypeEnum) else alert_type: count
            for alert_type, count in results
        }
    
    @staticmethod
    def get_alert_count_by_severity() -> Dict[str, int]:
        """
        获取各等级告警的数量统计
        
        Returns:
            字典，键为危险等级，值为数量
        """
        from sqlalchemy import func
        
        results = db.session.query(
            AlertRecord.severity,
            func.count(AlertRecord.id)
        ).group_by(AlertRecord.severity).all()
        
        return {
            severity.value if isinstance(severity, SeverityEnum) else severity: count
            for severity, count in results
        }
    
    @staticmethod
    def get_alerts_by_driver(driver_id: int, limit: int = 10) -> List[AlertRecord]:
        """
        获取指定驾驶员的最近告警记录
        
        Args:
            driver_id: 驾驶员 ID
            limit: 返回数量限制
            
        Returns:
            告警记录列表
        """
        return db.session.query(AlertRecord).filter_by(
            driver_id=driver_id
        ).order_by(
            AlertRecord.created_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_alerts_by_session(session_id: int) -> List[AlertRecord]:
        """
        获取指定会话的所有告警记录
        
        Args:
            session_id: 会话 ID
            
        Returns:
            告警记录列表
        """
        return db.session.query(AlertRecord).filter_by(
            session_id=session_id
        ).order_by(
            AlertRecord.created_at.asc()
        ).all()


if __name__ == "__main__":
    print("AlertService 业务逻辑服务")
    print("提供告警记录的查询、筛选、分页操作")
