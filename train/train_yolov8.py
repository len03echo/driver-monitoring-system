"""
YOLOv8 训练脚本
用于训练驾驶员行为检测模型（smoke, phone, drink）
"""

import os
from pathlib import Path
from ultralytics import YOLO


def train_yolov8():
    """训练 YOLOv8 模型"""
    
    # 配置参数
    model_name = 'yolov8s.pt'  # 基础模型
    script_dir = Path(__file__).resolve().parent
    data_yaml = str(script_dir / 'dataset.yaml')  # 数据集配置文件
    epochs = 300
    imgsz = 640
    batch = 16
    workers = 4
    project = str(script_dir / 'runs')  # 结果保存目录
    name = 'train'  # 本次训练的名称
    
    print("=" * 60)
    print("YOLOv8 驾驶员行为检测模型训练")
    print("=" * 60)
    print(f"基础模型: {model_name}")
    print(f"数据集配置: {data_yaml}")
    print(f"训练轮数: {epochs}")
    print(f"图像尺寸: {imgsz}")
    print(f"批次大小: {batch}")
    print(f"工作线程: {workers}")
    print("=" * 60)
    
    # 检查数据集配置文件
    if not os.path.exists(data_yaml):
        print(f"错误: 找不到数据集配置文件 {data_yaml}")
        print("请确保 dataset.yaml 文件存在并已正确配置")
        return
    
    # 加载模型
    print("\n正在加载模型...")
    model = YOLO(model_name)
    
    # 开始训练
    print("\n开始训练...")
    try:
        results = model.train(
            data=data_yaml,
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            workers=workers,
            project=project,
            name=name,
            patience=20,  # 早停耐心值
            save=True,  # 保存检查点
            save_period=10,  # 每10轮保存一次
            cache=False,  # 不缓存图像到内存（数据集较大时）
            device=0,  # 使用 GPU 0，如果没有 GPU 会自动使用 CPU
            verbose=True,  # 详细输出
            plots=True,  # 生成训练图表
        )
        
        print("\n" + "=" * 60)
        print("训练完成！")
        print("=" * 60)
        
        # 获取最优模型路径
        best_model_path = Path(project) / name / 'weights' / 'best.pt'
        last_model_path = Path(project) / name / 'weights' / 'last.pt'
        
        print(f"\n最优模型路径: {best_model_path.absolute()}")
        print(f"最后模型路径: {last_model_path.absolute()}")
        print(f"\n训练结果保存在: {Path(project) / name}")
        print("\n可以使用以下命令进行验证:")
        print(f"  python predict_test.py --model {best_model_path} --source <图片/视频路径>")
        
    except Exception as e:
        print(f"\n训练过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    train_yolov8()
