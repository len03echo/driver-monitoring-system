"""
YOLOv8 推理测试脚本
支持图片、视频、摄像头输入
过滤 face 类别，只显示 smoke/phone/drink 检测结果
"""

import argparse
import cv2
from pathlib import Path
from ultralytics import YOLO


# 类别映射（与 dataset.yaml 一致）
CLASS_NAMES = {
    0: 'face',
    1: 'smoke',
    2: 'phone',
    3: 'drink'
}

# 颜色映射（BGR格式）
CLASS_COLORS = {
    1: (0, 0, 255),    # smoke - 红色
    2: (0, 165, 255),  # phone - 橙色
    3: (0, 255, 255)   # drink - 黄色
}


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='YOLOv8 驾驶员行为检测推理测试')
    parser.add_argument('--model', type=str, required=True,
                        help='训练好的模型路径，例如: runs/train/weights/best.pt')
    parser.add_argument('--source', type=str, default='0',
                        help='输入源: 图片路径/视频路径/摄像头ID(0,1,...)')
    parser.add_argument('--conf', type=float, default=0.5,
                        help='置信度阈值 (默认: 0.5)')
    parser.add_argument('--save', action='store_true',
                        help='是否保存结果')
    parser.add_argument('--output', type=str, default='output',
                        help='结果保存目录 (默认: output)')
    return parser.parse_args()


def draw_detections(frame, results, conf_threshold=0.5):
    """
    在图像上绘制检测结果
    过滤掉 class_id=0 (face)，只显示 smoke/phone/drink
    """
    for result in results:
        boxes = result.boxes
        for box in boxes:
            # 获取检测信息
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            
            # 过滤：跳过 face 类别和低置信度
            if cls_id == 0 or conf < conf_threshold:
                continue
            
            # 获取边界框坐标
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            
            # 获取类别名称和颜色
            class_name = CLASS_NAMES.get(cls_id, 'unknown')
            color = CLASS_COLORS.get(cls_id, (255, 255, 255))
            
            # 绘制边界框
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # 绘制标签背景
            label = f'{class_name} {conf:.2f}'
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            label_y = max(y1 - 10, label_size[1])
            cv2.rectangle(frame, (x1, label_y - label_size[1] - 5),
                         (x1 + label_size[0], label_y + 5), color, -1)
            
            # 绘制标签文字
            cv2.putText(frame, label, (x1, label_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    return frame


def predict_image(model, image_path, conf_threshold, save_result, output_dir):
    """对单张图片进行推理"""
    print(f"\n处理图片: {image_path}")
    
    # 读取图片
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"错误: 无法读取图片 {image_path}")
        return
    
    # 推理
    results = model(frame, verbose=False)
    
    # 绘制结果
    frame = draw_detections(frame, results, conf_threshold)
    
    # 显示结果
    cv2.imshow('YOLOv8 Detection', frame)
    print("按任意键继续...")
    cv2.waitKey(0)
    
    # 保存结果
    if save_result:
        output_path = Path(output_dir) / f"result_{Path(image_path).name}"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), frame)
        print(f"结果已保存到: {output_path}")
    
    cv2.destroyAllWindows()


def predict_video(model, video_source, conf_threshold, save_result, output_dir):
    """对视频或摄像头进行推理"""
    # 判断是摄像头还是视频文件
    if video_source.isdigit():
        video_source = int(video_source)
        print(f"\n打开摄像头: {video_source}")
    else:
        print(f"\n处理视频: {video_source}")
    
    # 打开视频源
    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        print(f"错误: 无法打开视频源 {video_source}")
        return
    
    # 获取视频信息
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # 视频写入器
    writer = None
    if save_result:
        output_path = Path(output_dir) / f"result_{Path(str(video_source)).name if isinstance(video_source, str) else 'camera.mp4'}"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        print(f"结果将保存到: {output_path}")
    
    print("\n开始推理... (按 'q' 退出)")
    
    frame_count = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # 推理
            results = model(frame, verbose=False)
            
            # 绘制结果
            frame = draw_detections(frame, results, conf_threshold)
            
            # 显示帧数
            cv2.putText(frame, f'Frame: {frame_count}', (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # 显示结果
            cv2.imshow('YOLOv8 Detection', frame)
            
            # 保存结果
            if writer:
                writer.write(frame)
            
            # 按 'q' 退出
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n用户中断")
                break
    
    except KeyboardInterrupt:
        print("\n用户中断")
    
    finally:
        cap.release()
        if writer:
            writer.release()
        cv2.destroyAllWindows()
        print(f"\n处理完成，共处理 {frame_count} 帧")


def main():
    """主函数"""
    args = parse_args()
    
    print("=" * 60)
    print("YOLOv8 驾驶员行为检测推理测试")
    print("=" * 60)
    print(f"模型路径: {args.model}")
    print(f"输入源: {args.source}")
    print(f"置信度阈值: {args.conf}")
    print(f"保存结果: {args.save}")
    if args.save:
        print(f"输出目录: {args.output}")
    print("=" * 60)
    
    # 加载模型
    print("\n正在加载模型...")
    try:
        model = YOLO(args.model)
        print("模型加载成功！")
    except Exception as e:
        print(f"错误: 无法加载模型 {args.model}")
        print(f"详细信息: {e}")
        return
    
    # 判断输入类型
    source = args.source
    
    # 图片文件
    if source.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp')):
        predict_image(model, source, args.conf, args.save, args.output)
    
    # 视频文件或摄像头
    else:
        predict_video(model, source, args.conf, args.save, args.output)


if __name__ == '__main__':
    main()
