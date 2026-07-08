<template>
  <el-form :model="form" label-width="120px" size="small">
    <!-- 一、项目基本信息区 -->
    <el-divider content-position="left">一、项目基本信息区</el-divider>
    <el-row :gutter="16">
      <el-col :span="8">
        <el-form-item label="项目名称">
          <el-input :model-value="autoProjectName" disabled placeholder="自动生成" />
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="产品类型">
          <el-select v-model="form.product_type" placeholder="选择产品类型" clearable style="width:100%">
            <el-option v-for="o in kb.product_type" :key="o.code" :label="o.name" :value="o.code" />
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
          <el-select v-model="form.target_market" placeholder="选择目标市场" clearable style="width:100%">
            <el-option v-for="o in kb.market" :key="o.code" :label="o.name" :value="o.code" />
          </el-select>
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="16">
      <el-col :span="6">
        <el-form-item label="系列名称">
          <el-select v-model="form.series_name" placeholder="选择系列" clearable style="width:100%">
            <el-option v-for="o in kb.series" :key="o.code" :label="o.name" :value="o.code" />
          </el-select>
        </el-form-item>
      </el-col>
      <el-col :span="6">
        <el-form-item label="温带">
          <el-select v-model="form.climate_zone" placeholder="选择温带" clearable style="width:100%">
            <el-option label="T1（温带）" value="T1" />
            <el-option label="T2（寒带）" value="T2" />
            <el-option label="T3（热带）" value="T3" />
          </el-select>
        </el-form-item>
      </el-col>
      <el-col :span="6">
        <el-form-item label="制冷剂">
          <el-select v-model="form.refrigerant" placeholder="选择制冷剂" clearable style="width:100%">
            <el-option label="R32" value="R32" />
            <el-option label="R410A" value="R410A" />
            <el-option label="R290" value="R290" />
            <el-option label="R454B" value="R454B" />
          </el-select>
        </el-form-item>
      </el-col>
      <el-col :span="6">
        <el-form-item label="能效等级">
          <el-select v-model="form.energy_rating" placeholder="能效星级" clearable style="width:100%">
            <el-option v-for="o in kb.energy_rating" :key="o.code" :label="o.name" :value="o.code" />
          </el-select>
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="16">
      <el-col :span="8">
        <el-form-item label="能力段">
          <el-select v-model="form.capacity_range" placeholder="选择能力段" clearable style="width:100%">
            <el-option v-for="o in kb.capacity" :key="o.code" :label="o.name" :value="o.code" />
          </el-select>
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="电压频率">
          <el-select v-model="form.voltage_freq" placeholder="选择电压频率" clearable style="width:100%">
            <el-option v-for="o in kb.voltage" :key="o.code" :label="o.name" :value="o.code" />
          </el-select>
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="客户名称">
          <el-input v-model="form.customer_name" placeholder="客户名称" />
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="16">
      <el-col :span="8">
        <el-form-item label="立项日期">
          <el-date-picker v-model="form.start_date" type="date" placeholder="立项日期" style="width:100%" value-format="YYYY-MM-DD" />
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="计划完成">
          <el-date-picker v-model="form.target_end_date" type="date" placeholder="计划完成日期" style="width:100%" value-format="YYYY-MM-DD" />
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="项目周期">
          <el-input :model-value="autoDuration" disabled placeholder="自动计算" />
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="16">
      <el-col :span="8">
        <el-form-item label="知识产权归属">
          <el-select v-model="form.ip_ownership" placeholder="选择IP归属" clearable style="width:100%">
            <el-option v-for="o in kb.ip_ownership" :key="o.code" :label="o.name" :value="o.code" />
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
          <el-select v-model="form.dev_category" placeholder="选择开发类别" clearable style="width:100%">
            <el-option label="全新开发" value="全新开发" />
            <el-option label="派生" value="派生" />
            <el-option label="降本优化" value="降本优化" />
          </el-select>
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="项目来源">
          <el-select v-model="form.project_origin" placeholder="选择项目来源" clearable style="width:100%">
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
    <el-form-item v-if="form.project_origin === '产品年度规划'" label="年度规划项">
      <el-select v-model="form.annual_planning_id" placeholder="选择关联的年度规划项" clearable filterable style="width:100%">
        <el-option v-for="item in planningItems" :key="item.id" :label="`${item.name} (${item.year})`" :value="item.id" />
      </el-select>
    </el-form-item>
    <el-form-item label="其他要求">
      <el-input v-model="form.other_requirements" type="textarea" :rows="2" placeholder="其他特殊要求" />
    </el-form-item>

    <!-- 二、项目背景与目标 -->
    <el-divider content-position="left">二、项目背景与目标</el-divider>
    <el-form-item label="立项背景与依据">
      <el-input v-model="form.background_basis" type="textarea" :rows="3" placeholder="项目立项背景、市场依据等" />
    </el-form-item>
    <el-row :gutter="16">
      <el-col :span="12">
        <el-form-item label="目标BOM成本">
          <el-input :model-value="form.bom_cost_target || '暂无数据'" disabled placeholder="← 成本核算Tab同步">
            <template #suffix><span style="color:#909399;font-size:12px">← 成本核算Tab同步</span></template>
          </el-input>
        </el-form-item>
      </el-col>
      <el-col :span="12">
        <el-form-item label="年销量预测">
          <el-input :model-value="form.annual_sales_forecast || '暂无数据'" disabled placeholder="← 成本核算Tab同步">
            <template #suffix><span style="color:#909399;font-size:12px">← 成本核算Tab同步</span></template>
          </el-input>
        </el-form-item>
      </el-col>
    </el-row>

    <!-- 三、市场分析 -->
    <el-divider content-position="left">三、市场分析</el-divider>
    <el-row :gutter="16">
      <el-col :span="12">
        <el-form-item label="能效要求">
          <el-input v-model="form.energy_efficiency_req" placeholder="如: SEER≥6.1" />
        </el-form-item>
      </el-col>
      <el-col :span="12">
        <el-form-item label-width="80px">
          <template #label>
            认证要求
            <el-tooltip content="从安全管理标准自动生成" placement="top">
              <el-icon style="margin-left:4px;cursor:help;color:#909399"><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-input :model-value="certText" disabled placeholder="自动生成">
            <template #suffix><span style="color:#67c23a;font-size:12px">自动</span></template>
          </el-input>
        </el-form-item>
      </el-col>
    </el-row>
    <el-form-item label="年度规划引用">
      <el-select v-model="form.annual_planning_ref" placeholder="选择年度规划引用" clearable filterable style="width:100%">
        <el-option v-for="item in planningItems" :key="item.id" :label="item.name" :value="item.name" />
      </el-select>
    </el-form-item>

    <!-- 客户关键需求表格 -->
    <el-divider content-position="left">客户关键需求</el-divider>
    <el-table :data="customerReqs" border size="small" class="section-table">
      <el-table-column prop="category" label="需求类别" width="120">
        <template #default="{ row }"><el-input v-model="row.category" size="small" placeholder="类别" /></template>
      </el-table-column>
      <el-table-column prop="description" label="需求描述" min-width="160">
        <template #default="{ row }"><el-input v-model="row.description" size="small" placeholder="需求描述" /></template>
      </el-table-column>
      <el-table-column prop="source" label="需求来源" width="120">
        <template #default="{ row }"><el-input v-model="row.source" size="small" placeholder="来源" /></template>
      </el-table-column>
      <el-table-column prop="tech_impact" label="技术影响" width="120">
        <template #default="{ row }"><el-input v-model="row.tech_impact" size="small" placeholder="技术影响" /></template>
      </el-table-column>
      <el-table-column prop="market_impact" label="市场影响" width="120">
        <template #default="{ row }"><el-input v-model="row.market_impact" size="small" placeholder="市场影响" /></template>
      </el-table-column>
      <el-table-column label="操作" width="70">
        <template #default="{ $index }">
          <el-button link type="danger" size="small" @click="$emit('remove-req-row', $index)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-button size="small" style="margin-top:8px" @click="$emit('add-req-row')">+ 添加行</el-button>

    <!-- 四、交付物 -->
    <el-divider content-position="left">四、交付物</el-divider>
    <el-row :gutter="16">
      <el-col :span="12">
        <el-form-item label="样机数量">
          <el-input-number v-model="form.sample_qty" :min="0" :step="1" style="width:100%" />
        </el-form-item>
      </el-col>
      <el-col :span="12">
        <el-form-item label="样机需求日期">
          <el-date-picker v-model="form.sample_required_date" type="date" placeholder="需求日期" style="width:100%" value-format="YYYY-MM-DD" />
        </el-form-item>
      </el-col>
    </el-row>
    <el-form-item label="交付物清单">
      <el-input v-model="form.deliverables" type="textarea" :rows="3" placeholder="项目交付物清单（样机/图纸/BOM/测试报告等）" />
    </el-form-item>

    <!-- 项目归属 -->
    <el-divider content-position="left">项目归属</el-divider>
    <el-form-item label="所属项目群" label-width="120px" size="small">
      <el-select v-model="form.program_id" placeholder="选择项目群" clearable filterable style="width:100%">
        <el-option v-for="p in programs" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
    </el-form-item>
    <el-form-item label="项目负责人" label-width="120px" size="small">
      <el-select v-model="form.leader_id" placeholder="从团队成员中选择" clearable filterable style="width:100%">
        <el-option v-for="u in teamUsers" :key="u.id" :label="`${u.full_name || u.username} (${u.role})`" :value="u.id" />
      </el-select>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
defineProps<{
  form: any
  kb: Record<string, any[]>
  autoProjectName: string
  autoDuration: string
  certText: string
  customerReqs: any[]
  planningItems: any[]
  programs: any[]
  teamUsers: any[]
}>()
defineEmits<{
  'add-req-row': []
  'remove-req-row': [index: number]
}>()
</script>
