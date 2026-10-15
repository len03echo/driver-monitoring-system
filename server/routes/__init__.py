"""
Flask 路由蓝图
"""

from .drivers import drivers_bp
from .alerts import alerts_bp
from .stats import stats_bp
from .snapshots import snapshots_bp

__all__ = ['drivers_bp', 'alerts_bp', 'stats_bp', 'snapshots_bp']
