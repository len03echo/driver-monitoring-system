-- ============================================================
-- 智能驾驶员状态监测系统 数据库初始化脚本
-- MySQL 8.0
-- ============================================================

CREATE DATABASE IF NOT EXISTS driver_monitor
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE driver_monitor;

-- ------------------------------------------------------------
-- 表1：drivers（驾驶员档案表）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS drivers (
    id           INT          NOT NULL AUTO_INCREMENT        COMMENT '主键，自增ID',
    name         VARCHAR(50)  NOT NULL                       COMMENT '驾驶员姓名',
    employee_id  VARCHAR(30)  NOT NULL                       COMMENT '工号，全局唯一',
    face_feature BLOB                                        COMMENT '人脸特征向量（InsightFace ArcFace 512维 float32，numpy tobytes 序列化）；Web端新增时为 NULL',
    avatar_path  VARCHAR(255)                                COMMENT '头像图片相对路径，如 avatars/001.jpg',
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '档案创建时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_employee_id (employee_id)                  -- 工号唯一约束
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COMMENT='驾驶员档案';

-- ------------------------------------------------------------
-- 表2：sessions（监测会话表）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    id           INT      NOT NULL AUTO_INCREMENT            COMMENT '主键，自增ID',
    driver_id    INT      NOT NULL                           COMMENT '关联驾驶员ID',
    start_time   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '会话开始时间（身份认证通过时刻）',
    end_time     DATETIME                                    COMMENT '会话结束时间（停止监测或视频播放结束时刻）；NULL 表示会话进行中',
    total_alerts INT      NOT NULL DEFAULT 0                 COMMENT '本次会话累计告警次数',
    PRIMARY KEY (id),
    CONSTRAINT fk_session_driver
        FOREIGN KEY (driver_id) REFERENCES drivers(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    INDEX idx_session_driver_id (driver_id),
    INDEX idx_session_start_time (start_time)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COMMENT='监测会话';

-- ------------------------------------------------------------
-- 表3：alert_records（告警记录表）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alert_records (
    id            INT  NOT NULL AUTO_INCREMENT               COMMENT '主键，自增ID',
    driver_id     INT  NOT NULL                              COMMENT '关联驾驶员ID',
    session_id    INT  NOT NULL                              COMMENT '关联会话ID',
    alert_type    ENUM(
                      'phone',       -- 使用手机
                      'cup',         -- 持杯
                      'smoking',     -- 抽烟
                      'eye_closed',  -- 闭眼（疲劳）
                      'yawning',     -- 哈欠（疲劳）
                      'head_down',   -- 低头（疲劳）
                      'unknown'      -- 未知类型（兜底）
                  ) NOT NULL                                 COMMENT '告警类型枚举',
    severity      ENUM('low', 'medium', 'high') NOT NULL     COMMENT '危险等级：low/medium/high',
    snapshot_path VARCHAR(255)                               COMMENT '截图相对路径，格式：{session_id}_{alert_type}_{timestamp}.jpg',
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '告警触发时间',
    PRIMARY KEY (id),
    CONSTRAINT fk_alert_driver
        FOREIGN KEY (driver_id)  REFERENCES drivers(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_alert_session
        FOREIGN KEY (session_id) REFERENCES sessions(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    INDEX idx_alert_driver_id  (driver_id),
    INDEX idx_alert_session_id (session_id),
    INDEX idx_alert_created_at (created_at),
    INDEX idx_alert_type       (alert_type),
    INDEX idx_alert_severity   (severity)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COMMENT='告警记录';

-- ------------------------------------------------------------
-- 验证脚本：检查表结构和约束
-- ------------------------------------------------------------

-- 显示数据库信息
SELECT 'Database created successfully' as status;
SHOW TABLES;

-- 显示表结构
DESCRIBE drivers;
DESCRIBE sessions;
DESCRIBE alert_records;

-- 验证外键约束
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    CONSTRAINT_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM 
    INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
WHERE 
    REFERENCED_TABLE_SCHEMA = 'driver_monitor'
    AND REFERENCED_TABLE_NAME IS NOT NULL;

-- 验证唯一约束
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    CONSTRAINT_NAME
FROM 
    INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
WHERE 
    TABLE_SCHEMA = 'driver_monitor'
    AND CONSTRAINT_NAME LIKE 'uk_%';