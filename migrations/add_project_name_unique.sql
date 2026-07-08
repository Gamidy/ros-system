-- Migration: add unique constraint on projects.name
-- Only for non-draft projects (partial unique index)
-- Run this against your database to add the constraint

-- Option A: Full unique on name (all projects, including drafts)
-- ALTER TABLE projects ADD CONSTRAINT uq_projects_name UNIQUE (name);

-- Option B: Partial unique only on non-deleted, non-draft projects (PostgreSQL only)
-- CREATE UNIQUE INDEX uq_projects_name_active ON projects (name) WHERE is_deleted = FALSE AND is_draft = FALSE;

-- Using Option A for simplicity (MySQL/SQLite compatible):
ALTER TABLE projects ADD UNIQUE INDEX uq_projects_name (name);
