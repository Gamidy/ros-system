-- ROS 项目模型产品经理业务字段迁移
-- 执行方式: mysql -u ros -pNingBo2026* ros < migrations/add_pm_fields.sql

ALTER TABLE projects ADD COLUMN market_policy VARCHAR(200) NULL COMMENT '市场政策背景';
ALTER TABLE projects ADD COLUMN annual_planning_ref VARCHAR(100) NULL COMMENT '年度规划关联';
ALTER TABLE projects ADD COLUMN budget INT NULL COMMENT '项目预算(元)';
