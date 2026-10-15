"""
截图静态文件路由

提供截图文件的访问接口：
- GET /snapshots/<filename> - 获取截图文件

依赖：
- Flask
"""

from flask import Blueprint, send_from_directory, jsonify
import os
from pathlib import Path

# 创建蓝图
snapshots_bp = Blueprint('snapshots', __name__, url_prefix='/snapshots')

# 截图目录路径（client/snapshots/）
SNAPSHOTS_DIR = Path(__file__).parent.parent.parent / 'client' / 'snapshots'


@snapshots_bp.route('/<path:filename>', methods=['GET'])
def get_snapshot(filename):
    """
    获取截图文件
    
    Path Parameters:
        filename (str): 截图文件名（支持子目录路径）
    
    Returns:
        200: 图片文件
        404: 文件不存在
        500: 服务器错误
    
    Examples:
        GET /snapshots/1_phone_20240101120000.jpg
        GET /snapshots/2024/01/1_phone_20240101120000.jpg
    """
    try:
        # 安全检查：防止路径遍历攻击（必须在文件存在性检查之前）
        file_path = SNAPSHOTS_DIR / filename
        try:
            resolved = file_path.resolve()
            resolved.relative_to(SNAPSHOTS_DIR.resolve())
        except ValueError:
            return jsonify({
                'code': 403,
                'data': None,
                'msg': '非法的文件路径'
            }), 403
        except (OSError, RuntimeError):
            # Windows 上非法字符（如 <> 等）会导致 resolve() 抛出 OSError
            return jsonify({
                'code': 404,
                'data': None,
                'msg': '截图文件不存在'
            }), 404
        
        # 确保截图目录存在
        if not SNAPSHOTS_DIR.exists():
            return jsonify({
                'code': 404,
                'data': None,
                'msg': '截图文件不存在'
            }), 404
        
        # 检查文件是否存在
        if not file_path.exists() or not file_path.is_file():
            return jsonify({
                'code': 404,
                'data': None,
                'msg': '截图文件不存在'
            }), 404
        
        # 返回文件
        directory = str(file_path.parent)
        filename_only = file_path.name
        
        return send_from_directory(
            directory,
            filename_only,
            mimetype='image/jpeg'
        )
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'data': None,
            'msg': '服务器内部错误'
        }), 500


if __name__ == "__main__":
    print("Snapshots API Routes:")
    print("GET /snapshots/<filename> - 获取截图文件")
    print(f"Snapshots directory: {SNAPSHOTS_DIR}")
