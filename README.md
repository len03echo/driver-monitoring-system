# 智能驾驶员状态监测系统

**Intelligent Driver State Monitoring System** — 基于 PyQt5、YOLOv8、MediaPipe、InsightFace、Flask 与 Vue 3 的驾驶员状态监测实践项目。

> **个人课程项目 / Personal Course Project**
>
> 已取得软件著作权登记证书；证书、完整登记材料及个人信息不在本仓库中。

**English overview:** A driver-state monitoring project with a PyQt5 desktop client, YOLOv8 behavior detection, MediaPipe fatigue analysis, InsightFace authentication, a Flask/MySQL API, and a Vue 3 dashboard. Model weights, datasets, personal media, runtime credentials, and the complete software-copyright application are not distributed here.

## 版本说明

本仓库同时保留了软著登记版本的核心桌面端能力，并在其后继续扩展。两者边界如下：

| 版本 | 范围 |
| --- | --- |
| 软著登记版本 V1.0.0 | 以 PyQt5 桌面端为主体，包含视频采集、YOLOv8 危险行为检测、MediaPipe 疲劳检测、InsightFace 身份认证、状态面板、告警与 MySQL 持久化。下方截图来自该版本的历史运行记录。 |
| 当前仓库扩展版 | 在桌面端基础上增加 Flask REST API、Vue 3 管理后台、配置安全处理、训练资料整理及自动化测试。扩展内容不应被理解为软著登记范围或登记时已具备的功能。 |

## 历史运行截图

截图来自软著登记版本的历史说明材料。公开前已检查个人信息：YOLOv8 与 MediaPipe 截图中的真人面部、姓名和工号均已匿名化；原始说明书及未处理截图未收入仓库。截图中的 FPS、告警次数和置信度只反映当时单次运行界面，不代表当前版本的性能指标。

### 软件主界面

![PyQt5 软件主界面](docs/screenshots/main-interface.png)

桌面端采用视频区与控制面板分栏布局，集中提供视频源、身份认证、监测控制、实时状态、统计计数和系统日志。

### YOLOv8 危险行为检测

![YOLOv8 手机检测匿名化截图](docs/screenshots/yolov8-phone-detection-anonymized.png)

YOLOv8 检测模块识别 `phone`、`smoke`、`drink` 等行为，并将类别、置信度与检测框绘制到视频帧。仓库不分发自定义模型权重或训练数据。

### MediaPipe 疲劳检测

![MediaPipe 疲劳检测匿名化截图](docs/screenshots/mediapipe-fatigue-detection-anonymized.png)

MediaPipe Face Mesh 提取面部关键点，计算 EAR（眼睛纵横比）、MAR（嘴巴纵横比）及头部姿态，用于闭眼、打哈欠和低头状态判断。截图保留了关键点与诊断信息，人物身份已不可识别。

### 系统状态面板

![系统状态面板](docs/screenshots/system-status-panel.png)

状态面板同步展示眼睛、嘴巴、头部与危险行为状态，以及 FPS、告警次数和累计持续时间，异常项通过颜色变化突出显示。

## 系统设计

### 1. 系统总体架构

系统按职责划分为数据持久化层、核心检测层、业务逻辑层和用户交互层。当前扩展版在原桌面端之外增加了 Flask API 与 Vue 管理后台。

```mermaid
flowchart TB
    IN[摄像头或本地视频]

    subgraph UI[用户交互层]
        DESKTOP[PyQt5 桌面客户端]
        WEB[Vue 3 管理后台<br/>当前扩展]
    end

    subgraph BIZ[业务逻辑层]
        THREAD[DetectionThread 检测线程]
        API[Flask REST API<br/>当前扩展]
    end

    subgraph CORE[核心检测层]
        YOLO[YOLOv8<br/>危险行为检测]
        FATIGUE[MediaPipe<br/>疲劳检测]
        FACE[InsightFace<br/>人脸认证]
        ALERT[AlertEngine<br/>告警引擎]
    end

    subgraph DATA[数据持久化层]
        DB[(MySQL 数据库)]
        SHOT[告警截图目录]
    end

    IN --> THREAD
    DESKTOP -->|控制监测| THREAD
    THREAD -->|帧与检测信号| DESKTOP
    THREAD -->|逐帧调用| YOLO
    THREAD -->|逐帧调用| FATIGUE
    DESKTOP -->|认证对话框| FACE
    FACE -->|查询已注册特征| DB
    THREAD -->|异常事件| ALERT
    ALERT --> SHOT
    ALERT -->|告警记录| DB
    DB <--> API
    API <--> WEB
```

- **数据持久化层**：保存驾驶员、监测会话和告警记录；截图目录与运行数据默认不公开。
- **核心检测层**：封装危险行为、疲劳状态、人脸特征与预警处理。
- **业务逻辑层**：协调视频源、检测器、会话、告警和服务端数据访问。
- **用户交互层**：提供桌面实时监测界面及扩展后的 Web 管理界面。

图中的 PyQt5、检测器、认证、告警与 MySQL 属于软著登记版本的核心范围；Flask REST API 与 Vue 3 管理后台为当前仓库的后续扩展。

### 2. 监测业务流程

```mermaid
flowchart TD
    START([程序启动]) --> DEP{依赖检查通过}
    DEP -- 否 --> START_ERR[记录错误并退出]
    DEP -- 是 --> CFG{配置加载成功}
    CFG -- 否 --> START_ERR
    CFG -- 是 --> UI_INIT[创建 Qt 应用与主窗口]
    UI_INIT --> SOURCE[选择摄像头或本地视频]
    SOURCE --> OPEN{视频源打开成功}
    OPEN -- 否 --> VIDEO_ERR[显示错误并等待重新选择]
    VIDEO_ERR --> SOURCE
    OPEN -- 是 --> PREVIEW[DetectionThread 启动视频预览]
    PREVIEW --> AUTH{驾驶员认证成功}
    AUTH -- 否或取消 --> PREVIEW
    AUTH -- 异常 --> AUTH_ERR[记录并显示认证错误]
    AUTH_ERR --> PREVIEW
    AUTH -- 是 --> MONITOR[创建检测器与告警引擎<br/>创建监测会话并启用检测]
    MONITOR --> FRAME{读取到视频帧}
    FRAME -- 读取错误 --> FRAME
    FRAME -- 视频结束 --> STOP
    FRAME -- 是 --> DETECT[YOLOv8 与 MediaPipe 检测]
    DETECT --> DISPLAY[发送视频帧和检测结果<br/>更新状态面板与 FPS]
    DETECT --> HAS_ALERT{是否产生异常事件}
    HAS_ALERT -- 是 --> ALERT_FLOW[交给告警逻辑]
    HAS_ALERT -- 否 --> END_CHECK
    DISPLAY --> END_CHECK{停止监测}
    ALERT_FLOW --> END_CHECK
    END_CHECK -- 否 --> FRAME
    END_CHECK -- 是 --> STOP[结束会话并关闭检测<br/>保留视频预览]
```

预览阶段关闭行为与疲劳检测；认证成功后才创建检测器、告警引擎和监测会话。视频源打不开、配置加载失败或认证异常时分别进入源码对应的错误处理分支。

### 3. 告警触发逻辑

```mermaid
flowchart TD
    FRAME[当前视频帧] --> YOLO_CHECK[YOLOv8 行为检测]
    FRAME --> FATIGUE_CHECK[MediaPipe 疲劳检测]
    YOLO_CHECK --> YOLO_COUNT{同类行为达到<br/>连续帧阈值}
    FATIGUE_CHECK --> FATIGUE_COUNT{闭眼 打哈欠或低头<br/>达到各自连续帧阈值}
    YOLO_COUNT -- 否 --> UI_UPDATE[发送检测结果并更新状态面板]
    FATIGUE_COUNT -- 否 --> UI_UPDATE
    YOLO_COUNT -- 是 --> MERGE[汇总异常类型]
    FATIGUE_COUNT -- 是 --> MERGE
    MERGE --> UI_UPDATE
    MERGE --> READY{AlertEngine 与数据库<br/>是否可用}
    READY -- 否 --> NEXT[跳过持久化告警处理]
    READY -- 是 --> COOL{该告警类型是否处于<br/>默认 30 秒冷却期}
    COOL -- 是 --> SUPPRESS[抑制同类重复告警]
    COOL -- 否 --> SNAP[保存当前帧截图]
    SNAP --> SOUND[播放告警音效]
    SOUND --> DB_WRITE[写入数据库告警记录]
    DB_WRITE --> UPDATE_COOL[更新该类型冷却时间]
    UPDATE_COOL --> NEXT_FRAME([处理下一帧])
    SUPPRESS --> NEXT_FRAME
    NEXT --> NEXT_FRAME
    UI_UPDATE --> NEXT_FRAME
```

连续帧阈值在 YOLOv8 与 MediaPipe 检测器内部独立判断；`DetectionThread` 只汇总已经触发的异常。状态面板接收检测结果并更新，`AlertEngine` 则按告警类型独立执行冷却、截图、音效与数据库记录。

## 技术亮点

### QThread 检测线程

`DetectionThread` 继承 `QThread`，在后台完成视频帧读取、YOLOv8 与 MediaPipe 推理、告警处理和帧率控制。主线程负责界面渲染与交互，两者通过 `frame_ready`、`detection_result`、`status_changed`、`error_occurred`、`fps_updated` 等 Qt 信号通信；运行、暂停和组件切换状态由 `QMutex` 保护，避免推理阻塞界面事件循环。

### 连续帧预警

单帧检测容易受遮挡、姿态和瞬时误检影响。行为检测器按类别维护连续帧计数，达到配置阈值后才产生事件，未连续命中则重置；疲劳检测也分别维护闭眼、打哈欠和低头计数。当前配置中的行为阈值默认为 10 帧，疲劳阈值可在 `client/config.yaml` 中调整。

### 30 秒告警冷却

`AlertEngine` 为每种告警类型独立记录最近触发时间，默认在 30 秒冷却期内抑制同类重复告警。有效告警可关联危险等级、截图和数据库记录，从而降低持续状态造成的告警刷屏，同时不影响其他类型告警。

### 状态与告警闭环

检测结果不仅绘制在视频帧上，还会更新状态标签、累计次数与持续时间；告警引擎负责冷却判断、截图和持久化，管理端可通过 API 查询驾驶员、告警与统计数据。

## 功能与技术栈

| 模块 | 主要技术 | 功能 |
| --- | --- | --- |
| 桌面客户端 | Python、PyQt5、OpenCV | 摄像头/视频文件处理、状态与告警展示 |
| 危险行为检测 | Ultralytics YOLOv8 | 手机、吸烟、喝水等行为检测与连续帧过滤 |
| 疲劳检测 | MediaPipe Face Mesh | EAR、MAR、头部姿态与连续帧判断 |
| 人脸认证 | InsightFace | 人脸特征提取、身份注册与验证 |
| 告警与持久化 | AlertEngine、PyMySQL、MySQL | 冷却、截图、会话及告警记录 |
| API 服务 | Flask、Flask-SQLAlchemy | 驾驶员、告警和统计接口 |
| Web 管理后台 | Vue 3、Vite、Element Plus、ECharts | 驾驶员管理、告警列表和图表展示 |

## 项目结构

```text
client/               PyQt5 客户端：core/、ui/、db/
server/               Flask 服务端：routes/、services/
frontend/             Vue 3 管理后台
train/                训练与预测脚本（不含训练数据）
database/init.sql     MySQL 建表脚本
tests/                单元、集成和属性测试
docs/screenshots/     已脱敏的历史运行截图
docs/training_curves/ 历史训练曲线与原始 results.csv
```

## 本地搭建

项目最初按 Python 3.9–3.11 环境开发。PyTorch、CUDA、MediaPipe 与 InsightFace 的兼容组合可能随平台而异，建议使用独立虚拟环境。

1. 安装 `requirements.txt`；开发与测试依赖见 `requirements-dev.txt`。
2. 准备本地 MySQL，执行 `database/init.sql`。
3. 复制 `.env.example` 为 `.env`，填写数据库配置；切勿提交 `.env`。
4. 确认许可后，将有权使用的 YOLOv8 行为检测权重放到配置指定位置。
5. 启动桌面端：`python client/main.py`。
6. 如需扩展管理端，启动 `python -m server.app`，再在 `frontend/` 执行 `npm ci` 与 `npm run dev`。

更多说明见 [本地配置指南](docs/SETUP.md)。

## 训练结果与复现边界

`docs/training_curves/` 保存历史训练曲线、混淆矩阵和 `results.csv`，仅用于展示训练过程。原始数据集与对应权重未公开，因此不能仅凭本仓库完整复现训练或独立核验历史模型指标。README 不将历史界面中的 FPS、置信度或告警计数解释为当前性能结论。

## 测试状态

发布准备阶段在项目指定 Conda 环境中完成全量 pytest：**494 passed，0 failed，0 skipped**。此外，已在 Windows 本机启动 PyQt5 客户端并成功显示摄像头画面。MySQL 凭据尚未完成配置，因此人脸注册及完整业务闭环尚未验证；现有验证也不代表模型精度或真实道路场景表现。

## 安全与隐私

- Flask API 未实现生产级身份鉴权，默认只用于本地演示，切勿直接暴露到公网。
- `.env`、模型权重、训练数据、数据库、日志、缓存、告警截图与真实人像均由 `.gitignore` 排除。
- 本仓库只保留经过匿名化处理的历史截图；完整软著说明书、登记证书及原始截图不公开。
- 不要使用真实个人数据进行公开演示；如需采集人脸或驾驶员资料，应先取得授权并制定保存、访问和删除策略。

## 第三方组件与许可

- YOLOv8 使用 Ultralytics 技术栈，基础模型与派生权重的分发义务需依据适用许可单独核实。
- InsightFace 预训练模型可能有额外用途或许可限制；仓库不包含 `buffalo_l` 权重。
- 本仓库暂未提供统一开源许可证。公开可阅读不等于获得任意复制、修改或商业使用授权；第三方依赖分别适用其许可证。

---

**用途：** 校园招聘技术作品展示与学习研究。建议先阅读架构与技术亮点，再查看 `client/core/`、`server/routes/` 和 `train/`。
