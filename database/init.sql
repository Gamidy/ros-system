-- PLM 系统数据库初始化脚本
-- PostgreSQL 14+

-- 创建数据库
-- CREATE DATABASE plm_system WITH ENCODING = 'UTF8';

-- 启用必要扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 租户表
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    username VARCHAR(100) NOT NULL,
    email VARCHAR(200) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    department VARCHAR(200),
    title VARCHAR(100),
    phone VARCHAR(50),
    avatar_url VARCHAR(500),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'locked')),
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(tenant_id, username),
    UNIQUE(tenant_id, email)
);

-- 角色表
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    code VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, code)
);

-- 权限表
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(200) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    module VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 角色权限关联
CREATE TABLE role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id, permission_id)
);

-- 用户角色关联
CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);

-- 物料分类表
CREATE TABLE material_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    parent_id UUID REFERENCES material_categories(id),
    code VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    level INTEGER DEFAULT 1,
    path VARCHAR(500),
    sort_order INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, code)
);

-- 物料主数据表
CREATE TABLE materials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    category_id UUID REFERENCES material_categories(id),
    part_number VARCHAR(200) NOT NULL,
    part_name VARCHAR(500) NOT NULL,
    part_type VARCHAR(50) NOT NULL CHECK (part_type IN ('raw', 'component', 'assembly', 'finished', 'semi-finished', 'tool')),
    specification TEXT,
    unit VARCHAR(50) DEFAULT 'PCS',
    version VARCHAR(20) DEFAULT 'A.1',
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'released', 'obsolete', 'pending')),
    lifecycle_phase VARCHAR(50) DEFAULT 'development' CHECK (lifecycle_phase IN ('concept', 'development', 'production', 'mature', 'obsolete')),
    manufacturer VARCHAR(200),
    manufacturer_part_number VARCHAR(200),
    cost DECIMAL(15, 4) DEFAULT 0,
    weight DECIMAL(10, 4),
    weight_unit VARCHAR(20),
    description TEXT,
    custom_attributes JSONB,
    created_by UUID NOT NULL REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(tenant_id, part_number, version)
);

-- 物料版本历史
CREATE TABLE material_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    material_id UUID NOT NULL REFERENCES materials(id),
    version VARCHAR(20) NOT NULL,
    change_description TEXT,
    change_reason TEXT,
    status VARCHAR(20) DEFAULT 'draft',
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 替代料关系表
CREATE TABLE material_substitutes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    material_id UUID NOT NULL REFERENCES materials(id),
    substitute_id UUID NOT NULL REFERENCES materials(id),
    priority INTEGER DEFAULT 1,
    is_full_substitute BOOLEAN DEFAULT TRUE,
    notes TEXT,
    valid_from DATE,
    valid_until DATE,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(material_id, substitute_id)
);

-- BOM表
CREATE TABLE boms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    material_id UUID NOT NULL REFERENCES materials(id),
    version VARCHAR(20) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'released', 'obsolete')),
    is_default BOOLEAN DEFAULT FALSE,
    effective_date DATE,
    expiry_date DATE,
    created_by UUID NOT NULL REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, material_id, version)
);

-- BOM行项目表
CREATE TABLE bom_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bom_id UUID NOT NULL REFERENCES boms(id) ON DELETE CASCADE,
    material_id UUID NOT NULL REFERENCES materials(id),
    parent_item_id UUID REFERENCES bom_items(id),
    quantity DECIMAL(15, 6) NOT NULL DEFAULT 1,
    unit VARCHAR(50),
    reference_designator VARCHAR(100),
    position VARCHAR(100),
    notes TEXT,
    is_optional BOOLEAN DEFAULT FALSE,
    is_substitute_allowed BOOLEAN DEFAULT FALSE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 变更请求表（ECR）
CREATE TABLE change_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    request_number VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    change_type VARCHAR(50) NOT NULL CHECK (change_type IN ('design', 'process', 'material', 'specification', 'other')),
    priority VARCHAR(20) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'submitted', 'reviewing', 'approved', 'rejected', 'cancelled')),
    requested_by UUID NOT NULL REFERENCES users(id),
    requested_date DATE DEFAULT CURRENT_DATE,
    target_date DATE,
    impact_analysis TEXT,
    affected_materials UUID[],
    affected_boms UUID[],
    affected_documents UUID[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, request_number)
);

-- 变更单表（ECO）
CREATE TABLE change_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    order_number VARCHAR(100) NOT NULL,
    change_request_id UUID REFERENCES change_requests(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    change_type VARCHAR(50) NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'submitted', 'reviewing', 'approved', 'implemented', 'rejected', 'cancelled')),
    planned_by UUID NOT NULL REFERENCES users(id),
    planned_date DATE DEFAULT CURRENT_DATE,
    target_impl_date DATE,
    actual_impl_date DATE,
    implementation_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, order_number)
);

-- 变更单行项目
CREATE TABLE change_order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    change_order_id UUID NOT NULL REFERENCES change_orders(id) ON DELETE CASCADE,
    action_type VARCHAR(50) NOT NULL CHECK (action_type IN ('add', 'remove', 'modify', 'replace')),
    object_type VARCHAR(50) NOT NULL CHECK (object_type IN ('material', 'bom', 'document', 'process')),
    object_id UUID NOT NULL,
    old_value JSONB,
    new_value JSONB,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'implemented', 'cancelled')),
    implemented_at TIMESTAMP WITH TIME ZONE,
    implemented_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 项目表
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    project_code VARCHAR(100) NOT NULL,
    project_name VARCHAR(500) NOT NULL,
    description TEXT,
    project_type VARCHAR(50) DEFAULT 'product' CHECK (project_type IN ('product', 'process', 'research', 'improvement')),
    status VARCHAR(20) DEFAULT 'planning' CHECK (status IN ('planning', 'active', 'on_hold', 'completed', 'cancelled')),
    priority VARCHAR(20) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'critical')),
    manager_id UUID REFERENCES users(id),
    start_date DATE,
    target_end_date DATE,
    actual_end_date DATE,
    budget DECIMAL(15, 2),
    progress DECIMAL(5, 2) DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    created_by UUID NOT NULL REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, project_code)
);

-- 项目任务表
CREATE TABLE project_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES project_tasks(id),
    task_code VARCHAR(100),
    task_name VARCHAR(500) NOT NULL,
    description TEXT,
    task_type VARCHAR(50) DEFAULT 'task' CHECK (task_type IN ('milestone', 'task', 'phase', 'deliverable')),
    status VARCHAR(20) DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'completed', 'blocked', 'cancelled')),
    priority VARCHAR(20) DEFAULT 'normal',
    assigned_to UUID REFERENCES users(id),
    planned_start DATE,
    planned_end DATE,
    actual_start DATE,
    actual_end DATE,
    estimated_hours DECIMAL(8, 2),
    actual_hours DECIMAL(8, 2),
    progress DECIMAL(5, 2) DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    created_by UUID NOT NULL REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 文档表
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    document_number VARCHAR(200) NOT NULL,
    document_name VARCHAR(500) NOT NULL,
    document_type VARCHAR(100) NOT NULL,
    category VARCHAR(100),
    description TEXT,
    version VARCHAR(20) DEFAULT '1.0',
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'approved', 'released', 'obsolete')),
    file_path VARCHAR(500),
    file_size BIGINT,
    file_hash VARCHAR(100),
    mime_type VARCHAR(100),
    content TEXT,
    created_by UUID NOT NULL REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(tenant_id, document_number, version)
);

-- 文档关联表
CREATE TABLE document_relations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id),
    related_object_type VARCHAR(50) NOT NULL,
    related_object_id UUID NOT NULL,
    relation_type VARCHAR(50) DEFAULT 'reference',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, related_object_type, related_object_id)
);

-- 工作流定义表
CREATE TABLE workflow_definitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    code VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    applicable_object_types VARCHAR(100)[] NOT NULL,
    definition JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    version INTEGER DEFAULT 1,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, code, version)
);

-- 工作流实例表
CREATE TABLE workflow_instances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_definition_id UUID NOT NULL REFERENCES workflow_definitions(id),
    object_type VARCHAR(100) NOT NULL,
    object_id UUID NOT NULL,
    status VARCHAR(20) DEFAULT 'running' CHECK (status IN ('running', 'completed', 'cancelled', 'suspended')),
    current_node_id VARCHAR(100),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_by UUID NOT NULL REFERENCES users(id)
);

-- 工作流任务表（审批任务）
CREATE TABLE workflow_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_instance_id UUID NOT NULL REFERENCES workflow_instances(id),
    node_id VARCHAR(100) NOT NULL,
    node_name VARCHAR(200) NOT NULL,
    task_type VARCHAR(50) NOT NULL CHECK (task_type IN ('approval', 'notification', 'automation')),
    assignee_id UUID REFERENCES users(id),
    assignee_role_id UUID REFERENCES roles(id),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'delegated', 'cancelled')),
    comments TEXT,
    due_date TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    completed_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 审计日志表
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    object_type VARCHAR(100) NOT NULL,
    object_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_materials_tenant ON materials(tenant_id);
CREATE INDEX idx_materials_category ON materials(category_id);
CREATE INDEX idx_materials_part_number ON materials(part_number);
CREATE INDEX idx_materials_status ON materials(status);
CREATE INDEX idx_boms_material ON boms(material_id);
CREATE INDEX idx_bom_items_bom ON bom_items(bom_id);
CREATE INDEX idx_bom_items_material ON bom_items(material_id);
CREATE INDEX idx_change_requests_tenant ON change_requests(tenant_id);
CREATE INDEX idx_change_orders_tenant ON change_orders(tenant_id);
CREATE INDEX idx_projects_tenant ON projects(tenant_id);
CREATE INDEX idx_project_tasks_project ON project_tasks(project_id);
CREATE INDEX idx_documents_tenant ON documents(tenant_id);
CREATE INDEX idx_audit_logs_tenant ON audit_logs(tenant_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- 创建全文搜索索引
CREATE INDEX idx_materials_search ON materials USING gin(to_tsvector('chinese', part_name || ' ' || COALESCE(description, '')));
CREATE INDEX idx_documents_search ON documents USING gin(to_tsvector('chinese', document_name || ' ' || COALESCE(description, '')));

-- 插入默认数据
INSERT INTO tenants (code, name, description) VALUES 
('default', '默认租户', '系统默认租户');

INSERT INTO permissions (code, name, module, action, description) VALUES
('material.view', '查看物料', 'material', 'view', '查看物料信息'),
('material.create', '创建物料', 'material', 'create', '创建新物料'),
('material.edit', '编辑物料', 'material', 'edit', '编辑物料信息'),
('material.delete', '删除物料', 'material', 'delete', '删除物料'),
('bom.view', '查看BOM', 'bom', 'view', '查看BOM结构'),
('bom.create', '创建BOM', 'bom', 'create', '创建BOM'),
('bom.edit', '编辑BOM', 'bom', 'edit', '编辑BOM'),
('change.view', '查看变更', 'change', 'view', '查看变更请求/单'),
('change.create', '创建变更', 'change', 'create', '创建变更请求/单'),
('change.approve', '审批变更', 'change', 'approve', '审批变更请求/单'),
('project.view', '查看项目', 'project', 'view', '查看项目信息'),
('project.create', '创建项目', 'project', 'create', '创建项目'),
('project.edit', '编辑项目', 'project', 'edit', '编辑项目'),
('document.view', '查看文档', 'document', 'view', '查看文档'),
('document.create', '创建文档', 'document', 'create', '创建文档'),
('document.edit', '编辑文档', 'document', 'edit', '编辑文档'),
('system.manage', '系统管理', 'system', 'manage', '系统管理权限');
