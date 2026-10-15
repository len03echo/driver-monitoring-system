"""
统计数据路由

提供统计数据的 REST API 接口：
- GET /api/stats/overview - 获取概览统计
- GET /api/stats/trend - 获取告警趋势统计
- GET /api/stats/type - 获取告警类型分布统计

依赖：
- Flask
- StatsService
"""

import traceback
from flask import Blueprint, request, jsonify, current_app
from server.services.stats_service import StatsService

# 创建蓝图
stats_bp = Blueprint('stats', __name__, url_prefix='/api/stats')


@stats_bp.route('/overview', methods=['GET'])
def get_overview():
    """
    获取概览统计数据
    
    Returns:
        200: 概览统计数据
        {
            "code": 200,
            "data": {
                "today_alerts": 23,
                "total_drivers": 45,
                "today_sessions": 8
            },
            "msg": "success"
        }
        500: 服务器错误
    """
    try:
        stats = StatsService.get_overview_stats()
        
        return jsonify({
            'code': 200,
            'data': stats,
            'msg': 'success'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"[/api/stats/overview] 异常: {traceback.format_exc()}")
        return jsonify({
            'code': 500,
            'data': None,
            'msg': f'数据库查询失败: {str(e)}'
        }), 500


@stats_bp.route('/trend', methods=['GET'])
def get_trend():
    """
    获取告警趋势统计数据（近7天）
    
    Returns:
        200: 趋势统计数据
        {
            "code": 200,
            "data": [
                {"date": "2024-01-11", "count": 12},
                {"date": "2024-01-12", "count": 8},
                {"date": "2024-01-13", "count": 15},
                {"date": "2024-01-14", "count": 6},
                {"date": "2024-01-15", "count": 20},
                {"date": "2024-01-16", "count": 11},
                {"date": "2024-01-17", "count": 23}
            ],
            "msg": "success"
        }
        500: 服务器错误
    """
    try:
        # 固定返回近7天数据
        trend_data = StatsService.get_trend_stats(days=7)
        
        return jsonify({
            'code': 200,
            'data': trend_data,
            'msg': 'success'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"[/api/stats/trend] 异常: {traceback.format_exc()}")
        return jsonify({
            'code': 500,
            'data': None,
            'msg': f'数据库查询失败: {str(e)}'
        }), 500


@stats_bp.route('/type', methods=['GET'])
def get_type_distribution():
    """
    获取告警类型分布统计数据
    
    Returns:
        200: 类型分布统计数据
        {
            "code": 200,
            "data": [
                {"alert_type": "phone",      "count": 45},
                {"alert_type": "eye_closed", "count": 38},
                {"alert_type": "yawning",    "count": 27},
                {"alert_type": "smoking",    "count": 15},
                {"alert_type": "head_down",  "count": 12},
                {"alert_type": "cup",        "count": 8}
            ],
            "msg": "success"
        }
        500: 服务器错误
    """
    try:
        type_distribution = StatsService.get_type_distribution_stats()
        
        return jsonify({
            'code': 200,
            'data': type_distribution,
            'msg': 'success'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"[/api/stats/type] 异常: {traceback.format_exc()}")
        return jsonify({
            'code': 500,
            'data': None,
            'msg': f'数据库查询失败: {str(e)}'
        }), 500


if __name__ == "__main__":
    print("Stats API Routes:")
    print("GET /api/stats/overview - 获取概览统计")
    print("GET /api/stats/trend - 获取告警趋势统计")
    print("GET /api/stats/type - 获取告警类型分布统计")
