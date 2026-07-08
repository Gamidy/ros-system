<template>
  <div>
    <!-- 流程引导 el-steps -->
    <el-steps :active="techStep" finish-status="success" align-center style="margin-bottom:20px;cursor:pointer">
      <el-step title="性能指标" description="核心性能参数" @click="$emit('update:techStep', 0)" />
      <el-step title="安全合规" description="法规标准要求" @click="$emit('update:techStep', 1)" />
      <el-step title="物料部件" description="关键物料与部件" @click="$emit('update:techStep', 2)" />
      <el-step title="附件/功能配置" description="配件与功能选配" @click="$emit('update:techStep', 3)" />
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
  </div>
</template>

<script setup lang="ts">
interface CorePerfRow { param_name: string; baseline: string; target_value: string; aux_competitor: string; tcl_competitor: string; source: string }
interface MaterialComponentRow { type: string; name: string; spec: string; qty: number; unit: string; usage: string; supplier: string; delivery_cycle: string; unit_price: number; candidate_vendors: string; remark: string }
interface SafetyComplianceRow { standard: string; applicable_market: string; key_requirement: string; verification_method: string; involved_parts: string; cert_cycle: string; remark: string }
interface ConfigRow { name: string; selection: string; _original?: string }

const props = defineProps<{
  tabStatus: Record<string, { valid: boolean }>
  techStep: number
  corePerfTable: CorePerfRow[]
  safetyComplianceTable: SafetyComplianceRow[]
  materialComponentTable: MaterialComponentRow[]
  accessoryConfigTable: ConfigRow[]
  featureConfigTable: ConfigRow[]
}>()

const emit = defineEmits<{
  'update:techStep': [val: number]
  'add-core-perf-row': []
  'remove-core-perf-row': [index: number]
  'add-material-row': []
  'remove-material-row': [index: number]
}>()

function addCorePerfRow() {
  props.corePerfTable.push({
    param_name: '', baseline: '', target_value: '',
    aux_competitor: '', tcl_competitor: '', source: 'manual'
  })
}
function removeCorePerfRow(index: number) {
  props.corePerfTable.splice(index, 1)
}
function addMaterialComponentRow() {
  props.materialComponentTable.push({
    type: '物料', name: '', spec: '', qty: 1, unit: '个', usage: '',
    supplier: '', delivery_cycle: '', unit_price: 0,
    candidate_vendors: '', remark: ''
  })
}
function removeMaterialComponentRow(index: number) {
  props.materialComponentTable.splice(index, 1)
}
</script>
