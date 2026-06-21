<template>
  <div class="admin-config">
    <h2>⚙️ 系统设置 — 成本核算参数</h2>

    <!-- 单套成本表 -->
    <el-card shadow="never" class="config-section">
      <template #header>
        <span>📐 样机单套成本（万元）</span>
      </template>
      <el-table :data="unitCostRows" border size="small">
        <el-table-column prop="key" label="冷量段" width="100" />
        <el-table-column label="费用(万元)">
          <template #default="{ row }">
            <el-input-number v-model="row.value" :min="0" :step="0.001" size="small" controls-position="right" style="width:140px" />
          </template>
        </el-table-column>
        <el-table-column label="折合(元)" width="100">
          <template #default="{ row }">
            {{ (row.value * 10000).toFixed(0) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 测试单价 -->
    <el-card shadow="never" class="config-section">
      <template #header>
        <span>🧪 测试单价</span>
      </template>
      <el-form label-width="120px" size="small">
        <el-form-item label="单价(万元/天)">
          <el-input-number v-model="testUnitPrice" :min="0" :step="0.01" size="small" controls-position="right" />
        </el-form-item>
        <el-form-item label="折合">
          <span class="hint">{{ (testUnitPrice * 10000).toFixed(0) }} 元/天</span>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 制造费用 -->
    <el-card shadow="never" class="config-section">
      <template #header>
        <span>🏭 制造费用阈值</span>
      </template>
      <el-table :data="mfgCostRows" border size="small">
        <el-table-column prop="max_kw" label="冷量范围" width="150">
          <template #default="{ row, $index }">
            ≤{{ row.max_kw }}K{{ $index === mfgCostRows.length - 1 ? ' 以上' : '' }}
          </template>
        </el-table-column>
        <el-table-column label="费用(元)">
          <template #default="{ row }">
            <el-input-number v-model="row.cost" :min="0" :step="1" size="small" controls-position="right" style="width:100px" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 认证费用 -->
    <el-card shadow="never" class="config-section">
      <template #header>
        <span>📜 认证费用（万元）</span>
      </template>
      <el-table :data="certCostRows" border size="small">
        <el-table-column prop="key" label="认证类型" width="150" />
        <el-table-column label="费用(万元)">
          <template #default="{ row }">
            <el-input-number v-model="row.value" :min="0" :step="1" size="small" controls-position="right" style="width:140px" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 配件默认选项 -->
    <el-card shadow="never" class="config-section">
      <template #header>
        <div class="card-header">
          <span>🔌 配件默认选项</span>
          <el-button type="primary" size="small" @click="addAccessoryDefault">+ 添加</el-button>
        </div>
      </template>
      <el-table :data="accessoryDefaultRows" border size="small">
        <el-table-column label="市场" width="140">
          <template #default="{ row }">
            <el-input v-model="row.market" size="small" placeholder="如: 沙特" />
          </template>
        </el-table-column>
        <el-table-column label="配件名称" min-width="160">
          <template #default="{ row }">
            <el-input v-model="row.name" size="small" placeholder="配件名称" />
          </template>
        </el-table-column>
        <el-table-column label="默认选配" width="130">
          <template #default="{ row }">
            <el-select v-model="row.default_selection" size="small" style="width:100%">
              <el-option label="标配" value="标配" />
              <el-option label="选配" value="选配" />
              <el-option label="不配" value="不配" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="70">
          <template #default="{ $index }">
            <el-button link type="danger" size="small" @click="accessoryDefaultRows.splice($index, 1)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 功能默认选项 -->
    <el-card shadow="never" class="config-section">
      <template #header>
        <div class="card-header">
          <span>⚙️ 功能默认选项</span>
          <el-button type="primary" size="small" @click="addFeatureDefault">+ 添加</el-button>
        </div>
      </template>
      <el-table :data="featureDefaultRows" border size="small">
        <el-table-column label="市场" width="140">
          <template #default="{ row }">
            <el-input v-model="row.market" size="small" placeholder="如: 沙特" />
          </template>
        </el-table-column>
        <el-table-column label="功能名称" min-width="160">
          <template #default="{ row }">
            <el-input v-model="row.name" size="small" placeholder="功能名称" />
          </template>
        </el-table-column>
        <el-table-column label="默认选配" width="130">
          <template #default="{ row }">
            <el-select v-model="row.default_selection" size="small" style="width:100%">
              <el-option label="标配" value="标配" />
              <el-option label="选配" value="选配" />
              <el-option label="不配" value="不配" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="70">
          <template #default="{ $index }">
            <el-button link type="danger" size="small" @click="featureDefaultRows.splice($index, 1)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 试制数量 -->
    <el-card shadow="never" class="config-section">
      <template #header><span>🔧 试制数量（按项目等级）</span></template>
      <el-table :data="trialQtyRows" border size="small">
        <el-table-column prop="class" label="等级" width="80" />
        <el-table-column label="试制台数">
          <template #default="{ row }">
            <el-input-number v-model="row.qty" :min="1" :step="1" size="small" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 产品类型简写映射 -->
    <el-card shadow="never" class="config-section">
      <template #header>
        <div class="card-header">
          <span>📝 产品类型简写</span>
          <el-button type="primary" size="small" @click="addShortNameRow">+ 添加</el-button>
        </div>
      </template>
      <el-table :data="shortNameRows" border size="small">
        <el-table-column label="产品类型全称">
          <template #default="{ row }">
            <el-input v-model="row.full" size="small" placeholder="如: 分体式壁挂机" />
          </template>
        </el-table-column>
        <el-table-column label="简写">
          <template #default="{ row }">
            <el-input v-model="row.short" size="small" placeholder="如: 挂机" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="70">
          <template #default="{ $index }">
            <el-button link type="danger" size="small" @click="shortNameRows.splice($index, 1)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <div class="save-bar">
      <el-button type="primary" @click="saveAll" :loading="saving">💾 保存全部配置</el-button>
      <span v-if="saveSuccess" class="success-msg">✅ 保存成功</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const saving = ref(false)
const saveSuccess = ref(false)

// 单套成本
const unitCostRows = reactive([
  { key: '7K', value: 0.075 },
  { key: '9K', value: 0.095 },
  { key: '12K', value: 0.105 },
  { key: '18K', value: 0.142 },
  { key: '24K', value: 0.178 },
])

// 测试单价
const testUnitPrice = ref(0.11)

// 制造费用
const mfgCostRows = reactive([
  { max_kw: 12, cost: 50 },
  { max_kw: 999, cost: 60 },
])

// 认证费用
const certCostRows = reactive([
  { key: 'UL', value: 20 },
  { key: 'CE', value: 3 },
  { key: '其他', value: 3 },
])

// 配件默认选项
interface AccessoryDefaultRow { market: string; name: string; default_selection: string }
const accessoryDefaultRows = reactive<AccessoryDefaultRow[]>([
  { market: '沙特', name: '遥控器', default_selection: '标配' },
  { market: '沙特', name: '安装支架', default_selection: '标配' },
])

function addAccessoryDefault() {
  accessoryDefaultRows.push({ market: '', name: '', default_selection: '选配' })
}

// 功能默认选项
interface FeatureDefaultRow { market: string; name: string; default_selection: string }
const featureDefaultRows = reactive<FeatureDefaultRow[]>([
  { market: '沙特', name: '自清洁', default_selection: '标配' },
  { market: '沙特', name: '防直吹', default_selection: '标配' },
])

function addFeatureDefault() {
  featureDefaultRows.push({ market: '', name: '', default_selection: '选配' })
}

// 试制数量（按项目等级）
interface TrialQtyRow { class: string; qty: number }
const trialQtyRows = reactive<TrialQtyRow[]>([
  { class: 'T', qty: 5 },
  { class: 'A', qty: 3 },
  { class: 'B', qty: 2 },
  { class: 'C', qty: 1 },
])

// 产品类型简写
interface ShortNameRow { full: string; short: string }
const shortNameRows = reactive<ShortNameRow[]>([
  { full: '分体式壁挂机', short: '挂机' },
  { full: '分体立柜机', short: '柜机' },
  { full: '窗机', short: '窗机' },
])
function addShortNameRow() {
  shortNameRows.push({ full: '', short: '' })
}

async function loadConfig() {
  try {
    const res = await api.get('/admin/config')
    const data = res.data?.data || {}

    if (data.proto_unit_cost) {
      const parsed = JSON.parse(data.proto_unit_cost)
      Object.entries(parsed).forEach(([k, v]: [string, any]) => {
        const row = unitCostRows.find(r => r.key === k)
        if (row) row.value = Number(v)
      })
    }
    if (data.test_unit_price) testUnitPrice.value = Number(data.test_unit_price)
    if (data.mfg_cost_threshold) {
      const parsed = JSON.parse(data.mfg_cost_threshold)
      parsed.forEach((item: any, i: number) => {
        if (mfgCostRows[i]) {
          mfgCostRows[i].max_kw = item.max_kw
          mfgCostRows[i].cost = item.cost
        }
      })
    }
    if (data.cert_cost) {
      const parsed = JSON.parse(data.cert_cost)
      Object.entries(parsed).forEach(([k, v]: [string, any]) => {
        const row = certCostRows.find(r => r.key === k)
        if (row) row.value = Number(v)
      })
    }
    if (data.accessory_defaults) {
      const parsed = JSON.parse(data.accessory_defaults)
      if (Array.isArray(parsed)) {
        accessoryDefaultRows.length = 0
        parsed.forEach((item: any) => accessoryDefaultRows.push({ market: item.market || '', name: item.name || '', default_selection: item.default_selection || '选配' }))
      }
    }
    if (data.feature_defaults) {
      const parsed = JSON.parse(data.feature_defaults)
      if (Array.isArray(parsed)) {
        featureDefaultRows.length = 0
        parsed.forEach((item: any) => featureDefaultRows.push({ market: item.market || '', name: item.name || '', default_selection: item.default_selection || '选配' }))
      }
    }
    if (data.trial_qty_per_class) {
      const parsed = JSON.parse(data.trial_qty_per_class)
      trialQtyRows.length = 0
      Object.entries(parsed).forEach(([cls, qty]: [string, any]) => {
        trialQtyRows.push({ class: cls, qty: Number(qty) })
      })
    }
    if (data.product_short_names) {
      const parsed = JSON.parse(data.product_short_names)
      shortNameRows.length = 0
      Object.entries(parsed).forEach(([full, short]: [string, any]) => {
        shortNameRows.push({ full, short: String(short) })
      })
    }
  } catch { /* use defaults */ }
}

async function saveAll() {
  saving.value = true
  saveSuccess.value = false
  try {
    const payload: Record<string, string> = {
      proto_unit_cost: JSON.stringify(
        Object.fromEntries(unitCostRows.map(r => [r.key, r.value]))
      ),
      test_unit_price: String(testUnitPrice.value),
      mfg_cost_threshold: JSON.stringify(
        mfgCostRows.map(r => ({ max_kw: r.max_kw, cost: r.cost }))
      ),
      cert_cost: JSON.stringify(
        Object.fromEntries(certCostRows.map(r => [r.key, r.value]))
      ),
      accessory_defaults: JSON.stringify(
        accessoryDefaultRows.map(r => ({ market: r.market, name: r.name, default_selection: r.default_selection }))
      ),
      feature_defaults: JSON.stringify(
        featureDefaultRows.map(r => ({ market: r.market, name: r.name, default_selection: r.default_selection }))
      ),
      trial_qty_per_class: JSON.stringify(
        Object.fromEntries(trialQtyRows.map(r => [r.class, r.qty]))
      ),
      product_short_names: JSON.stringify(
        Object.fromEntries(shortNameRows.map(r => [r.full, r.short]))
      ),
    }
    await api.put('/admin/config/batch', payload)
    saveSuccess.value = true
    ElMessage.success('配置已保存')
  } catch {
    ElMessage.error('保存失败，请确认您有管理员权限')
  } finally {
    saving.value = false
  }
}

onMounted(loadConfig)
</script>

<style scoped>
.admin-config {
  padding: 16px;
  max-width: 800px;
}
.admin-config h2 {
  margin: 0 0 16px;
  font-size: 18px;
}
.config-section {
  margin-bottom: 16px;
}
.save-bar {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.success-msg {
  color: #67c23a;
  font-size: 14px;
}
.hint {
  color: #909399;
  font-size: 13px;
}
</style>
