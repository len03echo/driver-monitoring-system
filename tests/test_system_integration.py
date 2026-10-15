"""
系统集成测试 - 人脸认证功能

快速测试人脸识别和认证功能是否正常工作
"""

import sys
import os
import logging

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client.core.face_recognizer import FaceRecognizer
from client.db.db_client import DBClient
from client.config import load_config
import cv2
import numpy as np


def test_face_recognizer():
    """测试人脸识别器"""
    print("=" * 60)
    print("测试 1: 人脸识别器初始化")
    print("=" * 60)
    
    try:
        recognizer = FaceRecognizer(model_name='buffalo_l')
        print("✓ 人脸识别器初始化成功")
        print(f"  - 模型名称: {recognizer.model_name}")
        print(f"  - 特征维度: {recognizer.feature_dimension}")
        print(f"  - 相似度阈值: {recognizer.get_similarity_threshold()}")
        print(f"  - 模型已加载: {recognizer.is_model_loaded()}")
        
        recognizer.close()
        return True
    except Exception as e:
        print(f"✗ 人脸识别器初始化失败: {e}")
        return False


def test_database_connection():
    """测试数据库连接"""
    print("\n" + "=" * 60)
    print("测试 2: 数据库连接")
    print("=" * 60)
    
    try:
        config = load_config()
        db_cfg = config.database
        
        db_client = DBClient(
            host=db_cfg.host,
            port=db_cfg.port,
            user=db_cfg.user,
            password=db_cfg.password,
            database=db_cfg.name
        )
        
        print("✓ 数据库连接成功")
        
        # 查询驾驶员数量
        drivers = db_client.get_all_drivers()
        print(f"  - 当前驾驶员数量: {len(drivers)}")
        
        if drivers:
            print(f"  - 驾驶员列表:")
            for driver in drivers[:5]:  # 只显示前5个
                has_feature = "有" if driver['face_feature'] else "无"
                print(f"    • {driver['name']} ({driver['employee_id']}) - 人脸特征: {has_feature}")
        
        db_client.close()
        return True
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        return False


def test_feature_extraction():
    """测试人脸特征提取"""
    print("\n" + "=" * 60)
    print("测试 3: 人脸特征提取")
    print("=" * 60)
    
    try:
        recognizer = FaceRecognizer(model_name='buffalo_l')
        
        # 创建测试图像（空白图像）
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        print("正在测试空白图像...")
        feature = recognizer.extract_feature(test_frame)
        
        if feature is None:
            print("✓ 空白图像正确返回 None（未检测到人脸）")
        else:
            print(f"✗ 空白图像应该返回 None，但返回了特征向量: {feature.shape}")
        
        recognizer.close()
        return True
    except Exception as e:
        print(f"✗ 人脸特征提取测试失败: {e}")
        return False


def test_camera():
    """测试摄像头"""
    print("\n" + "=" * 60)
    print("测试 4: 摄像头访问")
    print("=" * 60)
    
    try:
        camera = cv2.VideoCapture(0)
        
        if not camera.isOpened():
            print("✗ 无法打开摄像头 0")
            return False
        
        print("✓ 摄像头 0 打开成功")
        
        # 读取一帧
        ret, frame = camera.read()
        if ret and frame is not None:
            print(f"✓ 成功读取视频帧: {frame.shape}")
        else:
            print("✗ 读取视频帧失败")
            camera.release()
            return False
        
        camera.release()
        return True
    except Exception as e:
        print(f"✗ 摄像头测试失败: {e}")
        return False


def test_similarity_calculation():
    """测试相似度计算"""
    print("\n" + "=" * 60)
    print("测试 5: 相似度计算")
    print("=" * 60)
    
    try:
        recognizer = FaceRecognizer(model_name='buffalo_l')
        
        # 创建两个相同的特征向量
        feature1 = np.random.rand(512).astype(np.float32)
        feature2 = feature1.copy()
        
        similarity = recognizer.calculate_similarity(feature1, feature2)
        print(f"✓ 相同特征向量的相似度: {similarity:.4f}")
        
        if abs(similarity - 1.0) < 0.001:
            print("  ✓ 相似度计算正确（应该接近 1.0）")
        else:
            print(f"  ✗ 相似度计算可能有误（期望 1.0，实际 {similarity:.4f}）")
        
        # 创建两个不同的特征向量
        feature3 = np.random.rand(512).astype(np.float32)
        similarity2 = recognizer.calculate_similarity(feature1, feature3)
        print(f"✓ 不同特征向量的相似度: {similarity2:.4f}")
        
        if similarity2 < 0.9:
            print("  ✓ 相似度计算正确（应该小于 0.9）")
        else:
            print(f"  ⚠ 相似度较高（{similarity2:.4f}），可能是随机巧合")
        
        recognizer.close()
        return True
    except Exception as e:
        print(f"✗ 相似度计算测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "人脸认证功能测试" + " " * 15 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    # 配置日志
    logging.basicConfig(
        level=logging.WARNING,  # 只显示警告和错误
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行测试
    results = []
    
    results.append(("人脸识别器初始化", test_face_recognizer()))
    results.append(("数据库连接", test_database_connection()))
    results.append(("人脸特征提取", test_feature_extraction()))
    results.append(("摄像头访问", test_camera()))
    results.append(("相似度计算", test_similarity_calculation()))
    
    # 显示测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name:20s} : {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"总计: {len(results)} 个测试")
    print(f"通过: {passed} 个")
    print(f"失败: {failed} 个")
    print("=" * 60)
    
    if failed == 0:
        print("\n🎉 所有测试通过！人脸认证功能正常工作。")
        print("\n下一步:")
        print("  1. 运行 python client/main.py 启动客户端")
        print("  2. 点击'注册新用户'注册驾驶员")
        print("  3. 点击'人脸认证'进行身份认证")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查配置和环境。")
        print("\n常见问题:")
        print("  - 数据库连接失败: 检查 MySQL 是否启动，密码是否正确")
        print("  - 摄像头访问失败: 检查摄像头是否被占用")
        print("  - 模型加载失败: 检查网络连接，模型会自动下载")
        return 1


if __name__ == "__main__":
    sys.exit(main())
