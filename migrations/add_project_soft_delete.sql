-- Migration: add soft delete column to projects table

-- Add is_deleted column (MySQL syntax)
ALTER TABLE projects ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记';

-- Create index for performance
CREATE INDEX idx_projects_is_deleted ON projects (is_deleted);
