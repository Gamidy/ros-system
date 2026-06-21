<template>
  <div class="pm-workspace">
    <!-- ═══════════════ 顶部标题 ═══════════════ -->
    <div class="workspace-header">
      <h2>📋 产品经理工作台</h2>
      <span class="header-date">{{ currentDate }}</span>
    </div>

    <!-- ═══════════════ 我的提案（顶部横幅） ═══════════════ -->
    <div class="proposals-section" v-if="myProposals.length > 0">
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>📝 我的提案</span>
            <div class="proposals-filter">
              <el-radio-group v-model="proposalFilter" size="small" @change="fetchProposals">
                <el-radio-button value="all">全部 ({{ proposalCounts.all }})</el-radio-button>
                <el-radio-button value="draft">草稿 ({{ proposalCounts.draft }})</el-radio-button>
                <el-radio-button value="submitted">已提交 ({{ proposalCounts.submitted }})</el-radio-button>
              </el-radio-group>
            </div>
          </div>
        </template>
        <div class="proposals-list">
          <div
            v-for="prop in filteredProposals"
            :key="prop.id"
            class="proposal-item"
            @click="openProposal(prop)"
          >
            <div class="proposal-item-left">
              <span class="proposal-name">{{ prop.name }}</span>
              <span class="proposal-date">{{ formatDate(prop.updated_at || prop.created_at) }}</span>
            </div>
            <div class="proposal-item-right">
              <el-tag v-if="prop.is_draft" type="warning" size="small">草稿</el-tag>
              <el-tag v-else-if="prop.approval_status" :type="approvalTagType(prop.approval_status)" size="small">
                {{ approvalLabel(prop.approval_status) }}
              </el-tag>
              <el-tag :type="statusTagType(prop.status)" size="small">{{ statusLabel(prop.status) }}</el-tag>
              <!-- 撤销按钮：已提交且审批中 -->
              <el-button
                v-if="!prop.is_draft && prop.approval_status === 'pending'"
                type="warning"
                size="small"
                link
                style="margin-left:8px"
                @click.stop="withdrawProposal(prop)"
              >
                ↩️ 撤销
              </el-button>
            </div>
          </div>
        </div>
        <div v-if="filteredProposals.length === 0" class="empty-state">
          <el-empty description="暂无提案" :image-size="40" />
        </div>
      </el-card>
    </div>

    <!-- ═══════════════ 三栏布局 ═══════════════ -->
    <div class="workspace-body">
      <!-- 左栏 (30%)：年度产品规划 -->
      <div class="col-left">
        <el-card shadow="never" class="col-card">
          <template #header>
            <div class="card-header">
              <span>📋 年度产品规划</span>
              <el-button type="primary" size="small" @click="openPlanDialog">新建规划项</el-button>
            </div>
          </template>
          <el-input v-model="annualPlanningRef" :prefix-icon="Link" placeholder="规划文档引用链接" size="small" class="plan-ref-input" />
          <div v-if="planningItems.length === 0" class="empty-state">
            <el-empty description="暂无年度规划项" :image-size="60" />
          </div>
          <div
            v-for="item in planningItems"
            :key="item.id"
            class="plan-item"
            :class="{ 'plan-item--active': selectedPlanId === item.id }"
            @click="selectPlan(item)"
          >
            <div class="plan-item-name">{{ item.name }}</div>
            <div class="plan-item-meta">
              <el-tag size="small" type="warning">{{ item.year }}</el-tag>
              <span class="plan-item-desc">{{ item.description || '暂无描述' }}</span>
            </div>
            <div class="plan-item-count" v-if="item.project_count !== undefined">
              关联项目: {{ item.project_count }} 个
            </div>
            <div class="plan-item-actions">
              <el-button link circle :icon="Edit" size="small" @click.stop="editPlanItem(item)" title="编辑" />
              <el-button link circle :icon="Delete" size="small" @click.stop="deletePlanItem(item)" title="删除" />
            </div>
          </div>
          <!-- 选中规划 → 显示关联项目 -->
          <div v-if="filteredProjects.length > 0" class="linked-projects">
            <div class="linked-title">关联项目</div>
            <div v-for="proj in filteredProjects" :key="proj.id" class="linked-item">
              <span>{{ proj.name }}</span>
              <div class="linked-item-tags">
                <el-tag v-if="proj.approval_status" :type="approvalTagType(proj.approval_status)" size="small">{{ approvalLabel(proj.approval_status) }}</el-tag>
                <el-tag :type="statusTagType(proj.status)" size="small">{{ statusLabel(proj.status) }}</el-tag>
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 中栏 (40%)：产品立项入口 -->
      <div class="col-middle">
        <el-card shadow="never" class="col-card">
          <template #header>
            <div class="card-header">
              <span>📝 产品立项</span>
            </div>
          </template>
          <div class="initiation-intro">
            <p>新建产品立项申请，填写以下四个模块信息：</p>
            <ul>
              <li>📋 <strong>项目概述与市场</strong> — 基本信息、背景目标、市场分析、交付物</li>
              <li>⚙️ <strong>技术要求</strong> — 核心性能参数、安全合规、配件功能选配</li>
              <li>💰 <strong>成本核算</strong> — 开发费用、经济指标、模具/样机/人工/测试费用</li>
              <li>👥 <strong>团队与职责</strong> — 14角色团队选择、职责分工</li>
            </ul>
          </div>
          <el-button type="primary" size="large" style="width:100%;margin-top:16px" @click="openDrawer()">
            📝 产品立项
          </el-button>
          <div v-if="draftId" class="draft-hint">
            <el-tag type="warning" effect="dark">草稿</el-tag>
            <span>点击按钮继续编辑草稿</span>
          </div>
        </el-card>
      </div>

      <!-- 右栏 (30%)：我的项目看板 -->
      <div class="col-right">
        <el-card shadow="never" class="col-card">
          <template #header>
            <div class="card-header">
              <span>📊 我的项目</span>
            </div>
          </template>
          <!-- 统计行 -->
          <div class="stats-row">
            <div class="stat-item">
              <div class="stat-num">{{ myProjects.length }}</div>
              <div class="stat-label">总数</div>
            </div>
            <div class="stat-item">
              <div class="stat-num" style="color:#409eff">{{ stats.running }}</div>
              <div class="stat-label">进行中</div>
            </div>
            <div class="stat-item">
              <div class="stat-num" style="color:#67c23a">{{ stats.completed }}</div>
              <div class="stat-label">已完成</div>
            </div>
            <div class="stat-item">
              <div class="stat-num" style="color:#f56c6c">{{ stats.overdue }}</div>
              <div class="stat-label">超期</div>
            </div>
          </div>
          <div v-if="myProjects.length === 0" class="empty-state">
            <el-empty description="暂无项目" :image-size="60" />
          </div>
          <div v-for="proj in myProjects" :key="proj.id" class="project-card" @click="toggleExpand(proj.id)">
            <div class="project-card-header">
              <span class="project-name">{{ proj.name }}</span>
              <div class="project-card-tags">
                <el-tag v-if="proj.approval_status" :type="approvalTagType(proj.approval_status)" size="small">{{ approvalLabel(proj.approval_status) }}</el-tag>
                <el-tag :type="statusTagType(proj.status)" size="small">{{ statusLabel(proj.status) }}</el-tag>
              </div>
            </div>
            <el-progress
              :percentage="proj.progress || 0"
              :color="progressColor(proj.progress || 0)"
              :stroke-width="6"
              style="margin:6px 0"
            />
            <div class="project-card-meta" v-if="proj.budget || proj.market_policy">
              <span v-if="proj.budget">预算: ¥{{ formatMoney(proj.budget) }}</span>
              <span v-if="proj.market_policy">{{ proj.market_policy }}</span>
            </div>
            <!-- 展开详情 -->
            <div v-if="expandedProjectId === proj.id" class="project-detail">
              <div class="detail-row"><label>项目等级:</label> {{ proj.project_class || '-' }}级</div>
              <div class="detail-row"><label>应用场景:</label> {{ proj.scene || '-' }}</div>
              <div class="detail-row"><label>关联产品:</label> {{ proj.linked_product || '-' }}</div>
              <div class="detail-row"><label>目标日期:</label> {{ proj.target_end_date || '-' }}</div>
              <div class="detail-row"><label>背景:</label> {{ proj.background_basis || '-' }}</div>
              <div class="detail-row"><label>市场政策:</label> {{ proj.market_policy || '-' }}</div>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- ═══════════════ 对话框：新建年度规划项 ═══════════════ -->
    <el-dialog v-model="showPlanDialog" :title="editingPlanId ? '编辑年度规划项' : '新建年度规划项'" width="500px" :close-on-click-modal="false">
      <el-form :model="planForm" label-width="80px" size="small">
        <el-form-item label="名称">
          <el-input v-model="planForm.name" placeholder="如: 2026年度海外空调产品规划" />
        </el-form-item>
        <el-form-item label="年份">
          <el-input v-model="planForm.year" placeholder="如: 2026" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="planForm.description" type="textarea" :rows="3" placeholder="规划描述" />
        </el-form-item>
        <el-form-item label="文档引用">
          <el-input v-model="planForm.doc_ref" placeholder="文档链接或引用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPlanDialog = false">取消</el-button>
        <el-button type="primary" @click="savePlanItem" :loading="savingPlan">保存</el-button>
      </template>
    </el-dialog>

    <!-- ═══════════════ 抽屉：产品立项书 (85%宽度) ═══════════════ -->
    <el-drawer
      v-model="drawerVisible"
      title="📝 产品立项书 — 海外空调研发项目"
      size="85%"
      :close-on-click-modal="false"
      @close="resetForm"
    >
      <el-tabs v-model="activeTab" type="border-card" class="drawer-tabs">
        <!-- ═══════════ Tab 1: 项目概述与市场 ═══════════ -->
        <el-tab-pane name="overview_market">
          <template #label>
            <span>
              <span v-if="tabStatus.overview_market.valid">✅</span>
              <span v-else>❌</span>
              📋 项目概述与市场
            </span>
          </template>
          <el-form :model="projectForm" label-width="120px" size="small">
            <!-- 一、项目基本信息区 -->
            <el-divider content-position="left">一、项目基本信息区</el-divider>
            <!-- Row1: 项目名称 | 产品类型 | 目标市场 -->
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="项目名称">
                  <el-input :model-value="autoProjectName" disabled placeholder="自动生成" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="产品类型">
                  <el-select v-model="projectForm.product_type" placeholder="选择产品类型" clearable style="width:100%">
                    <el-option v-for="o in kbOptions.product_type" :key="o.code" :label="o.name" :value="o.code" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label-width="80px">
                  <template #label>
                    目标市场
                    <el-tooltip content="选择产品目标销售市场，将自动加载该市场的安全合规标准要求（UL/CE/CB等）" placement="top">
                      <el-icon style="margin-left:4px;cursor:help;color:#909399"><QuestionFilled /></el-icon>
                    </el-tooltip>
                  </template>
                  <el-select v-model="projectForm.target_market" placeholder="选择目标市场" clearable style="width:100%">
                    <el-option v-for="o in kbOptions.market" :key="o.code" :label="o.name" :value="o.code" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <!-- Row2: 系列名称 | 温带 | 制冷剂 | 能效等级 -->
            <el-row :gutter="16">
              <el-col :span="6">
                <el-form-item label="系列名称">
                  <el-select v-model="projectForm.series_name" placeholder="选择系列" clearable style="width:100%">
                    <el-option v-for="o in kbOptions.series" :key="o.code" :label="o.name" :value="o.code" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="温带">
                  <el-select v-model="projectForm.climate_zone" placeholder="选择温带" clearable style="width:100%">
                    <el-option label="T1（热带）" value="T1" />
                    <el-option label="T2（温带）" value="T2" />
                    <el-option label="T3（寒带）" value="T3" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="制冷剂">
                  <el-select v-model="projectForm.refrigerant" placeholder="选择制冷剂" clearable style="width:100%">
                    <el-option label="R32" value="R32" />
                    <el-option label="R410A" value="R410A" />
                    <el-option label="R290" value="R290" />
                    <el-option label="R454B" value="R454B" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="能效等级">
                  <el-select v-model="projectForm.energy_rating" placeholder="能效星级" clearable style="width:100%">
                    <el-option v-for="o in kbOptions.energy_rating" :key="o.code" :label="o.name" :value="o.code" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <!-- Row3: 能力段 | 电压频率 | 客户名称 -->
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="能力段">
                  <el-select v-model="projectForm.capacity_range" placeholder="选择能力段" clearable style="width:100%">
                    <el-option v-for="o in kbOptions.capacity" :key="o.code" :label="o.name" :value="o.code" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="电压频率">
                  <el-select v-model="projectForm.voltage_freq" placeholder="选择电压频率" clearable style="width:100%">
                    <el-option v-for="o in kbOptions.voltage" :key="o.code" :label="o.name" :value="o.code" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="客户名称">
                  <el-input v-model="projectForm.customer_name" placeholder="客户名称" />
                </el-form-item>
              </el-col>
            </el-row>
            <!-- Row4: 立项日期 | 计划完成 | 项目周期 -->
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="立项日期">
                  <el-date-picker v-model="projectForm.start_date" type="date" placeholder="立项日期" style="width:100%" value-format="YYYY-MM-DD" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="计划完成">
                  <el-date-picker v-model="projectForm.target_end_date" type="date" placeholder="计划完成日期" style="width:100%" value-format="YYYY-MM-DD" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="项目周期">
                  <el-input :model-value="autoProjectDuration" disabled placeholder="自动计算" />
                </el-form-item>
              </el-col>
            </el-row>
            <!-- Row5: 知识产权归属 | 开发类别 | 项目来源 -->
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="知识产权归属">
                  <el-select v-model="projectForm.ip_ownership" placeholder="选择IP归属" clearable style="width:100%">
                    <el-option v-for="o in kbOptions.ip_ownership" :key="o.code" :label="o.name" :value="o.code" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label-width="80px">
                  <template #label>
                    开发类别
                    <el-tooltip content="项目开发等级决定试制数量、评审流程等。全新开发≥20台试制，派生≥10台，降本优化≥5台" placement="top">
                      <el-icon style="margin-left:4px;cursor:help;color:#909399"><QuestionFilled /></el-icon>
                    </el-tooltip>
                  </template>
                  <el-select v-model="projectForm.dev_category" placeholder="选择开发类别" clearable style="width:100%">
                    <el-option label="全新开发" value="全新开发" />
                    <el-option label="派生" value="派生" />
                    <el-option label="降本优化" value="降本优化" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="项目来源">
                  <el-select v-model="projectForm.project_origin" placeholder="选择项目来源" clearable style="width:100%">
                    <el-option label="产品年度规划" value="产品年度规划" />
                    <el-option label="客户需求" value="客户需求" />
                    <el-option label="品质整改" value="品质整改" />
                    <el-option label="研发降本" value="研发降本" />
                    <el-option label="供应链二供" value="供应链二供" />
                    <el-option label="工艺提效" value="工艺提效" />
                    <el-option label="法规升级" value="法规升级" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <!-- ⭐ 条件联动：项目来源选"产品年度规划"时显示 -->
            <el-form-item v-if="projectForm.project_origin === '产品年度规划'" label="年度规划项">
              <el-select v-model="projectForm.annual_planning_id" placeholder="选择关联的年度规划项" clearable filterable style="width:100%">
                <el-option v-for="item in planningItems" :key="item.id" :label="`${item.name} (${item.year})`" :value="item.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="其他要求">
              <el-input v-model="projectForm.other_requirements" type="textarea" :rows="2" placeholder="其他特殊要求" />
            </el-form-item>

            <!-- 二、项目背景与目标 -->
            <el-divider content-position="left">二、项目背景与目标</el-divider>
            <el-form-item label="立项背景与依据">
              <el-input v-model="projectForm.background_basis" type="textarea" :rows="3" placeholder="项目立项背景、市场依据等" />
            </el-form-item>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="目标BOM成本">
                  <el-input :model-value="projectForm.bom_cost_target || '暂无数据'" disabled placeholder="← 成本核算Tab同步">
                    <template #suffix>
                      <span style="color:#909399;font-size:12px">← 成本核算Tab同步</span>
                    </template>
                  </el-input>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="年销量预测">
                  <el-input :model-value="projectForm.annual_sales_forecast || '暂无数据'" disabled placeholder="← 成本核算Tab同步">
                    <template #suffix>
                      <span style="color:#909399;font-size:12px">← 成本核算Tab同步</span>
                    </template>
                  </el-input>
                </el-form-item>
              </el-col>
            </el-row>

            <!-- 三、市场分析 -->
            <el-divider content-position="left">三、市场分析</el-divider>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="能效要求">
                  <el-input v-model="projectForm.energy_efficiency_req" placeholder="如: SEER≥6.1" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label-width="80px">
                  <template #label>
                    认证要求
                    <el-tooltip content="从Tab3安全合规标准自动生成，选择目标市场后自动加载对应市场的认证标准要求" placement="top">
                      <el-icon style="margin-left:4px;cursor:help;color:#909399"><QuestionFilled /></el-icon>
                    </el-tooltip>
                  </template>
                  <el-input :model-value="certRequirementsText" disabled placeholder="自动生成">
                    <template #suffix>
                      <span style="color:#67c23a;font-size:12px">自动</span>
                    </template>
                  </el-input>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="年度规划引用">
              <el-select v-model="projectForm.annual_planning_ref" placeholder="选择年度规划引用" clearable filterable style="width:100%">
                <el-option v-for="item in planningItems" :key="item.id" :label="item.name" :value="item.name" />
              </el-select>
            </el-form-item>

            <!-- 客户关键需求表格 -->
            <el-divider content-position="left">客户关键需求</el-divider>
            <el-table :data="customerReqTable" border size="small" class="section-table">
              <el-table-column prop="category" label="需求类别" width="120">
                <template #default="{ row }">
                  <el-input v-model="row.category" size="small" placeholder="类别" />
                </template>
              </el-table-column>
              <el-table-column prop="description" label="需求描述" min-width="160">
                <template #default="{ row }">
                  <el-input v-model="row.description" size="small" placeholder="需求描述" />
                </template>
              </el-table-column>
              <el-table-column prop="source" label="需求来源" width="120">
                <template #default="{ row }">
                  <el-input v-model="row.source" size="small" placeholder="来源" />
                </template>
              </el-table-column>
              <el-table-column prop="tech_impact" label="技术影响" width="120">
                <template #default="{ row }">
                  <el-input v-model="row.tech_impact" size="small" placeholder="技术影响" />
                </template>
              </el-table-column>
              <el-table-column prop="market_impact" label="市场影响" width="120">
                <template #default="{ row }">
                  <el-input v-model="row.market_impact" size="small" placeholder="市场影响" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="70">
                <template #default="{ $index }">
                  <el-button link type="danger" size="small" @click="removeCustomerReqRow($index)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-button size="small" style="margin-top:8px" @click="addCustomerReqRow">+ 添加行</el-button>

            <!-- 四、交付物 -->
            <el-divider content-position="left">四、交付物</el-divider>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="样机数量">
                  <el-input-number v-model="projectForm.sample_qty" :min="0" :step="1" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="样机需求日期">
                  <el-date-picker v-model="projectForm.sample_required_date" type="date" placeholder="需求日期" style="width:100%" value-format="YYYY-MM-DD" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="交付物清单">
              <el-input v-model="projectForm.deliverables" type="textarea" :rows="3" placeholder="项目交付物清单（样机/图纸/BOM/测试报告等）" />
            </el-form-item>

            <!-- 底部：所属项目群 + 项目负责人 -->
            <el-divider content-position="left">项目归属</el-divider>
            <el-form-item label="所属项目群" label-width="120px" size="small">
              <el-select v-model="projectForm.program_id" placeholder="选择项目群" clearable filterable style="width:100%">
                <el-option v-for="p in programOptions" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="项目负责人" label-width="120px" size="small">
              <el-select v-model="projectForm.leader_id" placeholder="从团队成员中选择" clearable filterable style="width:100%">
                <el-option v-for="u in allTeamUsers" :key="u.id" :label="`${u.full_name || u.username} (${u.role})`" :value="u.id" />
              </el-select>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- ═══════════ Tab 3: 技术要求 ═══════════ -->
        <el-tab-pane name="technical">
          <template #label>
            <span>
              <span v-if="tabStatus.technical.valid">✅</span>
              <span v-else>❌</span>
              ⚙️ 技术要求
            </span>
          </template>

          <!-- 流程引导 el-steps -->
          <el-steps :active="techStep" finish-status="success" align-center style="margin-bottom:20px;cursor:pointer">
            <el-step title="性能指标" description="核心性能参数" @click="techStep = 0" />
            <el-step title="安全合规" description="法规标准要求" @click="techStep = 1" />
            <el-step title="物料部件" description="关键物料与部件" @click="techStep = 2" />
            <el-step title="附件/功能配置" description="配件与功能选配" @click="techStep = 3" />
          </el-steps>

          <!-- Step ❶: 性能指标 -->
          <template v-if="techStep === 0">
            <el-divider content-position="left">❶ 核心性能参数</el-divider>
            <el-table :data="corePerfTable" border size="small" class="section-table">
              <el-table-column prop="param_name" label="参数名称" width="130">
                <template #default="{ row }">
                  <el-input v-model="row.param_name" size="small" placeholder="如: 制冷量(W)" />
                </template>
              </el-table-column>
              <el-table-column prop="baseline" label="基准值" width="140">
                <template #default="{ row }">
                  <el-input
                    v-if="row.source === 'auto' || row.source === 'market_config'"
                    :model-value="row.baseline"
                    size="small"
                    disabled
                  />
                  <el-input v-else v-model="row.baseline" size="small" placeholder="手动填写" />
                </template>
              </el-table-column>
              <el-table-column prop="target_value" label="目标值" width="140">
                <template #default="{ row }">
                  <el-input v-model="row.target_value" size="small" placeholder="如: 3500W" />
                </template>
              </el-table-column>
              <el-table-column prop="aux_competitor" label="AUX竞品" width="120">
                <template #default="{ row }">
                  <el-input v-model="row.aux_competitor" size="small" placeholder="AUX对应值" />
                </template>
              </el-table-column>
              <el-table-column prop="tcl_competitor" label="TCL竞品" width="120">
                <template #default="{ row }">
                  <el-input v-model="row.tcl_competitor" size="small" placeholder="TCL对应值" />
                </template>
              </el-table-column>
              <el-table-column prop="source" label="来源" width="100">
                <template #default="{ row }">
                  <el-tag v-if="row.source === 'auto'" type="success" size="small">自动</el-tag>
                  <el-tag v-else-if="row.source === 'market_config'" type="primary" size="small">市场配置</el-tag>
                  <el-tag v-else type="info" size="small">手动</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="70">
                <template #default="{ $index }">
                  <el-button link type="danger" size="small" @click="removeCorePerfRow($index)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-button size="small" style="margin-top:8px" @click="addCorePerfRow">+ 添加行</el-button>
            <CompetitorBench 
              :market="projectForm.target_market"
              :coolingCapacity="projectForm.capacity_range"
              @adopt="onAdoptCompetitor"
            />
          </template>

          <!-- Step ❷: 安全合规 -->
          <template v-if="techStep === 1">
            <el-divider content-position="left">❷ 安全与合规要求</el-divider>
            <div v-if="safetyComplianceTable.length === 0" style="color:#909399;font-size:13px;padding:20px 0">
              请在「项目概述与市场」中选择目标市场以加载安全合规标准
            </div>
            <el-table v-else :data="safetyComplianceTable" border size="small" class="section-table">
              <el-table-column prop="standard" label="法规标准" width="160">
                <template #default="{ row }">
                  <span class="linked-val">{{ row.standard }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="applicable_market" label="适用市场" width="100">
                <template #default="{ row }">
                  <span class="linked-val">{{ row.applicable_market }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="key_requirement" label="关键要求" min-width="140">
                <template #default="{ row }">
                  <span class="linked-val">{{ row.key_requirement }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="verification_method" label="验证方式" width="120">
                <template #default="{ row }">
                  <span class="linked-val">{{ row.verification_method }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="involved_parts" label="涉及零部件" width="120">
                <template #default="{ row }">
                  <el-input v-model="row.involved_parts" size="small" placeholder="如: 压缩机/电控板" />
                </template>
              </el-table-column>
              <el-table-column prop="cert_cycle" label="认证周期" width="100">
                <template #default="{ row }">
                  <el-input v-model="row.cert_cycle" size="small" placeholder="如: 45天" />
                </template>
              </el-table-column>
              <el-table-column prop="remark" label="备注" width="140">
                <template #default="{ row }">
                  <el-input v-model="row.remark" size="small" placeholder="如: 需第三方检测" />
                </template>
              </el-table-column>
            </el-table>
          </template>

          <!-- Step ❸: 物料部件 -->
          <template v-if="techStep === 2">
            <el-divider content-position="left">❸ 物料与部件清单</el-divider>
            <el-table :data="materialComponentTable" border size="small" class="section-table">
              <el-table-column prop="type" label="类型" width="90">
                <template #default="{ row }">
                  <el-select v-model="row.type" size="small" style="width:100%">
                    <el-option label="物料" value="物料" />
                    <el-option label="部件" value="部件" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column prop="name" label="名称" width="120">
                <template #default="{ row }">
                  <el-input v-model="row.name" size="small" placeholder="如: 蒸发器" />
                </template>
              </el-table-column>
              <el-table-column prop="spec" label="规格" width="120">
                <template #default="{ row }">
                  <el-input v-model="row.spec" size="small" placeholder="如: Φ7×0.25 双排" />
                </template>
              </el-table-column>
              <el-table-column prop="qty" label="数量" width="80">
                <template #default="{ row }">
                  <el-input-number v-model="row.qty" :min="0" :step="1" size="small" controls-position="right" style="width:100%" />
                </template>
              </el-table-column>
              <el-table-column prop="unit" label="单位" width="70">
                <template #default="{ row }">
                  <el-input v-model="row.unit" size="small" placeholder="如: 个/套/m" />
                </template>
              </el-table-column>
              <el-table-column prop="usage" label="用途" width="100">
                <template #default="{ row }">
                  <el-input v-model="row.usage" size="small" placeholder="如: 换热核心部件" />
                </template>
              </el-table-column>
              <el-table-column prop="supplier" label="供应商" width="120">
                <template #default="{ row }">
                  <el-input v-model="row.supplier" size="small" placeholder="如: 美的/格力" />
                </template>
              </el-table-column>
              <el-table-column prop="delivery_cycle" label="交期" width="90">
                <template #default="{ row }">
                  <el-input v-model="row.delivery_cycle" size="small" placeholder="如: 30天" />
                </template>
              </el-table-column>
              <el-table-column prop="unit_price" label="单价(¥)" width="100">
                <template #default="{ row }">
                  <el-input-number v-model="row.unit_price" :min="0" :step="0.01" size="small" controls-position="right" style="width:100%" />
                </template>
              </el-table-column>
              <el-table-column prop="subtotal" label="小计(¥)" width="100">
                <template #default="{ row }">
                  <span>{{ ((row.qty || 0) * (row.unit_price || 0)).toFixed(2) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="candidate_vendors" label="候选厂家" min-width="160">
                <template #default="{ row }">
                  <el-input v-model="row.candidate_vendors" type="textarea" :rows="2" size="small" placeholder="一行一个厂家" />
                </template>
              </el-table-column>
              <el-table-column prop="remark" label="备注" width="120">
                <template #default="{ row }">
                  <el-input v-model="row.remark" size="small" placeholder="如: 长周期物料(8周)" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="70" fixed="right">
                <template #default="{ $index }">
                  <el-button link type="danger" size="small" @click="removeMaterialComponentRow($index)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-button size="small" style="margin-top:8px" @click="addMaterialComponentRow">+ 添加行</el-button>
          </template>

          <!-- Step ❹: 附件/功能配置 -->
          <template v-if="techStep === 3">
            <el-divider content-position="left">❹ 附件配置</el-divider>
            <el-table :data="accessoryConfigTable" border size="small" class="section-table">
              <el-table-column prop="name" label="配件名称" min-width="160">
                <template #default="{ row }">
                  <span>{{ row.name }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="selection" label="选配情况" min-width="160">
                <template #default="{ row }">
                  <el-select v-model="row.selection" size="small" style="width:100%">
                    <el-option label="标配" value="标配" />
                    <el-option label="选配" value="选配" />
                    <el-option label="不配" value="不配" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="" width="90">
                <template #default="{ row }">
                  <span v-if="row.selection !== row._original" style="color:#e6a23c;font-size:12px">✏️ 已调整</span>
                </template>
              </el-table-column>
            </el-table>

            <el-divider content-position="left" style="margin-top:20px">❹ 功能配置</el-divider>
            <el-table :data="featureConfigTable" border size="small" class="section-table">
              <el-table-column prop="name" label="功能名称" min-width="160">
                <template #default="{ row }">
                  <span>{{ row.name }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="selection" label="选配情况" min-width="160">
                <template #default="{ row }">
                  <el-select v-model="row.selection" size="small" style="width:100%">
                    <el-option label="标配" value="标配" />
                    <el-option label="选配" value="选配" />
                    <el-option label="不配" value="不配" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="" width="90">
                <template #default="{ row }">
                  <span v-if="row.selection !== row._original" style="color:#e6a23c;font-size:12px">✏️ 已调整</span>
                </template>
              </el-table-column>
            </el-table>
          </template>

          <!-- 竞品快速参考 -->
          <el-divider content-position="left">🔍 竞品快速参考</el-divider>
          <el-collapse v-model="competitorRefActive" style="margin-top:8px">
            <el-collapse-item title="展开竞品数据对比（根据已选目标市场和冷量段自动过滤）" name="ref">
              <el-table :data="quickRefCompetitors" border size="small" max-height="300">
                <el-table-column prop="brand" label="品牌" width="80" />
                <el-table-column prop="model" label="型号" width="140" />
                <el-table-column prop="cooling_capacity" label="冷量" width="70" />
                <el-table-column prop="energy_rating" label="能效" width="60" />
                <el-table-column prop="cooling_w" label="制冷(W)" width="80" />
                <el-table-column prop="eer" label="EER" width="60" />
                <el-table-column prop="noise_indoor_db" label="噪音(dB)" width="80" />
                <el-table-column prop="factory_price" label="出厂价" width="90" />
              </el-table>
            </el-collapse-item>
          </el-collapse>
        </el-tab-pane>

        <!-- ═══════════ Tab 4: 成本核算 ═══════════ -->
        <el-tab-pane name="cost">
          <template #label>
            <span>
              <span v-if="tabStatus.cost.valid">✅</span>
              <span v-else>❌</span>
              💰 成本核算
            </span>
          </template>
          <!-- 一、项目开发费用 -->
          <el-divider content-position="left">一、项目开发费用</el-divider>
          <el-table :data="devCostTable" border size="small" class="section-table">
            <el-table-column prop="item" label="费用项目" width="140" />
            <el-table-column label="预算(W)" width="140">
              <template #default="{ row }">
                <template v-if="row.item === '委外开发费用'">
                  <el-input-number
                    v-if="projectForm.has_outsourcing"
                    v-model="row.budget"
                    :min="0" :step="0.1" size="small" controls-position="right" style="width:100%"
                  />
                  <span v-else class="linked-val">0.0</span>
                </template>
                <template v-else>
                  <el-input-number
                    v-if="!row.linked"
                    v-model="row.budget"
                    :min="0" :step="0.1" size="small" controls-position="right" style="width:100%"
                  />
                  <span v-else class="linked-val">{{ row.budget.toFixed(1) }}</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column label="占比%" width="100">
              <template #default="{ row }">
                {{ devCostGrandTotal > 0 ? ((row.budget / devCostGrandTotal) * 100).toFixed(1) : '0.0' }}%
              </template>
            </el-table-column>
            <el-table-column prop="remark" label="说明" min-width="280">
              <template #default="{ row }">
                <span class="linked-val">{{ row.remark }}</span>
              </template>
            </el-table-column>
          </el-table>
          <div class="cost-summary">开发费用合计: <strong>¥{{ devCostGrandTotal.toFixed(1) }} 万元</strong></div>
          <div style="margin-top:8px;display:flex;align-items:center;gap:8px">
            <el-switch v-model="projectForm.has_outsourcing" size="small" active-text="有委外开发" inactive-text="无委外开发" />
          </div>

          <!-- 二、经济指标分析 -->
          <el-divider content-position="left">二、经济指标分析</el-divider>
          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item label="目标出厂价FOB($)(美元)" label-width="150px" size="small">
                <el-input-number v-model="projectForm.fob_price" :min="0" :step="1" size="small" controls-position="right" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="汇率(USD/CNY)" label-width="130px" size="small">
                <el-input :model-value="exchangeRate.toFixed(2)" disabled size="small" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="目标BOM成本(￥)(人民币)" label-width="140px" size="small">
                <el-input-number v-model="projectForm.bom_cost_target" :min="0" :step="1" size="small" controls-position="right" style="width:100%" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item label-width="150px" size="small">
                <template #label>
                  BOM成本占比
                  <el-tooltip content="BOM成本占出厂价的比例，计算公式: BOM成本÷(FOB价格×汇率)×100%" placement="top">
                    <el-icon style="margin-left:4px;cursor:help;color:#909399"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </template>
                <el-input :model-value="bomCostRatioText" disabled size="small" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label-width="130px" size="small">
                <template #label>
                  制造费用+人工(￥)
                  <el-tooltip content="制造费用和人工成本合计(万元)，由系统按配置自动计算" placement="top">
                    <el-icon style="margin-left:4px;cursor:help;color:#909399"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </template>
                <el-input :model-value="manufacturingCost.toFixed(0)" disabled size="small" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label-width="140px" size="small">
                <template #label>
                  毛利(￥)
                  <el-tooltip content="毛利 = 出厂价 - BOM成本 - 制造费用 - 人工费用，反映项目盈利能力" placement="top">
                    <el-icon style="margin-left:4px;cursor:help;color:#909399"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </template>
                <el-input :model-value="grossMarginText" disabled size="small" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="年销量预测(首年)(台)" label-width="140px" size="small">
                <el-input-number v-model="projectForm.annual_sales_forecast" :min="0" :step="1000" size="small" controls-position="right" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="产品生命周期" label-width="120px" size="small">
                <el-input v-model="projectForm.product_lifecycle" size="small" placeholder="如: 5年" />
              </el-form-item>
            </el-col>
          </el-row>

          <!-- 三、模具/工装费用初步核算 -->
          <el-divider content-position="left">三、模具/工装费用初步核算</el-divider>
          <div style="margin-bottom:8px">
            <el-button size="small" @click="addMoldRow">+ 添加行</el-button>
          </div>
          <el-table :data="moldCostTable" border size="small" class="section-table">
            <el-table-column label="模具名称" min-width="160">
              <template #default="{ row }">
                <el-input v-model="row.name" size="small" placeholder="模具名称" />
              </template>
            </el-table-column>
            <el-table-column label="数量(副)" width="100">
              <template #default="{ row }">
                <el-input-number v-model="row.qty" :min="0" :step="1" size="small" controls-position="right" style="width:100%" />
              </template>
            </el-table-column>
            <el-table-column label="合计(W)" width="130">
              <template #default="{ row }">
                <el-input-number v-model="row.total" :min="0" :step="0.1" size="small" controls-position="right" style="width:100%" />
              </template>
            </el-table-column>
            <el-table-column label="备注" min-width="160">
              <template #default="{ row }">
                <el-input v-model="row.remark" size="small" placeholder="备注" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="70">
              <template #default="{ $index }">
                <el-button link type="danger" size="small" @click="removeMoldRow($index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="cost-summary">模具/工装合计: <strong>¥{{ moldCostTotal.toFixed(1) }} 万元</strong></div>

          <!-- 四、试制费用（按项目等级确定数量） -->
          <el-divider content-position="left">四、试制费用</el-divider>
          <div class="cost-summary" style="background:#f0f9eb;padding:10px 16px;border-radius:6px;margin-bottom:8px">
            试制数量: <strong>{{ trialQty }}台</strong>（按项目等级「{{ projectForm.dev_category || '未设置' }}」自动确定）
            <el-tooltip content="全新开发≥20台，派生≥10台，降本优化≥5台，高难度/高复杂度项目可适当上浮" placement="top">
              <el-icon style="margin-left:4px;cursor:help;color:#909399"><QuestionFilled /></el-icon>
            </el-tooltip>
            <span v-if="trialQty > 20" style="color:#e6a23c;margin-left:8px">⚠ 建议分批试制</span>
          </div>

          <!-- 五、试制样机费用 -->
          <el-divider content-position="left">五、试制样机费用</el-divider>
          <el-table :data="protoCostTable" border size="small" class="section-table">
            <el-table-column prop="stage" label="阶段" width="80" />
            <el-table-column label="数量(台)" width="100">
              <template #default="{ row }">
                <el-input-number v-model="row.qty" :min="0" :step="1" size="small" controls-position="right" style="width:100%" />
              </template>
            </el-table-column>
            <el-table-column label="单套费用(W)" width="130">
              <template #default="{ row }">
                <span>{{ row.unit_cost.toFixed(3) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="合计(W)" width="120">
              <template #default="{ row }">
                {{ (row.qty * row.unit_cost).toFixed(2) }}
              </template>
            </el-table-column>
          </el-table>
          <div class="cost-summary">样机合计: P0~P2 <strong>¥{{ protoDevTotal.toFixed(2) }} 万元</strong> | 客户样机: <strong>¥{{ clientSampleCost.toFixed(2) }} 万元</strong> | 总计: <strong>¥{{ protoCostTotal.toFixed(2) }} 万元</strong></div>

          <!-- 六、人工费用初步核算 -->
          <el-divider content-position="left">六、人工费用初步核算</el-divider>
          <el-table :data="laborCostTable" border size="small" class="section-table">
            <el-table-column prop="module" label="模块" width="100" />
            <el-table-column label="人数(人)" width="80">
              <template #default="{ row }">
                <el-input-number v-model="row.people_count" :min="0" :step="1" size="small" controls-position="right" style="width:100%" />
              </template>
            </el-table-column>
            <el-table-column label="月薪(W)" width="110">
              <template #default="{ row }">
                <el-input-number v-model="row.monthly_salary" :min="0" :step="0.1" size="small" controls-position="right" style="width:100%" />
              </template>
            </el-table-column>
            <el-table-column label="人月" width="130">
              <template #default="{ row }">
                <span class="linked-val">{{ (projectDurationMonths * (row.occupancy_rate || 100) / 100).toFixed(1) }}</span>
                <div style="font-size:11px;color:#909399">{{ projectDurationMonths }}月 × {{ row.occupancy_rate || 100 }}%</div>
              </template>
            </el-table-column>
            <el-table-column label="占用度%" width="100">
              <template #default="{ row }">
                <el-input-number v-model="row.occupancy_rate" :min="0" :max="100" :step="10" size="small" controls-position="right" style="width:100%" />
              </template>
            </el-table-column>
            <el-table-column label="费用(W)" width="120">
              <template #default="{ row }">
                {{ (row.people_count * row.monthly_salary * projectDurationMonths * (row.occupancy_rate || 100) / 100).toFixed(1) }}
              </template>
            </el-table-column>
          </el-table>
          <div class="cost-summary">人工费用合计: <strong>¥{{ laborCostTotal.toFixed(1) }} 万元</strong></div>

          <!-- 七、测试费用 -->
          <el-divider content-position="left">七、测试费用</el-divider>
          <el-table :data="testCostTable" border size="small" class="section-table">
            <el-table-column prop="stage" label="阶段" width="80" />
            <el-table-column label="天数(天)" width="100">
              <template #default="{ row }">
                <el-input-number v-model="row.days" :min="0" :step="1" size="small" controls-position="right" style="width:100%" />
              </template>
            </el-table-column>
            <el-table-column label="单价(W)" width="120">
              <template #default="{ row }">
                <span>{{ row.unit_price.toFixed(3) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="合计(W)" width="120">
              <template #default="{ row }">
                {{ (row.days * row.unit_price).toFixed(2) }}
              </template>
            </el-table-column>
          </el-table>
          <div class="cost-summary">测试费用合计: <strong>¥{{ testCostTotal.toFixed(2) }} 万元</strong></div>

          <!-- 八、认证费用（从Tab3安全合规自动生成） -->
          <el-divider content-position="left">
            八、认证费用（从Tab3安全合规自动生成）
            <el-tooltip content="认证费用从Tab3安全合规标准自动映射，在Tab3填写标准后此处自动生成费用项，可手动调整金额" placement="top">
              <el-icon style="margin-left:6px;cursor:help;color:#909399;font-size:14px"><QuestionFilled /></el-icon>
            </el-tooltip>
          </el-divider>
          <el-table v-if="certCostTable.length > 0" :data="certCostTable" border size="small" class="section-table">
            <el-table-column prop="cert_name" label="标准名" width="100" />
            <el-table-column prop="cert_body" label="认证机构" width="100" />
            <el-table-column label="费用(W)" width="130">
              <template #default="{ row }">
                <el-input-number v-model="row.cost_wan" :min="0" :step="0.1" size="small" controls-position="right" style="width:100%" />
              </template>
            </el-table-column>
            <el-table-column prop="remark" label="备注" min-width="160">
              <template #default="{ row }">
                <el-input v-model="row.remark" size="small" placeholder="备注" />
              </template>
            </el-table-column>
          </el-table>
          <div v-else class="cost-summary" style="color:#909399">暂无认证费用（请在Tab3填写安全合规标准后自动生成）</div>
          <div v-if="certCostTable.length > 0" class="cost-summary">认证费用合计: <strong>¥{{ certCostTotal.toFixed(1) }} 万元</strong></div>

          <!-- 九、间接成本 -->
          <el-divider content-position="left">九、间接成本</el-divider>
          <div class="cost-summary" style="background:#f5f7fa;padding:10px 16px;border-radius:6px">
            间接成本（管理/场地/水电等）: <strong>¥{{ indirectCost.toFixed(0) }} 元</strong>
            <span style="font-size:12px;color:#909399;margin-left:8px">（管理员配置，不可修改）</span>
          </div>
        </el-tab-pane>

        <!-- ═══════════ Tab 5: 团队与职责 ═══════════ -->
        <el-tab-pane name="team">
          <template #label>
            <span>
              <span v-if="tabStatus.team.valid">✅</span>
              <span v-else>❌</span>
              👥 团队与职责
            </span>
          </template>
          <div class="team-section">
            <!-- 项目类型选择（与Tab1 dev_category同步） -->
            <div class="team-toolbar">
              <el-form-item label="项目类型" label-width="80px" size="small" style="margin-bottom:0">
                <el-select v-model="selectedProjectType" placeholder="选择项目类型加载角色模板" clearable @change="onProjectTypeChange" style="width:180px">
                  <el-option label="全新开发" value="全新开发" />
                  <el-option label="派生" value="派生" />
                  <el-option label="降本优化" value="降本优化" />
                </el-select>
              </el-form-item>
              <el-button type="primary" size="small" @click="addTeamRow">添加成员</el-button>
              <span class="team-hint">选择项目类型自动加载预设角色模板</span>
            </div>

            <!-- 团队摘要面板 -->
            <div class="team-summary" v-if="teamTable.length > 0">
              <el-tag size="small" type="info">总角色: {{ teamSummary.totalRoles }}</el-tag>
              <el-tag size="small" type="info">总人数: {{ teamSummary.totalSlots }}</el-tag>
              <el-tag size="small" :type="teamSummary.unfilled === 0 ? 'success' : 'warning'">已分配: {{ teamSummary.filled }}</el-tag>
              <el-tag size="small" :type="teamSummary.unfilled > 0 ? 'danger' : 'success'">未分配: {{ teamSummary.unfilled }}</el-tag>
              <span class="team-summary-roles">
                <span v-for="sr in teamSummary.roleSummaries" :key="sr.role" class="summary-role-item">
                  {{ sr.role }} {{ sr.headcount }}
                  <span v-if="sr.filled === sr.headcount">✅</span>
                  <span v-else>⚠{{ sr.filled }}/{{ sr.headcount }}</span>
                </span>
              </span>
            </div>

            <el-table :data="teamTable" border size="small" class="section-table" row-key="seq">
              <!-- 序号 -->
              <el-table-column label="序号" width="55" align="center">
                <template #default="{ $index }">{{ $index + 1 }}</template>
              </el-table-column>
              <!-- 角色 -->
              <el-table-column width="140">
                <template #header>
                  角色
                  <el-tooltip content="选择项目类型后自动加载预设角色模板，可自行调整人数和分配人员。14种标准角色覆盖研发全流程" placement="top">
                    <el-icon style="margin-left:4px;cursor:help;color:#909399;font-size:13px"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </template>
                <template #default="{ row, $index }">
                  <el-select v-model="row.role" size="small" placeholder="选择角色" @change="onTeamRoleChange($index)" style="width:100%">
                    <el-option v-for="r in teamRoles" :key="r.value" :label="r.label" :value="r.value" />
                  </el-select>
                </template>
              </el-table-column>
              <!-- 人数 -->
              <el-table-column label="人数" width="65" align="center">
                <template #default="{ row, $index }">
                  <el-input-number v-model="row.headcount" :min="1" :max="10" size="small" controls-position="right" @change="onHeadcountChange($index)" style="width:60px" />
                </template>
              </el-table-column>
              <!-- 姓名（支持槽位展开） -->
              <el-table-column label="姓名" min-width="200">
                <template #default="{ row, $index }">
                  <!-- headcount=1: 直接显示 -->
                  <template v-if="row.headcount <= 1">
                    <el-select v-model="row.user_id" size="small" placeholder="选择人员" filterable @change="onTeamUserChange($index, 0)" style="width:100%">
                      <el-option
                        v-for="u in getUsersByRole(row.role)"
                        :key="u.id"
                        :label="getUserOptionLabel(u)"
                        :value="u.id"
                      >
                        <div class="user-option">
                          <span>{{ u.full_name || u.username }}</span>
                          <span v-if="getWorkloadBadge(u.id)" class="workload-badge" :style="{color: getWorkloadBadge(u.id)?.color}">
                            {{ getWorkloadBadge(u.id)?.text }}
                          </span>
                        </div>
                      </el-option>
                    </el-select>
                  </template>
                  <!-- headcount>1: 弹出槽位编辑 -->
                  <template v-else>
                    <el-popover placement="bottom" :width="320" trigger="click">
                      <template #reference>
                        <el-tag
                          :type="getSlotFillStatus(row) === 'full' ? 'success' : getSlotFillStatus(row) === 'partial' ? 'warning' : 'info'"
                          style="cursor:pointer"
                        >
                          {{ getSlotSummary(row) }}
                        </el-tag>
                      </template>
                      <div class="slot-editor">
                        <div v-for="(slot, si) in row.slots" :key="slot.slot_id" class="slot-row">
                          <span class="slot-label">槽{{ slot.slot_id }}</span>
                          <el-select v-model="slot.user_id" size="small" placeholder="选择人员" filterable @change="onSlotUserChange($index, si)" style="width:180px">
                            <el-option
                              v-for="u in getUsersByRole(row.role)"
                              :key="u.id"
                              :label="getUserOptionLabel(u)"
                              :value="u.id"
                            >
                              <div class="user-option">
                                <span>{{ u.full_name || u.username }}</span>
                                <span v-if="getWorkloadBadge(u.id)" class="workload-badge" :style="{color: getWorkloadBadge(u.id)?.color}">
                                  {{ getWorkloadBadge(u.id)?.text }}
                                </span>
                              </div>
                            </el-option>
                          </el-select>
                          <span v-if="slot.department" class="slot-dept">{{ slot.department }}</span>
                        </div>
                      </div>
                    </el-popover>
                  </template>
                </template>
              </el-table-column>
              <!-- 部门 -->
              <el-table-column label="部门" width="120">
                <template #default="{ row }">
                  <el-tooltip
                    v-if="row._departmentFailed && !row.department"
                    content="该用户未设置部门信息，请手动填写"
                    placement="top"
                    :disabled="!row._departmentFailed"
                  >
                    <el-input v-model="row.department" size="small" :disabled="!row._departmentFailed && !row._departmentManual" placeholder="自动填充" />
                  </el-tooltip>
                  <el-input v-else v-model="row.department" size="small" :disabled="!row._departmentManual" placeholder="自动填充" />
                </template>
              </el-table-column>
              <!-- 上级（汇报关系） -->
              <el-table-column label="上级" width="140">
                <template #default="{ row, $index }">
                  <el-select v-model="row.superior_id" size="small" placeholder="选择上级" clearable filterable style="width:100%">
                    <el-option
                      v-for="s in getSuperiorOptions($index)"
                      :key="s.id"
                      :label="s.label"
                      :value="s.id"
                    />
                  </el-select>
                </template>
              </el-table-column>
              <!-- 核心职责 -->
              <el-table-column label="核心职责" min-width="180">
                <template #default="{ row }">
                  <el-input v-model="row.responsibility" size="small" placeholder="核心职责描述（可从模板自动填充）" />
                </template>
              </el-table-column>
              <!-- 操作 -->
              <el-table-column label="操作" width="70">
                <template #default="{ $index }">
                  <el-button link type="danger" size="small" @click="removeTeamRow($index)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>

      <!-- 抽屉底部按钮 -->
      <template #footer>
        <div class="drawer-footer">
          <el-button @click="saveDraft" :loading="savingDraft">💾 保存草稿</el-button>
          <el-button type="primary" @click="submitProposal" :loading="submitting">✅ 提交立项</el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Link, Edit, Delete, QuestionFilled } from '@element-plus/icons-vue'
import api from '../../api'
import CompetitorBench from './CompetitorBench.vue'

// ═══════════════════════════════════════════════
// 类型定义
// ═══════════════════════════════════════════════

interface KbOption { id: number; category: string; code: string; name: string }
interface PlanningItem {
  id: number; name: string; year: string; description: string
  doc_ref: string; project_count: number; projects?: ProjectSummary[]
}
interface ProjectSummary { id: number; name: string; status: string; approval_status?: string }
interface Product { id: number; code: string; name: string; status: string; capacity?: string }
interface ProjectItem {
  id: number; name: string; status: string; project_class: string
  progress: number; budget?: number; market_policy?: string
  scene?: string; linked_product?: string; target_end_date?: string
  background_basis?: string; product_type?: string; target_market?: string
  refrigerant?: string; main_capacity?: string; capacity_range?: string
  voltage_freq?: string; series_name?: string; energy_rating?: string
  ip_ownership?: string; project_duration?: string
  dev_category?: string; project_origin?: string
  start_date?: string; required_date?: string; sample_qty?: number
  annual_planning_ref?: string; annual_planning_id?: number | null
  market_demand_overview?: string; competitor_analysis?: string; customer_special_req?: string
  climate_zone?: string; is_draft?: boolean
  has_outsourcing?: boolean
  customer_name?: string; cert_requirements?: string; energy_efficiency_req?: string
  target_price?: string; customer_requirements?: string; other_requirements?: string
  program_id?: number | null; leader_id?: number | null
  overall_goal?: string; background_basis_raw?: string; tech_goal?: string
  cost_goal?: string; sales_goal?: string; cert_goal?: string
  schedule_goal?: string; patent_goal?: string; other_goals?: string
  deliverables?: string; fob_price?: number; bom_cost_target?: number
  annual_sales_forecast?: number; product_lifecycle?: string
  dev_cost_items?: string; mold_costs?: string; prototype_costs_detail?: string
  test_costs?: string; labor_costs?: string; cert_costs?: string
  core_performance?: string; safety_compliance?: string
  material_components?: string
  accessory_config?: string; feature_config?: string
  team_members?: string
  approval_status?: string  // 审批状态: pending/approved/rejected
  created_at?: string
  updated_at?: string
}
interface CustomerReqRow { category: string; description: string; source: string; tech_impact: string; market_impact: string }
interface CorePerfRow { param_name: string; baseline: string; target_value: string; aux_competitor: string; tcl_competitor: string; source: string }
interface MaterialComponentRow { type: string; name: string; spec: string; qty: number; unit: string; usage: string; supplier: string; delivery_cycle: string; unit_price: number; candidate_vendors: string; remark: string }
interface SafetyComplianceRow { standard: string; applicable_market: string; key_requirement: string; verification_method: string; involved_parts: string; cert_cycle: string; remark: string }
interface ConfigRow { name: string; selection: string; _original?: string }
interface DevCostRow { item: string; budget: number; remark: string; linked: boolean }
interface MoldCostRow { name: string; qty: number; total: number; remark: string }
interface CertCostRow { cert_name: string; cert_body: string; cost_wan: number; remark: string }
interface ProtoCostRow { stage: string; qty: number; unit_cost: number }
interface LaborCostRow { module: string; people_count: number; monthly_salary: number; months: number; occupancy_rate: number }
interface TestCostRow { stage: string; days: number; unit_price: number }
interface TeamSlot {
  slot_id: number       // 1-based index within a row
  user_id: number | null
  full_name: string
  department: string
}
interface TeamMemberRow {
  role: string
  headcount: number     // 新增：该角色需要的人数
  slots: TeamSlot[]     // 新增：人员槽位
  user_id: number | null  // headcount=1时快捷字段
  full_name: string
  department: string
  responsibility: string
  superior_id: number | null  // 新增：上级汇报对象 user_id
  seq: number           // 新增：排序
  _departmentManual?: boolean  // 部门是否手动填写
  _departmentFailed?: boolean  // 部门自动填充失败
}
interface TeamRole { label: string; value: string; sys_role: string }
interface UserInfo { id: number; username: string; full_name: string; department: string; position: string; role: string; job_title?: string }
interface RoleMapping { project_role: string; sys_roles: string[] }
interface UserWorkload { user_id: number; project_count: number; workload_pct: number }
interface TeamRoleTemplateItem { role_name: string; headcount: number; responsibility_default: string; seq: number }

// ═══════════════════════════════════════════════
// 计算属性 (必须在所有响应式数据定义之前？不，必须在之后。但按规范，computed可在任意位置)
// ═══════════════════════════════════════════════

// 当前日期
const currentDate = computed(() => {
  const d = new Date()
  const weekDays = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${weekDays[d.getDay()]}`
})

// ═══════════════════════════════════════════════
// 响应式数据
// ═══════════════════════════════════════════════

// 年度规划
const annualPlanningRef = ref('')
const planningItems = ref<PlanningItem[]>([])
const selectedPlanId = ref<number | null>(null)
const filteredProjects = ref<ProjectSummary[]>([])
const showPlanDialog = ref(false)
const savingPlan = ref(false)
const planForm = reactive({ name: '', year: '', description: '', doc_ref: '' })
const editingPlanId = ref<number | null>(null)

// 产品/项目
const products = ref<Product[]>([])
const myProjects = ref<ProjectItem[]>([])
const myProposals = ref<ProjectItem[]>([])
const proposalFilter = ref('all')

// 看板统计
const stats = computed(() => {
  const items = myProjects.value
  const running = items.filter(p => p.status === 'running').length
  const completed = items.filter(p => p.status === 'completed').length
  const overdue = items.filter(p => p.status === 'overdue').length
  return { running, completed, overdue }
})

// 提案统计与过滤
const proposalCounts = computed(() => {
  const items = myProposals.value
  return {
    all: items.length,
    draft: items.filter(p => p.is_draft).length,
    submitted: items.filter(p => !p.is_draft).length,
  }
})

const filteredProposals = computed(() => {
  const items = myProposals.value
  if (proposalFilter.value === 'draft') return items.filter(p => p.is_draft)
  if (proposalFilter.value === 'submitted') return items.filter(p => !p.is_draft)
  return items
})

// 展开的项目ID
const expandedProjectId = ref<number | null>(null)

// 抽屉
const drawerVisible = ref(false)
const activeTab = ref('overview_market')
const draftId = ref<number | null>(null)
const savingDraft = ref(false)
const submitting = ref(false)

// Tab 校验状态
const tabStatus = reactive<Record<string, { valid: boolean; errors: string[] }>>({
  overview_market: { valid: false, errors: [] },
  technical: { valid: false, errors: [] },
  cost: { valid: false, errors: [] },
  team: { valid: false, errors: [] },
})

// 项目表单 - budget和sample_qty初始值为undefined
const projectForm = reactive<Record<string, any>>({
  name: '',
  program_id: null as number | null,
  leader_id: null as number | null,
  product_type: '', target_market: '', climate_zone: '', refrigerant: '',
  customer_name: '', capacity_range: '', voltage_freq: '',
  series_name: '', energy_rating: '',
  start_date: null, target_end_date: null,
  ip_ownership: '', project_duration: '',
  dev_category: '', project_origin: '', other_requirements: '',
  annual_planning_id: null as number | null,
  background_basis: '', overall_goal: '', tech_goal: '', cost_goal: '',
  sales_goal: '', cert_goal: '', schedule_goal: '', patent_goal: '', other_goals: '',
  sample_qty: undefined as number | undefined,
  sample_required_date: null as string | null,
  deliverables: '',
  main_capacity: '', target_price: '', energy_efficiency_req: '', cert_requirements: '',
  market_demand_overview: '', competitor_analysis: '', customer_special_req: '',
  fob_price: undefined as number | undefined,
  bom_cost_target: undefined as number | undefined,
  annual_sales_forecast: undefined as number | undefined,
  product_lifecycle: '',
  annual_planning_ref: '',
  has_outsourcing: false,
})

// 知识库下拉选项
const kbOptions = reactive<Record<string, KbOption[]>>({
  market: [], product_type: [], capacity: [], voltage: [],
  ip_ownership: [], main_capacity: [], cert: [],
  series: [], energy_rating: [],
})

// 项目群选项
const programOptions = ref<{ id: number; name: string; code: string }[]>([])

// 团队
const teamRoles = ref<TeamRole[]>([])
const allTeamUsers = ref<UserInfo[]>([])
const roleMappings = ref<RoleMapping[]>([])          // 新增：项目角色→系统岗位多映射
const userWorkloads = ref<UserWorkload[]>([])         // 新增：人员负载数据
const selectedProjectType = ref('')                   // 新增：选中的项目类型（与Tab1 dev_category同步）


// 汇率
const exchangeRate = ref(7.20)

// ═══════════════════════════════════════════════
// Tab 2 表格: 客户关键需求
// ═══════════════════════════════════════════════
const customerReqTable = reactive<CustomerReqRow[]>([
  { category: '能效', description: '需达到当地最高能效等级', source: '市场调研', tech_impact: '高', market_impact: '高' },
  { category: '噪音', description: '室内机噪音<35dB(A)', source: '客户反馈', tech_impact: '中', market_impact: '中' },
  { category: '智能控制', description: '支持WiFi远程控制', source: '竞品分析', tech_impact: '中', market_impact: '高' },
  { category: '安装便利', description: '快速安装结构设计', source: '客户需求', tech_impact: '低', market_impact: '中' },
])

// ═══════════════════════════════════════════════
// Tab 3 表格: 核心性能参数 (13行)
// ═══════════════════════════════════════════════
const corePerfTable = reactive<CorePerfRow[]>([
  { param_name: '制冷量(W)', baseline: '', target_value: '', aux_competitor: '', tcl_competitor: '', source: 'auto' },
  { param_name: 'CSPF(W/W)', baseline: '', target_value: '', aux_competitor: '', tcl_competitor: '', source: 'market_config' },
  { param_name: '能效等级', baseline: '', target_value: '', aux_competitor: '', tcl_competitor: '', source: 'market_config' },
  { param_name: '容差(%)', baseline: '', target_value: '', aux_competitor: '', tcl_competitor: '', source: 'market_config' },
  { param_name: '出风量(m³/h)', baseline: '', target_value: '', aux_competitor: '', tcl_competitor: '', source: 'manual' },
  { param_name: '噪音dB(A)(内/外)', baseline: '', target_value: '', aux_competitor: '', tcl_competitor: '', source: 'manual' },
  { param_name: '尺寸(mm)(内/外)', baseline: '', target_value: '', aux_competitor: '', tcl_competitor: '', source: 'manual' },
  { param_name: '电压/频率', baseline: '', target_value: '', aux_competitor: '', tcl_competitor: '', source: 'auto' },
  { param_name: '制冷剂', baseline: '', target_value: '', aux_competitor: '', tcl_competitor: '', source: 'auto' },
  { param_name: '充注量(g)', baseline: '', target_value: '', aux_competitor: '', tcl_competitor: '', source: 'manual' },
  { param_name: '装柜量(20GP)', baseline: '', target_value: '', aux_competitor: '', tcl_competitor: '', source: 'manual' },
  { param_name: '制热量(W)', baseline: '', target_value: '', aux_competitor: '', tcl_competitor: '', source: 'manual' },
  { param_name: 'HSPF(W/W)', baseline: '', target_value: '', aux_competitor: '', tcl_competitor: '', source: 'market_config' },
])

// Tab 3: 技术步骤导航
const techStep = ref(0)

// 竞品快速参考
const competitorRefActive = ref<string[]>([])
const quickRefCompetitors = ref<any[]>([])

// Tab 3 表格: 物料与部件清单
const materialComponentTable = reactive<MaterialComponentRow[]>([
  { type: '物料', name: '', spec: '', qty: 1, unit: '个', usage: '', supplier: '', delivery_cycle: '', unit_price: 0, candidate_vendors: '', remark: '' },
])

// Tab 3 表格: 安全与合规要求 (3行)
const safetyComplianceTable = reactive<SafetyComplianceRow[]>([
  { standard: 'IEC 60335-2-40', applicable_market: '全球', key_requirement: '电气安全', verification_method: '型式试验', involved_parts: '电控组件', cert_cycle: '3个月', remark: '' },
  { standard: 'CE EMC Directive', applicable_market: '欧盟', key_requirement: '电磁兼容', verification_method: 'EMC测试', involved_parts: 'PCB/电机', cert_cycle: '2个月', remark: '' },
  { standard: 'SASO 2663', applicable_market: '沙特', key_requirement: '能效+安全', verification_method: '第三方测试', involved_parts: '整机', cert_cycle: '4个月', remark: '' },
])

// Tab1 认证要求自动拼装（从安全合规表格提取标准名）
const certRequirementsText = computed(() => {
  return safetyComplianceTable.map(s => s.standard).join('、') || ''
})

// Tab 3 表格: 配件选配 (6行)
const accessoryConfigTable = reactive<ConfigRow[]>([
  { name: '遥控器', selection: '标配红外遥控器' },
  { name: '安装支架', selection: '标配壁挂支架' },
  { name: '排水管', selection: '标配1.5m' },
  { name: '铜管组件', selection: '选配3m/5m' },
  { name: 'WiFi模块', selection: '选配' },
  { name: '过滤网', selection: '标配可清洗滤网' },
])

// Tab 3 表格: 功能选配 (3行)
const featureConfigTable = reactive<ConfigRow[]>([
  { name: '自清洁', selection: '标配' },
  { name: '防直吹', selection: '标配' },
  { name: '静音模式', selection: '标配' },
])

// ═══════════════════════════════════════════════
// Tab 4 表格: 项目开发费用 (8行)
// ═══════════════════════════════════════════════
const devCostTable = reactive<DevCostRow[]>([
  { item: '工装及模具费用', budget: 0, remark: '', linked: true },
  { item: '认证费用', budget: 0, remark: '', linked: true },
  { item: '研发人工费用', budget: 0, remark: '', linked: true },
  { item: '样机试制费用', budget: 0, remark: '', linked: true },
  { item: '测试费用耗材', budget: 0, remark: '', linked: true },
  { item: '委外开发费用', budget: 0, remark: '无', linked: false },
  { item: '客户样机费用', budget: 0, remark: '', linked: true },
  { item: '开发费用合计', budget: 0, remark: '', linked: true },
])

// Tab 4 表格: 模具/工装费用 (可增删)
const moldCostTable = reactive<MoldCostRow[]>([
  { name: '内机钣金模具', qty: 0, total: 0, remark: '' },
  { name: '内机注塑模具', qty: 0, total: 0, remark: '' },
  { name: '外机钣金模具', qty: 0, total: 0, remark: '' },
  { name: '外机注塑模具', qty: 0, total: 0, remark: '' },
  { name: '翅片模具', qty: 0, total: 0, remark: '' },
  { name: '工装夹具', qty: 0, total: 0, remark: '' },
])

// Tab 4 表格: 试制样机费用 (5行)
const protoCostTable = reactive<ProtoCostRow[]>([
  { stage: 'P0', qty: 5, unit_cost: 0 },
  { stage: 'P1-1', qty: 10, unit_cost: 0 },
  { stage: 'P1-2', qty: 10, unit_cost: 0 },
  { stage: 'P2', qty: 20, unit_cost: 0 },
  { stage: '客户样机', qty: 5, unit_cost: 0 },
])

// Tab 4 表格: 人工费用 (6行)
const laborCostTable = reactive<LaborCostRow[]>([
  { module: '结构', people_count: 3, monthly_salary: 1.5, months: 8, occupancy_rate: 100 },
  { module: '系统', people_count: 2, monthly_salary: 1.5, months: 8, occupancy_rate: 100 },
  { module: '电控', people_count: 2, monthly_salary: 1.8, months: 8, occupancy_rate: 100 },
  { module: '电气', people_count: 2, monthly_salary: 1.5, months: 6, occupancy_rate: 50 },
  { module: '工艺', people_count: 1, monthly_salary: 1.2, months: 6, occupancy_rate: 50 },
  { module: '质量', people_count: 1, monthly_salary: 1.2, months: 6, occupancy_rate: 50 },
])

// Tab 4 表格: 测试费用 (4行)
const testCostTable = reactive<TestCostRow[]>([
  { stage: 'P0', days: 10, unit_price: 0.11 },
  { stage: 'P1-1', days: 20, unit_price: 0.11 },
  { stage: 'P1-2', days: 15, unit_price: 0.11 },
  { stage: 'P2', days: 30, unit_price: 0.11 },
])

// Tab 4 表格: 认证费用 (从Tab3安全合规自动生成)
const certCostTable = reactive<CertCostRow[]>([])

// ═══════════════════════════════════════════════
// Tab 5 表格: 团队人员（动态从角色模板加载，初始为空）
// ═══════════════════════════════════════════════
const teamTable = reactive<TeamMemberRow[]>([])

function createEmptySlot(slotId: number): TeamSlot {
  return { slot_id: slotId, user_id: null, full_name: '', department: '' }
}

function createTeamRow(role: string, headcount: number, responsibility: string, seq: number): TeamMemberRow {
  const slots: TeamSlot[] = []
  for (let i = 1; i <= headcount; i++) {
    slots.push(createEmptySlot(i))
  }
  return {
    role,
    headcount,
    slots,
    user_id: headcount === 1 ? null : null,
    full_name: '',
    department: '',
    responsibility,
    superior_id: null,
    seq,
    _departmentManual: false,
    _departmentFailed: false,
  }
}

// ═══════════════════════════════════════════════
// 计算属性
// ═══════════════════════════════════════════════

// 系统配置（从API加载，admin可修改）
const systemConfig = ref<Record<string, any>>({})

const protoUnitCostFromConfig = computed(() => {
  const raw = systemConfig.value.capacity_unit_cost_map
  if (raw) {
    try { return JSON.parse(raw) as Record<string, { btu: number; cost: number }> } catch {}
  }
  // fallback
  return {
    '07K': { btu: 7000, cost: 0.075 },
    '09K': { btu: 9000, cost: 0.095 },
    '12K': { btu: 12000, cost: 0.105 },
    '18K': { btu: 18000, cost: 0.142 },
    '22K': { btu: 22000, cost: 0.178 },
    '24K': { btu: 24000, cost: 0.178 },
  }
})

// 样机单套费用 - 按冷量段查表 (万元)
const prototypeUnitCost = computed(() => {
  const cr = projectForm.capacity_range
  if (!cr) return 0
  const map = protoUnitCostFromConfig.value
  const upper = cr.toUpperCase()
  // Try to match by key
  for (const [key, val] of Object.entries(map)) {
    if (upper.includes(key.toUpperCase())) return Number((val as any).cost || val)
  }
  return 0.1 // default
})

// 项目周期月数 (用于人月计算)
const projectDurationMonths = computed(() => {
  const s = projectForm.start_date
  const e = projectForm.target_end_date
  if (!s || !e) return 0
  try {
    const start = new Date(s)
    const end = new Date(e)
    if (isNaN(start.getTime()) || isNaN(end.getTime())) return 0
    const diffMs = end.getTime() - start.getTime()
    if (diffMs < 0) return 0
    const days = Math.ceil(diffMs / (1000 * 60 * 60 * 24))
    return Math.floor(days / 30)
  } catch { return 0 }
})

// 试制数量 — 按项目等级查表
const trialQty = computed(() => {
  const dc = projectForm.dev_category
  if (!dc) return 5
  const raw = systemConfig.value.trial_qty_per_class
  const map: Record<string, number> = (() => {
    if (raw) { try { return JSON.parse(raw) } catch {} }
    return { 'T': 5, 'A': 3, 'B': 2, 'C': 1 }
  })()
  return map[dc] ?? map['C'] ?? 1
})

// 间接成本 — 管理员配置
const indirectCost = computed(() => {
  const raw = systemConfig.value.indirect_cost
  if (raw) {
    const n = Number(raw)
    if (!isNaN(n)) return n
  }
  return 5000
})

// 制造费用+人工 - 按冷量
const manufacturingCost = computed(() => {
  const cr = projectForm.capacity_range
  const thresholds: Array<{max_kw: number; cost: number}> = (() => {
    const raw = systemConfig.value.mfg_cost_threshold
    if (raw) { try { return JSON.parse(raw) } catch {} }
    return [{max_kw: 12, cost: 50}, {max_kw: 999, cost: 60}]
  })()
  if (!cr) return thresholds[0]?.cost || 50
  const upper = cr.toUpperCase()
  const kwMatch = upper.match(/(\d+)K/)
  if (!kwMatch) return thresholds[0]?.cost || 50
  const kw = parseInt(kwMatch[1])
  for (const t of thresholds) {
    if (kw <= t.max_kw) return t.cost
  }
  return thresholds[thresholds.length - 1]?.cost || 60
})

// 模具费用合计
const moldCostTotal = computed(() =>
  moldCostTable.reduce((sum, r) => sum + (r.total || 0), 0)
)

// 样机费用 (P0~P2, 不含客户样机)
const protoDevTotal = computed(() =>
  protoCostTable.filter(r => r.stage !== '客户样机').reduce((sum, r) => sum + (r.qty || 0) * (r.unit_cost || 0), 0)
)

// 客户样机费用
const clientSampleCost = computed(() => {
  const row = protoCostTable.find(r => r.stage === '客户样机')
  return row ? (row.qty || 0) * (row.unit_cost || 0) : 0
})

// 样机总费用
const protoCostTotal = computed(() =>
  protoCostTable.reduce((sum, r) => sum + (r.qty || 0) * (r.unit_cost || 0), 0)
)

// 人工费用合计 (使用项目周期月数)
const laborCostTotal = computed(() =>
  laborCostTable.reduce((sum, r) => sum + (r.people_count || 0) * (r.monthly_salary || 0) * projectDurationMonths.value * ((r.occupancy_rate || 100) / 100), 0)
)

// 测试费用合计
const testCostTotal = computed(() =>
  testCostTable.reduce((sum, r) => sum + (r.days || 0) * (r.unit_price || 0), 0)
)

// 认证费用合计
const certCostTotal = computed(() =>
  certCostTable.reduce((sum, r) => sum + (Number(r.cost_wan) || 0), 0)
)

// 说明自动生成
// 每行说明独立刷新
function refreshDevCostRemarks() {
  // [0] 工装及模具费用
  const moldModules = moldCostTable.filter(r => r.total > 0)
  if (moldModules.length > 0) {
    devCostTable[0].remark = '模具：' + moldModules.map(r => `${r.name}${r.qty}套${r.total.toFixed(1)}W`).join(' / ')
  } else {
    devCostTable[0].remark = ''
  }
  // [1] 认证费用
  const certCostVal = certCostTotal.value
  if (certCostVal > 0) {
    const certParts = certCostTable.map(r => `${r.cert_name} ${r.cost_wan}W`)
    devCostTable[1].remark = certParts.join(' + ')
  } else {
    devCostTable[1].remark = ''
  }
  // [2] 研发人工费用
  const laborRows = laborCostTable.filter(r => r.people_count > 0)
  if (laborRows.length > 0) {
    const totalPeople = laborRows.reduce((s, r) => s + r.people_count, 0)
    devCostTable[2].remark = `${totalPeople}人 ${laborCostTotal.value.toFixed(1)}W`
  } else {
    devCostTable[2].remark = ''
  }
  // [3] 样机试制费用（仅P0~P2）
  const devStages = protoCostTable.filter(r => r.stage !== '客户样机')
  const totalDevQty = devStages.reduce((s, r) => s + (r.qty || 0), 0)
  if (protoDevTotal.value > 0) {
    devCostTable[3].remark = `P0~P2 共${totalDevQty}套 ${protoDevTotal.value.toFixed(1)}W`
  } else {
    devCostTable[3].remark = ''
  }
  // [4] 测试费用耗材
  const testRows = testCostTable.filter(r => r.days > 0)
  if (testRows.length > 0) {
    const totalDays = testRows.reduce((s, r) => s + (r.days || 0), 0)
    devCostTable[4].remark = `${totalDays}天 ${testCostTotal.value.toFixed(1)}W`
  } else {
    devCostTable[4].remark = ''
  }
  // [5] 委外开发费用
  if (projectForm.has_outsourcing && devCostTable[5].budget > 0) {
    devCostTable[5].remark = `${devCostTable[5].budget.toFixed(1)}W`
  } else {
    devCostTable[5].remark = '无'
  }
  // [6] 客户样机费用
  const clientRow = protoCostTable.find(r => r.stage === '客户样机')
  if (clientRow && clientRow.qty > 0) {
    devCostTable[6].remark = `${clientRow.qty}套 ${clientSampleCost.value.toFixed(1)}W`
  } else {
    devCostTable[6].remark = ''
  }
  // [7] 开发费用合计 — 不使用说明
  devCostTable[7].remark = ''
}
const devCostGrandTotal = computed(() => {
  const sumFirst7 = devCostTable.slice(0, 7).reduce((s, r) => s + (Number(r.budget) || 0), 0)
  // 总预算 = 前7项 + 认证费用合计 + 间接成本
  return sumFirst7 + certCostTotal.value + indirectCost.value / 10000
})

// BOM成本占比
const bomCostRatioText = computed(() => {
  const fob = Number(projectForm.fob_price) || 0
  const bom = Number(projectForm.bom_cost_target) || 0
  const rate = Number(exchangeRate.value) || 7.2
  if (fob <= 0 || rate <= 0) return '-'
  const fobCny = fob * rate
  return ((bom / fobCny) * 100).toFixed(1) + '%'
})

// 毛利率
const grossMarginText = computed(() => {
  const fob = Number(projectForm.fob_price) || 0
  const bom = Number(projectForm.bom_cost_target) || 0
  const rate = Number(exchangeRate.value) || 7.2
  const mfg = manufacturingCost.value
  if (fob <= 0 || rate <= 0) return '-'
  const fobCny = fob * rate
  const totalCost = bom + mfg
  const gross = fobCny - totalCost
  return '¥' + gross.toFixed(0) + ' (' + (fobCny > 0 ? ((gross / fobCny) * 100).toFixed(1) : '0.0') + '%)'
})

// 系统配置中的产品类型简写映射
const productShortNames = computed(() => {
  const raw = systemConfig.value.product_short_names
  if (raw) {
    try { return JSON.parse(raw) as Record<string, string> } catch {}
  }
  return {} as Record<string, string>
})

// 自动生成项目名称: 出口{市场}{系列}款{冷量K}/{制冷剂}/{能效等级}{产品简写}项目开发
const autoProjectName = computed(() => {
  const f = projectForm
  const hasAny = f.target_market || f.series_name || f.capacity_range || f.refrigerant || f.energy_rating || f.product_type
  if (!hasAny) return '（自动生成：请填写相关字段）'

  // code→name 查找（KB下拉存的是code，显示需用name）
  const lookup = (cat: string, code: string) => {
    const opts = (kbOptions as any)[cat] as Array<{code:string;name:string}> | undefined
    const found = opts?.find(o => o.code === code)
    return found ? found.name : code
  }

  const parts: string[] = ['出口']

  // 市场: code "VN" → name "越南"
  if (f.target_market) parts.push(lookup('market', f.target_market))

  // 系列: code "J" → name "J系列" → 去掉"系列" → "J款"
  if (f.series_name) {
    const seriesLabel = lookup('series', f.series_name).replace(/系列$/, '')
    parts.push(seriesLabel + '款')
  }

  // 冷量: code "7K" → name "7K" 直接使用
  const cr = (f.capacity_range || '').trim()
  let capK = lookup('capacity', f.capacity_range) || cr
  // 如果没有匹配到KB，尝试解析数字
  if (capK === cr) {
    const m = cr.match(/(\d+)/)
    if (m) capK = m[1] + 'K'
  }
  if (capK) parts.push(capK)

  // 制冷剂: KB存的就是"R32"这种，直接用
  if (f.refrigerant) parts.push('/' + f.refrigerant)

  // 能效等级: code "5star" → name "5星"
  if (f.energy_rating) parts.push('/' + lookup('energy_rating', f.energy_rating))

  // 产品类型: code "WALL" → name "分体式壁挂机" → shortNames["分体式壁挂机"] → "挂机"
  if (f.product_type) {
    const fullName = lookup('product_type', f.product_type)
    const shorts = productShortNames.value
    const short = shorts[fullName] || fullName
    parts.push(short)
  }

  return parts.join('') + '项目开发'
})

// 自动计算项目周期
const autoProjectDuration = computed(() => {
  const s = projectForm.start_date
  const e = projectForm.target_end_date
  if (!s || !e) return '请选择起止日期'
  try {
    const start = new Date(s)
    const end = new Date(e)
    if (isNaN(start.getTime()) || isNaN(end.getTime())) return '日期格式无效'
    const diffMs = end.getTime() - start.getTime()
    if (diffMs < 0) return '结束日期早于开始日期'
    const days = Math.ceil(diffMs / (1000 * 60 * 60 * 24))
    const months = Math.floor(days / 30)
    const remainDays = days % 30
    if (months > 0) return `${months}个月${remainDays > 0 ? remainDays + '天' : ''}（${days}天）`
    return `${days}天`
  } catch {
    return '计算异常'
  }
})

// ═══════════════════════════════════════════════
// Watch 联动 (必须在onMounted之前)
// ═══════════════════════════════════════════════

// capacity_range → main_capacity 同步
watch(() => projectForm.capacity_range, (val) => {
  if (val && !projectForm.main_capacity) {
    projectForm.main_capacity = val
  }
})

// autoProjectName → projectForm.name
watch(autoProjectName, (val) => {
  projectForm.name = val
}, { immediate: true })

// autoProjectDuration → projectForm.project_duration
watch(autoProjectDuration, (val) => {
  projectForm.project_duration = val
}, { immediate: true })

// capacity_range → 核心性能表制冷量行 (自动计算 BTU→W)
watch(() => projectForm.capacity_range, (val) => {
  if (corePerfTable.length > 0) {
    corePerfTable[0].target_value = val || ''
    // 自动计算制冷量基准值: 解析BTU ÷ 3.4128 取整
    if (val && corePerfTable[0].source === 'auto') {
      const btuMatch = (val || '').match(/(\d+)\s*K?(?:\s*BTU)?/i)
      if (btuMatch) {
        let btu = parseInt(btuMatch[1])
        // "07K"/"12K" format: K means ×1000
        if (/(\d+)\s*K/i.test(val)) btu *= 1000
        const watts = Math.round(btu / 3.4128)
        corePerfTable[0].baseline = watts + 'W'
      } else {
        corePerfTable[0].baseline = ''
      }
    }
  }
})

// refrigerant → 核心性能表制冷剂行
watch(() => projectForm.refrigerant, (val) => {
  if (corePerfTable.length > 8) {
    corePerfTable[8].target_value = val || ''
    if (corePerfTable[8].source === 'auto') {
      corePerfTable[8].baseline = val || ''
    }
  }
})

// voltage_freq → 核心性能表电压行 (同步基准值)
watch(() => projectForm.voltage_freq, (val) => {
  if (corePerfTable.length > 7) {
    corePerfTable[7].target_value = val || ''
    if (corePerfTable[7].source === 'auto') {
      corePerfTable[7].baseline = val || ''
    }
  }
})

// 认证费用联动 (certCostTotal → devCostTable[1])
watch(certCostTotal, (val) => {
  if (devCostTable.length > 1 && devCostTable[1].linked) {
    devCostTable[1].budget = val
  }
})

// safetyComplianceTable 变化 → 自动生成认证费用表
watch(
  () => safetyComplianceTable.map(r => r.standard),
  (standards) => {
    if (standards.length === 0) {
      certCostTable.length = 0
      return
    }
    const costMap: Record<string, number> = (() => {
      const raw = systemConfig.value.cert_cost
      if (raw) { try { return JSON.parse(raw) } catch {} }
      return { 'UL': 20, 'CE': 3, 'CB': 4, 'CCC': 5, 'TUV': 15, 'ETL': 12, 'CSA': 10, 'SAA': 6, 'PSE': 8, 'KC': 7, 'BSMI': 5, 'NOM': 4, 'INMETRO': 6, 'SASO': 5, 'ISO': 3, 'IEC': 3, 'EN': 3, 'default': 3 }
    })()
    const defaultCost = costMap['default'] || 3
    const seen = new Set<string>()
    const newRows: CertCostRow[] = []
    for (const std of standards) {
      // Extract cert body name (e.g., "IEC 60335-2-40" → "IEC", "CE EMC Directive" → "CE")
      const upper = std.toUpperCase()
      const certNames = upper.split(/[/,;，；、\s]+/).filter(t => /^[A-Z]{2,8}$/.test(t))
      for (const cn of certNames) {
        if (!seen.has(cn)) {
          seen.add(cn)
          const cost = costMap[cn] ?? defaultCost
          newRows.push({ cert_name: cn, cert_body: cn, cost_wan: cost, remark: '' })
        }
      }
    }
    // If no cert names extracted, use the whole standard as name
    if (newRows.length === 0 && standards.length > 0) {
      const first = standards[0].toUpperCase().split(/[/,;，；、\s]+/).filter(t => /^[A-Z]{2,8}$/.test(t))[0] || standards[0]
      if (!seen.has(first)) {
        seen.add(first)
        newRows.push({ cert_name: first, cert_body: first, cost_wan: defaultCost, remark: '' })
      }
    }
    certCostTable.length = 0
    newRows.forEach(r => certCostTable.push(r))
  },
  { deep: true }
)

// 样板单套费用联动 → 更新protoCostTable的unit_cost
watch(prototypeUnitCost, (val) => {
  protoCostTable.forEach(r => {
    if (r.stage !== '客户样机') {
      r.unit_cost = val
    }
  })
  // 客户样机的单套费用是P0~P2阶段的1.2倍
  const clientRow = protoCostTable.find(r => r.stage === '客户样机')
  if (clientRow) {
    clientRow.unit_cost = Math.round(val * 1.2 * 1000) / 1000
  }
}, { immediate: true })

// 联动行: 模具→devCostTable[0], 样机(P0~P2)→devCostTable[3], 测试→devCostTable[4]
watch(moldCostTotal, (val) => {
  if (devCostTable.length > 0 && devCostTable[0].linked) {
    devCostTable[0].budget = val
  }
})

watch(laborCostTotal, (val) => {
  if (devCostTable.length > 2 && devCostTable[2].linked) {
    devCostTable[2].budget = val
  }
})

watch(protoDevTotal, (val) => {
  if (devCostTable.length > 3 && devCostTable[3].linked) {
    devCostTable[3].budget = val
  }
})

watch(testCostTotal, (val) => {
  if (devCostTable.length > 4 && devCostTable[4].linked) {
    devCostTable[4].budget = val
  }
})

// 客户样机费用→devCostTable[6]
watch(clientSampleCost, (val) => {
  if (devCostTable.length > 6 && devCostTable[6].linked) {
    devCostTable[6].budget = val
  }
})

// 开发费用合计联动(第8行 = 前7之和) + 刷新每行说明
watch(devCostGrandTotal, (val) => {
  if (devCostTable.length > 7 && devCostTable[7].linked) {
    devCostTable[7].budget = val
  }
  refreshDevCostRemarks()
})

// 委外开发: has_outsourcing=false → budget=0
watch(() => projectForm.has_outsourcing, (val) => {
  if (!val && devCostTable.length > 5) {
    devCostTable[5].budget = 0
    devCostTable[5].remark = '无'
  }
})

// 目标市场变化 → 加载安全合规标准 + 配件/功能默认
watch(() => projectForm.target_market, (market) => {
  if (market) {
    fetchCertStandards(market)
    fetchAccessoryDefaults(market)
    fetchFeatureDefaults(market)
  }
})

// 目标市场或冷量段变化 → 加载核心性能参数
watch([() => projectForm.target_market, () => projectForm.capacity_range], ([market, capacity]) => {
  if (market && capacity) {
    fetchPerfDefaults(market, capacity)
  }
})

// 目标市场或冷量段变化 → 加载竞品快速参考数据
watch([() => projectForm.target_market, () => projectForm.capacity_range], async ([market, capacity]) => {
  if (market) {
    try {
      const res = await api.get('/pm/competitors/benchmark', { params: { market } })
      const comps = res.data?.competitors || []
      if (capacity) {
        quickRefCompetitors.value = comps.filter((c: any) => 
          (c.cooling_capacity || '').includes(capacity.replace('K',''))
        ).slice(0, 10)
      } else {
        quickRefCompetitors.value = comps.slice(0, 10)
      }
    } catch { quickRefCompetitors.value = [] }
  }
})

// Tab 切换时自动校验当前Tab
watch(activeTab, () => {
  validateCurrentTab()
})

// ⭐ 项目来源选"产品年度规划"时联动清空/显示年度规划选择器
watch(() => projectForm.project_origin, (val) => {
  if (val !== '产品年度规划') {
    projectForm.annual_planning_id = null
  }
})

// ⭐ 新增：dev_category → selectedProjectType 同步（Tab1↔Tab5）
watch(() => projectForm.dev_category, (val) => {
  if (val && val !== selectedProjectType.value) {
    selectedProjectType.value = val
    loadTeamRoleTemplate(val)
  }
})

// ⭐ 新增：项目负责人双向同步（Tab1↔Tab5）
// teamTable中role为'项目经理'或'项目负责人'的行的user_id → projectForm.leader_id
watch(
  () => {
    const leaderRow = teamTable.find(r => r.role === '项目经理' || r.role === '项目负责人')
    if (!leaderRow) return null
    if (leaderRow.headcount <= 1) return leaderRow.user_id
    return leaderRow.slots.length > 0 ? leaderRow.slots[0].user_id : null
  },
  (newLeaderId) => {
    if (newLeaderId != null && projectForm.leader_id !== newLeaderId) {
      projectForm.leader_id = newLeaderId
    }
  }
)

// projectForm.leader_id变化 → 同步回teamTable
watch(() => projectForm.leader_id, (newId) => {
  if (newId == null) return
  const leaderRow = teamTable.find(r => r.role === '项目经理' || r.role === '项目负责人')
  if (!leaderRow) return
  // Only sync if leader row user_id doesn't already match
  const currentLeaderId = leaderRow.headcount <= 1 ? leaderRow.user_id : (leaderRow.slots.length > 0 ? leaderRow.slots[0].user_id : null)
  if (currentLeaderId !== newId) {
    if (leaderRow.headcount <= 1) {
      leaderRow.user_id = newId
      // Trigger user change effects
      const user = allTeamUsers.value.find(u => u.id === newId)
      if (user) {
        leaderRow.full_name = user.full_name || user.username
        leaderRow.department = user.department || ''
      }
    } else if (leaderRow.slots.length > 0) {
      leaderRow.slots[0].user_id = newId
      const user = allTeamUsers.value.find(u => u.id === newId)
      if (user) {
        leaderRow.slots[0].full_name = user.full_name || user.username
        leaderRow.slots[0].department = user.department || ''
      }
    }
  }
})

// ═══════════════════════════════════════════════
// Tab 校验函数
// ═══════════════════════════════════════════════

function validateOverviewMarket(): void {
  const errs: string[] = []
  const f = projectForm
  if (!f.program_id) errs.push('所属项目群')
  if (!f.leader_id) errs.push('项目负责人')
  if (!f.product_type) errs.push('产品类型')
  if (!f.target_market) errs.push('目标市场')
  if (!f.capacity_range) errs.push('能力段')
  if (!f.refrigerant) errs.push('制冷剂')
  if (!f.voltage_freq) errs.push('电压频率')
  if (!f.start_date) errs.push('立项日期')
  if (!f.target_end_date) errs.push('计划完成日期')
  const hasCustomerReq = customerReqTable.some(row =>
    row.category || row.description || row.source || row.tech_impact || row.market_impact
  )
  if (!hasCustomerReq) errs.push('客户关键需求至少填写一行')
  tabStatus.overview_market.valid = errs.length === 0
  tabStatus.overview_market.errors = errs
}

function validateTechnical(): void {
  const errs: string[] = []
  const hasTargetValue = corePerfTable.some(row => row.target_value)
  if (!hasTargetValue) errs.push('核心性能参数至少一行填写目标值')
  if (safetyComplianceTable.length === 0) errs.push('安全合规标准未加载，请先选择目标市场')
  const hasMaterial = materialComponentTable.some(row => row.name || row.spec)
  if (!hasMaterial) errs.push('物料部件清单至少填写一行')
  tabStatus.technical.valid = errs.length === 0
  tabStatus.technical.errors = errs
}

function validateCost(): void {
  const errs: string[] = []
  const f = projectForm
  if (devCostGrandTotal.value <= 0) errs.push('开发费用合计必须大于0')
  if (f.fob_price === undefined || f.fob_price === null || Number(f.fob_price) <= 0) errs.push('目标出厂价FOB')
  if (f.bom_cost_target === undefined || f.bom_cost_target === null || Number(f.bom_cost_target) <= 0) errs.push('目标BOM成本')
  tabStatus.cost.valid = errs.length === 0
  tabStatus.cost.errors = errs
}

function validateTeam(): void {
  const errs: string[] = []
  const hasUser = teamTable.some(row => {
    if (row.headcount <= 1) return row.user_id != null
    return row.slots.some(s => s.user_id != null)
  })
  if (!hasUser) errs.push('团队至少选择一名成员')
  if (teamTable.length === 0) errs.push('团队表格不能为空')
  tabStatus.team.valid = errs.length === 0
  tabStatus.team.errors = errs
}

function validateAllTabs(): boolean {
  validateOverviewMarket()
  validateTechnical()
  validateCost()
  validateTeam()
  return Object.values(tabStatus).every(t => t.valid)
}

function validateCurrentTab(): void {
  const tab = activeTab.value
  const validators: Record<string, () => void> = {
    overview_market: validateOverviewMarket,
    technical: validateTechnical,
    cost: validateCost,
    team: validateTeam,
  }
  validators[tab]?.()
}

// ═══════════════════════════════════════════════
// 工具函数
// ═══════════════════════════════════════════════

function formatMoney(val: number | null | undefined): string {
  if (val == null) return '0'
  return Number(val).toLocaleString('zh-CN')
}

function statusTagType(status: string): string {
  const map: Record<string, string> = {
    planning: 'info', running: '', completed: 'success',
    paused: 'warning', cancelled: 'danger', draft: 'info', overdue: 'danger',
    submitted: 'primary'
  }
  return map[status] || 'info'
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    planning: '规划中', running: '进行中', completed: '已完成',
    paused: '暂停', cancelled: '已取消', draft: '草稿', overdue: '超期',
    submitted: '已提交'
  }
  return map[status] || status
}

function approvalTagType(status: string): string {
  const map: Record<string, string> = {
    pending: 'warning', approved: 'success', rejected: 'danger'
  }
  return map[status] || 'info'
}

function approvalLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '审批中', approved: '审批通过', rejected: '审批驳回'
  }
  return map[status] || status
}

function progressColor(progress: number): string {
  if (progress >= 80) return '#67c23a'
  if (progress >= 40) return '#409eff'
  return '#e6a23c'
}

// ═══════════════════════════════════════════════
// Tab 5 计算属性
// ═══════════════════════════════════════════════

// 团队摘要
const teamSummary = computed(() => {
  const totalRoles = teamTable.length
  let totalSlots = 0
  let filled = 0
  const roleSummaries: { role: string; headcount: number; filled: number }[] = []
  
  for (const row of teamTable) {
    const hc = row.headcount || 1
    totalSlots += hc
    let rowFilled = 0
    if (hc <= 1) {
      if (row.user_id != null) rowFilled = 1
    } else {
      rowFilled = row.slots.filter(s => s.user_id != null).length
    }
    filled += rowFilled
    roleSummaries.push({ role: row.role, headcount: hc, filled: rowFilled })
  }
  return {
    totalRoles,
    totalSlots,
    filled,
    unfilled: totalSlots - filled,
    roleSummaries,
  }
})

// ═══════════════════════════════════════════════
// 团队按角色过滤（多岗位映射）
// ═══════════════════════════════════════════════

function getUsersByRole(role: string): UserInfo[] {
  if (!role) return allTeamUsers.value
  // 先查项目角色→系统岗位映射表
  const mapping = roleMappings.value.find(m => m.project_role === role)
  if (mapping && mapping.sys_roles.length > 0) {
    // 多岗位：用户role字段或job_title字段包含任一映射值即可
    return allTeamUsers.value.filter(u => {
      const userRole = u.role || ''
      const userTitle = u.job_title || ''
      return mapping.sys_roles.some(sr =>
        userRole === sr || userTitle.includes(sr) || userRole.includes(sr)
      )
    })
  }
  // fallback: 沿用旧的 sys_role 映射
  const roleMap: Record<string, string> = {}
  teamRoles.value.forEach(r => { roleMap[r.value] = r.sys_role })
  const sysRole = roleMap[role]
  if (!sysRole) return allTeamUsers.value
  return allTeamUsers.value.filter(u => u.role === sysRole)
}

// 用户选项标签（含负载badge文本）
function getUserOptionLabel(u: UserInfo): string {
  const wl = getWorkloadInfo(u.id)
  if (wl) {
    return `${u.full_name || u.username} · ${wl.project_count}个项目 · 负载${wl.workload_pct}%`
  }
  return u.full_name || u.username
}

// 获取负载badge信息（颜色 + 文本）
function getWorkloadBadge(userId: number): { text: string; color: string } | null {
  const wl = getWorkloadInfo(userId)
  if (!wl) return null
  const pct = wl.workload_pct
  let color = '#67c23a' // green: <50%
  if (pct >= 80) color = '#f56c6c'      // red: >80%
  else if (pct >= 50) color = '#e6a23c' // yellow: 50-80%
  return { text: `负载${pct}%`, color }
}

function getWorkloadInfo(userId: number): UserWorkload | undefined {
  return userWorkloads.value.find(w => w.user_id === userId)
}

// 槽位填充状态
function getSlotFillStatus(row: TeamMemberRow): 'full' | 'partial' | 'empty' {
  if (row.headcount <= 1) {
    return row.user_id != null ? 'full' : 'empty'
  }
  const filled = row.slots.filter(s => s.user_id != null).length
  if (filled === row.headcount) return 'full'
  if (filled > 0) return 'partial'
  return 'empty'
}

// 槽位摘要文本
function getSlotSummary(row: TeamMemberRow): string {
  if (row.headcount <= 1) {
    return row.full_name || '未分配'
  }
  const filled = row.slots.filter(s => s.user_id != null).length
  const names = row.slots.filter(s => s.full_name).map(s => s.full_name).join(', ')
  return names || `${filled}/${row.headcount} 已分配`
}

// 上级选项：从teamTable中已选人员过滤（排除自己）
function getSuperiorOptions(excludeIndex: number): { id: number; label: string }[] {
  const options: { id: number; label: string }[] = []
  const excludeIds = new Set<number>()
  
  // 收集当前行的所有user_id，排除自己
  const row = teamTable[excludeIndex]
  if (row) {
    if (row.headcount <= 1) {
      if (row.user_id != null) excludeIds.add(row.user_id)
    } else {
      row.slots.forEach(s => { if (s.user_id != null) excludeIds.add(s.user_id) })
    }
  }

  for (let i = 0; i < teamTable.length; i++) {
    const r = teamTable[i]
    if (r.headcount <= 1) {
      if (r.user_id != null && !excludeIds.has(r.user_id)) {
        options.push({ id: r.user_id, label: r.full_name || `成员#${r.user_id}` })
      }
    } else {
      for (const slot of r.slots) {
        if (slot.user_id != null && !excludeIds.has(slot.user_id)) {
          options.push({ id: slot.user_id, label: slot.full_name || `成员#${slot.user_id}` })
        }
      }
    }
  }
  return options
}

// ═══════════════════════════════════════════════
// 年度规划相关
// ═══════════════════════════════════════════════

function openPlanDialog() {
  planForm.name = ''
  planForm.year = ''
  planForm.description = ''
  planForm.doc_ref = ''
  editingPlanId.value = null
  showPlanDialog.value = true
}

async function savePlanItem() {
  if (!planForm.name.trim()) {
    ElMessage.warning('请输入规划名称')
    return
  }
  savingPlan.value = true
  try {
    const payload = {
      name: planForm.name,
      year: planForm.year,
      description: planForm.description,
      doc_ref: planForm.doc_ref || annualPlanningRef.value,
    }
    if (editingPlanId.value) {
      await api.put(`/pm/planning-items/${editingPlanId.value}`, payload)
      ElMessage.success('年度规划项更新成功')
    } else {
      await api.post('/pm/planning-items', payload)
      ElMessage.success('年度规划项创建成功')
    }
    showPlanDialog.value = false
    editingPlanId.value = null
    await fetchWorkspaceData()
  } catch {
    // handled by interceptor
  } finally {
    savingPlan.value = false
  }
}

function selectPlan(item: PlanningItem) {
  selectedPlanId.value = item.id
  filteredProjects.value = item.projects || []
  projectForm.annual_planning_ref = item.name
  projectForm.annual_planning_id = item.id
}

function editPlanItem(item: PlanningItem) {
  planForm.name = item.name
  planForm.year = item.year
  planForm.description = item.description || ''
  planForm.doc_ref = item.doc_ref || ''
  editingPlanId.value = item.id
  showPlanDialog.value = true
}

async function deletePlanItem(item: PlanningItem) {
  try {
    await ElMessageBox.confirm(
      `确认删除年度规划项「${item.name}」吗？此操作不可恢复。`,
      '删除确认',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
    )
    await api.delete(`/pm/planning-items/${item.id}`)
    ElMessage.success('已删除')
    if (selectedPlanId.value === item.id) {
      selectedPlanId.value = null
      filteredProjects.value = []
    }
    await fetchWorkspaceData()
  } catch {
    // cancelled or handled by interceptor
  }
}

// ═══════════════════════════════════════════════
// 项目看板
// ═══════════════════════════════════════════════

function toggleExpand(projId: number) {
  expandedProjectId.value = expandedProjectId.value === projId ? null : projId
}

// ═══════════════════════════════════════════════
// 抽屉相关
// ═══════════════════════════════════════════════

function openDrawer(draft?: ProjectItem | null) {
  if (draft) {
    populateFormFromDraft(draft)
    draftId.value = draft.id
  } else {
    draftId.value = null
    resetForm()
  }
  // Reset tab validation status
  Object.keys(tabStatus).forEach(key => {
    tabStatus[key].valid = false
    tabStatus[key].errors = []
  })
  activeTab.value = 'overview_market'
  drawerVisible.value = true
}

function resetForm() {
  draftId.value = null
  const empty: Record<string, any> = {
    program_id: null, leader_id: null,
    product_type: '', target_market: '', climate_zone: '', refrigerant: '',
    customer_name: '', capacity_range: '', voltage_freq: '',
    series_name: '', energy_rating: '',
    start_date: null, target_end_date: null,
    ip_ownership: '', project_duration: '',
    dev_category: '', project_origin: '', other_requirements: '',
    annual_planning_id: null,
    background_basis: '', overall_goal: '', tech_goal: '', cost_goal: '',
    sales_goal: '', cert_goal: '', schedule_goal: '', patent_goal: '', other_goals: '',
    sample_qty: undefined,
    sample_required_date: null,
    deliverables: '',
    main_capacity: '', target_price: '', energy_efficiency_req: '', cert_requirements: '',
    market_demand_overview: '', competitor_analysis: '', customer_special_req: '',
    fob_price: undefined,
    bom_cost_target: undefined,
    annual_sales_forecast: undefined,
    product_lifecycle: '',
    annual_planning_ref: '',
    has_outsourcing: false,
  }
  Object.assign(projectForm, empty)
  // Reset cost tables
  devCostTable.forEach(r => { r.budget = 0; r.remark = '' })
  moldCostTable.length = 0
  moldCostTable.push(
    { name: '内机钣金模具', qty: 0, total: 0, remark: '' },
    { name: '内机注塑模具', qty: 0, total: 0, remark: '' },
    { name: '外机钣金模具', qty: 0, total: 0, remark: '' },
    { name: '外机注塑模具', qty: 0, total: 0, remark: '' },
    { name: '翅片模具', qty: 0, total: 0, remark: '' },
    { name: '工装夹具', qty: 0, total: 0, remark: '' },
  )
  protoCostTable.forEach(r => { r.qty = r.stage === 'P2' ? 20 : r.stage === 'P1-1' || r.stage === 'P1-2' ? 10 : 5 })
  certCostTable.length = 0
  laborCostTable.forEach(r => { r.people_count = 1; r.monthly_salary = 1.5; r.months = 6; r.occupancy_rate = 100 })
  testCostTable.forEach(r => { r.days = 10; r.unit_price = parseFloat(systemConfig.value.test_unit_price) || 0.11 })
  // Reset Tab3 tables
  materialComponentTable.length = 0
  materialComponentTable.push({ type: '物料', name: '', spec: '', qty: 1, unit: '个', usage: '', supplier: '', delivery_cycle: '', unit_price: 0, candidate_vendors: '', remark: '' })
  techStep.value = 0
  // Reset tab validation status
  Object.keys(tabStatus).forEach(key => {
    tabStatus[key].valid = false
    tabStatus[key].errors = []
  })
  // Reset team table
  teamTable.length = 0
  selectedProjectType.value = ''
}

function populateFormFromDraft(draft: ProjectItem) {
  projectForm.program_id = draft.program_id ?? null
  projectForm.leader_id = draft.leader_id ?? null
  projectForm.product_type = draft.product_type || ''
  projectForm.target_market = draft.target_market || ''
  projectForm.climate_zone = (draft as any).climate_zone || ''
  projectForm.refrigerant = draft.refrigerant || ''
  projectForm.customer_name = draft.customer_name || ''
  projectForm.capacity_range = draft.capacity_range || ''
  projectForm.voltage_freq = draft.voltage_freq || ''
  projectForm.series_name = draft.series_name || ''
  projectForm.energy_rating = draft.energy_rating || ''
  projectForm.start_date = draft.start_date || null
  projectForm.target_end_date = draft.target_end_date || null
  projectForm.ip_ownership = draft.ip_ownership || ''
  projectForm.dev_category = draft.dev_category || ''
  projectForm.project_origin = draft.project_origin || ''
  projectForm.annual_planning_id = (draft as any).annual_planning_id ?? null
  projectForm.other_requirements = draft.other_requirements || ''
  projectForm.background_basis = draft.background_basis || draft.background_basis_raw || ''
  projectForm.overall_goal = draft.overall_goal || ''
  projectForm.tech_goal = draft.tech_goal || ''
  projectForm.cost_goal = draft.cost_goal || ''
  projectForm.sales_goal = draft.sales_goal || ''
  projectForm.cert_goal = draft.cert_goal || ''
  projectForm.schedule_goal = draft.schedule_goal || ''
  projectForm.patent_goal = draft.patent_goal || ''
  projectForm.other_goals = draft.other_goals || ''
  projectForm.sample_qty = draft.sample_qty ?? undefined
  projectForm.sample_required_date = draft.required_date || null
  projectForm.deliverables = draft.deliverables || ''
  projectForm.main_capacity = draft.main_capacity || ''
  projectForm.target_price = draft.target_price || ''
  projectForm.energy_efficiency_req = draft.energy_efficiency_req || ''
  projectForm.cert_requirements = draft.cert_requirements || ''
  projectForm.market_demand_overview = (draft as any).market_demand_overview || ''
  projectForm.competitor_analysis = (draft as any).competitor_analysis || ''
  projectForm.customer_special_req = (draft as any).customer_special_req || ''
  projectForm.fob_price = draft.fob_price ?? undefined
  projectForm.bom_cost_target = draft.bom_cost_target ?? undefined
  projectForm.annual_sales_forecast = draft.annual_sales_forecast ?? undefined
  projectForm.product_lifecycle = draft.product_lifecycle || ''
  projectForm.annual_planning_ref = draft.annual_planning_ref || ''
  projectForm.has_outsourcing = draft.has_outsourcing || false

  // 恢复成本表格
  if (draft.dev_cost_items) {
    try {
      const parsed = JSON.parse(draft.dev_cost_items)
      if (Array.isArray(parsed)) {
        parsed.forEach((item: any, i: number) => {
          if (devCostTable[i]) {
            devCostTable[i].budget = item.budget ?? 0
            devCostTable[i].remark = item.remark || ''
          }
        })
      }
    } catch { /* ignore */ }
  }
  if (draft.mold_costs) {
    try {
      const parsed = JSON.parse(draft.mold_costs)
      if (Array.isArray(parsed)) {
        moldCostTable.length = 0
        parsed.forEach((item: any) => {
          moldCostTable.push({
            name: item.name || item.category || '',
            qty: item.qty ?? 0,
            total: item.total ?? 0,
            remark: item.remark || '',
          })
        })
      }
    } catch { /* ignore */ }
  }
  if (draft.prototype_costs_detail) {
    try {
      const parsed = JSON.parse(draft.prototype_costs_detail)
      if (Array.isArray(parsed)) {
        parsed.forEach((item: any, i: number) => {
          if (protoCostTable[i]) protoCostTable[i].qty = item.qty ?? protoCostTable[i].qty
        })
      }
    } catch { /* ignore */ }
  }
  if (draft.team_members) {
    try {
      const parsed = JSON.parse(draft.team_members)
      if (Array.isArray(parsed)) {
        teamTable.length = 0
        parsed.forEach((item: any) => {
          const row = createTeamRow(
            item.role || '',
            item.headcount || 1,
            item.responsibility || '',
            item.seq || teamTable.length + 1
          )
          // Restore single-user fields
          if (item.headcount <= 1 || !item.slots) {
            row.user_id = item.user_id ?? null
            row.full_name = item.full_name || ''
            row.department = item.department || ''
            if (row.slots.length > 0) {
              row.slots[0].user_id = item.user_id ?? null
              row.slots[0].full_name = item.full_name || ''
              row.slots[0].department = item.department || ''
            }
          }
          // Restore slots
          if (item.slots && Array.isArray(item.slots)) {
            item.slots.forEach((s: any, si: number) => {
              if (row.slots[si]) {
                row.slots[si].user_id = s.user_id ?? null
                row.slots[si].full_name = s.full_name || ''
                row.slots[si].department = s.department || ''
              }
            })
          }
          row.superior_id = item.superior_id ?? null
          teamTable.push(row)
        })
      }
    } catch { /* ignore */ }
  }
  // 恢复测试费用
  if (draft.test_costs) {
    try {
      const parsed = JSON.parse(draft.test_costs)
      if (Array.isArray(parsed)) {
        parsed.forEach((item: any, i: number) => {
          if (testCostTable[i]) {
            testCostTable[i].days = item.days ?? testCostTable[i].days
            testCostTable[i].unit_price = item.unit_price ?? testCostTable[i].unit_price
          }
        })
      }
    } catch { /* ignore */ }
  }
  // 恢复认证费用
  if (draft.cert_costs) {
    try {
      const parsed = JSON.parse(draft.cert_costs)
      if (Array.isArray(parsed)) {
        certCostTable.length = 0
        parsed.forEach((item: any) => {
          certCostTable.push({
            cert_name: item.cert_name || item.cert_type || '',
            cert_body: item.cert_body || '',
            cost_wan: item.cost_wan ?? item.cost ?? 0,
            remark: item.remark || '',
          })
        })
      }
    } catch { /* ignore */ }
  }
  // 恢复人工费用
  if (draft.labor_costs) {
    try {
      const parsed = JSON.parse(draft.labor_costs)
      const items: any[] = parsed.items || (Array.isArray(parsed) ? parsed : [])
      if (Array.isArray(items)) {
        items.forEach((item: any) => {
          // DB字段: role/headcount/occupancy(0-1); 前端字段: module/people_count/occupancy_rate(0-100)
          const row = laborCostTable.find(r => r.module === item.module || item.role?.startsWith(r.module))
          if (row) {
            row.people_count = item.people_count ?? item.headcount ?? row.people_count
            row.monthly_salary = item.monthly_salary ?? row.monthly_salary
            row.months = item.months ?? row.months
            if (item.occupancy_rate != null) row.occupancy_rate = item.occupancy_rate
            else if (item.occupancy != null) row.occupancy_rate = item.occupancy * 100
          }
        })
      }
    } catch { /* ignore */ }
  }
  // 恢复客户需求
  if (draft.customer_requirements) {
    try {
      const parsed = JSON.parse(draft.customer_requirements)
      if (Array.isArray(parsed)) {
        customerReqTable.length = 0
        parsed.forEach((item: any) => customerReqTable.push({ ...item }))
      }
    } catch { /* ignore */ }
  }
  // 恢复核心性能参数（仅当草稿中有数据时；否则保持API加载的值）
  if (draft.core_performance) {
    try {
      const parsed = JSON.parse(draft.core_performance)
      if (Array.isArray(parsed) && parsed.length > 0) {
        corePerfTable.length = 0
        parsed.forEach((item: any) => corePerfTable.push({
          param_name: item.param_name || '',
          baseline: item.baseline || '',
          target_value: item.target_value || '',
          aux_competitor: item.aux_competitor || '',
          tcl_competitor: item.tcl_competitor || '',
          source: item.source || 'manual',
        }))
      }
    } catch { /* ignore */ }
  }
  // 恢复物料与部件清单
  if (draft.material_components) {
    try {
      const parsed = JSON.parse(draft.material_components)
      if (Array.isArray(parsed) && parsed.length > 0) {
        materialComponentTable.length = 0
        parsed.forEach((item: any) => materialComponentTable.push({
          type: item.type || '物料', name: item.name || '', spec: item.spec || '',
          qty: item.qty ?? 1, unit: item.unit || '个', usage: item.usage || '',
          supplier: item.supplier || '', delivery_cycle: item.delivery_cycle || '',
          unit_price: item.unit_price ?? 0, candidate_vendors: item.candidate_vendors || '',
          remark: item.remark || '',
        }))
      }
    } catch { /* ignore */ }
  }
  // 恢复安全合规（仅当草稿中有数据时）
  if (draft.safety_compliance) {
    try {
      const parsed = JSON.parse(draft.safety_compliance)
      if (Array.isArray(parsed) && parsed.length > 0) {
        safetyComplianceTable.length = 0
        parsed.forEach((item: any) => safetyComplianceTable.push({
          standard: item.standard || '',
          applicable_market: item.applicable_market || '',
          key_requirement: item.key_requirement || '',
          verification_method: item.verification_method || '',
          involved_parts: item.involved_parts || '',
          cert_cycle: item.cert_cycle || '',
          remark: item.remark || ''
        }))
      }
    } catch { /* ignore */ }
  }
  // 恢复配件选配
  if (draft.accessory_config) {
    try {
      const parsed = JSON.parse(draft.accessory_config)
      if (Array.isArray(parsed)) {
        accessoryConfigTable.length = 0
        parsed.forEach((item: any) => accessoryConfigTable.push({ name: item.name || '', selection: item.selection || '', _original: item.selection || '' }))
      }
    } catch { /* ignore */ }
  }
  // 恢复功能选配
  if (draft.feature_config) {
    try {
      const parsed = JSON.parse(draft.feature_config)
      if (Array.isArray(parsed)) {
        featureConfigTable.length = 0
        parsed.forEach((item: any) => featureConfigTable.push({ name: item.name || '', selection: item.selection || '', _original: item.selection || '' }))
      }
    } catch { /* ignore */ }
  }
}

function buildProjectPayload(): Record<string, any> {
  const f = projectForm
  return {
    name: autoProjectName.value,
    program_id: f.program_id ?? undefined,
    leader_id: f.leader_id ?? undefined,
    product_type: f.product_type || undefined,
    target_market: f.target_market || undefined,
    climate_zone: f.climate_zone || undefined,
    refrigerant: f.refrigerant || undefined,
    customer_name: f.customer_name || undefined,
    capacity_range: f.capacity_range || undefined,
    voltage_freq: f.voltage_freq || undefined,
    series_name: f.series_name || undefined,
    energy_rating: f.energy_rating || undefined,
    start_date: f.start_date || undefined,
    target_end_date: f.target_end_date || undefined,
    ip_ownership: f.ip_ownership || undefined,
    project_duration: autoProjectDuration.value !== '请选择起止日期' ? autoProjectDuration.value : undefined,
    dev_category: f.dev_category || undefined,
    project_origin: f.project_origin || undefined,
    annual_planning_id: f.annual_planning_id ?? undefined,
    other_requirements: f.other_requirements || undefined,
    background_basis: f.background_basis || undefined,
    overall_goal: f.overall_goal || undefined,
    tech_goal: f.tech_goal || undefined,
    cost_goal: f.cost_goal || undefined,
    sales_goal: f.sales_goal || undefined,
    cert_goal: f.cert_goal || undefined,
    schedule_goal: f.schedule_goal || undefined,
    patent_goal: f.patent_goal || undefined,
    other_goals: f.other_goals || undefined,
    sample_qty: f.sample_qty ?? undefined,
    sample_required_date: f.sample_required_date || undefined,
    deliverables: f.deliverables || undefined,
    main_capacity: f.main_capacity || undefined,
    target_price: f.target_price || undefined,
    energy_efficiency_req: f.energy_efficiency_req || undefined,
    cert_requirements: f.cert_requirements || undefined,
    market_demand_overview: f.market_demand_overview || undefined,
    competitor_analysis: f.competitor_analysis || undefined,
    customer_special_req: f.customer_special_req || undefined,
    fob_price: f.fob_price ?? undefined,
    bom_cost_target: f.bom_cost_target ?? undefined,
    annual_sales_forecast: f.annual_sales_forecast ?? undefined,
    product_lifecycle: f.product_lifecycle || undefined,
    annual_planning_ref: f.annual_planning_ref || undefined,
    has_outsourcing: f.has_outsourcing || false,
    // 表格数据
    customer_requirements: JSON.stringify(customerReqTable),
    core_performance: JSON.stringify(corePerfTable),
    safety_compliance: JSON.stringify(safetyComplianceTable),
    material_components: JSON.stringify(materialComponentTable.map(r => ({
      type: r.type, name: r.name, spec: r.spec, qty: r.qty, unit: r.unit,
      usage: r.usage, supplier: r.supplier, delivery_cycle: r.delivery_cycle,
      unit_price: r.unit_price, candidate_vendors: r.candidate_vendors, remark: r.remark
    }))),
    accessory_config: JSON.stringify(accessoryConfigTable.map(({ name, selection }) => ({ name, selection }))),
    feature_config: JSON.stringify(featureConfigTable.map(({ name, selection }) => ({ name, selection }))),
    dev_cost_items: JSON.stringify(devCostTable.map(r => ({ item: r.item, budget: r.budget, remark: r.remark, linked: r.linked }))),
    mold_costs: JSON.stringify(moldCostTable.map(r => ({ name: r.name, qty: r.qty, total: r.total, remark: r.remark }))),
    prototype_costs_detail: JSON.stringify(protoCostTable.map(r => ({ stage: r.stage, qty: r.qty, unit_cost: r.unit_cost }))),
    labor_costs: JSON.stringify(laborCostTable.map(r => ({ module: r.module, people_count: r.people_count, monthly_salary: r.monthly_salary, months: r.months, occupancy_rate: r.occupancy_rate }))),
    test_costs: JSON.stringify(testCostTable.map(r => ({ stage: r.stage, days: r.days, unit_price: r.unit_price }))),
    cert_costs: JSON.stringify(certCostTable.map(r => ({ cert_name: r.cert_name, cert_body: r.cert_body, cost_wan: r.cost_wan, remark: r.remark }))),
    team_members: JSON.stringify(teamTable.map(t => ({
      role: t.role,
      headcount: t.headcount || 1,
      user_id: t.headcount <= 1 ? t.user_id : null,
      full_name: t.full_name || '',
      department: t.department || '',
      responsibility: t.responsibility || '',
      superior_id: t.superior_id,
      seq: t.seq || 0,
      slots: t.slots.map(s => ({
        slot_id: s.slot_id,
        user_id: s.user_id,
        full_name: s.full_name || '',
        department: s.department || '',
      })),
    }))),
  }
}

async function saveDraft() {
  savingDraft.value = true
  try {
    const payload = buildProjectPayload()
    if (draftId.value) {
      await api.put(`/pm/project/draft/${draftId.value}`, payload)
      ElMessage.success('草稿已更新')
    } else {
      const res = await api.post('/pm/project/draft', payload)
      if (res.data?.id) draftId.value = res.data.id
      ElMessage.success('草稿已保存')
    }
  } catch {
    // handled by interceptor
  } finally {
    savingDraft.value = false
  }
}

async function submitProposal() {
  const name = autoProjectName.value
  if (!name || name === '（自动生成：请填写相关字段）') {
    ElMessage.warning('请完善产品类型、目标市场、系列名称、能力段、制冷剂、能效等级以生成项目名称')
    activeTab.value = 'overview_market'
    return
  }

  // 全Tab校验
  const allValid = validateAllTabs()
  if (!allValid) {
    // 找到第一个不通过的Tab并切换
    const tabOrder = ['overview_market', 'technical', 'cost', 'team']
    const firstInvalid = tabOrder.find(t => !tabStatus[t].valid)
    if (firstInvalid) {
      activeTab.value = firstInvalid
      const errors = tabStatus[firstInvalid].errors
      ElMessage.warning(`请完善「${firstInvalid}」信息：${errors.join('、')}`)
    }
    return
  }

  submitting.value = true
  try {
    // 1. 必须先保存草稿（后端 submit 只接受 project_id）
    if (!draftId.value) {
      await saveDraft()
      if (!draftId.value) {
        ElMessage.error('草稿保存失败，无法提交')
        submitting.value = false
        return
      }
    }
    // 2. 提交审批 — 后端期望 {project_id: int}
    await api.post('/pm/proposals/submit', { project_id: draftId.value })
    ElMessage.success('已提交审批，等待审批人审核')
    drawerVisible.value = false
    await fetchWorkspaceData()
  } catch {
    // handled by interceptor
  } finally {
    submitting.value = false
  }
}

async function withdrawProposal(proposal: ProjectItem) {
  try {
    await ElMessageBox.confirm(
      `确定撤销「${proposal.name}」的立项申请？撤销后项目将恢复为草稿状态，可重新编辑后再次提交。`,
      '确认撤销提交',
      { type: 'warning', confirmButtonText: '确认撤销', cancelButtonText: '取消' }
    )
    await api.post(`/pm/proposals/${proposal.id}/withdraw`)
    ElMessage.success('已撤销提交，项目已恢复为草稿')
    await fetchWorkspaceData()
  } catch {
    // cancelled or error (handled by interceptor)
  }
}

// ═══════════════════════════════════════════════
// 表格增删行函数
// ═══════════════════════════════════════════════

function addMoldRow() {
  moldCostTable.push({ name: '', qty: 0, total: 0, remark: '' })
}
function removeMoldRow(index: number) { moldCostTable.splice(index, 1) }

function addCustomerReqRow() {
  customerReqTable.push({ category: '', description: '', source: '', tech_impact: '', market_impact: '' })
}
function removeCustomerReqRow(index: number) { customerReqTable.splice(index, 1) }

function addCorePerfRow() {
  corePerfTable.push({ param_name: '', baseline: '', target_value: '', aux_competitor: '', tcl_competitor: '', source: 'manual' })
}
function removeCorePerfRow(index: number) { corePerfTable.splice(index, 1) }

function addMaterialComponentRow() {
  materialComponentTable.push({ type: '物料', name: '', spec: '', qty: 1, unit: '个', usage: '', supplier: '', delivery_cycle: '', unit_price: 0, candidate_vendors: '', remark: '' })
}
function removeMaterialComponentRow(index: number) { materialComponentTable.splice(index, 1) }

function addTeamRow() {
  const seq = teamTable.length > 0 ? Math.max(...teamTable.map(r => r.seq || 0)) + 1 : 1
  teamTable.push(createTeamRow('', 1, '', seq))
}
function removeTeamRow(index: number) { teamTable.splice(index, 1) }

function onTeamRoleChange(index: number) {
  const row = teamTable[index]
  if (!row) return
  row.user_id = null
  row.full_name = ''
  row.department = ''
  row._departmentManual = false
  row._departmentFailed = false
  row.slots.forEach(s => { s.user_id = null; s.full_name = ''; s.department = '' })
}

function onHeadcountChange(index: number) {
  const row = teamTable[index]
  if (!row) return
  const newHc = row.headcount || 1
  // Adjust slots array
  while (row.slots.length < newHc) {
    row.slots.push(createEmptySlot(row.slots.length + 1))
  }
  while (row.slots.length > newHc) {
    row.slots.pop()
  }
  // If headcount becomes 1, copy first slot data to row-level fields
  if (newHc === 1 && row.slots.length > 0) {
    row.user_id = row.slots[0].user_id
    row.full_name = row.slots[0].full_name
    row.department = row.slots[0].department
  } else {
    row.user_id = null
    row.full_name = ''
  }
}

function onTeamUserChange(index: number, _slotIndex: number = 0) {
  const row = teamTable[index]
  if (!row) return
  
  if (row.headcount <= 1) {
    // Direct user assignment
    const user = allTeamUsers.value.find(u => u.id === row.user_id)
    if (user) {
      row.full_name = user.full_name || user.username
      if (user.department) {
        row.department = user.department
        row._departmentFailed = false
        row._departmentManual = false
      } else {
        row.department = ''
        row._departmentFailed = true
        row._departmentManual = true // allow manual input
      }
    }
  }
  // Slot-level changes are handled by onSlotUserChange
}

function onSlotUserChange(rowIndex: number, slotIndex: number) {
  const row = teamTable[rowIndex]
  if (!row || !row.slots[slotIndex]) return
  const slot = row.slots[slotIndex]
  const user = allTeamUsers.value.find(u => u.id === slot.user_id)
  if (user) {
    slot.full_name = user.full_name || user.username
    slot.department = user.department || ''
  }
  // Sync row-level for headcount=1
  if (row.headcount === 1 && row.slots.length > 0) {
    row.user_id = row.slots[0].user_id
    row.full_name = row.slots[0].full_name
    row.department = row.slots[0].department
  }
  // Update row department from all slots
  if (row.headcount > 1) {
    const depts = row.slots.filter(s => s.department).map(s => s.department)
    row.department = [...new Set(depts)].join('/')
    row._departmentFailed = depts.length < row.slots.length
  }
}

// 项目类型变更 → 加载角色模板
async function onProjectTypeChange(projectType: string) {
  selectedProjectType.value = projectType
  if (projectType) {
    // 同步到Tab1 dev_category
    projectForm.dev_category = projectType
    await loadTeamRoleTemplate(projectType)
  }
}

// ═══════════════════════════════════════════════
// API调用
// ═══════════════════════════════════════════════

const ALL_KB_CATEGORIES = ['market', 'product_type', 'capacity', 'voltage', 'ip_ownership', 'main_capacity', 'cert', 'series', 'energy_rating']

async function fetchCertStandards(market: string) {
  try {
    const res = await api.get('/pm/cert-standards', { params: { market } })
    const items = res.data?.items || []
    safetyComplianceTable.length = 0
    items.forEach((item: any) => {
      safetyComplianceTable.push({
        standard: item.standard,
        applicable_market: item.market || market,
        key_requirement: item.key_requirement || '',
        verification_method: item.verification_method || '',
        involved_parts: '',
        cert_cycle: item.cert_cycle || '',
        remark: ''
      })
    })
  } catch {
    // API not available yet, keep existing data
  }
}

async function fetchPerfDefaults(market: string, capacity: string) {
  try {
    const res = await api.get('/pm/perf-defaults', { params: { market, capacity } })
    const items = res.data?.items || []
    corePerfTable.length = 0
    items.forEach((item: any) => {
      corePerfTable.push({
        param_name: item.param_name,
        baseline: item.baseline || '',
        target_value: item.target_value || '',
        aux_competitor: item.aux_competitor || '',
        tcl_competitor: item.tcl_competitor || '',
        source: item.source || 'market_config',
      })
    })
  } catch {
    // API not available yet, keep existing data
  }
}

async function fetchAccessoryDefaults(market: string) {
  try {
    const res = await api.get('/pm/accessory-defaults', { params: { market } })
    const items = res.data?.items || []
    accessoryConfigTable.length = 0
    items.forEach((item: any) => {
      accessoryConfigTable.push({
        name: item.name,
        selection: item.default_selection || '选配',
        _original: item.default_selection || '选配'
      })
    })
  } catch {
    // API not available yet, keep existing data
  }
}

async function fetchFeatureDefaults(market: string) {
  try {
    const res = await api.get('/pm/feature-defaults', { params: { market } })
    const items = res.data?.items || []
    featureConfigTable.length = 0
    items.forEach((item: any) => {
      featureConfigTable.push({
        name: item.name,
        selection: item.default_selection || '选配',
        _original: item.default_selection || '选配'
      })
    })
  } catch {
    // API not available yet, keep existing data
  }
}

async function fetchWorkspaceData() {
  try {
    const res = await api.get('/pm/workspace')
    const data = res.data
    planningItems.value = data.annual_plans || []
    products.value = data.products || []
    myProjects.value = data.my_projects || []
    if (data.draft) {
      draftId.value = data.draft.id
    }
    if (data.annual_planning_ref) {
      annualPlanningRef.value = data.annual_planning_ref
    }
  } catch {
    // handled by interceptor
  }
}

async function fetchProposals() {
  try {
    const res = await api.get('/pm/proposals', {
      params: { status: proposalFilter.value }
    })
    myProposals.value = res.data.proposals || []
  } catch {
    // handled by interceptor
  }
}

function openProposal(proposal: ProjectItem) {
  if (proposal.is_draft) {
    // 草稿 → 打开抽屉编辑
    openDrawer(proposal)
  } else {
    // 已提交 → 打开抽屉查看/编辑
    openDrawer(proposal)
  }
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

async function fetchKbOptions() {
  try {
    const results = await Promise.allSettled(
      ALL_KB_CATEGORIES.map(cat => api.get(`/kb/items?category=${cat}`))
    )
    results.forEach((r, i) => {
      if (r.status === 'fulfilled') {
        const data = r.value.data
        if (Array.isArray(data)) {
          kbOptions[ALL_KB_CATEGORIES[i]] = data
        }
      }
    })
  } catch { /* non-critical */ }
}

async function fetchTeamRoles() {
  try {
    const res = await api.get('/kb/team-roles')
    teamRoles.value = res.data || []
  } catch { /* non-critical */ }
}

async function fetchAllTeamUsers() {
  try {
    const res = await api.get('/kb/team')
    allTeamUsers.value = res.data || []
  } catch { /* non-critical */ }
}

// 新增：获取角色映射表
async function fetchRoleMappings() {
  try {
    const res = await api.get('/pm/role-mappings')
    roleMappings.value = res.data?.items || res.data || []
  } catch { /* non-critical, fallback to sys_role mapping */ }
}

// 新增：获取人员负载数据
async function fetchUserWorkloads() {
  try {
    const res = await api.get('/pm/user-workloads')
    userWorkloads.value = res.data?.items || res.data || []
  } catch { /* non-critical */ }
}

// 新增：加载角色模板
async function loadTeamRoleTemplate(projectType: string) {
  try {
    const res = await api.get('/pm/team-role-template', { params: { project_type: projectType } })
    const items: TeamRoleTemplateItem[] = res.data?.items || res.data || []
    if (items.length > 0) {
      teamTable.length = 0
      items
        .sort((a, b) => (a.seq || 0) - (b.seq || 0))
        .forEach(item => {
          teamTable.push(createTeamRow(
            item.role_name,
            item.headcount || 1,
            item.responsibility_default || '',
            item.seq || 0
          ))
        })
    }
  } catch {
    // API not available, use default fallback
    if (teamTable.length === 0) {
      loadDefaultTeamTemplate()
    }
  }
}

// 默认角色模板（API不可用时的fallback）
function loadDefaultTeamTemplate() {
  const defaults: TeamRoleTemplateItem[] = [
    { role_name: '项目经理', headcount: 1, responsibility_default: '全面负责项目管理', seq: 1 },
    { role_name: '系统工程师', headcount: 2, responsibility_default: '系统方案设计与性能匹配', seq: 2 },
    { role_name: '结构工程师', headcount: 3, responsibility_default: '结构设计与外观设计', seq: 3 },
    { role_name: '电控工程师', headcount: 2, responsibility_default: '硬件电路与软件控制', seq: 4 },
    { role_name: '电气工程师', headcount: 2, responsibility_default: '电气系统与线束设计', seq: 5 },
    { role_name: '工艺工程师', headcount: 1, responsibility_default: '生产工艺规划', seq: 6 },
    { role_name: 'IQC工程师', headcount: 1, responsibility_default: '来料质量控制', seq: 7 },
    { role_name: '采购工程师', headcount: 1, responsibility_default: '零部件采购', seq: 8 },
    { role_name: '项目管理员', headcount: 1, responsibility_default: '项目文档及进度跟踪', seq: 9 },
  ]
  teamTable.length = 0
  defaults.forEach(item => {
    teamTable.push(createTeamRow(item.role_name, item.headcount, item.responsibility_default, item.seq))
  })
}

async function fetchPrograms() {
  try {
    const res = await api.get('/pm/programs')
    programOptions.value = res.data || []
  } catch { /* non-critical */ }
}

async function fetchExchangeRate() {
  try {
    const res = await api.get('/kb/exchange-rate')
    exchangeRate.value = res.data?.rate || 7.20
  } catch { /* use fallback */ }
}

async function fetchSystemConfig() {
  try {
    const res = await api.get('/admin/config/public')
    if (res.data?.data) {
      systemConfig.value = res.data.data
    }
    // 同步测试费用单价
    const tp = parseFloat(systemConfig.value.test_unit_price)
    if (!isNaN(tp) && tp > 0) {
      testCostTable.forEach(r => { r.unit_price = tp })
    }
  } catch { /* use defaults */ }
}

// ═══════════════════════════════════════════════
// 竞品对标：采纳竞品参数
// ═══════════════════════════════════════════════
// paramKey → corePerfTable.param_name 映射表
const PARAM_KEY_MAP: Record<string, string> = {
  cooling_w: '制冷量(W)',
  cspf: 'CSPF(W/W)',
  energy_grade: '能效等级',
  tolerance: '容差(%)',
  air_flow: '出风量(m³/h)',
  noise_indoor: '室内噪音dB(A)',
  noise_outdoor: '室外噪音dB(A)',
  pipe_size: '接管尺寸',
  refrigerant: '制冷剂',
  net_weight_indoor: '内机净重(kg)',
  net_weight_outdoor: '外机净重(kg)',
  dimension_indoor: '内机尺寸(mm)',
  dimension_outdoor: '外机尺寸(mm)',
}

function onAdoptCompetitor({ paramKey, value, brand }: { paramKey: string; value: number; brand: string }) {
  const paramName = PARAM_KEY_MAP[paramKey]
  if (!paramName) {
    ElMessage.warning(`未知参数: ${paramKey}`)
    return
  }
  const row = corePerfTable.find(r => r.param_name === paramName)
  if (!row) {
    ElMessage.warning(`核心性能表中未找到参数: ${paramName}`)
    return
  }
  row.target_value = String(value)
  row.source = brand
  ElMessage.success(`已采纳 ${brand} 的 ${paramName} 值: ${value}`)
}

// ═══════════════════════════════════════════════
// 生命周期
// ═══════════════════════════════════════════════

onMounted(async () => {
  try {
    await fetchSystemConfig()
    await fetchWorkspaceData()
    await fetchProposals()
    await fetchKbOptions()
    await fetchTeamRoles()
    await fetchAllTeamUsers()
    await fetchRoleMappings()
    await fetchUserWorkloads()
    await fetchPrograms()
    await fetchExchangeRate()
    // 加载默认角色模板（如果没有项目类型则用默认值）
    if (projectForm.dev_category) {
      selectedProjectType.value = projectForm.dev_category
      await loadTeamRoleTemplate(projectForm.dev_category)
    } else if (teamTable.length === 0) {
      loadDefaultTeamTemplate()
    }
    // 如果已有默认值（如从草稿加载），自动加载相关联数据
    if (projectForm.target_market) {
      fetchCertStandards(projectForm.target_market)
      fetchAccessoryDefaults(projectForm.target_market)
      fetchFeatureDefaults(projectForm.target_market)
    }
    if (projectForm.target_market && projectForm.capacity_range) {
      fetchPerfDefaults(projectForm.target_market, projectForm.capacity_range)
    }
  } catch (e) {
    console.error('PMWorkspace init error:', e)
  }
})
</script>

<style scoped>
.pm-workspace {
  height: 100%;
  overflow-y: auto;
}

.workspace-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.workspace-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.header-date {
  font-size: 14px;
  color: #909399;
}

/* 三栏布局 */
.workspace-body {
  display: flex;
  gap: 16px;
  min-height: 500px;
}

.col-left {
  flex: 0 0 30%;
}
.col-middle {
  flex: 0 0 40%;
}
.col-right {
  flex: 0 0 30%;
}

.col-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.col-card :deep(.el-card__body) {
  flex: 1;
  overflow-y: auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.plan-ref-input {
  margin-bottom: 12px;
}

.empty-state {
  padding: 20px 0;
}

/* 规划项列表 */
.plan-item {
  padding: 10px 12px;
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  border: 1px solid #ebeef5;
  transition: all 0.2s;
}

.plan-item:hover {
  border-color: #409eff;
  background: #ecf5ff;
}

.plan-item--active {
  border-color: #409eff;
  background: #ecf5ff;
}

.plan-item-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.plan-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}

.plan-item-desc {
  font-size: 12px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.plan-item-count {
  font-size: 12px;
  color: #606266;
}

.linked-projects {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}

.linked-title {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 8px;
}

.linked-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  font-size: 13px;
}

.linked-item-tags {
  display: flex;
  gap: 4px;
  align-items: center;
}

/* 立项入口 */
.initiation-intro {
  font-size: 13px;
  color: #606266;
  line-height: 1.8;
}

.initiation-intro p {
  margin: 0 0 8px 0;
}

.initiation-intro ul {
  margin: 0;
  padding-left: 16px;
}

.initiation-intro li {
  margin-bottom: 4px;
}

.draft-hint {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #e6a23c;
}

/* 看板统计 */
.stats-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.stat-item {
  flex: 1;
  text-align: center;
}

.stat-num {
  font-size: 20px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 11px;
  color: #909399;
  margin-top: 2px;
}

/* 项目卡片 */
.project-card {
  padding: 10px 12px;
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  border: 1px solid #ebeef5;
  transition: all 0.2s;
}

.project-card:hover {
  border-color: #409eff;
  background: #ecf5ff;
}

.project-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.project-card-tags {
  display: flex;
  gap: 4px;
  align-items: center;
}

.project-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  margin-right: 8px;
}

.project-card-meta {
  font-size: 12px;
  color: #909399;
  display: flex;
  gap: 12px;
}

.project-detail {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed #dcdfe6;
  font-size: 12px;
  color: #606266;
}

.detail-row {
  padding: 2px 0;
}

.detail-row label {
  font-weight: 500;
  color: #303133;
  margin-right: 4px;
}

/* 抽屉 */
.drawer-tabs {
  height: calc(100vh - 160px);
}

.drawer-tabs :deep(.el-tabs__content) {
  height: calc(100vh - 240px);
  overflow-y: auto;
  padding: 0 8px;
}

.section-table {
  margin-bottom: 8px;
}

.linked-val {
  color: #909399;
  font-size: 13px;
}

.cost-summary {
  text-align: right;
  font-size: 14px;
  color: #606266;
  padding: 8px 0;
}

.cost-summary strong {
  color: #409eff;
}

.team-section {
  padding: 0;
}

.team-toolbar {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.team-hint {
  font-size: 12px;
  color: #909399;
}

/* 团队摘要 */
.team-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.team-summary-roles {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-left: auto;
}

.summary-role-item {
  font-size: 12px;
  color: #606266;
  white-space: nowrap;
}

/* 用户选项负载badge */
.user-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.workload-badge {
  font-size: 11px;
  margin-left: 8px;
  white-space: nowrap;
}

/* 槽位编辑器 */
.slot-editor {
  max-height: 300px;
  overflow-y: auto;
}

.slot-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px solid #ebeef5;
}

.slot-row:last-child {
  border-bottom: none;
}

.slot-label {
  font-size: 12px;
  font-weight: 500;
  color: #606266;
  min-width: 30px;
}

.slot-dept {
  font-size: 11px;
  color: #909399;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 8px;
}

/* ── 我的提案（顶部横幅） ── */
.proposals-section {
  margin-bottom: 16px;
}

.proposals-section .el-card {
  border: 1px solid #d9ecff;
  background: #f5f9ff;
}

.proposals-section .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.proposals-filter {
  display: flex;
  align-items: center;
}

.proposals-list {
  max-height: 200px;
  overflow-y: auto;
}

.proposal-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-radius: 6px;
  margin-bottom: 6px;
  cursor: pointer;
  border: 1px solid #ebeef5;
  background: #fff;
  transition: all 0.2s;
}

.proposal-item:hover {
  border-color: #409eff;
  background: #ecf5ff;
}

.proposal-item-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.proposal-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.proposal-date {
  font-size: 11px;
  color: #909399;
}

.proposal-item-right {
  display: flex;
  gap: 4px;
  align-items: center;
  flex-shrink: 0;
  margin-left: 12px;
}
</style>
