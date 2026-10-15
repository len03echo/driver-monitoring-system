"""
统计数据业务逻辑服务

提供统计数据的聚合查询操作。

依赖：
- SQLAlchemy
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from server.models.models import db, Driver, Session, AlertRecord, AlertTypeEnum


class StatsService:
    """统计数据服务类"""
    
    @staticmethod
    def get_overview_stats() -> Dict[str, int]:
        """
        获取概览统计数据
        
        Returns:
            字典，包含三项统计数据：
            - today_alerts: 今日告警总数
            - total_drivers: 已注册驾驶员总数
            - today_sessions: 今日监测会话数
        """
        # 获取今日日期范围
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        # 今日告警总数
        today_alerts = db.session.query(func.count(AlertRecord.id)).filter(
            and_(
                AlertRecord.created_at >= today_start,
                AlertRecord.created_at <= today_end
            )
        ).scalar() or 0
        
        # 已注册驾驶员总数
        total_drivers = db.session.query(func.count(Driver.id)).scalar() or 0
        
        # 今日监测会话数
        today_sessions = db.session.query(func.count(Session.id)).filter(
            and_(
                Session.start_time >= today_start,
                Session.start_time <= today_end
            )
        ).scalar() or 0
        
        return {
            'today_alerts': today_alerts,
            'total_drivers': total_drivers,
            'today_sessions': today_sessions
        }
    
    @staticmethod
    def get_trend_stats(days: int = 7) -> List[Dict[str, Any]]:
        """
        获取告警趋势统计数据
        
        Args:
            days: 统计天数，默认 7 天
            
        Returns:
            列表，每个元素包含：
            - date: 日期（YYYY-MM-DD 格式）
            - count: 当天告警数量
            
            按日期升序排列
        """
        # 计算起始日期
        end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        start_date = (end_date - timedelta(days=days-1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 查询每天的告警数量
        results = db.session.query(
            func.date(AlertRecord.created_at).label('date'),
            func.count(AlertRecord.id).label('count')
        ).filter(
            and_(
                AlertRecord.created_at >= start_date,
                AlertRecord.created_at <= end_date
            )
        ).group_by(
            func.date(AlertRecord.created_at)
        ).order_by(
            func.date(AlertRecord.created_at).asc()
        ).all()
        
        # 转换为字典格式
        trend_data = {}
        for date, count in results:
            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            trend_data[date_str] = count
        
        # 填充缺失的日期（数量为 0）
        trend_list = []
        current_date = start_date
        for i in range(days):
            date_str = current_date.strftime('%Y-%m-%d')
            trend_list.append({
                'date': date_str,
                'count': trend_data.get(date_str, 0)
            })
            current_date += timedelta(days=1)
        
        return trend_list
    
    @staticmethod
    def get_type_distribution_stats() -> List[Dict[str, Any]]:
        """
        获取告警类型分布统计数据
        
        Returns:
            列表，每个元素包含：
            - alert_type: 告警类型
            - count: 数量
            
            按数量降序排列
        """
        # 查询各类型告警数量
        results = db.session.query(
            AlertRecord.alert_type,
            func.count(AlertRecord.id).label('count')
        ).group_by(
            AlertRecord.alert_type
        ).order_by(
            func.count(AlertRecord.id).desc()
        ).all()
        
        # 转换为字典格式
        type_distribution = []
        for alert_type, count in results:
            alert_type_str = alert_type.value if isinstance(alert_type, AlertTypeEnum) else alert_type
            
            type_distribution.append({
                'alert_type': alert_type_str,
                'count': count
            })
        
        return type_distribution
    
if __name__ == "__main__":
    print("StatsService 业务逻辑服务")
    print("提供统计数据的聚合查询操作")
