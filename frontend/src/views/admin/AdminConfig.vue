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
