<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>目标市场配置</span>
          <el-button type="primary" @click="openMarketDialog()">新建市场</el-button>
        </div>
      </template>

      <div v-loading="loading">
        <el-row :gutter="16">
          <el-col v-for="m in markets" :key="m.id" :span="8" style="margin-bottom: 16px">
            <el-card shadow="hover" :body-style="{ padding: '12px' }">
              <template #header>
                <div class="market-card-header">
                  <span>
                    <strong>{{ m.name || m.market_code }}</strong>
                  </span>
                  <div>
                    <el-button link type="primary" size="small" @click="openMarketDialog(m)">编辑</el-button>
                    <el-button link type="danger" size="small" @click="removeMarket(m)">删除</el-button>
                  </div>
                </div>
              </template>

              <el-collapse v-model="activeCollapse" @change="onCollapseChange($event, m)">
                <el-collapse-item :name="`tests-${m.id}`" title="测试要求">
                  <div v-if="!m.testItems">点击展开加载...</div>
                  <div v-else>
                    <el-table :data="m.testItems" size="mini" stripe border max-height="200">
                      <el-table-column prop="test_code" label="测试编码" width="100" />
                      <el-table-column prop="description" label="描述" min-width="120" />
                      <el-table-column label="操作" width="60">
                        <template #default="{ row }">
                          <el-button link type="danger" size="small" @click="removeChildItem(m, 'tests', row.id)">×</el-button>
                        </template>
                      </el-table-column>
                    </el-table>
                    <el-button size="small" type="primary" style="margin-top: 8px" @click="showAddChildDialog(m, 'tests')">+ 添加</el-button>
                  </div>
                </el-collapse-item>

                <el-collapse-item :name="`certs-${m.id}`" title="认证要求">
                  <div v-if="!m.certItems">点击展开加载...</div>
                  <div v-else>
                    <el-table :data="m.certItems" size="mini" stripe border max-height="200">
                      <el-table-column prop="cert_type" label="认证类型" width="100" />
                      <el-table-column prop="cert_body" label="认证机构" min-width="120" />
                      <el-table-column label="操作" width="60">
                        <template #default="{ row }">
                          <el-button link type="danger" size="small" @click="removeChildItem(m, 'certs', row.id)">×</el-button>
                        </template>
                      </el-table-column>
                    </el-table>
                    <el-button size="small" type="primary" style="margin-top: 8px" @click="showAddChildDialog(m, 'certs')">+ 添加</el-button>
                  </div>
                </el-collapse-item>

                <el-collapse-item :name="`standards-${m.id}`" title="标准要求">
                  <div v-if="!m.standardItems">点击展开加载...</div>
                  <div v-else>
                    <el-table :data="m.standardItems" size="mini" stripe border max-height="200">
                      <el-table-column prop="standard_code" label="标准编号" width="100" />
                      <el-table-column prop="standard_name" label="标准名称" min-width="150" />
                      <el-table-column label="操作" width="60">
                        <template #default="{ row }">
                          <el-button link type="danger" size="small" @click="removeChildItem(m, 'standards', row.id)">×</el-button>
                        </template>
                      </el-table-column>
                    </el-table>
                    <el-button size="small" type="primary" style="margin-top: 8px" @click="showAddChildDialog(m, 'standards')">+ 添加</el-button>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </el-card>

    <!-- 新建/编辑市场对话框 -->
    <el-dialog v-model="marketDialogVisible" :title="editingMarketId ? '编辑市场' : '新建市场'" width="450">
      <el-form :model="marketForm" label-width="100">
        <el-form-item label="名称" required>
          <el-input v-model="marketForm.name" placeholder="如 欧盟, 越南, 中国" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="marketDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveMarket">保存</el-button>
      </template>
    </el-dialog>

    <!-- 添加子项对话框 -->
    <el-dialog v-model="childDialogVisible" :title="childDialogTitle" width="500">
      <el-form :model="childForm" label-width="100">
        <template v-if="childType === 'tests'">
          <el-form-item label="测试编码" required>
            <el-input v-model="childForm.test_code" placeholder="如 NOISE-001" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="childForm.description" type="textarea" :rows="2" />
          </el-form-item>
        </template>
        <template v-if="childType === 'certs'">
          <el-form-item label="认证类型" required>
            <el-input v-model="childForm.cert_type" placeholder="如 CE, UL" />
          </el-form-item>
          <el-form-item label="认证机构">
            <el-input v-model="childForm.cert_body" placeholder="如 TÜV" />
          </el-form-item>
        </template>
        <template v-if="childType === 'standards'">
          <el-form-item label="标准编号" required>
            <el-input v-model="childForm.standard_code" placeholder="如 IEC 60335" />
          </el-form-item>
          <el-form-item label="标准名称">
            <el-input v-model="childForm.standard_name" placeholder="标准全称" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="childDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="childSaving" @click="saveChildItem">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'
import type { TableRow } from '@/types/common'

const markets = ref<TableRow[]>([])
const loading = ref(false)
const saving = ref(false)
const childSaving = ref(false)
const marketDialogVisible = ref(false)
const editingMarketId = ref<number | null>(null)
const marketForm = ref({ market_code: '', name: '' })

const activeCollapse = ref<string[]>([])

const childDialogVisible = ref(false)
const childDialogTitle = ref('')
const childType = ref<'tests' | 'certs' | 'standards'>('tests')
const childTargetMarket = ref<TableRow | null>(null)
const childForm = ref<Record<string, unknown>>({})

async function fetchMarkets() {
  loading.value = true
  try {
    const res = await api.get('/target-markets')
    markets.value = (res.data || []).map((m: TableRow) => ({
      ...m,
      testItems: null as TableRow[] | null,
      certItems: null as TableRow[] | null,
      standardItems: null as TableRow[] | null,
    }))
  } finally { loading.value = false }
}

async function onCollapseChange(val: string[], market: TableRow) {
  const key = val?.slice(-1)?.[0] || ''
  if (key.startsWith('tests-') && !market.testItems) {
    try { const r = await api.get(`/target-markets/${market.id}/tests`); market.testItems = r.data } catch { market.testItems = [] }
  }
  if (key.startsWith('certs-') && !market.certItems) {
    try { const r = await api.get(`/target-markets/${market.id}/certifications`); market.certItems = r.data } catch { market.certItems = [] }
  }
  if (key.startsWith('standards-') && !market.standardItems) {
    try { const r = await api.get(`/target-markets/${market.id}/standards`); market.standardItems = r.data } catch { market.standardItems = [] }
  }
}

function openMarketDialog(row?: TableRow) {
  if (row) {
    editingMarketId.value = (row.id ?? 0) as number
    marketForm.value = { market_code: row.market_code || '', name: row.name || '' }
  } else {
    editingMarketId.value = null
    marketForm.value = { market_code: '', name: '' }
  }
  marketDialogVisible.value = true
}

async function saveMarket() {
  saving.value = true
  try {
    // 新建时自动用名称作为市场编码
    const payload = { ...marketForm.value }
    if (!editingMarketId.value && !payload.market_code) {
      payload.market_code = payload.name
    }
    if (editingMarketId.value) {
      await api.put(`/target-markets/${editingMarketId.value}`, payload)
      ElMessage.success('更新成功')
    } else {
      await api.post('/target-markets', payload)
      ElMessage.success('创建成功')
    }
    marketDialogVisible.value = false
    await fetchMarkets()
  } finally { saving.value = false }
}

async function removeMarket(row: TableRow) {
  try {
    await ElMessageBox.confirm('确定删除此市场？', '确认', { type: 'warning' })
    await api.delete(`/target-markets/${row.id}`)
    ElMessage.success('删除成功')
    await fetchMarkets()
  } catch { /* cancelled */ }
}

function showAddChildDialog(market: TableRow, type: 'tests' | 'certs' | 'standards') {
  childTargetMarket.value = market
  childType.value = type
  childForm.value = {}
  if (type === 'tests') {
    childDialogTitle.value = '添加测试项'
    childForm.value = { test_code: '', description: '' }
  } else if (type === 'certs') {
    childDialogTitle.value = '添加认证要求'
    childForm.value = { cert_type: '', cert_body: '' }
  } else {
    childDialogTitle.value = '添加标准要求'
    childForm.value = { standard_code: '', standard_name: '' }
  }
  childDialogVisible.value = true
}

async function saveChildItem() {
  const market = childTargetMarket.value
  if (!market) return
  childSaving.value = true
  try {
    let url = ''
    if (childType.value === 'tests') {
      url = `/target-markets/${market.id}/tests`
    } else if (childType.value === 'certs') {
      url = `/target-markets/${market.id}/certifications`
    } else {
      url = `/target-markets/${market.id}/standards`
    }
    await api.post(url, childForm.value)
    ElMessage.success('添加成功')
    childDialogVisible.value = false
    // Reload the relevant items
    if (childType.value === 'tests') {
      const r = await api.get(`/target-markets/${market.id}/tests`); market.testItems = r.data
    } else if (childType.value === 'certs') {
      const r = await api.get(`/target-markets/${market.id}/certifications`); market.certItems = r.data
    } else {
      const r = await api.get(`/target-markets/${market.id}/standards`); market.standardItems = r.data
    }
  } finally { childSaving.value = false }
}

async function removeChildItem(market: TableRow, type: string, itemId: number) {
  try {
    await ElMessageBox.confirm('确定删除？', '确认', { type: 'warning' })
    let url = ''
    if (type === 'tests') url = `/target-markets/${market.id}/tests/${itemId}`
    else if (type === 'certs') url = `/target-markets/${market.id}/certifications/${itemId}`
    else url = `/target-markets/${market.id}/standards/${itemId}`
    await api.delete(url)
    ElMessage.success('删除成功')
    // Reload
    if (type === 'tests') {
      const r = await api.get(`/target-markets/${market.id}/tests`); market.testItems = r.data
    } else if (type === 'certs') {
      const r = await api.get(`/target-markets/${market.id}/certifications`); market.certItems = r.data
    } else {
      const r = await api.get(`/target-markets/${market.id}/standards`); market.standardItems = r.data
    }
  } catch { /* cancelled */ }
}

onMounted(fetchMarkets)
</script>

<style scoped>
.page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
.market-card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
