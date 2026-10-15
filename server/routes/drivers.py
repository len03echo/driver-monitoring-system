"""
驾驶员档案路由

提供驾驶员档案的 REST API 接口：
- GET /api/drivers - 获取驾驶员列表
- POST /api/drivers - 创建新驾驶员
- DELETE /api/drivers/<id> - 删除驾驶员

依赖：
- Flask
- DriverService
"""

from flask import Blueprint, request, jsonify
from server.services.driver_service import DriverService

# 创建蓝图
drivers_bp = Blueprint('drivers', __name__, url_prefix='/api/drivers')


@drivers_bp.route('', methods=['GET'])
def get_drivers():
    """
    获取驾驶员列表
    
    Returns:
        200: 驾驶员列表
        {
            "code": 200,
            "data": [
                {
                    "id": 1,
                    "name": "张三",
                    "employee_id": "EMP001",
                    "avatar_path": "avatars/001.jpg",
                    "created_at": "2024-01-01T12:00:00",
                    "has_face_feature": true
                }
            ],
            "msg": "success"
        }
    """
    try:
        # 获取所有驾驶员
        drivers = DriverService.get_all_drivers()
        
        # 转换为字典格式
        drivers_data = [driver.to_dict() for driver in drivers]
        
        return jsonify({
            'code': 200,
            'data': drivers_data,
            'msg': 'success'
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'data': None,
            'msg': '数据库查询失败'
        }), 500



@drivers_bp.route('', methods=['POST'])
def create_driver():
    """
    创建新驾驶员
    
    Request Body:
        {
            "name": "张三",
            "employee_id": "EMP001"
        }
    
    Returns:
        200: 创建成功
        400: 参数错误或工号重复
        500: 服务器错误
    """
    try:
        # 获取请求数据
        data = request.get_json(silent=True)
        
        if not data or not isinstance(data, dict):
            return jsonify({
                'code': 400,
                'data': None,
                'msg': '请求体格式错误，请使用 JSON 格式'
            }), 400
        
        # 提取参数
        name = data.get('name')
        employee_id = data.get('employee_id')
        
        # 参数验证
        if not name:
            return jsonify({
                'code': 400,
                'data': None,
                'msg': '缺少必填字段：name'
            }), 400
        
        if not employee_id:
            return jsonify({
                'code': 400,
                'data': None,
                'msg': '缺少必填字段：employee_id'
            }), 400
        
        # 创建驾驶员
        driver = DriverService.create_driver(
            name=name,
            employee_id=employee_id
        )
        
        return jsonify({
            'code': 200,
            'data': driver.to_dict(),
            'msg': 'success'
        }), 200
        
    except ValueError as e:
        return jsonify({
            'code': 400,
            'data': None,
            'msg': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'code': 500,
            'data': None,
            'msg': '数据库操作失败'
        }), 500


@drivers_bp.route('/<int:driver_id>', methods=['DELETE'])
def delete_driver(driver_id):
    """
    删除驾驶员
    
    Path Parameters:
        driver_id (int): 驾驶员 ID
    
    Returns:
        200: 删除成功
        404: 驾驶员不存在
        500: 服务器错误
    """
    try:
        success = DriverService.delete_driver(driver_id)
        
        if not success:
            return jsonify({
                'code': 404,
                'data': None,
                'msg': f'驾驶员 ID {driver_id} 不存在'
            }), 404
        
        return jsonify({
            'code': 200,
            'data': None,
            'msg': '删除成功'
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'data': None,
            'msg': '数据库操作失败'
        }), 500


if __name__ == "__main__":
    print("Drivers API Routes:")
    print("GET    /api/drivers - 获取驾驶员列表")
    print("POST   /api/drivers - 创建驾驶员")
    print("DELETE /api/drivers/<id> - 删除驾驶员")
