"""
告警记录路由

提供告警记录的 REST API 接口：
- GET /api/alerts - 获取告警记录列表（支持分页和筛选）

依赖：
- Flask
- AlertService
"""

import traceback
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from server.services.alert_service import AlertService

# 创建蓝图
alerts_bp = Blueprint('alerts', __name__, url_prefix='/api/alerts')


@alerts_bp.route('', methods=['GET'])
def get_alerts():
    """
    获取告警记录列表（分页+筛选）
    
    Query Parameters:
        page (int, optional): 页码，默认 1
        page_size (int, optional): 每页数量，默认 20
        alert_type (str, optional): 告警类型筛选
        severity (str, optional): 危险等级筛选
        driver_id (int, optional): 驾驶员 ID 筛选
        start_date (str, optional): 开始日期筛选（YYYY-MM-DD）
        end_date (str, optional): 结束日期筛选（YYYY-MM-DD）
    
    Returns:
        200: 告警记录列表
        {
            "code": 200,
            "data": {
                "total": 156,
                "page": 1,
                "page_size": 20,
                "items": [
                    {
                        "id": 88,
                        "driver_id": 1,
                        "driver_name": "张三",
                        "session_id": 12,
                        "alert_type": "phone",
                        "severity": "medium",
                        "snapshot_path": "12_phone_20240117142035.jpg",
                        "snapshot_url": "/snapshots/12_phone_20240117142035.jpg",
                        "created_at": "2024-01-17T14:20:35"
                    }
                ]
            },
            "msg": "success"
        }
        400: 参数错误
        500: 服务器错误
    """
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        # 获取筛选参数
        alert_type = request.args.get('alert_type', '').strip() or None
        severity = request.args.get('severity', '').strip() or None
        driver_id = request.args.get('driver_id', type=int)
        
        # 解析日期参数（YYYY-MM-DD格式）
        start_date = None
        end_date = None
        
        start_date_str = request.args.get('start_date', '').strip()
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'code': 400,
                    'data': None,
                    'msg': f'无效的开始日期格式: {start_date_str}，请使用 YYYY-MM-DD 格式'
                }), 400
        
        end_date_str = request.args.get('end_date', '').strip()
        if end_date_str:
            try:
                # 结束日期包含当天，所以设置为当天23:59:59
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                end_date = end_date.replace(hour=23, minute=59, second=59)
            except ValueError:
                return jsonify({
                    'code': 400,
                    'data': None,
                    'msg': f'无效的结束日期格式: {end_date_str}，请使用 YYYY-MM-DD 格式'
                }), 400
        
        # 查询告警记录
        alerts, total = AlertService.get_alerts_with_filters(
            page=page,
            page_size=page_size,
            alert_type=alert_type,
            severity=severity,
            driver_id=driver_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # 转换为字典格式并添加snapshot_url
        alerts_data = []
        for alert in alerts:
            alert_dict = alert.to_dict()
            # 添加snapshot_url字段
            if alert_dict.get('snapshot_path'):
                alert_dict['snapshot_url'] = f"/snapshots/{alert_dict['snapshot_path']}"
            else:
                alert_dict['snapshot_url'] = None
            alerts_data.append(alert_dict)
        
        return jsonify({
            'code': 200,
            'data': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'items': alerts_data
            },
            'msg': 'success'
        }), 200
        
    except ValueError as e:
        return jsonify({
            'code': 400,
            'data': None,
            'msg': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"[/api/alerts] 异常: {traceback.format_exc()}")
        return jsonify({
            'code': 500,
            'data': None,
            'msg': f'数据库查询失败: {str(e)}'
        }), 500


if __name__ == "__main__":
    print("Alerts API Routes:")
    print("GET  /api/alerts - 获取告警记录列表（支持分页和筛选）")




if __name__ == "__main__":
    print("Alerts API Routes:")
    print("GET  /api/alerts - 获取告警记录列表（支持分页和筛选）")
    print("GET  /api/alerts/<id> - 获取告警记录详情")
    print("POST /api/alerts - 创建告警记录")
