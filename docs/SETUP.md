# 本地搭建指南（待端到端验证）

> 此仓库是公开发布候选版，刻意不包含行为检测模型、数据集、InsightFace 权重和真人影像。原项目曾在其他环境中开发；本候选版尚未端到端验证。

## 1. 环境

- 推荐从 Python 3.9 环境开始。依赖锁定版本来自原项目，并非对 Python 3.13 的兼容承诺。
- 推荐本机安装 MySQL 8 与 Node.js。GPU 加速需自行匹配 PyTorch、CUDA 与 NVIDIA 驱动版本。
- Python 安装：`python -m pip install -r requirements.txt`（基础安装默认使用非特定 CUDA 的 PyTorch 版本）。如需指定 GPU wheel，参考 [PyTorch 官方安装指南](https://pytorch.org/get-started/previous-versions/)。

## 2. 创建数据库

```bash
mysql -u root -p < database/init.sql
```

请在 MySQL 内创建权限适当的专用账户，不要让程序使用生产数据库或含真实个人信息的数据库。

## 3. 配置凭据

Windows PowerShell：

```powershell
Copy-Item .env.example .env
notepad .env
```

在根目录 `.env` 中填写 `DB_HOST`、`DB_PORT`、`DB_USER`、`DB_PASSWORD`、`DB_NAME`。客户端与服务端会读取同一份 `.env`；系统环境变量优先于文件中的值。不要把凭据写回 `config.yaml` 或提交 `.env`。

## 4. 模型

- `client/config.yaml` 的 `model.yolo_path` 默认是 `yolov8_behavior.pt`，程序会按客户端配置文件所在目录解析。
- 权重不包含在仓库内。需自行提供**有权使用并符合许可要求**的模型文件，放到 `client/yolov8_behavior.pt`。普通的 `yolov8n.pt` 不能等价替代该自训练行为分类权重。
- `buffalo_l` 由 InsightFace 在运行时按其机制获取；需核实该模型的下载、授权及使用限制。
- `train/dataset.yaml` 仅为示例路径；训练数据不在仓库内，训练前需按本地数据集组织方式调整路径。

## 5. 启动服务（必须是仅本机测试）

```bash
python -m server.app
python client/main.py
```

在另一个终端运行前端：

```bash
cd frontend
npm ci
npm run dev
```

默认 Web 页面是 `http://127.0.0.1:3000`，API 是 `http://127.0.0.1:5000`。后端尚无认证授权，禁止改为公网监听直接运行。缺少数据库、摄像头和模型时应用可能无法正常启动或工作。

## 6. 检查与常见误区

- `python -m compileall ...` 只能查 Python 语法，不代表全项目通过运行测试。
- `python -m pytest tests` 依赖已安装的测试依赖及外部环境；可按具体测试拆分验证，不要将历史测试结果当成当前成绩。
- 配置引用 `client/assets/alert.wav`，源项目并未提供该音效；不存在时告警音效会降级。
- 原工程中旧版开发文档的性能和端口说明可能过时；本候选仓库以当前源码与此文档为准。
