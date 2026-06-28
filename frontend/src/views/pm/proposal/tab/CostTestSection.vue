<template>
  <div class="cost-test-section">
    <!-- 4. 测试费用 -->
    <el-card shadow="never" class="cost-section">
      <template #header>
        <span class="section-header">4️⃣ 测试费用 <small class="section-hint">（手动填写）</small></span>
      </template>
      <el-form :model="testForm" label-width="140px" size="small">
        <el-form-item label="测试费用(万元)">
          <el-input-number v-model="testForm.cost" :min="0" :precision="2" :step="0.1" size="small" controls-position="right" style="width:120px" @change="emitTestUpdate" />
        </el-form-item>
        <el-form-item label="测试费用说明">
          <el-input v-model="testForm.remark" type="textarea" :rows="2" size="small" placeholder="测试项目说明" @input="emitTestUpdate" />
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 5. 认证费用 -->
    <el-card shadow="never" class="cost-section">
      <template #header>
        <span class="section-header">5️⃣ 认证费用 <small class="section-hint">（从安全合规标准×配置自动生成）</small></span>
      </template>
      <el-table :data="certCostTable" size="small" border stripe v-if="certCostTable.length > 0">
        <el-table-column label="认证标准" prop="certName" width="120" />
        <el-table-column label="认证机构" prop="certBody" width="120" />
        <el-table-column label="费用(万元)" width="110">
          <template #default="{ row }">
            <el-input-number v-model="row.costWan" :min="0" :precision="2" :step="0.5" size="small" controls-position="right" style="width:90px" @change="emitTestUpdate" />
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="160">
          <template #default="{ row }">
            <el-input v-model="row.remark" size="small" placeholder="备注" @input="emitTestUpdate" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="60" fixed="right">
          <template #default="{ $index }">
            <el-button type="danger" size="small" link @click="removeCertRow($index)">✕</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="请在「技术要求」Tab 填写安全合规标准以自动生成认证费用" :image-size="60" />
      <div class="section-actions">
        <el-button size="small" type="primary" plain @click="addCertRow">+ 手动添加认证</el-button>
        <span class="section-total">小计：<el-tag type="primary" size="large" effect="dark">{{ certCostTotal.toFixed(2) }} 万元</el-tag></span>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, computed, watch } from 'vue'

interface CertCostRow {
  certName: string
  certBody: string
  costWan: number
  remark: string
}

const props = defineProps<{
  data: Record<string, unknown>
}>()

const emit = defineEmits<{
  update: [patch: Record<string, unknown>]
}>()

const formData = computed(() => props.data)

// Test Cost
const testForm = reactive({
  cost: 0,
  remark: '',
})

// Cert Cost
const certCostTable = reactive<CertCostRow[]>([])

function addCertRow(): void {
  certCostTable.push({ certName: '', certBody: '', costWan: 3, remark: '' })
  emitTestUpdate()
}

function removeCertRow(index: number): void {
  certCostTable.splice(index, 1)
  emitTestUpdate()
}

const certCostTotal = computed(() => {
  return certCostTable.reduce((sum, row) => sum + row.costWan, 0)
})

function generateCertCosts(): void {
  const safetyRaw = formData.value?.safety_compliance
  if (!safetyRaw || typeof safetyRaw !== 'string') return

  const certCostConfig: Record<string, number> = { UL: 20, CE: 3 }
  const defaultCost = 3

  const certNames: string[] = extractCertNames(safetyRaw)

  const existingMap = new Map<string, CertCostRow>()
  certCostTable.forEach((r) => {
    if (r.certName) existingMap.set(r.certName, r)
  })

  certCostTable.length = 0
  const seen = new Set<string>()
  certNames.forEach((name) => {
    if (seen.has(name)) return
    seen.add(name)
    const existing = existingMap.get(name)
    const cost = existing?.costWan ?? certCostConfig[name] ?? defaultCost
    certCostTable.push({
      certName: name,
      certBody: name,
      costWan: cost,
      remark: existing?.remark ?? (certCostConfig[name] !== undefined ? '' : '自动生成'),
    })
  })
  emitTestUpdate()
}

function extractCertNames(text: string): string[] {
  const names: string[] = []
  const pattern = /\b([A-Z]{2,8})\b/g
  let m: RegExpExecArray | null
  const regex = new RegExp(pattern)
  while ((m = regex.exec(text)) !== null) {
    const name = m[1]
    if (!/^\d/.test(name) && !['JSON', 'THE', 'AND', 'FOR', 'NOT', 'THIS', 'THAT', 'FROM', 'WITH'].includes(name)) {
      names.push(name)
    }
  }
  return [...new Set(names)]
}

function emitTestUpdate() {
  emit('update', {
    test_costs: JSON.stringify({
      cost: testForm.cost,
      remark: testForm.remark,
    }),
    cert_costs: JSON.stringify({
      items: certCostTable.map((r) => ({
        cert_name: r.certName,
        cert_body: r.certBody,
        cost_wan: r.costWan,
        remark: r.remark,
      })),
      total: certCostTotal.value,
    }),
  })
}

// Watch safety_compliance from sibling tab → regenerate cert costs
watch(() => formData.value?.safety_compliance, (val) => {
  if (val && typeof val === 'string' && val.length > 0) {
    generateCertCosts()
  }
}, { immediate: false })

// Restore from saved data
function restoreFromData() {
  // Restore test costs
  const testRaw = formData.value?.test_costs
  if (testRaw && typeof testRaw === 'string') {
    try {
      const parsed = JSON.parse(testRaw)
      if (parsed.cost !== undefined) testForm.cost = parsed.cost
      if (parsed.remark !== undefined) testForm.remark = parsed.remark
    } catch (e: unknown) {
      // ignore
    }
  }

  // Restore cert costs
  const certRaw = formData.value?.cert_costs
  if (certRaw && typeof certRaw === 'string') {
    try {
      const parsed = JSON.parse(certRaw)
      if (parsed.items && Array.isArray(parsed.items)) {
        certCostTable.length = 0
        parsed.items.forEach((item: Record<string, unknown>) => {
          certCostTable.push({
            certName: (item.cert_name as string) || '',
            certBody: (item.cert_body as string) || '',
            costWan: (item.cost_wan as number) || 0,
            remark: (item.remark as string) || '',
          })
        })
      }
    } catch (e: unknown) {
      // ignore
    }
  }
}

// Init
restoreFromData()
</script>

<style scoped>
.cost-section { margin-bottom: 16px; border-left: 3px solid #409eff; }
.section-header { font-size: 15px; font-weight: 600; color: #303133; }
.section-hint { color: #909399; font-weight: normal; font-size: 12px; margin-left: 6px; }
.section-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 10px; }
.section-total { text-align: right; margin-top: 10px; font-size: 13px; color: #606266; }
</style>
