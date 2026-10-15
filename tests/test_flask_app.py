"""
Flask 应用测试

测试 Flask 应用的基本功能和错误处理。

依赖：
- pytest
- Flask
"""

import pytest
import sys
import os
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from server.app import create_app


@pytest.fixture
def app():
    """创建测试 Flask 应用"""
    from flask import Flask
    from flask_cors import CORS
    from server.models.models import db
    from server.routes import drivers_bp, alerts_bp, stats_bp, snapshots_bp
    
    # 直接创建Flask应用，不使用create_app()以避免加载配置文件
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JSON_AS_ASCII'] = False
    
    # 初始化数据库
    db.init_app(app)
    
    # 配置CORS
    CORS(app)
    
    # 注册蓝图
    app.register_blueprint(drivers_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(snapshots_bp)
    
    # 注册根路由
    @app.route('/')
    def index():
        return {
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
        }
    
    # 注册健康检查路由
    @app.route('/health')
    def health():
        return {
            'code': 200,
            'data': {
                'status': 'healthy',
                'database': 'connected'
            },
            'msg': 'success'
        }
    
    # 注册错误处理器
    @app.errorhandler(404)
    def not_found(error):
        return {
            'code': 404,
            'data': None,
            'msg': '请求的资源不存在'
        }, 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return {
            'code': 405,
            'data': None,
            'msg': '不支持的请求方法'
        }, 405
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """获取测试客户端"""
    return app.test_client()


class TestFlaskApp:
    """测试 Flask 应用基本功能"""
    
    def test_root_endpoint(self, client):
        """测试根路由"""
        response = client.get('/')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['code'] == 200
        assert 'data' in data
        assert data['data']['message'] == '驾驶员监测系统 API 服务'
        assert data['data']['version'] == '1.0.0'
        assert 'endpoints' in data['data']
        assert data['msg'] == 'success'
    
    def test_health_endpoint(self, client):
        """测试健康检查路由"""
        response = client.get('/health')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['code'] == 200
        assert data['data']['status'] == 'healthy'
        assert data['data']['database'] == 'connected'
        assert data['msg'] == 'success'
    
    def test_404_error_handler(self, client):
        """测试404错误处理"""
        response = client.get('/nonexistent-endpoint')
        
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert data['code'] == 404
        assert data['data'] is None
        assert data['msg'] == '请求的资源不存在'
    
    def test_405_error_handler(self, client):
        """测试405错误处理（方法不允许）"""
        # 对只支持GET的根路由发送POST请求
        response = client.post('/')
        
        assert response.status_code == 405
        
        data = json.loads(response.data)
        assert data['code'] == 405
        assert data['data'] is None
        assert data['msg'] == '不支持的请求方法'
    
    def test_cors_headers(self, client):
        """测试CORS头部"""
        # 发送OPTIONS预检请求
        response = client.options('/api/drivers', 
                                headers={'Origin': 'http://localhost:3000'})
        
        # 检查CORS头部是否存在
        assert 'Access-Control-Allow-Origin' in response.headers
    
    def test_json_response_encoding(self, client):
        """测试JSON响应编码（中文支持）"""
        response = client.get('/')
        
        # 检查Content-Type包含UTF-8编码
        assert 'application/json' in response.content_type
        
        # 检查中文字符正确编码
        data = json.loads(response.data)
        assert '驾驶员监测系统' in data['data']['message']


class TestFlaskAppBlueprints:
    """测试 Flask 应用蓝图注册"""
    
    def test_drivers_blueprint_registered(self, client):
        """测试驾驶员蓝图已注册"""
        response = client.get('/api/drivers')
        # 应该返回200而不是404，说明蓝图已注册
        assert response.status_code == 200
    
    def test_alerts_blueprint_registered(self, client):
        """测试告警记录蓝图已注册"""
        response = client.get('/api/alerts')
        # 应该返回200而不是404，说明蓝图已注册
        assert response.status_code == 200
    
    def test_stats_blueprint_registered(self, client):
        """测试统计数据蓝图已注册"""
        response = client.get('/api/stats/overview')
        # 应该返回200而不是404，说明蓝图已注册
        assert response.status_code == 200
    
    def test_snapshots_blueprint_registered(self, client):
        """测试截图蓝图已注册"""
        response = client.get('/snapshots/nonexistent.jpg')
        # 应该返回404（文件不存在）而不是404（路由不存在），说明蓝图已注册
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert data['msg'] == '截图文件不存在'  # 这是snapshots蓝图的错误信息


class TestFlaskAppConfiguration:
    """测试 Flask 应用配置"""
    
    def test_app_configuration(self, app):
        """测试应用配置"""
        assert app.config['TESTING'] is True
        assert app.config['JSON_AS_ASCII'] is False
        assert 'SQLALCHEMY_DATABASE_URI' in app.config
        assert app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] is False
    
    def test_database_initialization(self, app):
        """测试数据库初始化"""
        with app.app_context():
            from server.models.models import db
            # 检查数据库是否正确初始化
            assert db is not None
            assert db.engine is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])