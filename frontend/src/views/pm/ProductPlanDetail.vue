<template>
<div class="plan-detail">
<div class="detail-header">
  <el-button text @click="$router.push('/product-plans')">← 返回策划列表</el-button>
  <h2>{{ plan?.name || '加载中...' }}</h2>
  <el-tag v-if="plan" :type="stageTagType(plan.status)" size="small">{{ stageLabel(plan.status) }}</el-tag>
  <el-button v-if="canQuickSubmit" type="warning" size="small" @click="quickSubmit" :loading="submittingQuick">📮 一键提交审批</el-button>
</div>

<!-- PlanStatusGuide: 5子表完成度引导条 -->
<div v-if="plan" class="plan-status-guide">
<div v-for="(tab, i) in subTabs" :key="tab.key" class="guide-step" :class="{ active: activeTab === tab.key, done: tabStatus[tab.key] === 'done' }" @click="guideClick(tab.key, i)">
<div class="guide-step-num">{{ tabStatus[tab.key] === 'done' ? '✓' : i + 1 }}</div>
<div class="guide-step-label">{{ tab.label }}</div>
<el-tag size="small" :type="tabStatus[tab.key] === 'done' ? 'success' : tabStatus[tab.key] === 'progress' ? 'warning' : 'info'" effect="plain">{{ tabStatus[tab.key] === 'done' ? '已完成' : tabStatus[tab.key] === 'progress' ? '进行中' : '未开始' }}</el-tag>
</div>
</div>

<!-- ─── 桌面端: 5个子表 Tab ─── -->
<template v-if="!isMobile">
<el-tabs v-model="activeTab" type="border-card" tab-position="left" v-if="plan">
<!-- 项目概述 -->
<el-tab-pane name="initiation">
  <template #label>
    <span>项目概述 <el-tag size="small" type="primary" v-if="initiationVersion > 0">v{{initiationVersion}}</el-tag></span>
  </template>
<el-form :model="editForm" label-width="100" size="small" class="quick-edit">
<el-row :gutter="12">
<el-col :span="8"><el-form-item label="策划名称"><el-input v-model="editForm.name" /></el-form-item></el-col>
<el-col :span="8"><el-form-item label="产品系列"><el-input v-model="editForm.series" /></el-form-item></el-col>
<el-col :span="8"><el-form-item label="目标市场"><el-select v-model="editForm.market" filterable clearable style="width:100%"><el-option v-for="m in marketOptions" :key="m.name" :label="m.name" :value="m.name" /></el-select><el-button size="small" type="primary" link @click="goCompetitor" style="margin-left:8px">📊 查看同类竞品</el-button></el-form-item></el-col>
</el-row>
<el-row :gutter="12">
<el-col :span="8"><el-form-item label="竞品关联"><el-input-number v-model="editForm.competitor_id" :min="0" style="width:100%" /></el-form-item></el-col>
<el-col :span="4"><el-form-item><el-button type="primary" size="small" @click="saveQuickEdit" :loading="saving">保存</el-button></el-form-item></el-col>
</el-row>
</el-form>
<el-divider />
<el-form :model="initiationForm" label-width="140" size="small">
<el-row :gutter="16">
<el-col :span="12"><el-form-item label="立项背景"><el-input v-model="initiationForm.background" type="textarea" :rows="2" /></el-form-item></el-col>
<el-col :span="12"><el-form-item label="产品类型"><el-input v-model="initiationForm.type" /></el-form-item></el-col>
</el-row>
<el-row :gutter="16">
<el-col :span="6"><el-form-item label="制冷剂"><el-input v-model="initiationForm.refrigerant" /></el-form-item></el-col>
<el-col :span="6"><el-form-item label="容量"><el-input v-model="initiationForm.capacity" /></el-form-item></el-col>
<el-col :span="6"><el-form-item label="电压"><el-input v-model="initiationForm.voltage" /></el-form-item></el-col>
<el-col :span="6"><el-form-item label="能效"><el-input v-model="initiationForm.energy" /></el-form-item></el-col>
</el-row>
<el-row :gutter="16">
<el-col :span="6"><el-form-item label="开发类别"><el-input v-model="initiationForm.dev_category" /></el-form-item></el-col>
<el-col :span="6"><el-form-item label="产地"><el-input v-model="initiationForm.origin" /></el-form-item></el-col>
<el-col :span="6"><el-form-item label="开发周期(月)"><el-input-number v-model="initiationForm.duration" :min="0" style="width:100%" /></el-form-item></el-col>
<el-col :span="6"><el-form-item label="IP等级"><el-input v-model="initiationForm.ip" /></el-form-item></el-col>
</el-row>
<el-row :gutter="16">
<el-col :span="12"><el-form-item label="项目目标"><el-input v-model="initiationForm.goals" type="textarea" :rows="2" /></el-form-item></el-col>
<el-col :span="12"><el-form-item label="交付物"><el-input v-model="initiationForm.deliverables" type="textarea" :rows="2" /></el-form-item></el-col>
</el-row>
<el-form-item label="样品数量"><el-input-number v-model="initiationForm.sample_qty" :min="0" style="width:200px" /></el-form-item>
<el-form-item><el-button type="primary" size="small" @click="saveInitiation" :loading="savingInitiation">保存</el-button></el-form-item>
</el-form>
<el-divider>BOM规划</el-divider>
<div class="bom-types">
<div v-for="bt in bomTypes" :key="bt.key" class="bom-card">
<div class="bom-icon">{{ bt.icon }}</div>
<div class="bom-name">{{ bt.label }}</div>
<el-tag size="small" :type="bt.status === 'active' ? 'warning' : 'info'" effect="plain">{{ bt.status === 'active' ? '待生成' : '未开始' }}</el-tag>
</div>
</div>
</el-tab-pane>

<!-- 市场与客户 -->
<el-tab-pane name="market">
  <template #label>
    <span>市场与客户 <el-tag size="small" type="primary" v-if="marketVersion > 0">v{{marketVersion}}</el-tag></span>
  </template>
<el-form :model="marketForm" label-width="180" size="small">
<el-form-item label="主要容量"><el-input v-model="marketForm.main_capacity" /></el-form-item>
<el-form-item label="能效要求"><el-input v-model="marketForm.energy_efficiency" /><div v-if="marketEnergyMap[editForm.market]" class="energy-standard-hint">当前市场标准: {{ marketEnergyMap[editForm.market]?.label }} ({{ marketEnergyMap[editForm.market]?.key }})</div></el-form-item>
<el-form-item label="认证要求"><el-input v-model="marketForm.cert_requirements" type="textarea" :rows="2" /></el-form-item>
<el-form-item label="目标价格"><el-input-number v-model="marketForm.target_price" :min="0" :precision="2" style="width:200px" /></el-form-item>
<el-form-item label="客户需求"><el-input v-model="marketForm.customer_requirements" type="textarea" :rows="3" /></el-form-item>
<el-form-item><el-button type="primary" size="small" @click="saveMarket" :loading="savingMarket">保存</el-button></el-form-item>
</el-form>
</el-tab-pane>

<!-- 技术要求 -->
<el-tab-pane name="techSpec">
  <template #label>
    <span>技术要求 <el-tag size="small" type="primary" v-if="techSpecVersion > 0">v{{techSpecVersion}}</el-tag></span>
  </template>
<el-form :model="techSpecForm" label-width="180" size="small">
<el-form-item label="核心性能指标"><el-input v-model="techSpecForm.core_performance" type="textarea" :rows="3" placeholder="制冷量、制热量、COP等" /></el-form-item>
<el-form-item label="安全合规要求"><el-input v-model="techSpecForm.safety_compliance" type="textarea" :rows="3" placeholder="CE、UL、CCC等" /></el-form-item>
<el-form-item label="可选配置"><el-input v-model="techSpecForm.optional_config" type="textarea" :rows="3" placeholder="WiFi模块、特殊面板等" /></el-form-item>
<el-form-item><el-button type="primary" size="small" @click="saveTechSpec" :loading="savingTechSpec">保存</el-button></el-form-item>
</el-form>
</el-tab-pane>

<!-- 成本核算 -->
<el-tab-pane label="成本核算" name="costingNew">
<div class="tab-toolbar"><el-button size="small" type="primary" @click="showCostDialog = true">+ 添加成本</el-button></div>
<el-table :data="costs" stripe border size="small" empty-text="暂无成本数据">
<el-table-column prop="item_name" label="成本项" min-width="120" />
<el-table-column prop="cost_type" label="类型" width="80"><template #default="{ row }"><el-tag size="small">{{ row.cost_type }}</el-tag></template></el-table-column>
<el-table-column prop="target_value" label="目标值" width="100" />
<el-table-column prop="actual_value" label="实际值" width="100" />
<el-table-column prop="currency" label="币种" width="70" />
<el-table-column prop="remark" label="备注" />
<el-table-column label="操作" width="60"><template #default="{ row }"><el-button link size="small" type="danger" @click="deleteCost(row)">删</el-button></template></el-table-column>
</el-table>

<!-- @deprecated 历史明细 — 展示 Initiation 中的旧成本JSON数据 -->
<div v-if="initiationCosts" class="history-costs">
  <el-divider content-position="left">📜 历史明细（立项旧数据）</el-divider>
  <el-descriptions :column="2" border size="small">
    <el-descriptions-item v-if="initiationCosts.dev_cost_items" label="研发费用">
      <pre class="cost-json">{{ formatCostJson(initiationCosts.dev_cost_items) }}</pre>
    </el-descriptions-item>
    <el-descriptions-item v-if="initiationCosts.mold_costs" label="模具费用">
      <pre class="cost-json">{{ formatCostJson(initiationCosts.mold_costs) }}</pre>
    </el-descriptions-item>
    <el-descriptions-item v-if="initiationCosts.prototype_costs_detail" label="样机费用">
      <pre class="cost-json">{{ formatCostJson(initiationCosts.prototype_costs_detail) }}</pre>
    </el-descriptions-item>
    <el-descriptions-item v-if="initiationCosts.test_costs" label="测试费用">
      <pre class="cost-json">{{ formatCostJson(initiationCosts.test_costs) }}</pre>
    </el-descriptions-item>
    <el-descriptions-item v-if="initiationCosts.cert_costs" label="认证费用">
      <pre class="cost-json">{{ formatCostJson(initiationCosts.cert_costs) }}</pre>
    </el-descriptions-item>
    <el-descriptions-item v-if="initiationCosts.labor_costs" label="人工费用">
      <pre class="cost-json">{{ formatCostJson(initiationCosts.labor_costs) }}</pre>
    </el-descriptions-item>
    <el-descriptions-item v-if="initiationCosts.economic_indicators" label="经济指标">
      <pre class="cost-json">{{ formatCostJson(initiationCosts.economic_indicators) }}</pre>
    </el-descriptions-item>
  </el-descriptions>
</div>
</el-tab-pane>

<!-- 团队 -->
<el-tab-pane name="team">
  <template #label>
    <span>团队 <el-tag size="small" type="primary" v-if="teamVersion > 0">v{{teamVersion}}</el-tag></span>
  </template>
<div class="tab-toolbar"><el-button size="small" type="primary" @click="showTeamDialog = true; teamDialogMode = 'add'">+ 添加成员</el-button></div>
<el-table :data="teamMembers" stripe border size="small" empty-text="暂无团队成员">
<el-table-column prop="member_name" label="姓名" min-width="100" />
<el-table-column prop="role_name" label="角色" width="120" />
<el-table-column prop="department" label="部门" width="120" />
<el-table-column prop="responsibility" label="职责" width="180" />
<el-table-column label="操作" width="120"><template #default="{ row }">
<el-button link size="small" type="primary" @click="editTeamMember(row)">编辑</el-button>
<el-button link size="small" type="danger" @click="deleteTeamMember(row)">删除</el-button>
</template></el-table-column>
</el-table>
</el-tab-pane>

<!-- 复盘 -->
<el-tab-pane name="review">
  <template #label>
    <span>复盘 <el-tag size="small" type="primary" v-if="reviewData?.id">v1</el-tag></span>
  </template>

  <!-- 已上市但无复盘的醒目提示 -->
  <el-alert
    v-if="plan?.status === 'released' && !reviewData?.id"
    title="⚠️ 该策划已「发布」，但尚未完成复盘"
    type="warning"
    :closable="false"
    show-icon
    style="margin-bottom:16px"
    description="请尽快补充复盘数据，完成产品全生命周期闭环。"
  />

  <el-form :model="reviewForm" label-width="160" size="small">
    <el-row :gutter="16">
      <el-col :span="8">
        <el-form-item label="复盘日期">
          <el-date-picker v-model="reviewForm.review_date" type="date" placeholder="选择复盘日期" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="实际成本总计">
          <el-input-number v-model="reviewForm.actual_cost_total" :min="0" :precision="2" style="width:100%" />
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="实际上市日期">
          <el-date-picker v-model="reviewForm.actual_launch_date" type="date" placeholder="选择实际上市日期" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
      </el-col>
    </el-row>

    <el-form-item label="市场反馈">
      <el-input v-model="reviewForm.market_feedback" type="textarea" :rows="3" placeholder="市场反馈信息" />
    </el-form-item>
    <el-form-item label="经验教训">
      <el-input v-model="reviewForm.lessons_learned" type="textarea" :rows="3" placeholder="总结的经验教训" />
    </el-form-item>
    <el-form-item label="综合评分">
      <el-rate v-model="reviewForm.overall_rating" :max="5" show-text :texts="['很差', '较差', '一般', '较好', '很好']" />
    </el-form-item>
    <el-form-item>
      <el-button type="primary" size="small" @click="saveReview" :loading="savingReview">
        {{ reviewData?.id ? '更新复盘' : '提交复盘' }}
      </el-button>
      <el-button v-if="reviewData?.id" size="small" @click="resetReviewForm">重置</el-button>
    </el-form-item>
  </el-form>

  <!-- 成本对比 -->
  <el-divider content-position="left">成本对比</el-divider>
  <el-descriptions :column="3" border size="small" style="margin-bottom:16px">
    <el-descriptions-item label="目标成本总计">
      <span style="font-weight:600">{{ formatCost(totalCostTarget) }}</span>
    </el-descriptions-item>
    <el-descriptions-item label="实际成本总计">
      <span style="font-weight:600">{{ reviewForm.actual_cost_total != null ? formatCost(reviewForm.actual_cost_total) : '待填写' }}</span>
    </el-descriptions-item>
    <el-descriptions-item label="偏差">
      <el-tag :type="costDeviationType" size="small">
        {{ costDeviationLabel }}
      </el-tag>
    </el-descriptions-item>
  </el-descriptions>

  <!-- 上市日期对比 -->
  <el-divider content-position="left">上市日期对比</el-divider>
  <el-descriptions :column="3" border size="small" style="margin-bottom:16px">
    <el-descriptions-item label="计划上市日期">
      <span>{{ plan?.planned_launch_date || '未设定' }}</span>
    </el-descriptions-item>
    <el-descriptions-item label="实际上市日期">
      <span>{{ reviewForm.actual_launch_date || '待填写' }}</span>
    </el-descriptions-item>
    <el-descriptions-item label="偏差天数">
      <el-tag :type="launchDeviationType" size="small">
        {{ launchDeviationLabel }}
      </el-tag>
    </el-descriptions-item>
  </el-descriptions>

  <!-- ========== P5 知识沉淀 ========== -->
  <el-divider content-position="left">📚 知识沉淀</el-divider>
  <div style="margin-bottom:12px">
    <el-button size="small" type="primary" @click="showKnowledgeDialog = true">+ 沉淀经验到知识库</el-button>
  </div>
  <div v-if="knowledgeList.length === 0" style="text-align:center;padding:24px 0;color:#909399;font-size:13px">
    暂无关联知识。点击上方按钮将复盘经验沉淀到知识库。
  </div>
  <el-table v-else :data="knowledgeList" stripe border size="small" empty-text="暂无关联知识">
    <el-table-column prop="title" label="知识标题" min-width="160">
      <template #default="{ row }">
        <el-link type="primary" @click="goToKnowledge(row)">{{ row.title }}</el-link>
      </template>
    </el-table-column>
    <el-table-column prop="category" label="分类" width="120">
      <template #default="{ row }"><el-tag size="small">{{ row.category }}</el-tag></template>
    </el-table-column>
    <el-table-column prop="content" label="内容摘要" min-width="240">
      <template #default="{ row }">
        <span class="knowledge-summary">{{ row.content?.substring(0, 80) }}{{ row.content?.length > 80 ? '...' : '' }}</span>
      </template>
    </el-table-column>
    <el-table-column prop="created_by" label="创建人" width="100" />
    <el-table-column prop="created_at" label="创建时间" width="160" />
  </el-table>
</el-tab-pane>

<!-- 关联项目 -->
<el-tab-pane label="关联项目" name="projectLinks">
  <div v-if="loadingProjects" style="text-align:center;padding:40px;color:#909399">
    <span style="font-size:32px">⏳</span>
    <p style="margin-top:12px">加载项目详情...</p>
  </div>
  <div v-else-if="projectDetails.length === 0" class="project-empty">
    <el-empty description="暂无关联项目" />
  </div>
  <div v-else v-for="proj in projectDetails" :key="proj.id" class="project-link-card">
    <el-divider v-if="projectDetails.length > 1 && proj !== projectDetails[0]" content-position="left" />
    <!-- 项目摘要 -->
    <h4 class="project-section-title">📋 项目摘要</h4>
    <el-descriptions :column="2" border size="small">
      <el-descriptions-item label="项目编号">{{ proj.code }}</el-descriptions-item>
      <el-descriptions-item label="项目名称">
        <el-link type="primary" @click="$router.push(`/projects/${proj.id}`)">{{ proj.name }}</el-link>
      </el-descriptions-item>
      <el-descriptions-item label="项目等级">
        <el-tag :type="classTagType(proj.project_class)" size="small">{{ proj.project_class }}级</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="状态">
        <el-tag :type="projectStatusTagType(proj.status)" size="small">{{ projectStatusLabel(proj.status) }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="项目经理">{{ proj.owner || '未指定' }}</el-descriptions-item>
    </el-descriptions>

    <!-- 门禁进度 -->
    <h4 class="project-section-title" style="margin-top:24px">🚧 门禁进度</h4>
    <el-steps :active="gateActiveStep(proj)" finish-status="success" simple>
      <el-step
        v-for="g in visibleGates(proj)"
        :key="g.gate_code"
        :title="g.gate_code"
        :description="g.gate_name"
        :status="gateStatus(g)"
      />
    </el-steps>

    <!-- 成本对比 -->
    <h4 class="project-section-title" style="margin-top:24px">💰 成本对比</h4>
    <el-descriptions :column="3" border size="small">
      <el-descriptions-item label="策划目标成本">
        <span style="font-weight:600">{{ formatCost(totalTargetCost) }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="项目实际成本">
        <span style="font-weight:600">{{ formatCost(totalActualCost) }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="对比结果">
        <el-tag :type="costCompareType(totalTargetCost, totalActualCost)" size="small">
          {{ costCompareLabel(totalTargetCost, totalActualCost) }}
        </el-tag>
      </el-descriptions-item>
    </el-descriptions>
  </div>
</el-tab-pane>
</el-tabs>

<!-- 底部审批操作栏 -->
<div v-if="plan" class="approval-bar">
<div class="approval-info"><span class="approval-node">当前节点: {{ stageLabel(plan.status) }}</span><span class="approval-approver">审批人: {{ plan.approver || '待指定' }}</span></div>
<div class="approval-actions">
<el-button v-if="canAdvance" type="primary" size="small" @click="advancePlan">推进流程</el-button>
<el-button v-if="isApprovalStage" type="success" size="small" @click="approvePlan" :loading="approving">通过</el-button>
<el-button v-if="isApprovalStage" type="danger" size="small" @click="rejectPlan" :loading="rejecting">驳回</el-button>
<el-button v-if="canWithdraw" size="small" @click="withdrawPlan" :loading="withdrawing">撤回</el-button>
</div>
</div>
</template>

<!-- ─── 移动端: 5步分步表单 ─── -->
<template v-if="isMobile && plan">
<el-steps :active="mobileStep" finish-status="success" simple style="margin-bottom:12px;overflow-x:auto;">
<el-step v-for="(s, i) in mobileSteps" :key="i" :title="s.label" :status="stepStatus(s.key)" />
</el-steps>
<div class="mobile-step-form" style="padding-bottom:72px">
<!-- Step 0: 项目概述 -->
<div v-show="mobileStep === 0">
<h3 class="step-title">📄 项目概述</h3>
<el-form label-width="80" size="small">
<el-form-item label="策划名称"><el-input v-model="editForm.name" /></el-form-item>
<el-form-item label="产品系列"><el-input v-model="editForm.series" /></el-form-item>
<el-form-item label="目标市场"><el-select v-model="editForm.market" filterable clearable style="width:100%"><el-option v-for="m in marketOptions" :key="m.name" :label="m.name" :value="m.name" /></el-select><el-button size="small" type="primary" link @click="goCompetitor" style="margin-left:8px">📊 查看同类竞品</el-button></el-form-item>
<el-form-item label="竞品ID"><el-input-number v-model="editForm.competitor_id" :min="0" style="width:100%" /></el-form-item>
<el-divider />
<el-form-item label="立项背景"><el-input v-model="initiationForm.background" type="textarea" :rows="2" /></el-form-item>
<el-form-item label="产品类型"><el-input v-model="initiationForm.type" /></el-form-item>
<el-row :gutter="8"><el-col :span="12"><el-form-item label="制冷剂"><el-input v-model="initiationForm.refrigerant" /></el-form-item></el-col><el-col :span="12"><el-form-item label="容量"><el-input v-model="initiationForm.capacity" /></el-form-item></el-col></el-row>
<el-row :gutter="8"><el-col :span="12"><el-form-item label="电压"><el-input v-model="initiationForm.voltage" /></el-form-item></el-col><el-col :span="12"><el-form-item label="能效"><el-input v-model="initiationForm.energy" /></el-form-item></el-col></el-row>
<el-row :gutter="8"><el-col :span="12"><el-form-item label="开发类别"><el-input v-model="initiationForm.dev_category" /></el-form-item></el-col><el-col :span="12"><el-form-item label="产地"><el-input v-model="initiationForm.origin" /></el-form-item></el-col></el-row>
<el-row :gutter="8"><el-col :span="12"><el-form-item label="开发周期(月)"><el-input-number v-model="initiationForm.duration" :min="0" style="width:100%" /></el-form-item></el-col><el-col :span="12"><el-form-item label="IP等级"><el-input v-model="initiationForm.ip" /></el-form-item></el-col></el-row>
<el-form-item label="项目目标"><el-input v-model="initiationForm.goals" type="textarea" :rows="2" /></el-form-item>
<el-form-item label="交付物"><el-input v-model="initiationForm.deliverables" type="textarea" :rows="2" /></el-form-item>
<el-form-item label="样品数量"><el-input-number v-model="initiationForm.sample_qty" :min="0" style="width:100%" /></el-form-item>
</el-form>
</div>
<!-- Step 1: 市场与客户 -->
<div v-show="mobileStep === 1">
<h3 class="step-title">🎯 市场与客户</h3>
<el-form label-width="90" size="small">
<el-form-item label="主要容量"><el-input v-model="marketForm.main_capacity" /></el-form-item>
<el-form-item label="能效要求"><el-input v-model="marketForm.energy_efficiency" /><div v-if="marketEnergyMap[editForm.market]" class="energy-standard-hint">当前市场标准: {{ marketEnergyMap[editForm.market]?.label }} ({{ marketEnergyMap[editForm.market]?.key }})</div></el-form-item>
<el-form-item label="认证要求"><el-input v-model="marketForm.cert_requirements" type="textarea" :rows="2" /></el-form-item>
<el-form-item label="目标价格"><el-input-number v-model="marketForm.target_price" :min="0" :precision="2" style="width:100%" /></el-form-item>
<el-form-item label="客户需求"><el-input v-model="marketForm.customer_requirements" type="textarea" :rows="3" /></el-form-item>
</el-form>
</div>
<!-- Step 2: 技术要求 -->
<div v-show="mobileStep === 2">
<h3 class="step-title">⚡ 技术要求</h3>
<el-form label-width="90" size="small">
<el-form-item label="核心性能指标"><el-input v-model="techSpecForm.core_performance" type="textarea" :rows="3" /></el-form-item>
<el-form-item label="安全合规要求"><el-input v-model="techSpecForm.safety_compliance" type="textarea" :rows="3" /></el-form-item>
<el-form-item label="可选配置"><el-input v-model="techSpecForm.optional_config" type="textarea" :rows="3" /></el-form-item>
</el-form>
</div>
<!-- Step 3: 成本核算 -->
<div v-show="mobileStep === 3">
<h3 class="step-title">💰 成本核算</h3>
<el-table :data="costs" stripe border size="small" empty-text="暂无数据" style="margin-bottom:12px">
<el-table-column prop="item_name" label="成本项" min-width="100" />
<el-table-column prop="target_value" label="目标" width="80" />
<el-table-column prop="actual_value" label="实际" width="80" />
</el-table>
<el-button size="small" type="primary" @click="showCostDialog = true">+ 添加</el-button>
<!-- @deprecated 历史明细（移动端精简版） -->
<div v-if="initiationCosts" class="history-costs-mobile" style="margin-top:16px;padding:12px;background:#fafafa;border-radius:6px;border:1px solid #ebeef5;">
  <div style="font-size:13px;font-weight:600;margin-bottom:8px;color:#909399">📜 历史明细（立项旧数据）</div>
  <div v-for="(val, key) in filteredCostFields(initiationCosts)" :key="key" style="margin-bottom:6px;font-size:12px">
    <span style="color:#606266;font-weight:500">{{ costFieldLabel(key) }}:</span>
    <pre style="margin:4px 0 0;background:#fff;padding:6px;border-radius:4px;font-size:11px;white-space:pre-wrap;word-break:break-all;max-height:120px;overflow-y:auto;">{{ formatCostJson(val) }}</pre>
  </div>
</div>
</div>
<!-- Step 4: 团队 -->
<div v-show="mobileStep === 4">
<h3 class="step-title">👥 团队</h3>
<el-button size="small" type="primary" @click="showTeamDialog = true; teamDialogMode = 'add'" style="margin-bottom:12px">+ 添加成员</el-button>
<div v-if="teamMembers.length === 0" style="text-align:center;padding:24px 0;color:#909399">暂无团队成员</div>
<div v-for="m in teamMembers" :key="m.id" class="mobile-team-card">
<div class="team-card-row"><span class="team-card-name">{{ m.member_name }}</span><el-tag size="small">{{ m.role_name }}</el-tag></div>
<div class="team-card-detail">{{ m.department }} · {{ m.responsibility }}</div>
<div class="team-card-actions"><el-button link size="small" type="primary" @click="editTeamMember(m)">编辑</el-button><el-button link size="small" type="danger" @click="deleteTeamMember(m)">删除</el-button></div>
</div>
</div>
</div>
<div class="mobile-step-footer">
<el-button v-if="mobileStep > 0" size="large" @click="prevStep" :disabled="savingAll">上一步</el-button>
<el-button v-if="mobileStep < mobileSteps.length - 1" type="primary" size="large" @click="nextStep">下一步</el-button>
<el-button v-if="mobileStep === mobileSteps.length - 1 && plan.status === 'project_init'" type="warning" size="large" @click="showApprovalDrawer = true" style="flex:1">提交审批</el-button>
<el-button v-else-if="mobileStep === mobileSteps.length - 1" type="primary" size="large" @click="saveAll" :loading="savingAll" style="flex:1">保存全部</el-button>
</div>
</template>

<!-- 成本弹窗 -->
<el-dialog v-model="showCostDialog" title="添加成本" width="450px" :close-on-click-modal="false">
<el-form :model="costForm" label-width="100" size="small">
<el-form-item label="成本项"><el-input v-model="costForm.item_name" /></el-form-item>
<el-form-item label="类型"><el-select v-model="costForm.cost_type"><el-option label="目标成本" value="target" /><el-option label="实际成本" value="actual" /><el-option label="估算" value="estimate" /></el-select></el-form-item>
<el-form-item label="目标值"><el-input-number v-model="costForm.target_value" :min="0" :precision="2" style="width:200px" /></el-form-item>
<el-form-item label="实际值"><el-input-number v-model="costForm.actual_value" :min="0" :precision="2" style="width:200px" /></el-form-item>
<el-form-item label="币种"><el-input v-model="costForm.currency" placeholder="CNY" /></el-form-item>
<el-form-item label="备注"><el-input v-model="costForm.remark" type="textarea" :rows="2" /></el-form-item>
</el-form>
<template #footer><el-button @click="showCostDialog = false">取消</el-button><el-button type="primary" @click="addCost" :loading="addingCost">添加</el-button></template>
</el-dialog>

<!-- 团队弹窗 -->
<el-dialog v-model="showTeamDialog" :title="teamDialogMode === 'add' ? '添加成员' : '编辑成员'" width="450px" :close-on-click-modal="false">
<el-form :model="teamForm" label-width="100" size="small">
<el-form-item label="姓名"><el-input v-model="teamForm.name" /></el-form-item>
<el-form-item label="角色"><el-input v-model="teamForm.role" /></el-form-item>
<el-form-item label="部门"><el-input v-model="teamForm.department" /></el-form-item>
<el-form-item label="邮箱"><el-input v-model="teamForm.email" /></el-form-item>
<el-form-item label="电话"><el-input v-model="teamForm.phone" /></el-form-item>
</el-form>
<template #footer><el-button @click="showTeamDialog = false">取消</el-button><el-button type="primary" @click="saveTeamMember" :loading="savingTeam">{{ teamDialogMode === 'add' ? '添加' : '保存' }}</el-button></template>
</el-dialog>

<!-- 知识沉淀弹窗 -->
<el-dialog v-model="showKnowledgeDialog" title="沉淀经验到知识库" width="550px" :close-on-click-modal="false">
<el-form :model="knowledgeForm" label-width="80" size="small">
<el-form-item label="标题"><el-input v-model="knowledgeForm.title" placeholder="知识标题" /></el-form-item>
<el-form-item label="分类">
<el-select v-model="knowledgeForm.category" placeholder="选择分类" style="width:100%">
<el-option label="项目经验" value="项目经验" />
<el-option label="技术方案" value="技术方案" />
<el-option label="市场洞察" value="市场洞察" />
<el-option label="成本控制" value="成本控制" />
<el-option label="质量改进" value="质量改进" />
<el-option label="流程优化" value="流程优化" />
<el-option label="其他" value="其他" />
</el-select>
</el-form-item>
<el-form-item label="内容"><el-input v-model="knowledgeForm.content" type="textarea" :rows="5" placeholder="详细描述经验内容..." /></el-form-item>
</el-form>
<template #footer>
<el-button @click="showKnowledgeDialog = false">取消</el-button>
<el-button type="primary" @click="submitKnowledge" :loading="savingKnowledge">提交</el-button>
</template>
</el-dialog>

<!-- 移动端审批 Drawer -->
<el-drawer v-if="isMobile" v-model="showApprovalDrawer" direction="btt" size="100%" :close-on-click-modal="false" :with-header="false" class="approval-drawer-mobile">
<div class="drawer-body">
<div class="drawer-header"><h3>✅ 审批操作</h3><el-button text @click="showApprovalDrawer = false">关闭</el-button></div>
<div class="drawer-content">
<el-descriptions :column="1" border size="small" style="margin-bottom:16px">
<el-descriptions-item label="策划名称">{{ plan?.name }}</el-descriptions-item>
<el-descriptions-item label="当前阶段">{{ plan ? stageLabel(plan.status) : '' }}</el-descriptions-item>
</el-descriptions>
<label class="comment-label">审批意见</label>
<el-input v-model="approvalComment" type="textarea" :rows="4" placeholder="请输入审批意见..." maxlength="500" show-word-limit resize="none" />
</div>
<div class="drawer-footer"><el-button type="primary" size="large" @click="submitApproval" :loading="submittingApproval" style="flex:1">提交审批</el-button><el-button size="large" @click="showApprovalDrawer = false" style="flex:1">取消</el-button></div>
</div>
</el-drawer>
</div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useResponsive } from '../../composables/useResponsive'
import api from '../../api'
import * as planAPI from '../../api/productPlan'
import type { TeamMemberPayload, MarketOption, ReviewData, KnowledgeItem } from '../../api/productPlan'
import { useSubTableProgress } from '../../composables/useSubTableProgress'
import { STAGE_LABELS, STAGE_TAGS } from './shared/constants'

// ── Types ──
interface PlanInfo {
  id: string
  name: string
  series?: string
  market?: string
  status: string
  costs?: CostItem[]
  competitor_id?: number | null
  approver?: string | null
  version_id?: number
  created_at?: string
  created_by?: string
  project_links?: ProjectLinkInfo[]
  planned_launch_date?: string
}

interface ProjectLinkInfo {
  id: number
  project_id: number
  link_type: string
  snapshot_data?: string | null
  version_major: number
  version_minor: number
  scenario_group_id?: string | null
  created_at?: string
}

interface ProjectGateInfo {
  id: number
  gate_code: string
  gate_name: string
  seq: number
  status: string
  planned_date?: string | null
  actual_date?: string | null
  decision_level?: string | null
  is_hidden?: boolean
  is_high_risk_zone?: boolean
}

interface ProjectDetailInfo {
  id: number
  code: string
  name: string
  project_class: string
  status: string
  owner?: string | null
  budget?: number | null
  start_date?: string | null
  target_end_date?: string | null
  gates: ProjectGateInfo[]
}

interface CostItem {
  id?: number
  item_name: string
  cost_type: string
  target_value: number
  actual_value: number
  currency: string
  remark?: string
  version_id?: number
}

// 后端 TeamOut 字段：role_name, member_name, department, responsibility, email, phone
interface TeamMember {
  id: number
  product_plan_id?: string
  role_name: string
  member_name: string
  department: string
  responsibility?: string
  email?: string
  phone?: string
  created_at?: string
  version_id?: number
}

const route = useRoute()
const router = useRouter()
const planId = route.params.id as string
const { isMobile } = useResponsive()

// ── Sub-table progress (useSubTableProgress) ──
const {
  subTabs,
  activeTab,
  tabStatus,
  refreshStatus,
  setSubTableDone,
  guideClick: guideClickFromComposable,
} = useSubTableProgress(planId)

// ── Mobile 5-step ──
const mobileStep = ref(0)
const savingAll = ref(false)
const savingStep = ref(false)
const mobileSteps = [
{ label: '项目概述', key: 'initiation' },
{ label: '市场客户', key: 'market' },
{ label: '技术要求', key: 'techSpec' },
{ label: '成本核算', key: 'costingNew' },
{ label: '团队', key: 'team' },
{ label: '复盘', key: 'review' },
]

/** Auto-save current mobile step before navigating */
async function saveCurrentStep(stepIdx: number) {
  const key = mobileSteps[stepIdx].key
  savingStep.value = true
  try {
    switch (key) {
      case 'initiation': {
        const p = initiationForm
        const payload: Record<string, any> = {}
        if (p.background) payload.background_basis = p.background
        if (p.type) payload.product_type = p.type
        if (p.market) payload.target_market = p.market
        if (p.refrigerant) payload.refrigerant = p.refrigerant
        if (p.capacity) payload.capacity_range = p.capacity
        if (p.voltage) payload.voltage_freq = p.voltage
        if (p.series) payload.series_name = p.series
        if (p.energy) payload.energy_rating = p.energy
        if (p.dev_category) payload.dev_category = p.dev_category
        if (p.origin) payload.project_origin = p.origin
        if (p.duration) payload.project_duration = p.duration
        if (p.ip) payload.ip_ownership = p.ip
        if (p.goals) payload.overall_goal = p.goals
        if (p.deliverables) payload.deliverables = p.deliverables
        if (p.sample_qty) payload.sample_qty = p.sample_qty
        await planAPI.upsertPlanInitiation(planId, payload)
        setSubTableDone('initiation', true)
        break
      }
      case 'market': {
        const p = marketForm
        const payload: Record<string, any> = {}
        if (p.main_capacity) payload.main_capacity = p.main_capacity
        if (p.energy_efficiency) payload.energy_efficiency_req = p.energy_efficiency
        if (p.cert_requirements) payload.cert_requirements = p.cert_requirements
        if (p.target_price) payload.target_price = p.target_price
        if (p.customer_requirements) payload.customer_requirements = p.customer_requirements
        await planAPI.upsertPlanMarket(planId, payload)
        setSubTableDone('market', true)
        break
      }
      case 'techSpec':
        await planAPI.upsertPlanTechSpec(planId, techSpecForm)
        setSubTableDone('techSpec', true)
        break
      // costingNew / team — 通过弹窗管理，无需自动保存
    }
  } catch (e: unknown) {
    const _autoSaveErr = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
    /* silent — auto-save 不应阻塞导航 */ ElMessage.error(_autoSaveErr || '自动保存失败')
  }
  finally { savingStep.value = false }
}

async function nextStep() {
  if (mobileStep.value >= mobileSteps.length - 1) return
  await saveCurrentStep(mobileStep.value)
  mobileStep.value++
}
async function prevStep() {
  if (mobileStep.value <= 0) return
  await saveCurrentStep(mobileStep.value)
  mobileStep.value--
}

/** Guide 引导条点击 — 同步 activeTab + 移动端切换步骤 */
function guideClick(key: string, idx: number) {
  guideClickFromComposable(key, idx)
  if (isMobile.value) mobileStep.value = idx
}

/** 移动端步骤完成状态 — 已完成步骤显示✓ */
function stepStatus(key: string): 'success' | undefined {
  if (tabStatus.value[key] === 'done') return 'success'
  return undefined
}

// ── Data ──
const plan = ref<PlanInfo | null>(null)
const costs = ref<CostItem[]>([])
const loading = ref(true)
const saving = ref(false)
const editForm = ref({ name: '', series: '', market: '', competitor_id: null as number | null })
const marketOptions = ref<MarketOption[]>([])
/** 市场名称 → 能效标准映射 */
const marketEnergyMap = computed(() => {
  const map: Record<string, { key: string; label: string }> = {}
  for (const m of marketOptions.value) {
    map[m.name] = { key: m.energy_standard, label: m.energy_label }
  }
  return map
})
const costForm = ref({ item_name: '', cost_type: 'target', target_value: 0, actual_value: 0, currency: 'CNY', remark: '' })
const showCostDialog = ref(false)
const addingCost = ref(false)
const approvalComment = ref('')
const submittingApproval = ref(false)
const approving = ref(false)
const rejecting = ref(false)
const withdrawing = ref(false)
const showApprovalDrawer = ref(false)
const submittingQuick = ref(false)

// ── 关联项目 ──
const projectLinks = ref<ProjectLinkInfo[]>([])
const projectDetails = ref<ProjectDetailInfo[]>([])
const loadingProjects = ref(false)

// ── 项目概述 ──
const initiationForm = reactive({ background: '', type: '', market: '', refrigerant: '', capacity: '', voltage: '', series: '', energy: '', dev_category: '', origin: '', duration: 0, ip: '', goals: '', deliverables: '', sample_qty: 0 })
const savingInitiation = ref(false)
/** @deprecated — 7个废弃JSON成本字段，仅供历史明细展示 */
const initiationCosts = ref<Record<string, any> | null>(null)

// ── 子表版本号 ──
const initiationVersion = ref(0)
const marketVersion = ref(0)
const techSpecVersion = ref(0)
const teamVersion = ref(0)

// ── 复盘 ──
const reviewData = ref<ReviewData | null>(null)
const reviewForm = reactive({
  review_date: '',
  actual_cost_total: null as number | null,
  actual_launch_date: '',
  market_feedback: '',
  lessons_learned: '',
  overall_rating: 0,
})
const savingReview = ref(false)

// ── 知识沉淀 ──
const knowledgeList = ref<KnowledgeItem[]>([])
const showKnowledgeDialog = ref(false)
const savingKnowledge = ref(false)
const knowledgeForm = reactive({
  title: '',
  category: '',
  content: '',
})

async function fetchInitiation() {
try { const res = await planAPI.getPlanInitiation(planId); if (res.data) {
  // 后端字段 → 前端字段映射
  const data = res.data
  initiationForm.background = data.background_basis || ''
  initiationForm.type = data.product_type || ''
  initiationForm.market = data.target_market || ''
  initiationForm.refrigerant = data.refrigerant || ''
  initiationForm.capacity = data.capacity_range || ''
  initiationForm.voltage = data.voltage_freq || ''
  initiationForm.series = data.series_name || ''
  initiationForm.energy = data.energy_rating || ''
  initiationForm.dev_category = data.dev_category || ''
  initiationForm.origin = data.project_origin || ''
  initiationForm.duration = data.project_duration || 0
  initiationForm.ip = data.ip_ownership || ''
  initiationForm.goals = data.overall_goal || ''
  initiationForm.deliverables = data.deliverables || ''
  initiationForm.sample_qty = data.sample_qty || 0
  initiationVersion.value = data.version_id ?? 0
  // @deprecated — 收集7个废弃JSON成本字段用于历史明细展示
  initiationCosts.value = (
    data.dev_cost_items || data.mold_costs || data.prototype_costs_detail ||
    data.test_costs || data.cert_costs || data.labor_costs || data.economic_indicators
  ) ? {
    dev_cost_items: data.dev_cost_items,
    mold_costs: data.mold_costs,
    prototype_costs_detail: data.prototype_costs_detail,
    test_costs: data.test_costs,
    cert_costs: data.cert_costs,
    labor_costs: data.labor_costs,
    economic_indicators: data.economic_indicators,
  } : null
} } catch (e: unknown) {
const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
ElMessage.error(_err || '操作失败，请重试')
}
}
async function saveInitiation() {
savingInitiation.value = true
try {
  // 前端字段 → 后端字段映射（只发送有值的字段，避免覆盖已有数据）
  const p = initiationForm
  const payload: Record<string, any> = {}
  if (p.background) payload.background_basis = p.background
  if (p.type) payload.product_type = p.type
  if (p.market) payload.target_market = p.market
  if (p.refrigerant) payload.refrigerant = p.refrigerant
  if (p.capacity) payload.capacity_range = p.capacity
  if (p.voltage) payload.voltage_freq = p.voltage
  if (p.series) payload.series_name = p.series
  if (p.energy) payload.energy_rating = p.energy
  if (p.dev_category) payload.dev_category = p.dev_category
  if (p.origin) payload.project_origin = p.origin
  if (p.duration) payload.project_duration = p.duration
  if (p.ip) payload.ip_ownership = p.ip
  if (p.goals) payload.overall_goal = p.goals
  if (p.deliverables) payload.deliverables = p.deliverables
  if (p.sample_qty) payload.sample_qty = p.sample_qty
  const res = await planAPI.upsertPlanInitiation(planId, payload); initiationVersion.value = res.data.version_id ?? 0; ElMessage.success('项目概述保存成功'); setSubTableDone('initiation', true) } catch (e: unknown) {
const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
ElMessage.error(_err || '操作失败，请重试')
}
finally { savingInitiation.value = false }
}

// ── 市场与客户 ──
const marketForm = reactive({ main_capacity: '', energy_efficiency: '', cert_requirements: '', target_price: 0, customer_requirements: '' })
const savingMarket = ref(false)

/** 从API加载市场选项列表 */
async function fetchMarketOptions() {
  try {
    const res = await planAPI.fetchMarkets()
    const data = (res.data || []) as MarketOption[]
    marketOptions.value = data
  } catch {
    // API不可用时使用空列表，用户可手动输入
    marketOptions.value = []
  }
}

/** 监听市场选择变化 — 自动填充能效标准 */
watch(() => editForm.value.market, (newMarket) => {
  if (!newMarket) return
  const std = marketEnergyMap.value[newMarket]
  if (std && !marketForm.energy_efficiency) {
    marketForm.energy_efficiency = `${std.label} (${std.key})`
  }
})

async function fetchMarket() {
try { const res = await planAPI.getPlanMarket(planId); if (res.data) {
  const data = res.data
  marketForm.main_capacity = data.main_capacity || ''
  marketForm.energy_efficiency = data.energy_efficiency_req || ''
  marketForm.cert_requirements = data.cert_requirements || ''
  marketForm.target_price = data.target_price || 0
  marketForm.customer_requirements = data.customer_requirements || ''
  marketVersion.value = data.version_id ?? 0
  // 自动填充能效标准（如果市场已选但能效为空）
  if (editForm.value.market && !marketForm.energy_efficiency) {
    const std = marketEnergyMap.value[editForm.value.market]
    if (std) marketForm.energy_efficiency = `${std.label} (${std.key})`
  }
} } catch (e: unknown) {
const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
ElMessage.error(_err || '操作失败，请重试')
}
}
async function saveMarket() {
savingMarket.value = true
try {
  const p = marketForm
  const payload: Record<string, any> = {}
  if (p.main_capacity) payload.main_capacity = p.main_capacity
  if (p.energy_efficiency) payload.energy_efficiency_req = p.energy_efficiency
  if (p.cert_requirements) payload.cert_requirements = p.cert_requirements
  if (p.target_price) payload.target_price = p.target_price
  if (p.customer_requirements) payload.customer_requirements = p.customer_requirements
  const res = await planAPI.upsertPlanMarket(planId, payload); marketVersion.value = res.data.version_id ?? 0; ElMessage.success('市场与客户需求保存成功'); setSubTableDone('market', true) } catch (e: unknown) {
const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
ElMessage.error(_err || '操作失败，请重试')
}
finally { savingMarket.value = false }
}

// ── 技术要求 ──
const techSpecForm = reactive({ core_performance: '', safety_compliance: '', optional_config: '' })
const savingTechSpec = ref(false)

async function fetchTechSpec() {
try { const res = await planAPI.getPlanTechSpec(planId); if (res.data) { Object.assign(techSpecForm, res.data); techSpecVersion.value = res.data.version_id ?? 0 } } catch (e: unknown) {
const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
ElMessage.error(_err || '操作失败，请重试')
}
}
async function saveTechSpec() {
savingTechSpec.value = true
try { const res = await planAPI.upsertPlanTechSpec(planId, techSpecForm); techSpecVersion.value = res.data.version_id ?? 0; ElMessage.success('技术要求保存成功'); setSubTableDone('techSpec', true) } catch (e: unknown) {
const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
ElMessage.error(_err || '操作失败，请重试')
}
finally { savingTechSpec.value = false }
}

// ── 团队 ──
const teamMembers = ref<TeamMember[]>([])
const showTeamDialog = ref(false)
const teamDialogMode = ref<'add' | 'edit'>('add')
const teamForm = reactive({ name: '', role: '', department: '', email: '', phone: '', version_id: undefined as number | undefined })
const editingTeamId = ref<number | null>(null)
const savingTeam = ref(false)

async function fetchTeam() {
try { const res = await planAPI.listPlanTeam(planId); teamMembers.value = res.data || []; teamVersion.value = teamMembers.value.length > 0 ? Math.max(...teamMembers.value.map((m: TeamMember) => m.version_id ?? 0)) : 0; setSubTableDone('team', teamMembers.value.length > 0) } catch (e: unknown) {
const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
teamMembers.value = []; teamVersion.value = 0; setSubTableDone('team', false); ElMessage.error(_err || '操作失败，请重试')
}
}
function editTeamMember(row: TeamMember) {
teamDialogMode.value = 'edit'; editingTeamId.value = row.id
Object.assign(teamForm, { name: row.member_name, role: row.role_name, department: row.department, email: row.email || '', phone: row.phone || '', version_id: row.version_id })
showTeamDialog.value = true
}
async function saveTeamMember() {
savingTeam.value = true
try {
// 字段映射: 前端 {name,role,department,email,phone} → 后端 {role_name,member_name,department,email,phone}
const payload: TeamMemberPayload = {
member_name: teamForm.name,
role_name: teamForm.role,
department: teamForm.department,
email: teamForm.email,
phone: teamForm.phone,
}
if (teamDialogMode.value === 'add') await planAPI.addPlanTeamMember(planId, payload)
else if (editingTeamId.value !== null) {
  // 更新时附带版本号做乐观锁
  if (teamForm.version_id !== undefined) {
    payload.version_id = teamForm.version_id
  }
  await planAPI.updatePlanTeamMember(planId, editingTeamId.value, payload)
}
ElMessage.success(teamDialogMode.value === 'add' ? '成员添加成功' : '成员更新成功')
showTeamDialog.value = false; teamForm.name = ''; teamForm.role = ''; teamForm.department = ''; teamForm.email = ''; teamForm.phone = ''
await fetchTeam()
} catch (e: unknown) {
const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
ElMessage.error(_err || '操作失败，请重试')
}
finally { savingTeam.value = false }
}
async function deleteTeamMember(row: TeamMember) {
try { await ElMessageBox.confirm(`确定删除「${row.member_name}」?`, '确认', { type: 'warning' }); await planAPI.deletePlanTeamMember(planId, row.id); ElMessage.success('已删除'); await fetchTeam() } catch (e: unknown) {
const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
ElMessage.error(_err || '操作失败，请重试')
}
}

// ── 主API ──
async function fetchPlan() {
loading.value = true
try {
const res = await api.get(`/product-plans/${planId}`)
plan.value = res.data
costs.value = res.data.costs || []
projectLinks.value = res.data.project_links || []
setSubTableDone('costingNew', costs.value.length > 0)
editForm.value = { name: res.data.name || '', series: res.data.series || '', market: res.data.market || '', competitor_id: res.data.competitor_id ?? null }
// 加载关联项目详情
if (projectLinks.value.length > 0) {
  fetchProjectDetails()
}
} catch (e: unknown) {
const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
ElMessage.error(_err || '操作失败，请重试')
}
finally { loading.value = false }
}

async function fetchProjectDetails() {
loadingProjects.value = true
try {
  const results = await Promise.allSettled(
    projectLinks.value.map(link => api.get(`/projects/${link.project_id}`))
  )
  projectDetails.value = results
    .filter((r): r is PromiseFulfilledResult<any> => r.status === 'fulfilled')
    .map(r => r.value.data as ProjectDetailInfo)
} catch {
  // 静默处理 — 项目详情加载失败不影响主页面
} finally {
  loadingProjects.value = false
}
}
async function saveQuickEdit() {
saving.value = true
try { await api.patch(`/product-plans/${planId}`, editForm.value); ElMessage.success('保存成功'); await fetchPlan() } catch (e: unknown) {
const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
ElMessage.error(_err || '操作失败，请重试')
}
finally { saving.value = false }
}

/** 跳转到竞品对标页，携带当前市场和产品类型 */
function goCompetitor() {
  const market = editForm.value.market
  const type = initiationForm.type || ''
  router.push(`/competitor-bench?market=${encodeURIComponent(market)}&type=${encodeURIComponent(type)}`)
}

// ── 成本 ──
async function addCost() {
addingCost.value = true
try { await api.post(`/product-plans/${planId}/costs`, costForm.value); ElMessage.success('成本添加成功'); showCostDialog.value = false; costForm.value = { item_name: '', cost_type: 'target', target_value: 0, actual_value: 0, currency: 'CNY', remark: '' }; await fetchPlan(); setSubTableDone('costingNew', true) } catch (e: unknown) {
const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
ElMessage.error(_err || '操作失败，请重试')
}
finally { addingCost.value = false }
}
async function deleteCost(row: CostItem) {
try { await ElMessageBox.confirm(`确定删除「${row.item_name}」?`, '确认', { type: 'warning' }); await api.delete(`/product-plans/${planId}/costs/${row.id}`); ElMessage.success('已删除'); await fetchPlan(); setSubTableDone('costingNew', costs.value.length > 0) } catch (e: unknown) {
const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
ElMessage.error(_err || '操作失败，请重试')
}
}

// ── BOM类型 ──
const bomTypes = [
{ key: 'concept_bom', icon: '📐', label: '概念BOM', desc: '初期架构', status: 'inactive' },
{ key: 'design_bom', icon: '✏️', label: '设计BOM', desc: '详细设计', status: 'inactive' },
{ key: 'pilot_bom', icon: '🧪', label: '试产BOM', desc: '试产验证', status: 'inactive' },
{ key: 'mass_bom', icon: '🏭', label: '量产BOM', desc: '量产正式', status: 'inactive' },
]

// ── 阶段映射 ──
function stageLabel(s: string): string { return STAGE_LABELS[s] || s }
function stageTagType(s: string): string { return STAGE_TAGS[s] || 'info' }

// ── 项目辅助函数 ──
function classTagType(cls: string): string {
  const map: Record<string, string> = { T: 'danger', A: 'warning', B: 'primary', C: 'info' }
  return map[cls] || 'info'
}
function projectStatusLabel(s: string): string {
  const map: Record<string, string> = { planning: '规划中', running: '进行中', completed: '已完成', paused: '暂停', cancelled: '已取消' }
  return map[s] || s
}
function projectStatusTagType(s: string): string {
  const map: Record<string, string> = { planning: 'info', running: 'primary', completed: 'success', paused: 'warning', cancelled: 'danger' }
  return map[s] || 'info'
}
function visibleGates(proj: ProjectDetailInfo): ProjectGateInfo[] {
  return (proj.gates || []).filter(g => !g.is_hidden).sort((a, b) => a.seq - b.seq)
}
function gateStatus(g: ProjectGateInfo): 'success' | 'process' | 'wait' {
  if (g.status === 'passed') return 'success'
  if (g.status === 'failed') return 'error'
  // 如果当前 gate 之前有未通过的，则是等待状态
  return 'wait'
}
function gateActiveStep(proj: ProjectDetailInfo): number {
  const gates = visibleGates(proj)
  // 找到最后一个已通过 gate 的索引 + 1 = active step
  let lastPassed = -1
  for (let i = 0; i < gates.length; i++) {
    if (gates[i].status === 'passed') lastPassed = i
    else break // 一旦遇到未通过的，后续都是等待
  }
  return lastPassed + 1
}
const totalTargetCost = computed(() => {
  return costs.value.reduce((sum, c) => sum + (Number(c.target_value) || 0), 0)
})
const totalActualCost = computed(() => {
  return costs.value.reduce((sum, c) => sum + (Number(c.actual_value) || 0), 0)
})
function formatCost(val: number): string {
  return `¥${val.toLocaleString('zh-CN')}`
}
/** 格式化 JSON 对象为可读字符串（用于历史明细展示） */
function formatCostJson(val: any): string {
  if (typeof val === 'string') {
    try { val = JSON.parse(val) } catch { return val }
  }
  if (val && typeof val === 'object') {
    return JSON.stringify(val, null, 2)
  }
  return String(val)
}
/** 过滤出有值的废弃成本字段（用于移动端展示） */
function filteredCostFields(obj: Record<string, any>): Record<string, any> {
  const result: Record<string, any> = {}
  for (const [k, v] of Object.entries(obj)) {
    if (v != null) result[k] = v
  }
  return result
}
/** 废弃成本字段中文标签 */
const COST_FIELD_LABELS: Record<string, string> = {
  dev_cost_items: '研发费用',
  mold_costs: '模具费用',
  prototype_costs_detail: '样机费用',
  test_costs: '测试费用',
  cert_costs: '认证费用',
  labor_costs: '人工费用',
  economic_indicators: '经济指标',
}
function costFieldLabel(key: string): string {
  return COST_FIELD_LABELS[key] || key
}
function costCompareType(target: number, actual: number): string {
  if (actual === 0 && target === 0) return 'info'
  if (actual > target * 1.05) return 'danger'    // 超支 >5%
  if (actual < target * 0.95) return 'success'   // 节省 >5%
  return 'warning'                                 // 持平 ±5%
}
function costCompareLabel(target: number, actual: number): string {
  if (actual === 0 && target === 0) return '无数据'
  if (actual > target * 1.05) return '超支'
  if (actual < target * 0.95) return '节省'
  return '持平'
}

// ── 复盘对比计算 ──
const totalCostTarget = computed(() => {
  return costs.value.reduce((sum, c) => sum + (Number(c.target_value) || 0), 0)
})
const costDeviationType = computed(() => {
  const target = totalCostTarget.value
  const actual = reviewForm.actual_cost_total
  if (target === 0 || actual == null) return 'info'
  if (actual > target * 1.05) return 'danger'
  if (actual < target * 0.95) return 'success'
  return 'warning'
})
const costDeviationLabel = computed(() => {
  const target = totalCostTarget.value
  const actual = reviewForm.actual_cost_total
  if (target === 0 && (actual == null || actual === 0)) return '无数据'
  if (target === 0) return '目标未设定'
  if (actual == null) return '待填写实际成本'
  const pct = ((actual - target) / target * 100).toFixed(1)
  if (actual > target) return `超支 ${pct}%`
  if (actual < target) return `节省 ${Math.abs(Number(pct))}%`
  return '持平'
})
const launchDeviationType = computed(() => {
  const planned = plan.value?.planned_launch_date
  const actual = reviewForm.actual_launch_date
  if (!planned || !actual) return 'info'
  const days = Math.round((new Date(actual).getTime() - new Date(planned).getTime()) / (1000 * 60 * 60 * 24))
  if (days > 7) return 'danger'
  if (days < -7) return 'success'
  if (days === 0) return 'success'
  return 'warning'
})
const launchDeviationLabel = computed(() => {
  const planned = plan.value?.planned_launch_date
  const actual = reviewForm.actual_launch_date
  if (!planned && !actual) return '无数据'
  if (!planned) return '计划日未设定'
  if (!actual) return '待填写实际日期'
  const days = Math.round((new Date(actual).getTime() - new Date(planned).getTime()) / (1000 * 60 * 60 * 24))
  if (days > 0) return `延迟 ${days} 天`
  if (days < 0) return `提前 ${Math.abs(days)} 天`
  return '准时上市'
})

// ── 底部审批操作栏 ──
const canAdvance = computed(() => plan.value && ['draft', 'competitor', 'definition', 'costing', 'tech_input'].includes(plan.value.status))
/** 是否可以一键提交审批（在项目立项之前的所有阶段都可使用） */
const canQuickSubmit = computed(() => plan.value && ['draft', 'competitor', 'definition', 'costing', 'tech_input'].includes(plan.value.status))
const isApprovalStage = computed(() => plan.value?.status === 'project_init')
const canWithdraw = computed(() => plan.value && !['draft', 'project_init', 'released'].includes(plan.value.status))

async function advancePlan() {
try { await api.post(`/product-plans/${planId}/advance`); ElMessage.success('流程已推进'); await fetchPlan() } catch (e: unknown) {
const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
ElMessage.error(_err || '操作失败，请重试')
}
}
async function approvePlan() {
try {
const { value: comment } = await ElMessageBox.prompt('请输入审批意见', '审批确认', {
confirmButtonText: '确认通过',
cancelButtonText: '取消',
inputType: 'textarea',
inputPlaceholder: '请填写审批意见...',
})
approving.value = true
await planAPI.approvePlan(planId, comment || '')
ElMessage.success('已通过')
await fetchPlan()
} catch (e: unknown) {
if ((e as {action?: string})?.action === 'cancel' || (e instanceof Error && e.message === 'cancel')) return // user cancelled
const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
ElMessage.error(_err || '操作失败，请重试')
}
finally { approving.value = false }
}
async function rejectPlan() {
try {
const { value: comment } = await ElMessageBox.prompt('请输入驳回意见', '驳回确认', {
confirmButtonText: '确认驳回',
cancelButtonText: '取消',
inputType: 'textarea',
inputPlaceholder: '请填写驳回意见...',
})
rejecting.value = true
await planAPI.rejectPlan(planId, comment || '')
ElMessage.success('已驳回')
await fetchPlan()
} catch (e: unknown) {
if ((e as {action?: string})?.action === 'cancel' || (e instanceof Error && e.message === 'cancel')) return // user cancelled
const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
ElMessage.error(_err || '操作失败，请重试')
}
finally { rejecting.value = false }
}
async function withdrawPlan() {
withdrawing.value = true
try { await planAPI.withdrawPlan(planId); ElMessage.success('已撤回'); await fetchPlan() } catch (e: unknown) {
const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
ElMessage.error(_err || '操作失败，请重试')
}
finally { withdrawing.value = false }
}

// ── 复盘 ──
async function fetchReview() {
  try {
    const res = await planAPI.getReview(planId)
    if (res.data) {
      reviewData.value = res.data
      reviewForm.review_date = res.data.review_date || ''
      reviewForm.actual_cost_total = res.data.actual_cost_total ?? null
      reviewForm.actual_launch_date = res.data.actual_launch_date || ''
      reviewForm.market_feedback = res.data.market_feedback || ''
      reviewForm.lessons_learned = res.data.lessons_learned || ''
      reviewForm.overall_rating = res.data.overall_rating || 0
      setSubTableDone('review', true)
    }
  } catch {
    // 404 = 无复盘数据，不报错
    reviewData.value = null
    setSubTableDone('review', false)
  }
}

function resetReviewForm() {
  if (reviewData.value) {
    reviewForm.review_date = reviewData.value.review_date || ''
    reviewForm.actual_cost_total = reviewData.value.actual_cost_total ?? null
    reviewForm.actual_launch_date = reviewData.value.actual_launch_date || ''
    reviewForm.market_feedback = reviewData.value.market_feedback || ''
    reviewForm.lessons_learned = reviewData.value.lessons_learned || ''
    reviewForm.overall_rating = reviewData.value.overall_rating || 0
  } else {
    reviewForm.review_date = ''
    reviewForm.actual_cost_total = null
    reviewForm.actual_launch_date = ''
    reviewForm.market_feedback = ''
    reviewForm.lessons_learned = ''
    reviewForm.overall_rating = 0
  }
}

async function saveReview() {
  savingReview.value = true
  try {
    const payload: ReviewData = {
      review_date: reviewForm.review_date || undefined,
      actual_cost_total: reviewForm.actual_cost_total ?? undefined,
      actual_launch_date: reviewForm.actual_launch_date || undefined,
      market_feedback: reviewForm.market_feedback || undefined,
      lessons_learned: reviewForm.lessons_learned || undefined,
      overall_rating: reviewForm.overall_rating || undefined,
    }
    if (reviewData.value?.id) {
      await planAPI.updateReview(planId, payload)
      ElMessage.success('复盘更新成功')
    } else {
      await planAPI.submitReview(planId, payload)
      ElMessage.success('复盘提交成功')
    }
    await fetchReview()
  } catch (e: unknown) {
    const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
    ElMessage.error(_err || '操作失败，请重试')
  } finally {
    savingReview.value = false
  }
}

// ── 知识沉淀 ──
async function fetchKnowledge() {
  try {
    const res = await planAPI.listPlanKnowledge(planId)
    knowledgeList.value = res.data || []
  } catch {
    knowledgeList.value = []
  }
}

async function submitKnowledge() {
  if (!knowledgeForm.title || !knowledgeForm.content) {
    ElMessage.warning('请填写标题和内容')
    return
  }
  savingKnowledge.value = true
  try {
    const payload: Record<string, unknown> = {
      title: knowledgeForm.title,
      category: knowledgeForm.category || '其他',
      content: knowledgeForm.content,
      source_type: 'product_plan',
      source_id: planId,
    }
    await planAPI.createKnowledge(payload)
    ElMessage.success('知识沉淀成功')
    showKnowledgeDialog.value = false
    knowledgeForm.title = ''
    knowledgeForm.category = ''
    knowledgeForm.content = ''
    await fetchKnowledge()
  } catch (e: unknown) {
    const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
    ElMessage.error(_err || '操作失败，请重试')
  } finally {
    savingKnowledge.value = false
  }
}

function goToKnowledge(row: KnowledgeItem) {
  // 如果有知识详情页则跳转，否则提示
  ElMessage.info(`知识: ${row.title}`)
}

// ── 移动端保存全部 ──
async function saveAll() {
savingAll.value = true
try {
await api.patch(`/product-plans/${planId}`, editForm.value)
// Initiation 字段映射
const ip = initiationForm
const initPayload: Record<string, any> = {}
if (ip.background) initPayload.background_basis = ip.background
if (ip.type) initPayload.product_type = ip.type
if (ip.market) initPayload.target_market = ip.market
if (ip.refrigerant) initPayload.refrigerant = ip.refrigerant
if (ip.capacity) initPayload.capacity_range = ip.capacity
if (ip.voltage) initPayload.voltage_freq = ip.voltage
if (ip.series) initPayload.series_name = ip.series
if (ip.energy) initPayload.energy_rating = ip.energy
if (ip.dev_category) initPayload.dev_category = ip.dev_category
if (ip.origin) initPayload.project_origin = ip.origin
if (ip.duration) initPayload.project_duration = ip.duration
if (ip.ip) initPayload.ip_ownership = ip.ip
if (ip.goals) initPayload.overall_goal = ip.goals
if (ip.deliverables) initPayload.deliverables = ip.deliverables
if (ip.sample_qty) initPayload.sample_qty = ip.sample_qty
await planAPI.upsertPlanInitiation(planId, initPayload)
// Market 字段映射
const mp = marketForm
const marketPayload: Record<string, any> = {}
if (mp.main_capacity) marketPayload.main_capacity = mp.main_capacity
if (mp.energy_efficiency) marketPayload.energy_efficiency_req = mp.energy_efficiency
if (mp.cert_requirements) marketPayload.cert_requirements = mp.cert_requirements
if (mp.target_price) marketPayload.target_price = mp.target_price
if (mp.customer_requirements) marketPayload.customer_requirements = mp.customer_requirements
await planAPI.upsertPlanMarket(planId, marketPayload)
await planAPI.upsertPlanTechSpec(planId, techSpecForm)
ElMessage.success('全部保存成功')
} catch (e: unknown) {
const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
ElMessage.error(_err || '操作失败，请重试')
}
finally { savingAll.value = false }
}

// ── 移动端审批 ──
/** 阶段流转顺序（与后端 PLAN_STAGE_TRANSITIONS 保持一致） */
const STAGE_FLOW = ['draft', 'competitor', 'definition', 'costing', 'tech_input', 'project_init', 'approved', 'released']

/**
 * 构建提交审批确认弹窗的 HTML 消息
 */
function buildApprovalConfirmMessage(currentStage: string): string {
  const currentIdx = STAGE_FLOW.indexOf(currentStage)
  const currentLabel = STAGE_LABELS[currentStage] || currentStage

  if (currentIdx < 0 || currentIdx >= STAGE_FLOW.length - 1) {
    // 未知或已结束阶段，简单提示
    return `<p>当前阶段：${currentLabel}</p><p style="color:#909399;font-size:12px;margin-top:8px">确认提交审批吗？</p>`
  }

  const nextStage = STAGE_FLOW[currentIdx + 1]
  const nextLabel = STAGE_LABELS[nextStage] || nextStage

  // 中间阶段 = currentIdx+1 到 nextIdx-1 之间的阶段（通常为空，保留逻辑便于扩展）
  const intermediateLabels: string[] = []
  // 只需往前看一步（后端每次只推进一级），中间阶段为空
  // 如有多步推进需求，可调整此处逻辑

  let message = `<div style="font-size:14px;line-height:2">`
  message += `<p><strong>📌 当前阶段：</strong><span style="color:#409eff;font-weight:600">${currentLabel}</span></p>`
  message += `<p><strong>🎯 目标阶段：</strong><span style="color:#67c23a;font-weight:600">${nextLabel}</span></p>`
  if (intermediateLabels.length > 0) {
    message += `<p><strong>🔄 中间阶段：</strong>${intermediateLabels.join(' → ')}</p>`
  } else {
    message += `<p><strong>🔄 中间阶段：</strong><span style="color:#909399">（直接推进，无中间阶段）</span></p>`
  }
  message += `<hr style="border:none;border-top:1px solid #ebeef5;margin:12px 0">`
  message += `<p style="color:#909399;font-size:12px">确认后将提交审批并推进流程，请确认所有信息已填写完整。</p></div>`

  return message
}

async function submitApproval() {
if (!approvalComment.value || !approvalComment.value.trim()) {
ElMessage.warning('请输入审批意见')
return
}

// ── 状态预览确认弹窗 ──
const msg = buildApprovalConfirmMessage(plan.value?.status || '')
try {
  await ElMessageBox.confirm(msg, '提交审批确认', {
    confirmButtonText: '确认提交',
    cancelButtonText: '取消',
    dangerouslyUseHTMLString: true,
  })
} catch {
  return // 用户取消
}

submittingApproval.value = true
try { await api.post(`/product-plans/${planId}/advance`, { comment: approvalComment.value }); ElMessage.success('审批已提交'); approvalComment.value = ''; showApprovalDrawer.value = false; await fetchPlan() } catch (e: unknown) {
const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : (e instanceof Error ? e.message : null)
ElMessage.error(_err || '操作失败，请重试')
}
finally { submittingApproval.value = false }
}

/** Tab 中文标签映射（用于校验报错提示） */
const TAB_LABELS: Record<string, string> = {
  initiation: '项目概述',
  market: '市场与客户',
  techSpec: '技术要求',
  costingNew: '成本核算',
  team: '团队',
}

/**
 * 一键提交审批 — 自动校验 → 保存 → 推进到 PROJECT_INIT → 提交审批
 */
async function quickSubmit() {
  // 1. 校验所有5个Tab是否已完成
  const requiredTabs = ['initiation', 'market', 'techSpec', 'costingNew', 'team']
  const unfinished = requiredTabs.filter(k => tabStatus.value[k] !== 'done')
  if (unfinished.length > 0) {
    ElMessage.warning(`以下子表尚未完成填写: ${unfinished.map(k => TAB_LABELS[k] || k).join('、')}`)
    return
  }

  // 2. 确认弹窗（复用 buildApprovalConfirmMessage）
  const msg = buildApprovalConfirmMessage(plan.value?.status || '')
  try {
    await ElMessageBox.confirm(msg, '📮 一键提交审批确认', {
      confirmButtonText: '确认提交',
      cancelButtonText: '取消',
      dangerouslyUseHTMLString: true,
    })
  } catch {
    return // 用户取消
  }

  // 3. 执行推进
  submittingQuick.value = true
  try {
    // 3a. 先保存所有子表表单数据（确保最新编辑内容已落库）
    const p = initiationForm
    const initPayload: Record<string, any> = {}
    if (p.background) initPayload.background_basis = p.background
    if (p.type) initPayload.product_type = p.type
    if (p.refrigerant) initPayload.refrigerant = p.refrigerant
    if (p.capacity) initPayload.capacity_range = p.capacity
    if (p.voltage) initPayload.voltage_freq = p.voltage
    if (p.series) initPayload.series_name = p.series
    if (p.energy) initPayload.energy_rating = p.energy
    if (p.dev_category) initPayload.dev_category = p.dev_category
    if (p.origin) initPayload.project_origin = p.origin
    if (p.duration) initPayload.project_duration = p.duration
    if (p.ip) initPayload.ip_ownership = p.ip
    if (p.goals) initPayload.overall_goal = p.goals
    if (p.deliverables) initPayload.deliverables = p.deliverables
    if (p.sample_qty) initPayload.sample_qty = p.sample_qty
    await planAPI.upsertPlanInitiation(planId, initPayload)

    const mp = marketForm
    const marketPayload: Record<string, any> = {}
    if (mp.main_capacity) marketPayload.main_capacity = mp.main_capacity
    if (mp.energy_efficiency) marketPayload.energy_efficiency_req = mp.energy_efficiency
    if (mp.cert_requirements) marketPayload.cert_requirements = mp.cert_requirements
    if (mp.target_price) marketPayload.target_price = mp.target_price
    if (mp.customer_requirements) marketPayload.customer_requirements = mp.customer_requirements
    await planAPI.upsertPlanMarket(planId, marketPayload)

    await planAPI.upsertPlanTechSpec(planId, techSpecForm)

    // 3b. 推进到 PROJECT_INIT（直接更新阶段，跳过中间步骤）
    await planAPI.updatePlanStage(planId, 'project_init')

    // 3c. 提交审批
    await api.post(`/product-plans/${planId}/advance`, { comment: '一键提交审批' })

    ElMessage.success('🎉 一键提交审批成功！')
    await fetchPlan()
  } catch (e: unknown) {
    const _err = e && typeof e === 'object' && 'response' in e
      ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail
      : (e instanceof Error ? e.message : null)
    ElMessage.error(_err || '一键提交失败，请重试')
  } finally {
    submittingQuick.value = false
  }
}

onMounted(async () => {
  await Promise.all([
    fetchPlan(),
    fetchInitiation(),
    fetchMarket(),
    fetchTechSpec(),
    fetchTeam(),
    fetchMarketOptions(),
    fetchReview(),
    fetchKnowledge(),
  ])
  refreshStatus()
})
</script>

<style scoped>
.detail-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.detail-header h2 { margin: 0; font-size: 18px; flex: 1; }
.tab-toolbar { margin-bottom: 12px; }
/* PlanStatusGuide */
.plan-status-guide { display: flex; gap: 8px; margin-bottom: 20px; padding: 16px; background: #f5f7fa; border-radius: 8px; }
.guide-step { flex: 1; text-align: center; cursor: pointer; padding: 8px; border-radius: 6px; transition: all .2s; }
.guide-step:hover { background: #e8eaed; }
.guide-step.active { background: #ecf5ff; box-shadow: 0 0 0 1px #409eff; }
.guide-step.done .guide-step-num { background: #67c23a; color: #fff; }
.guide-step-num { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 50%; background: #dcdfe6; color: #fff; font-size: 13px; font-weight: 600; margin-bottom: 4px; }
.guide-step.active .guide-step-num { background: #409eff; }
.guide-step-label { font-size: 13px; font-weight: 600; margin-bottom: 4px; color: #303133; }
/* BOM cards */
.bom-types { display: flex; gap: 12px; }
.bom-card { flex: 1; text-align: center; padding: 12px; border: 1px solid #ebeef5; border-radius: 6px; }
.bom-icon { font-size: 24px; margin-bottom: 4px; }
.bom-name { font-size: 13px; font-weight: 600; margin-bottom: 4px; }
/* Quick edit */
.quick-edit { padding: 12px; background: #fafafa; border-radius: 6px; border: 1px solid #ebeef5; }
/* Approval bar */
.approval-bar { display: flex; align-items: center; justify-content: space-between; margin-top: 16px; padding: 12px 16px; background: #fff; border: 1px solid #e4e7ed; border-radius: 6px; }
.approval-info { display: flex; gap: 20px; font-size: 13px; }
.approval-node { font-weight: 600; }
.approval-actions { display: flex; gap: 8px; }
/* Mobile */
.mobile-step-form { padding: 0 12px; }
.step-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid #ebeef5; }
.mobile-step-footer { position: fixed; bottom: 0; left: 0; right: 0; display: flex; gap: 12px; padding: 12px 16px; padding-bottom: calc(12px + env(safe-area-inset-bottom, 0px)); background: #fff; border-top: 1px solid #e4e7ed; box-shadow: 0 -2px 8px rgba(0,0,0,0.06); z-index: 100; }
.mobile-step-footer .el-button { flex: 1; }
.mobile-team-card { background: #f5f7fa; border-radius: 8px; padding: 12px; margin-bottom: 8px; }
.team-card-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.team-card-name { font-weight: 600; font-size: 14px; }
.team-card-detail { font-size: 12px; color: #909399; margin-bottom: 6px; }
.team-card-actions { display: flex; gap: 8px; }
.energy-standard-hint { font-size: 12px; color: #909399; margin-top: 4px; padding: 2px 8px; background: #f5f7fa; border-radius: 3px; display: inline-block; }
/* Approval Drawer */
.approval-drawer-mobile :deep(.el-drawer__body) { padding: 0; overflow: hidden; }
.drawer-body { display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.drawer-header { display: flex; align-items: center; justify-content: space-between; padding: 16px; border-bottom: 1px solid #e4e7ed; flex-shrink: 0; }
.drawer-header h3 { margin: 0; font-size: 18px; }
.drawer-content { flex: 1; overflow-y: auto; padding: 16px; padding-bottom: 80px; -webkit-overflow-scrolling: touch; }
.comment-label { display: block; font-size: 14px; font-weight: 600; margin-bottom: 8px; color: #303133; }
.drawer-footer { position: fixed; bottom: 0; left: 0; right: 0; display: flex; gap: 12px; padding: 12px 16px; padding-bottom: calc(12px + env(safe-area-inset-bottom, 0px)); background: #fff; border-top: 1px solid #e4e7ed; z-index: 10; }
/* Project Link Card */
.project-link-card { padding: 8px 0; }
.project-section-title { font-size: 15px; font-weight: 600; margin: 16px 0 12px; color: #303133; }
.project-empty { padding: 40px 0; }
.knowledge-summary { color: #606266; font-size: 12px; line-height: 1.5; }
/* 历史明细 */
.history-costs { margin-top: 16px; }
.cost-json { margin: 0; font-size: 11px; line-height: 1.5; white-space: pre-wrap; word-break: break-all; max-height: 160px; overflow-y: auto; background: #f8f9fa; padding: 8px; border-radius: 4px; }
</style>
