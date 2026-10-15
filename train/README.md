# YOLOv8 驾驶员行为检测模型训练指南

## 概述

本目录包含 YOLOv8 模型训练脚本，用于检测驾驶员的危险行为：
- **smoke** (吸烟)
- **phone** (使用手机)
- **drink** (喝水/饮料)

## 环境要求

### Python 版本
- Python 3.8 或更高版本

### 依赖库
```bash
pip install ultralytics opencv-python numpy
```

或使用 requirements.txt（如果有）：
```bash
pip install -r requirements.txt
```

### 硬件要求
- **推荐**: NVIDIA GPU (CUDA 支持)
- **最低**: CPU (训练速度较慢)

## 目录结构

```
train/
├── dataset.yaml          # 数据集配置文件
├── train_yolov8.py       # 训练脚本
├── predict_test.py       # 推理测试脚本
├── README.md             # 本文件
└── runs/                 # 训练结果目录（训练后自动生成）
    └── train/
        ├── weights/
        │   ├── best.pt   # 最优模型
        │   └── last.pt   # 最后一轮模型
        ├── results.png   # 训练曲线
        └── ...

数据集目录结构（需要自行准备）:
dataset/
├── images/
│   ├── train/            # 训练集图片 (2818张)
│   └── val/              # 验证集图片 (705张)
└── labels/
    ├── train/            # 训练集标签 (2818个txt)
    └── val/              # 验证集标签 (705个txt)
```

## 数据集配置

### 1. 准备数据集

确保你的数据集已按照 YOLO 格式组织：
- 图片放在 `images/train` 和 `images/val`
- 标签放在 `labels/train` 和 `labels/val`
- 标签文件为 txt 格式，每行一个目标：`class_id x_center y_center width height`

### 2. 配置 dataset.yaml

编辑 `dataset.yaml` 文件，填写数据集路径：

```yaml
nc: 4
names: ['face', 'smoke', 'phone', 'drink']

# 填写你的数据集路径（绝对路径或相对路径）
train: /path/to/your/dataset/images/train
val: /path/to/your/dataset/images/val
```

**示例**（绝对路径）：
```yaml
train: E:/datasets/driver_behavior/images/train
val: E:/datasets/driver_behavior/images/val
```

**示例**（相对路径）：
```yaml
train: ../dataset/images/train
val: ../dataset/images/val
```

### 3. 类别说明

| Class ID | 类别名称 | 说明 |
|----------|---------|------|
| 0 | face | 人脸（用于辅助检测，推理时会被过滤） |
| 1 | smoke | 吸烟行为 |
| 2 | phone | 使用手机 |
| 3 | drink | 喝水/饮料 |

## 训练模型

### 基础训练

```bash
cd train
python train_yolov8.py
```

### 训练参数说明

在 `train_yolov8.py` 中可以修改以下参数：

```python
model_name = 'yolov8s.pt'  # 基础模型: yolov8n/s/m/l/x
epochs = 100               # 训练轮数
imgsz = 640                # 图像尺寸
batch = 16                 # 批次大小（根据显存调整）
workers = 4                # 数据加载线程数
```

**模型选择建议**：
- `yolov8n.pt`: 最快，精度较低
- `yolov8s.pt`: 平衡（推荐）
- `yolov8m.pt`: 精度较高，速度较慢
- `yolov8l.pt` / `yolov8x.pt`: 最高精度，需要更多资源

### 训练输出

训练完成后，结果保存在 `runs/train/` 目录：
- `weights/best.pt`: 验证集上表现最好的模型
- `weights/last.pt`: 最后一轮的模型
- `results.png`: 训练曲线（loss, mAP 等）
- `confusion_matrix.png`: 混淆矩阵
- `val_batch*.jpg`: 验证集预测示例

## 测试模型

### 1. 测试单张图片

```bash
python predict_test.py --model runs/train/weights/best.pt --source path/to/image.jpg
```

### 2. 测试视频

```bash
python predict_test.py --model runs/train/weights/best.pt --source path/to/video.mp4
```

### 3. 测试摄像头

```bash
python predict_test.py --model runs/train/weights/best.pt --source 0
```

### 4. 保存结果

```bash
python predict_test.py --model runs/train/weights/best.pt --source video.mp4 --save --output results
```

### 参数说明

- `--model`: 模型路径（必需）
- `--source`: 输入源（图片/视频/摄像头ID）
- `--conf`: 置信度阈值（默认 0.5）
- `--save`: 保存结果
- `--output`: 结果保存目录（默认 output）

## 替换主系统模型

训练完成后，将新模型集成到主系统：

### 1. 复制模型文件

```bash
# 将训练好的模型复制到 client 目录
copy runs\train\weights\best.pt ..\client\yolov8_behavior.pt
```

### 2. 修改配置文件

编辑 `client/config.yaml`，更新模型路径：

```yaml
detection:
  behavior_model: "yolov8_behavior.pt"  # 新模型路径
```

### 3. 验证集成

运行主系统，确认新模型正常工作：

```bash
cd ../client
python main.py
```

### 4. 注意事项

- 新模型的类别映射已在 `client/core/behavior_detector.py` 中配置
- 系统会自动过滤 `class_id=0` (face)，只处理 smoke/phone/drink
- 危险等级映射：
  - smoke → high (高危)
  - phone → medium (中危)
  - drink → low (低危)

## 性能优化建议

### 训练优化

1. **增加批次大小**（如果显存允许）：
   ```python
   batch = 32  # 或更大
   ```

2. **使用数据增强**（已默认启用）：
   - 随机翻转、旋转、缩放
   - 颜色抖动、马赛克增强

3. **调整学习率**：
   ```python
   model.train(..., lr0=0.01, lrf=0.01)
   ```

4. **使用预训练权重**：
   - 默认使用 COCO 预训练权重
   - 可以使用自己的预训练模型

### 推理优化

1. **降低输入尺寸**（提高速度）：
   ```python
   results = model(frame, imgsz=320)  # 默认 640
   ```

2. **使用 TensorRT**（NVIDIA GPU）：
   ```python
   model.export(format='engine')  # 导出 TensorRT 引擎
   ```

3. **使用 ONNX**（跨平台）：
   ```python
   model.export(format='onnx')
   ```

## 常见问题

### Q1: 训练时显存不足

**解决方案**：
- 减小批次大小：`batch = 8` 或 `batch = 4`
- 使用更小的模型：`yolov8n.pt`
- 减小图像尺寸：`imgsz = 416`

### Q2: 训练速度太慢

**解决方案**：
- 确认使用 GPU：检查 CUDA 是否正确安装
- 增加 workers：`workers = 8`
- 使用更小的模型

### Q3: 模型精度不够

**解决方案**：
- 增加训练轮数：`epochs = 200`
- 使用更大的模型：`yolov8m.pt` 或 `yolov8l.pt`
- 检查数据集质量和标注准确性
- 调整数据增强参数

### Q4: 推理时检测不准确

**解决方案**：
- 调整置信度阈值：`--conf 0.3`（降低）或 `--conf 0.7`（提高）
- 使用 best.pt 而不是 last.pt
- 确保测试数据与训练数据分布一致

## 进阶功能

### 1. 断点续训

```python
# 从上次训练继续
model = YOLO('runs/train/weights/last.pt')
model.train(data='dataset.yaml', epochs=50, resume=True)
```

### 2. 超参数调优

```python
model.tune(data='dataset.yaml', epochs=30, iterations=300)
```

### 3. 模型验证

```python
from ultralytics import YOLO
model = YOLO('runs/train/weights/best.pt')
metrics = model.val(data='dataset.yaml')
print(f"mAP50: {metrics.box.map50}")
print(f"mAP50-95: {metrics.box.map}")
```

## 参考资料

- [Ultralytics YOLOv8 官方文档](https://docs.ultralytics.com/)
- [YOLOv8 GitHub](https://github.com/ultralytics/ultralytics)
- [YOLO 数据集格式说明](https://docs.ultralytics.com/datasets/)

## 技术支持

如有问题，请查看：
1. 主项目 README: `../docs/001-README.md`
2. 安装指南: `../docs/002-INSTALL.md`
3. 使用说明: `../docs/003-USAGE.md`
