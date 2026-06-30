<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>认证管理</span>
          <el-button type="primary" @click="openDialog()">新建认证</el-button>
        </div>
      </template>

      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="6">
          <el-select v-model="filterStatus" placeholder="状态筛选" clearable @change="fetchData" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option label="计划中" value="planning" />
            <el-option label="准备中" value="preparing" />
            <el-option label="测试中" value="testing" />
            <el-option label="已提交" value="submitted" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
            <el-option label="即将过期" value="expiring" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filterMarket" placeholder="目标市场" clearable @change="fetchData" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option label="欧盟" value="EU" />
            <el-option label="越南" value="VN" />
            <el-option label="台湾" value="TW" />
            <el-option label="日本" value="JP" />
            <el-option label="美国" value="US" />
            <el-option label="澳大利亚" value="AU" />
            <el-option label="马来西亚" value="MY" />
          </el-select>
        </el-col>
      </el-row>

      <el-table :data="items" stripe border max-height="500" v-loading="loading">
        <el-table-column prop="cert_no" label="认证编号" width="140" />
        <el-table-column prop="product_code" label="产品编码" width="120" />
        <el-table-column prop="cert_type" label="认证类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.cert_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target_market" label="目标市场" width="100" />
        <el-table-column prop="cert_body" label="认证机构" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="planned_date" label="计划日期" width="110" />
        <el-table-column prop="submit_date" label="提交日期" width="110" />
        <el-table-column prop="approved_date" label="获批日期" width="110" />
        <el-table-column prop="cdf_doc_ref" label="CDF引用" width="110" />
        <el-table-column prop="remark" label="备注" min-width="150" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑认证' : '新建认证'" width="600">
      <el-form :model="form" label-width="100">
        <el-form-item label="产品编码" required>
          <el-input v-model="form.product_code" placeholder="如 EU-09K" />
        </el-form-item>
        <el-form-item label="认证类型" required>
          <el-select v-model="form.cert_type" style="width: 100%">
            <el-option label="CE认证" value="CE" />
            <el-option label="UL认证" value="UL" />
            <el-option label="CCC认证" value="CCC" />
            <el-option label="ERP能效" value="ERP" />
            <el-option label="MEPS能效" value="MEPS" />
            <el-option label="GEMS能效" value="GEMS" />
            <el-option label="CB认证" value="CB" />
            <el-option label="能源之星" value="Energy Star" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标市场" required>
          <el-select v-model="form.target_market" style="width: 100%">
            <el-option label="欧盟" value="EU" />
            <el-option label="越南" value="VN" />
            <el-option label="台湾" value="TW" />
            <el-option label="日本" value="JP" />
            <el-option label="美国" value="US" />
            <el-option label="澳大利亚" value="AU" />
            <el-option label="马来西亚" value="MY" />
          </el-select>
        </el-form-item>
        <el-form-item label="认证机构">
          <el-input v-model="form.cert_body" placeholder="如 TÜV / Intertek / SGS" />
        </el-form-item>
        <el-form-item label="计划日期">
          <el-date-picker v-model="form.planned_date" type="date" style="width: 100%" />
        </el-form-item>
        <el-form-item label="CDF引用">
          <el-input v-model="form.cdf_doc_ref" placeholder="CDF文档编号" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item v-if="editingId" label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="计划中" value="planning" />
            <el-option label="准备中" value="preparing" />
            <el-option label="测试中" value="testing" />
            <el-option label="已提交" value="submitted" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
          </el-select>
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
import type { TableRow } from '@/types/common'
import api from '../../api'

const items = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const filterStatus = ref('')
const filterMarket = ref('')

const form = ref<any>({
  product_code: '', cert_type: '', target_market: '',
  cert_body: '', planned_date: null, cdf_doc_ref: '', remark: '', status: ''
})

const statusMap: Record<string, string> = {
  planning: '计划中', preparing: '准备中', testing: '测试中',
  submitted: '已提交', approved: '已通过', rejected: '已驳回',
  expiring: '即将过期'
}
const statusTypeMap: Record<string, string> = {
  planning: 'info', preparing: 'warning', testing: 'warning',
  submitted: '', approved: 'success', rejected: 'danger',
  expiring: 'danger'
}

function statusLabel(s: string) { return statusMap[s] || s }
function statusType(s: string): string { return statusTypeMap[s] || 'info' }

async function fetchData() {
  loading.value = true
  try {
    let url = '/certifications'
    const params: string[] = []
    if (filterStatus.value) params.push(`status=${filterStatus.value}`)
    if (filterMarket.value) params.push(`target_market=${filterMarket.value}`)
    if (params.length) url += '?' + params.join('&')
    const r = await api.get(url)
    items.value = r.data
  } finally { loading.value = false }
}

function openDialog(row?: TableRow) {
  if (row) {
    editingId.value = row.id as number
    form.value = { ...row }
  } else {
    editingId.value = null
    form.value = { product_code: '', cert_type: '', target_market: '', cert_body: '', planned_date: null, cdf_doc_ref: '', remark: '', status: '' }
  }
  dialogVisible.value = true
}

async function save() {
  saving.value = true
  try {
    const payload: Record<string, unknown> = { ...form.value }
    if (editingId.value) {
      await api.patch(`/certifications/${editingId.value}`, payload)
      ElMessage.success('更新成功')
    } else {
      delete payload.status
      await api.post('/certifications', payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } finally { saving.value = false }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
</style>
