"""
Flask 应用入口

创建 Flask 应用，注册蓝图，配置 CORS，设置全局错误处理器，初始化数据库连接。

依赖：
- Flask
- Flask-CORS
- SQLAlchemy
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, jsonify
from flask_cors import CORS
from server.models.models import db
from server.config import load_config, get_database_url
from server.routes import drivers_bp, alerts_bp, stats_bp, snapshots_bp


def create_app(config_path=None):
    """
    创建并配置 Flask 应用
    
    Args:
        config_path: 配置文件路径（可选）
        
    Returns:
        Flask 应用实例
    """
    # 创建 Flask 应用
    app = Flask(__name__)
    
    # 加载配置
    try:
        flask_config = load_config(config_path)
        
        # 配置数据库
        app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url(flask_config)
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SQLALCHEMY_ECHO'] = flask_config.server.debug
        
        # 配置 Flask
        app.config['DEBUG'] = flask_config.server.debug
        app.config['JSON_AS_ASCII'] = False  # 支持中文 JSON
        
        # 初始化数据库
        db.init_app(app)
        
        # 配置 CORS
        CORS(app, resources={
            r"/api/*": {
                "origins": flask_config.cors.allowed_origins,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"]
            },
            r"/snapshots/*": {
                "origins": flask_config.cors.allowed_origins,
                "methods": ["GET", "OPTIONS"]
            }
        })
        
        # 注册蓝图
        app.register_blueprint(drivers_bp)
        app.register_blueprint(alerts_bp)
        app.register_blueprint(stats_bp)
        app.register_blueprint(snapshots_bp)
        
        # 注册全局错误处理器
        register_error_handlers(app)
        
        # 注册根路由
        @app.route('/')
        def index():
            """根路由"""
            return jsonify({
                'code': 200,
                'data': {
                    'message': '驾驶员监测系统 API 服务',
                    'version': '1.0.0',
                    'endpoints': {
                        'drivers': '/api/drivers',
                        'alerts': '/api/alerts',
                        'stats': '/api/stats',
                        'snapshots': '/snapshots'
                    }
                },
                'msg': 'success'
            })
        
        # 注册健康检查路由
        @app.route('/health')
        def health():
            """健康检查"""
            return jsonify({
                'code': 200,
                'data': {
                    'status': 'healthy',
                    'database': 'connected'
                },
                'msg': 'success'
            })
        
        return app
        
    except Exception as e:
        print(f"创建 Flask 应用失败: {e}")
        raise


def register_error_handlers(app):
    """
    注册全局错误处理器
    
    Args:
        app: Flask 应用实例
    """
    
    @app.errorhandler(404)
    def not_found(error):
        """404 错误处理"""
        return jsonify({
            'code': 404,
            'data': None,
            'msg': '请求的资源不存在'
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """405 错误处理"""
        return jsonify({
            'code': 405,
            'data': None,
            'msg': '不支持的请求方法'
        }), 405
    
    @app.errorhandler(500)
    def internal_server_error(error):
        """500 错误处理"""
        return jsonify({
            'code': 500,
            'data': None,
            'msg': '服务器内部错误'
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """通用异常处理"""
        app.logger.error(f"未处理的异常: {error}", exc_info=True)
        
        return jsonify({
            'code': 500,
            'data': None,
            'msg': '服务器发生错误'
        }), 500


def main():
    """主函数"""
    try:
        # 创建应用
        app = create_app()
        
        # 加载配置
        flask_config = load_config()
        
        # 启动服务器
        print("=" * 60)
        print("驾驶员监测系统 Flask API 服务")
        print("=" * 60)
        print(f"服务地址: http://{flask_config.server.host}:{flask_config.server.port}")
        print(f"调试模式: {flask_config.server.debug}")
        print(f"数据库: {flask_config.database.host}:{flask_config.database.port}/{flask_config.database.name}")
        print("=" * 60)
        print("\nAPI 端点:")
        print("  GET    /                    - 根路由")
        print("  GET    /health              - 健康检查")
        print("  GET    /api/drivers         - 获取驾驶员列表")
        print("  POST   /api/drivers         - 创建驾驶员")
        print("  GET    /api/alerts          - 获取告警记录")
        print("  POST   /api/alerts          - 创建告警记录")
        print("  GET    /api/stats/overview  - 获取概览统计")
        print("  GET    /api/stats/trend     - 获取趋势统计")
        print("  GET    /api/stats/type      - 获取类型分布")
        print("  GET    /snapshots/<file>    - 获取截图文件")
        print("=" * 60)
        
        # 运行应用
        app.run(
            host=flask_config.server.host,
            port=flask_config.server.port,
            debug=flask_config.server.debug
        )
        
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"\n启动服务器失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
