<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>样机管理</span>
          <el-button type="primary" @click="openDialog()">新建样机</el-button>
        </div>
      </template>

      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="6">
          <el-select v-model="filterStatus" placeholder="状态筛选" clearable @change="fetchData" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option label="生产中" value="producing" />
            <el-option label="测试中" value="testing" />
            <el-option label="已完成" value="done" />
            <el-option label="已报废" value="scrapped" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filterType" placeholder="样机类型" clearable @change="fetchData" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option label="手工样机" value="hand_sample" />
            <el-option label="模具首样" value="模具首样" />
            <el-option label="工程样机" value="工程样机" />
            <el-option label="小批样机" value="小批样机" />
            <el-option label="认证样机" value="认证样机" />
          </el-select>
        </el-col>
      </el-row>

      <el-table :data="items" stripe border max-height="500" v-loading="loading" @expand-change="onExpandChange" :expand-row-keys="expandRowKeys" row-key="id">
        <el-table-column type="expand" width="40">
          <template #default="{ row }">
            <div v-if="row._timeline">
              <h4 style="margin: 0 0 8px 0; font-size: 14px;">关联实验判定时间线</h4>
              <el-table :data="row._timeline" size="small" stripe border>
                <el-table-column prop="test_title" label="实验名称" min-width="150" />
                <el-table-column prop="result" label="判定结果" width="100">
                  <template #default="{ row: t }">
                    <el-tag :type="t.result === 'PASS' ? 'success' : t.result === 'FAIL' ? 'danger' : 'warning'" size="small">{{ t.result || '-' }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="updated_at" label="判定时间" width="160">
                  <template #default="{ row: t }">{{ t.updated_at?.substring(0, 16) || '-' }}</template>
                </el-table-column>
              </el-table>
              <div v-if="!row._timeline.length" style="color: #999; padding: 12px;">暂无关联实验记录</div>
            </div>
            <div v-else style="padding: 12px; color: #999;">加载中...</div>
          </template>
        </el-table-column>
        <el-table-column prop="proto_no" label="样机编号" width="140" />
        <el-table-column prop="product_code" label="产品编码" width="120" />
        <el-table-column prop="project_code" label="项目编码" width="120" />
        <el-table-column label="版本" width="70">
          <template #default="{ row }">
            <el-tag v-if="row.version" :type="versionType(row.version)" size="small">{{ row.version }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="proto_type" label="样机类型" width="110">
          <template #default="{ row }">
            <el-tag size="small">{{ row.proto_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="stage" label="阶段" width="80" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="quantity" label="数量" width="70" />
        <el-table-column prop="material_status" label="齐套状态" width="100" />
        <el-table-column prop="produced_date" label="产出日期" width="110" />
        <el-table-column prop="test_date" label="测试日期" width="110" />
        <el-table-column prop="result" label="结果" width="80">
          <template #default="{ row }">
            <el-tag :type="row.result === 'pass' ? 'success' : row.result === 'fail' ? 'danger' : 'info'" size="small">
              {{ row.result || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="150" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button
              v-if="row.version"
              link type="warning" size="small"
              :loading="upgradingId === row.id"
              @click="upgradeVersion(row)"
            >升级版本</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑样机' : '新建样机'" width="550">
      <el-form :model="form" label-width="100">
        <el-form-item label="产品编码" required>
          <el-input v-model="form.product_code" placeholder="如 EU-09K" />
        </el-form-item>
        <el-form-item label="项目">
          <el-select v-model="form.project_id" clearable filterable placeholder="选择项目" style="width: 100%">
            <el-option v-for="p in projects" :key="p.id" :label="p.name || p.project_code" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="版本">
          <el-select v-model="form.version" clearable placeholder="选择版本" style="width: 100%">
            <el-option label="P0 - 初始样机" value="P0" />
            <el-option label="P1 - 工程样机" value="P1" />
            <el-option label="P2 - 试产样机" value="P2" />
            <el-option label="P3 - 量产样机" value="P3" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目编码">
          <el-input v-model="form.project_code" placeholder="如 P2026-01" />
        </el-form-item>
        <el-form-item label="样机类型" required>
          <el-select v-model="form.proto_type" style="width: 100%">
            <el-option label="手工样机" value="hand_sample" />
            <el-option label="模具首样" value="模具首样" />
            <el-option label="工程样机" value="工程样机" />
            <el-option label="小批样机" value="小批样机" />
            <el-option label="认证样机" value="认证样机" />
          </el-select>
        </el-form-item>
        <el-form-item label="阶段">
          <el-select v-model="form.stage" style="width: 100%" placeholder="关联Gate阶段">
            <el-option label="M4" value="M4" />
            <el-option label="M5" value="M5" />
            <el-option label="M6" value="M6" />
            <el-option label="M7" value="M7" />
            <el-option label="M8" value="M8" />
          </el-select>
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="form.quantity" :min="1" :max="100" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const items = ref<any[]>([])
const projects = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const filterStatus = ref('')
const filterType = ref('')
const expandRowKeys = ref<string[]>([])
const upgradingId = ref<number | null>(null)

const form = ref<any>({
  product_code: '', project_code: '', project_id: null,
  version: '', proto_type: '',
  stage: null, quantity: 1, remark: ''
})

const statusMap: Record<string, string> = {
  producing: '生产中', testing: '测试中', done: '已完成', scrapped: '已报废'
}
const statusTypeMap: Record<string, string> = {
  producing: 'warning', testing: 'warning', done: 'success', scrapped: 'info'
}

function statusLabel(s: string) { return statusMap[s] || s }
function statusType(s: string) { return statusTypeMap[s] || 'info' as any }
function versionType(v: string) {
  if (v === 'P0') return 'info'
  if (v === 'P1') return 'warning'
  if (v === 'P2') return 'success'
  if (v === 'P3') return 'danger'
  return 'info'
}

async function fetchData() {
  loading.value = true
  try {
    let url = '/certifications/prototypes'
    const params: string[] = []
    if (filterStatus.value) params.push(`status=${filterStatus.value}`)
    if (filterType.value) params.push(`proto_type=${filterType.value}`)
    if (params.length) url += '?' + params.join('&')
    const r = await api.get(url)
    items.value = r.data
  } finally { loading.value = false }
}

async function fetchProjects() {
  try {
    const res = await api.get('/projects')
    projects.value = res.data
  } catch { /* optional */ }
}

function openDialog(row?: any) {
  if (row) {
    editingId.value = row.id
    form.value = {
      product_code: row.product_code || '',
      project_code: row.project_code || '',
      project_id: row.project_id || null,
      version: row.version || '',
      proto_type: row.proto_type || '',
      stage: row.stage || null,
      quantity: row.quantity ?? 1,
      remark: row.remark || '',
    }
  } else {
    editingId.value = null
    form.value = { product_code: '', project_code: '', project_id: null, version: '', proto_type: '', stage: null, quantity: 1, remark: '' }
  }
  dialogVisible.value = true
}

async function save() {
  saving.value = true
  try {
    const payload = { ...form.value }
    if (!payload.project_code) delete payload.project_code
    if (!payload.project_id) delete payload.project_id
    if (!payload.version) delete payload.version
    if (!payload.stage) delete payload.stage

    if (editingId.value) {
      await api.put(`/certifications/prototypes/${editingId.value}`, payload)
      ElMessage.success('更新成功')
    } else {
      await api.post('/certifications/prototypes', payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } finally { saving.value = false }
}

async function upgradeVersion(row: any) {
  upgradingId.value = row.id
  try {
    await api.post(`/prototypes/${row.id}/upgrade`)
    ElMessage.success('版本升级成功')
    await fetchData()
  } finally { upgradingId.value = null }
}

async function onExpandChange(row: any, expanded: boolean) {
  if (!expanded) return
  // Load timeline data
  row._timeline = null
  expandRowKeys.value = [String(row.id)]
  try {
    const res = await api.get(`/prototypes/${row.id}/test-timeline`)
    row._timeline = res.data || []
  } catch {
    row._timeline = []
  }
}

onMounted(() => {
  fetchData()
  fetchProjects()
})
</script>

<style scoped>
.page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
</style>
