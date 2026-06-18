<template>
  <div class="pm-workspace">
    <!-- ═══════════════ 顶部标题 ═══════════════ -->
    <div class="workspace-header">
      <h2>📋 产品经理工作台</h2>
      <span class="header-date">{{ currentDate }}</span>
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
            <p>新建产品立项申请，填写以下五个模块信息：</p>
            <ul>
              <li>📋 <strong>项目概述</strong> — 基本信息、背景目标、交付物</li>
              <li>🏪 <strong>市场与客户需求</strong> — 市场需求背景、客户关键需求</li>
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
    <el-dialog v-model="showPlanDialog" title="新建年度规划项" width="500px" :close-on-click-modal="false">
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
        <!-- ═══════════ Tab 1: 项目概述 ═══════════ -->
        <el-tab-pane name="overview">
          <template #label>
            <span>
              <span v-if="tabStatus.overview.valid">✅</span>
              <span v-else>❌</span>
              📋 项目概述
            </span>
          </template>
          <el-form :model="projectForm" label-width="120px" size="small">
            <!-- 一、项目基本信息 -->
            <el-divider content-position="left">一、项目基本信息</el-divider>
            <!-- 新增：项目群选择 + 项目负责人 -->
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
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="项目名称">
                  <el-input :model-value="autoProjectName" disabled placeholder="自动生成" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="产品类型">
                  <el-select v-model="projectForm.product_type" placeholder="选择产品类型" clearable style="width:100%">
                    <el-option v-for="o in kbOptions.product_type" :key="o.code" :label="o.name" :value="o.code" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="目标市场">
                  <el-select v-model="projectForm.target_market" placeholder="选择目标市场" clearable style="width:100%">
                    <el-option v-for="o in kbOptions.market" :key="o.code" :label="o.name" :value="o.code" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="温带">
                  <el-select v-model="projectForm.climate_zone" placeholder="选择温带" clearable style="width:100%">
                    <el-option label="T1" value="T1" />
                    <el-option label="T2" value="T2" />
                    <el-option label="T3" value="T3" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="制冷剂">
                  <el-select v-model="projectForm.refrigerant" placeholder="选择制冷剂" clearable style="width:100%">
                    <el-option label="R32" value="R32" />
                    <el-option label="R410A" value="R410A" />
                    <el-option label="R290" value="R290" />
                    <el-option label="R454B" value="R454B" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="客户名称">
                  <el-input v-model="projectForm.customer_name" placeholder="客户名称" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="能力段">
                  <el-select v-model="projectForm.capacity_range" placeholder="选择能力段" clearable style="width:100%">
                    <el-option v-for="o in kbOptions.capacity" :key="o.code" :label="o.name" :value="o.code" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="电压频率">
                  <el-select v-model="projectForm.voltage_freq" placeholder="选择电压频率" clearable style="width:100%">
                    <el-option v-for="o in kbOptions.voltage" :key="o.code" :label="o.name" :value="o.code" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="立项日期">
                  <el-date-picker v-model="projectForm.start_date" type="date" placeholder="立项日期" style="width:100%" value-format="YYYY-MM-DD" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="计划完成">
                  <el-date-picker v-model="projectForm.target_end_date" type="date" placeholder="计划完成日期" style="width:100%" value-format="YYYY-MM-DD" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="知识产权归属">
                  <el-select v-model="projectForm.ip_ownership" placeholder="选择IP归属" clearable style="width:100%">
                    <el-option v-for="o in kbOptions.ip_ownership" :key="o.code" :label="o.name" :value="o.code" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="项目周期">
                  <el-input :model-value="autoProjectDuration" disabled placeholder="自动计算" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="开发类别">
                  <el-select v-model="projectForm.dev_category" placeholder="选择开发类别" clearable style="width:100%">
                    <el-option label="全新开发" value="全新开发" />
                    <el-option label="派生" value="派生" />
                    <el-option label="降本优化" value="降本优化" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
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
            <el-form-item label="其他要求">
              <el-input v-model="projectForm.other_requirements" type="textarea" :rows="2" placeholder="其他特殊要求" />
            </el-form-item>

            <!-- 二、项目背景与目标 -->
            <el-divider content-position="left">二、项目背景与目标</el-divider>
            <el-form-item label="立项背景与依据">
              <el-input v-model="projectForm.background_basis" type="textarea" :rows="3" placeholder="项目立项背景、市场依据等" />
            </el-form-item>
            <el-form-item label="总体目标">
              <el-input v-model="projectForm.overall_goal" type="textarea" :rows="2" placeholder="项目总体目标" />
            </el-form-item>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="技术目标">
                  <el-input v-model="projectForm.tech_goal" type="textarea" :rows="2" placeholder="技术指标目标" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="成本目标">
                  <el-input v-model="projectForm.cost_goal" type="textarea" :rows="2" placeholder="成本控制目标" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="销售目标">
                  <el-input v-model="projectForm.sales_goal" type="textarea" :rows="2" placeholder="销售数量/金额目标" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="认证目标">
                  <el-input v-model="projectForm.cert_goal" type="textarea" :rows="2" placeholder="认证取得目标" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="进度目标">
                  <el-input v-model="projectForm.schedule_goal" type="textarea" :rows="2" placeholder="进度节点目标" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="专利目标">
                  <el-input v-model="projectForm.patent_goal" type="textarea" :rows="2" placeholder="专利申请目标" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="其他目标">
              <el-input v-model="projectForm.other_goals" type="textarea" :rows="2" placeholder="其他目标" />
            </el-form-item>

            <!-- 三、项目交付物 -->
            <el-divider content-position="left">三、项目交付物</el-divider>
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
          </el-form>
        </el-tab-pane>

        <!-- ═══════════ Tab 2: 市场与客户需求 ═══════════ -->
        <el-tab-pane name="market">
          <template #label>
            <span>
              <span v-if="tabStatus.market.valid">✅</span>
              <span v-else>❌</span>
              🏪 市场与客户需求
            </span>
          </template>
          <el-form :model="projectForm" label-width="120px" size="small">
            <!-- 一、市场需求背景 -->
            <el-divider content-position="left">一、市场需求背景</el-divider>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="主销容量段">
                  <el-select v-model="projectForm.main_capacity" placeholder="选择主销容量段" clearable style="width:100%">
                    <el-option v-for="o in kbOptions.main_capacity" :key="o.code" :label="o.name" :value="o.code" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="目标价格区间">
                  <el-input v-model="projectForm.target_price" placeholder="如: $200-$300" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="能效要求">
                  <el-input v-model="projectForm.energy_efficiency_req" placeholder="如: SEER≥6.1" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="认证要求">
                  <el-input v-model="projectForm.cert_requirements" placeholder="如: CE, CB, SASO" />
                </el-form-item>
              </el-col>
            </el-row>

            <!-- 二、客户关键需求 -->
            <el-divider content-position="left">二、客户关键需求</el-divider>
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
          <!-- 一、核心性能参数 -->
          <el-divider content-position="left">一、核心性能参数</el-divider>
          <el-table :data="corePerfTable" border size="small" class="section-table">
            <el-table-column prop="param_name" label="参数名称" width="120">
              <template #default="{ row }">
                <el-input v-model="row.param_name" size="small" />
              </template>
            </el-table-column>
            <el-table-column prop="target_value" label="目标值" width="140">
              <template #default="{ row }">
                <el-input v-model="row.target_value" size="small" />
              </template>
            </el-table-column>
            <el-table-column prop="aux_competitor" label="AUX竞品" width="120">
              <template #default="{ row }">
                <el-input v-model="row.aux_competitor" size="small" />
              </template>
            </el-table-column>
            <el-table-column prop="tcl_competitor" label="TCL竞品" width="120">
              <template #default="{ row }">
                <el-input v-model="row.tcl_competitor" size="small" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="70">
              <template #default="{ $index }">
                <el-button link type="danger" size="small" @click="removeCorePerfRow($index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-button size="small" style="margin-top:8px" @click="addCorePerfRow">+ 添加行</el-button>

          <!-- 二、安全与合规要求 -->
          <el-divider content-position="left">二、安全与合规要求</el-divider>
          <el-table :data="safetyComplianceTable" border size="small" class="section-table">
            <el-table-column prop="standard" label="法规标准" width="140">
              <template #default="{ row }">
                <span class="linked-val">{{ row.standard }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="applicable_market" label="适用市场" width="120">
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
                <el-input v-model="row.involved_parts" size="small" />
              </template>
            </el-table-column>
            <el-table-column prop="cert_cycle" label="认证周期" width="100">
              <template #default="{ row }">
                <el-input v-model="row.cert_cycle" size="small" />
              </template>
            </el-table-column>
            <el-table-column prop="remark" label="备注" width="120">
              <template #default="{ row }">
                <el-input v-model="row.remark" size="small" />
              </template>
            </el-table-column>
          </el-table>

          <!-- 三、配件选配 -->
          <el-divider content-position="left">三、配件选配</el-divider>
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

          <!-- 四、功能选配 -->
          <el-divider content-position="left">四、功能选配</el-divider>
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
              <el-form-item label="目标出厂价FOB($)" label-width="150px" size="small">
                <el-input-number v-model="projectForm.fob_price" :min="0" :step="1" size="small" controls-position="right" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="汇率(USD/CNY)" label-width="130px" size="small">
                <el-input :model-value="exchangeRate.toFixed(2)" disabled size="small" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="目标BOM成本(￥)" label-width="140px" size="small">
                <el-input-number v-model="projectForm.bom_cost_target" :min="0" :step="1" size="small" controls-position="right" style="width:100%" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item label="BOM成本占比" label-width="150px" size="small">
                <el-input :model-value="bomCostRatioText" disabled size="small" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="制造费用+人工(￥)" label-width="130px" size="small">
                <el-input :model-value="manufacturingCost.toFixed(0)" disabled size="small" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="毛利(￥)" label-width="140px" size="small">
                <el-input :model-value="grossMarginText" disabled size="small" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="年销量预测(首年)" label-width="140px" size="small">
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
          <el-table :data="moldCostTable" border size="small" class="section-table">
            <el-table-column prop="unit_type" label="内外机" width="80" />
            <el-table-column prop="category" label="类别" width="100" />
            <el-table-column label="数量" width="100">
              <template #default="{ row }">
                <el-input-number v-model="row.qty" :min="0" :step="1" size="small" controls-position="right" style="width:100%" />
              </template>
            </el-table-column>
            <el-table-column label="合计(W)" width="120">
              <template #default="{ row }">
                <el-input-number v-model="row.total" :min="0" :step="0.1" size="small" controls-position="right" style="width:100%" />
              </template>
            </el-table-column>
          </el-table>
          <div class="cost-summary">模具/工装合计: <strong>¥{{ moldCostTotal.toFixed(1) }} 万元</strong></div>

          <!-- 四、试制样机费用 -->
          <el-divider content-position="left">四、试制样机费用</el-divider>
          <el-table :data="protoCostTable" border size="small" class="section-table">
            <el-table-column prop="stage" label="阶段" width="80" />
            <el-table-column label="数量" width="100">
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

          <!-- 五、人工费用初步核算 -->
          <el-divider content-position="left">五、人工费用初步核算</el-divider>
          <el-table :data="laborCostTable" border size="small" class="section-table">
            <el-table-column prop="module" label="模块" width="100" />
            <el-table-column label="人数" width="80">
              <template #default="{ row }">
                <el-input-number v-model="row.people_count" :min="0" :step="1" size="small" controls-position="right" style="width:100%" />
              </template>
            </el-table-column>
            <el-table-column label="月薪(W)" width="110">
              <template #default="{ row }">
                <el-input-number v-model="row.monthly_salary" :min="0" :step="0.1" size="small" controls-position="right" style="width:100%" />
              </template>
            </el-table-column>
            <el-table-column label="时间(月)" width="100">
              <template #default="{ row }">
                <el-input-number v-model="row.months" :min="0" :step="1" size="small" controls-position="right" style="width:100%" />
              </template>
            </el-table-column>
            <el-table-column label="占用度%" width="100">
              <template #default="{ row }">
                <el-input-number v-model="row.occupancy_rate" :min="0" :max="100" :step="10" size="small" controls-position="right" style="width:100%" />
              </template>
            </el-table-column>
            <el-table-column label="费用(W)" width="120">
              <template #default="{ row }">
                {{ (row.people_count * row.monthly_salary * row.months * (row.occupancy_rate || 100) / 100).toFixed(1) }}
              </template>
            </el-table-column>
          </el-table>
          <div class="cost-summary">人工费用合计: <strong>¥{{ laborCostTotal.toFixed(1) }} 万元</strong></div>

          <!-- 六、测试费用 -->
          <el-divider content-position="left">六、测试费用</el-divider>
          <el-table :data="testCostTable" border size="small" class="section-table">
            <el-table-column prop="stage" label="阶段" width="80" />
            <el-table-column label="天数" width="100">
              <template #default="{ row }">
                <el-input-number v-model="row.days" :min="0" :step="1" size="small" controls-position="right" style="width:100%" />
              </template>
            </el-table-column>
            <el-table-column label="单价(W)" width="120">
              <template>
                <span>0.110</span>
              </template>
            </el-table-column>
            <el-table-column label="合计(W)" width="120">
              <template #default="{ row }">
                {{ (row.days * row.unit_price).toFixed(2) }}
              </template>
            </el-table-column>
          </el-table>
          <div class="cost-summary">测试费用合计: <strong>¥{{ testCostTotal.toFixed(2) }} 万元</strong></div>
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
            <div class="team-toolbar">
              <el-button type="primary" size="small" @click="addTeamRow">添加成员</el-button>
              <span class="team-hint">选择角色后自动筛选对应人员，选择人员后自动填充部门</span>
            </div>
            <el-table :data="teamTable" border size="small" class="section-table">
              <el-table-column label="角色" width="140">
                <template #default="{ row, $index }">
                  <el-select v-model="row.role" size="small" placeholder="选择角色" @change="onTeamRoleChange($index)" style="width:100%">
                    <el-option v-for="r in teamRoles" :key="r.value" :label="r.label" :value="r.value" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="姓名" min-width="140">
                <template #default="{ row, $index }">
                  <el-select v-model="row.user_id" size="small" placeholder="选择人员" filterable @change="onTeamUserChange($index)" style="width:100%">
                    <el-option
                      v-for="u in getUsersByRole(row.role)"
                      :key="u.id"
                      :label="u.full_name"
                      :value="u.id"
                    />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="部门" width="120">
                <template #default="{ row }">
                  <el-input v-model="row.department" size="small" disabled />
                </template>
              </el-table-column>
              <el-table-column label="核心职责" min-width="180">
                <template #default="{ row }">
                  <el-input v-model="row.responsibility" size="small" placeholder="核心职责描述" />
                </template>
              </el-table-column>
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
import { ElMessage } from 'element-plus'
import { Link } from '@element-plus/icons-vue'
import api from '../../api'

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
  voltage_freq?: string; ip_ownership?: string; project_duration?: string
  dev_category?: string; project_origin?: string
  start_date?: string; required_date?: string; sample_qty?: number
  annual_planning_ref?: string; is_draft?: boolean
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
  test_costs?: string; labor_costs?: string
  core_performance?: string; safety_compliance?: string
  accessory_config?: string; feature_config?: string
  team_members?: string
  approval_status?: string  // 审批状态: pending/approved/rejected
}
interface CustomerReqRow { category: string; description: string; source: string; tech_impact: string; market_impact: string }
interface CorePerfRow { param_name: string; target_value: string; aux_competitor: string; tcl_competitor: string }
interface SafetyComplianceRow { standard: string; applicable_market: string; key_requirement: string; verification_method: string; involved_parts: string; cert_cycle: string; remark: string }
interface ConfigRow { name: string; selection: string; _original?: string }
interface DevCostRow { item: string; budget: number; remark: string; linked: boolean }
interface MoldCostRow { unit_type: string; category: string; qty: number; total: number }
interface ProtoCostRow { stage: string; qty: number; unit_cost: number }
interface LaborCostRow { module: string; people_count: number; monthly_salary: number; months: number; occupancy_rate: number }
interface TestCostRow { stage: string; days: number; unit_price: number }
interface TeamMemberRow { role: string; user_id: number | null; department: string; responsibility: string }
interface TeamRole { label: string; value: string; sys_role: string }
interface UserInfo { id: number; username: string; full_name: string; department: string; position: string; role: string }

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

// 产品/项目
const products = ref<Product[]>([])
const myProjects = ref<ProjectItem[]>([])

// 看板统计
const stats = computed(() => {
  const items = myProjects.value
  const running = items.filter(p => p.status === 'running').length
  const completed = items.filter(p => p.status === 'completed').length
  const overdue = items.filter(p => p.status === 'overdue').length
  return { running, completed, overdue }
})

// 展开的项目ID
const expandedProjectId = ref<number | null>(null)

// 抽屉
const drawerVisible = ref(false)
const activeTab = ref('overview')
const draftId = ref<number | null>(null)
const savingDraft = ref(false)
const submitting = ref(false)

// Tab 校验状态
const tabStatus = reactive<Record<string, { valid: boolean; errors: string[] }>>({
  overview: { valid: false, errors: [] },
  market: { valid: false, errors: [] },
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
  start_date: null, target_end_date: null,
  ip_ownership: '', project_duration: '',
  dev_category: '', project_origin: '', other_requirements: '',
  background_basis: '', overall_goal: '', tech_goal: '', cost_goal: '',
  sales_goal: '', cert_goal: '', schedule_goal: '', patent_goal: '', other_goals: '',
  sample_qty: undefined as number | undefined,
  sample_required_date: null as string | null,
  deliverables: '',
  main_capacity: '', target_price: '', energy_efficiency_req: '', cert_requirements: '',
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
})

// 项目群选项
const programOptions = ref<{ id: number; name: string; code: string }[]>([])

// 团队
const teamRoles = ref<TeamRole[]>([])
const allTeamUsers = ref<UserInfo[]>([])

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
  { param_name: '制冷量(W)', target_value: '', aux_competitor: '', tcl_competitor: '' },
  { param_name: 'CSPF(W/W)', target_value: '', aux_competitor: '', tcl_competitor: '' },
  { param_name: '能效等级', target_value: '', aux_competitor: '', tcl_competitor: '' },
  { param_name: '容差(%)', target_value: '', aux_competitor: '', tcl_competitor: '' },
  { param_name: '出风量(m³/h)', target_value: '', aux_competitor: '', tcl_competitor: '' },
  { param_name: '噪音dB(A)(内/外)', target_value: '', aux_competitor: '', tcl_competitor: '' },
  { param_name: '尺寸(mm)(内/外)', target_value: '', aux_competitor: '', tcl_competitor: '' },
  { param_name: '电压/频率', target_value: '', aux_competitor: '', tcl_competitor: '' },
  { param_name: '制冷剂', target_value: '', aux_competitor: '', tcl_competitor: '' },
  { param_name: '充注量(g)', target_value: '', aux_competitor: '', tcl_competitor: '' },
  { param_name: '装柜量(20GP)', target_value: '', aux_competitor: '', tcl_competitor: '' },
  { param_name: '制热量(W)', target_value: '', aux_competitor: '', tcl_competitor: '' },
  { param_name: 'HSPF(W/W)', target_value: '', aux_competitor: '', tcl_competitor: '' },
])

// Tab 3 表格: 安全与合规要求 (3行)
const safetyComplianceTable = reactive<SafetyComplianceRow[]>([
  { standard: 'IEC 60335-2-40', applicable_market: '全球', key_requirement: '电气安全', verification_method: '型式试验', involved_parts: '电控组件', cert_cycle: '3个月', remark: '' },
  { standard: 'CE EMC Directive', applicable_market: '欧盟', key_requirement: '电磁兼容', verification_method: 'EMC测试', involved_parts: 'PCB/电机', cert_cycle: '2个月', remark: '' },
  { standard: 'SASO 2663', applicable_market: '沙特', key_requirement: '能效+安全', verification_method: '第三方测试', involved_parts: '整机', cert_cycle: '4个月', remark: '' },
])

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

// Tab 4 表格: 模具/工装费用 (6行)
const moldCostTable = reactive<MoldCostRow[]>([
  { unit_type: '内机', category: '钣金', qty: 0, total: 0 },
  { unit_type: '内机', category: '注塑', qty: 0, total: 0 },
  { unit_type: '外机', category: '钣金', qty: 0, total: 0 },
  { unit_type: '外机', category: '注塑', qty: 0, total: 0 },
  { unit_type: '其他', category: '翅片', qty: 0, total: 0 },
  { unit_type: '工装', category: '工装', qty: 0, total: 0 },
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

// ═══════════════════════════════════════════════
// Tab 5 表格: 团队人员 (14行)
// ═══════════════════════════════════════════════
const teamTable = reactive<TeamMemberRow[]>([
  { role: '项目经理', user_id: null, department: '', responsibility: '全面负责项目管理' },
  { role: '系统工程师', user_id: null, department: '', responsibility: '系统方案设计' },
  { role: '系统工程师', user_id: null, department: '', responsibility: '性能匹配调试' },
  { role: '结构工程师', user_id: null, department: '', responsibility: '室内机结构设计' },
  { role: '结构工程师', user_id: null, department: '', responsibility: '室外机结构设计' },
  { role: '结构工程师', user_id: null, department: '', responsibility: '面板及外观设计' },
  { role: '电控工程师', user_id: null, department: '', responsibility: '硬件电路设计' },
  { role: '电控工程师', user_id: null, department: '', responsibility: '软件控制逻辑' },
  { role: '电气工程师', user_id: null, department: '', responsibility: '电气系统设计' },
  { role: '电气工程师', user_id: null, department: '', responsibility: '线束及接插件' },
  { role: '工艺工程师', user_id: null, department: '', responsibility: '生产工艺规划' },
  { role: 'IQC工程师', user_id: null, department: '', responsibility: '来料质量控制' },
  { role: '采购工程师', user_id: null, department: '', responsibility: '零部件采购' },
  { role: '项目管理员', user_id: null, department: '', responsibility: '项目文档及进度跟踪' },
])

// ═══════════════════════════════════════════════
// 计算属性
// ═══════════════════════════════════════════════

// 系统配置（从API加载，admin可修改）
const systemConfig = ref<Record<string, any>>({})

const protoUnitCostFromConfig = computed(() => {
  const raw = systemConfig.value.proto_unit_cost
  if (raw) {
    try { return JSON.parse(raw) as Record<string, number> } catch {}
  }
  // fallback
  return { '7K': 0.075, '9K': 0.095, '12K': 0.105, '18K': 0.142, '24K': 0.178 }
})

// 样机单套费用 - 按冷量段查表 (万元)
const prototypeUnitCost = computed(() => {
  const cr = projectForm.capacity_range
  if (!cr) return 0
  const map = protoUnitCostFromConfig.value
  // Try to match any key contained in capacity_range
  for (const [key, val] of Object.entries(map)) {
    if (cr.toUpperCase().includes(key.toUpperCase())) return Number(val)
  }
  return 0.1 // default
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

// 人工费用合计
const laborCostTotal = computed(() =>
  laborCostTable.reduce((sum, r) => sum + (r.people_count || 0) * (r.monthly_salary || 0) * (r.months || 0) * ((r.occupancy_rate || 100) / 100), 0)
)

// 测试费用合计
const testCostTotal = computed(() =>
  testCostTable.reduce((sum, r) => sum + (r.days || 0) * (r.unit_price || 0), 0)
)

const certCost = computed(() => {
  const cert = (projectForm.cert_requirements || '').toUpperCase()
  const costMap = (() => {
    const raw = systemConfig.value.cert_cost
    if (raw) {
      try { return JSON.parse(raw) as Record<string, number> } catch {}
    }
    return { 'UL': 20, 'CE': 3, 'default': 3 }
  })()
  let cost = 0
  if (cert.includes('UL')) cost += (costMap['UL'] || 20)
  if (cert.includes('CE')) cost += (costMap['CE'] || 3)
  if (!cert.includes('UL') && !cert.includes('CE') && cert.trim()) cost = (costMap['default'] || 3)
  return cost
})

// 说明自动生成
// 每行说明独立刷新
function refreshDevCostRemarks() {
  // [0] 工装及模具费用
  const moldModules = moldCostTable.filter(r => r.total > 0)
  if (moldModules.length > 0) {
    devCostTable[0].remark = '模具：' + moldModules.map(r => `${r.category}${r.qty}套${r.total.toFixed(1)}W`).join(' / ')
  } else {
    devCostTable[0].remark = ''
  }
  // [1] 认证费用
  const cert = (projectForm.cert_requirements || '').toUpperCase()
  const cost = certCost.value
  if (cert && cost > 0) {
    const certParts: string[] = []
    if (cert.includes('UL')) certParts.push(`UL ${cost}W`)
    else if (cert.includes('CE')) certParts.push(`CE ${cost}W`)
    else certParts.push(`${projectForm.cert_requirements} ${cost}W`)
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
  return sumFirst7
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

// 自动生成项目名称: 目标市场+能效+能力段+制冷剂+产品类型
const autoProjectName = computed(() => {
  const parts: string[] = []
  if (projectForm.target_market) parts.push(projectForm.target_market)
  if (projectForm.energy_efficiency_req) parts.push(projectForm.energy_efficiency_req)
  if (projectForm.capacity_range) parts.push(projectForm.capacity_range)
  if (projectForm.refrigerant) parts.push(projectForm.refrigerant)
  if (projectForm.product_type) parts.push(projectForm.product_type)
  return parts.length > 0 ? parts.join('-') + ' 新品立项' : '（自动生成：请填写相关字段）'
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

// capacity_range → 核心性能表制冷量行
watch(() => projectForm.capacity_range, (val) => {
  if (val && corePerfTable.length > 0) {
    corePerfTable[0].target_value = val
  }
})

// refrigerant → 核心性能表制冷剂行
watch(() => projectForm.refrigerant, (val) => {
  if (val && corePerfTable.length > 8) {
    corePerfTable[8].target_value = val
  }
})

// voltage_freq → 核心性能表电压行
watch(() => projectForm.voltage_freq, (val) => {
  if (val && corePerfTable.length > 7) {
    corePerfTable[7].target_value = val
  }
})

// budget/fob_price联动 → 认证费用联动 (certCost)
watch(certCost, (val) => {
  if (devCostTable.length > 1 && devCostTable[1].linked) {
    devCostTable[1].budget = val
  }
})

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

// Tab 切换时自动校验当前Tab
watch(activeTab, () => {
  validateCurrentTab()
})

// ═══════════════════════════════════════════════
// Tab 校验函数
// ═══════════════════════════════════════════════

function validateOverview(): void {
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
  tabStatus.overview.valid = errs.length === 0
  tabStatus.overview.errors = errs
}

function validateMarket(): void {
  const errs: string[] = []
  const hasContent = customerReqTable.some(row =>
    row.category || row.description || row.source || row.tech_impact || row.market_impact
  )
  if (!hasContent) errs.push('客户关键需求至少填写一行')
  tabStatus.market.valid = errs.length === 0
  tabStatus.market.errors = errs
}

function validateTechnical(): void {
  const errs: string[] = []
  const hasTargetValue = corePerfTable.some(row => row.target_value)
  if (!hasTargetValue) errs.push('核心性能参数至少一行填写目标值')
  if (safetyComplianceTable.length === 0) errs.push('安全合规标准未加载，请先选择目标市场')
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
  const hasUser = teamTable.some(row => row.user_id != null)
  if (!hasUser) errs.push('团队至少选择一名成员')
  if (teamTable.length === 0) errs.push('团队表格不能为空')
  tabStatus.team.valid = errs.length === 0
  tabStatus.team.errors = errs
}

function validateAllTabs(): boolean {
  validateOverview()
  validateMarket()
  validateTechnical()
  validateCost()
  validateTeam()
  return Object.values(tabStatus).every(t => t.valid)
}

function validateCurrentTab(): void {
  const tab = activeTab.value
  const validators: Record<string, () => void> = {
    overview: validateOverview,
    market: validateMarket,
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
    paused: 'warning', cancelled: 'danger', draft: 'info', overdue: 'danger'
  }
  return map[status] || 'info'
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    planning: '规划中', running: '进行中', completed: '已完成',
    paused: '暂停', cancelled: '已取消', draft: '草稿', overdue: '超期'
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
// 团队按角色过滤
// ═══════════════════════════════════════════════

function getUsersByRole(role: string): UserInfo[] {
  if (!role) return allTeamUsers.value
  const roleMap: Record<string, string> = {}
  teamRoles.value.forEach(r => { roleMap[r.value] = r.sys_role })
  const sysRole = roleMap[role]
  if (!sysRole) return allTeamUsers.value
  return allTeamUsers.value.filter(u => u.role === sysRole)
}

// ═══════════════════════════════════════════════
// 年度规划相关
// ═══════════════════════════════════════════════

function openPlanDialog() {
  planForm.name = ''
  planForm.year = ''
  planForm.description = ''
  planForm.doc_ref = ''
  showPlanDialog.value = true
}

async function savePlanItem() {
  if (!planForm.name.trim()) {
    ElMessage.warning('请输入规划名称')
    return
  }
  savingPlan.value = true
  try {
    await api.post('/pm/planning-items', {
      name: planForm.name,
      year: planForm.year,
      description: planForm.description,
      doc_ref: planForm.doc_ref || annualPlanningRef.value,
    })
    ElMessage.success('年度规划项创建成功')
    showPlanDialog.value = false
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
  activeTab.value = 'overview'
  drawerVisible.value = true
}

function resetForm() {
  draftId.value = null
  const empty: Record<string, any> = {
    program_id: null, leader_id: null,
    product_type: '', target_market: '', climate_zone: '', refrigerant: '',
    customer_name: '', capacity_range: '', voltage_freq: '',
    start_date: null, target_end_date: null,
    ip_ownership: '', project_duration: '',
    dev_category: '', project_origin: '', other_requirements: '',
    background_basis: '', overall_goal: '', tech_goal: '', cost_goal: '',
    sales_goal: '', cert_goal: '', schedule_goal: '', patent_goal: '', other_goals: '',
    sample_qty: undefined,
    sample_required_date: null,
    deliverables: '',
    main_capacity: '', target_price: '', energy_efficiency_req: '', cert_requirements: '',
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
  moldCostTable.forEach(r => { r.qty = 0 })
  protoCostTable.forEach(r => { r.qty = r.stage === 'P2' ? 20 : r.stage === 'P1-1' || r.stage === 'P1-2' ? 10 : 5 })
  laborCostTable.forEach(r => { r.people_count = 1; r.monthly_salary = 1.5; r.months = 6; r.occupancy_rate = 100 })
  testCostTable.forEach(r => { r.days = 10; r.unit_price = 0.11 })
  // Reset tab validation status
  Object.keys(tabStatus).forEach(key => {
    tabStatus[key].valid = false
    tabStatus[key].errors = []
  })
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
  projectForm.start_date = draft.start_date || null
  projectForm.target_end_date = draft.target_end_date || null
  projectForm.ip_ownership = draft.ip_ownership || ''
  projectForm.dev_category = draft.dev_category || ''
  projectForm.project_origin = draft.project_origin || ''
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
        parsed.forEach((item: any, i: number) => {
          if (moldCostTable[i]) moldCostTable[i].qty = item.qty ?? 0
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
        parsed.forEach((item: TeamMemberRow) => teamTable.push({ ...item }))
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
  // 恢复人工费用
  if (draft.labor_costs) {
    try {
      const parsed = JSON.parse(draft.labor_costs)
      if (Array.isArray(parsed)) {
        parsed.forEach((item: any) => {
          const row = laborCostTable.find(r => r.module === item.module)
          if (row) {
            row.people_count = item.people_count ?? row.people_count
            row.monthly_salary = item.monthly_salary ?? row.monthly_salary
            row.months = item.months ?? row.months
            row.occupancy_rate = item.occupancy_rate ?? row.occupancy_rate
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
          target_value: item.target_value || '',
          aux_competitor: item.aux_competitor || '',
          tcl_competitor: item.tcl_competitor || ''
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
    start_date: f.start_date || undefined,
    target_end_date: f.target_end_date || undefined,
    ip_ownership: f.ip_ownership || undefined,
    project_duration: autoProjectDuration.value !== '请选择起止日期' ? autoProjectDuration.value : undefined,
    dev_category: f.dev_category || undefined,
    project_origin: f.project_origin || undefined,
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
    accessory_config: JSON.stringify(accessoryConfigTable.map(({ name, selection }) => ({ name, selection }))),
    feature_config: JSON.stringify(featureConfigTable.map(({ name, selection }) => ({ name, selection }))),
    dev_cost_items: JSON.stringify(devCostTable.map(r => ({ item: r.item, budget: r.budget, remark: r.remark, linked: r.linked }))),
    mold_costs: JSON.stringify(moldCostTable.map(r => ({ unit_type: r.unit_type, category: r.category, qty: r.qty, total: r.total }))),
    prototype_costs_detail: JSON.stringify(protoCostTable.map(r => ({ stage: r.stage, qty: r.qty, unit_cost: r.unit_cost }))),
    labor_costs: JSON.stringify(laborCostTable.map(r => ({ module: r.module, people_count: r.people_count, monthly_salary: r.monthly_salary, months: r.months, occupancy_rate: r.occupancy_rate }))),
    test_costs: JSON.stringify(testCostTable.map(r => ({ stage: r.stage, days: r.days, unit_price: r.unit_price }))),
    team_members: JSON.stringify(teamTable.filter(t => t.user_id != null).map(t => ({
      role: t.role, user_id: t.user_id, department: t.department, responsibility: t.responsibility
    }))),
  }
}

async function saveDraft() {
  savingDraft.value = true
  try {
    const payload = buildProjectPayload()
    if (draftId.value) {
      await api.put('/pm/proposals/draft', { ...payload, id: draftId.value })
      ElMessage.success('草稿已更新')
    } else {
      const res = await api.post('/pm/proposals/draft', payload)
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
    ElMessage.warning('请完善产品类型、目标市场、能力段、制冷剂、能效要求以生成项目名称')
    activeTab.value = 'overview'
    return
  }

  // 全Tab校验
  const allValid = validateAllTabs()
  if (!allValid) {
    // 找到第一个不通过的Tab并切换
    const tabOrder = ['overview', 'market', 'technical', 'cost', 'team']
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
    const payload = buildProjectPayload()
    // Always submit via /pm/proposals/submit — backend handles both new & draft
    if (draftId.value) {
      payload.id = draftId.value
    }
    await api.post('/pm/proposals/submit', payload)
    ElMessage.success('已提交审批，等待审批人审核')
    drawerVisible.value = false
    await fetchWorkspaceData()
  } catch {
    // handled by interceptor
  } finally {
    submitting.value = false
  }
}

// ═══════════════════════════════════════════════
// 表格增删行函数
// ═══════════════════════════════════════════════

function addCustomerReqRow() {
  customerReqTable.push({ category: '', description: '', source: '', tech_impact: '', market_impact: '' })
}
function removeCustomerReqRow(index: number) { customerReqTable.splice(index, 1) }

function addCorePerfRow() {
  corePerfTable.push({ param_name: '', target_value: '', aux_competitor: '', tcl_competitor: '' })
}
function removeCorePerfRow(index: number) { corePerfTable.splice(index, 1) }

function addTeamRow() {
  teamTable.push({ role: '', user_id: null, department: '', responsibility: '' })
}
function removeTeamRow(index: number) { teamTable.splice(index, 1) }

function onTeamRoleChange(index: number) {
  const row = teamTable[index]
  if (!row) return
  row.user_id = null
  row.department = ''
}

function onTeamUserChange(index: number) {
  const row = teamTable[index]
  if (!row || row.user_id == null) return
  const user = allTeamUsers.value.find(u => u.id === row.user_id)
  if (user) {
    row.department = user.department || ''
  }
}

// ═══════════════════════════════════════════════
// API调用
// ═══════════════════════════════════════════════

const ALL_KB_CATEGORIES = ['market', 'product_type', 'capacity', 'voltage', 'ip_ownership', 'main_capacity', 'cert']

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
        target_value: item.target_value || '',
        aux_competitor: item.aux_competitor || '',
        tcl_competitor: item.tcl_competitor || ''
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
    planningItems.value = data.planning_items || []
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
    const res = await api.get('/admin/config')
    if (res.data?.data) {
      systemConfig.value = res.data.data
    }
  } catch { /* use defaults */ }
}

// ═══════════════════════════════════════════════
// 生命周期
// ═══════════════════════════════════════════════

onMounted(async () => {
  try {
    await fetchWorkspaceData()
    await fetchKbOptions()
    await fetchTeamRoles()
    await fetchAllTeamUsers()
    await fetchPrograms()
    await fetchExchangeRate()
    await fetchSystemConfig()
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

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 8px;
}
</style>
