<template>
  <div class="page">
    <el-card shadow="never">
      <el-tabs v-model="activeTab" @tab-change="fetchData">
        <el-tab-pane label="ECR 变更申请" name="ecr">
          <div style="margin-bottom: 16px; display: flex; justify-content: space-between">
            <el-select v-model="filterEcrStatus" placeholder="状态筛选" clearable @change="fetchData" style="width: 160px">
              <el-option label="全部" value="" />
              <el-option label="草稿" value="draft" />
              <el-option label="已提交" value="submitted" />
              <el-option label="已批准" value="approved" />
              <el-option label="已驳回" value="rejected" />
              <el-option label="已实施" value="implemented" />
            </el-select>
            <el-button type="primary" @click="openEcrDialog()">新建ECR</el-button>
          </div>
          <el-table :data="ecrItems" stripe border max-height="420" v-loading="loading">
            <el-table-column prop="ecr_no" label="ECR编号" width="140" />
            <el-table-column prop="title" label="标题" min-width="180" />
            <el-table-column prop="product_code" label="产品编码" width="120" />
            <el-table-column prop="change_type" label="变更类型" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ row.change_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="trigger" label="触发" width="90" />
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="submitted_by" label="提交人" width="90" />
            <el-table-column prop="approved_by" label="批准人" width="90" />
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="openEcrDialog(row)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="ECN 变更通知" name="ecn">
          <div style="margin-bottom: 16px; display: flex; justify-content: space-between">
            <div></div>
            <el-button type="primary" @click="openEcnDialog()">新建ECN</el-button>
          </div>
          <el-table :data="ecnItems" stripe border max-height="420" v-loading="loading">
            <el-table-column prop="ecn_no" label="ECN编号" width="140" />
            <el-table-column prop="title" label="标题" min-width="180" />
            <el-table-column prop="product_code" label="产品编码" width="120" />
            <el-table-column prop="ecr_id" label="关联ECR" width="90" />
            <el-table-column label="CDF影响" width="90">
              <template #default="{ row }">
                <el-tag :type="row.cdf_impact ? 'warning' : 'info'" size="small">
                  {{ row.cdf_impact ? '是' : '否' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="认证影响" width="90">
              <template #default="{ row }">
                <el-tag :type="row.certification_impact ? 'warning' : 'info'" size="small">
                  {{ row.certification_impact ? '是' : '否' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="effective_date" label="生效日期" width="110" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- ECR Dialog -->
    <el-dialog v-model="ecrDialogVisible" :title="editingEcrId ? '编辑ECR' : '新建ECR'" width="600">
      <el-form :model="ecrForm" label-width="100">
        <el-form-item label="标题" required>
          <el-input v-model="ecrForm.title" />
        </el-form-item>
        <el-form-item label="产品编码">
          <el-input v-model="ecrForm.product_code" placeholder="关联产品" />
        </el-form-item>
        <el-form-item label="变更类型" required>
          <el-select v-model="ecrForm.change_type" style="width: 100%">
            <el-option label="结构变更" value="结构" />
            <el-option label="系统变更" value="系统" />
            <el-option label="电控变更" value="电控" />
            <el-option label="物料变更" value="物料" />
            <el-option label="BOM变更" value="BOM" />
          </el-select>
        </el-form-item>
        <el-form-item label="触发">
          <el-select v-model="ecrForm.trigger" style="width: 100%" clearable>
            <el-option label="品质" value="品质" />
            <el-option label="降本" value="降本" />
            <el-option label="认证" value="认证" />
            <el-option label="工艺" value="工艺" />
            <el-option label="供应链" value="供应链" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="ecrForm.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="影响分析">
          <el-input v-model="ecrForm.impact_analysis" type="textarea" :rows="2" placeholder="性能/认证/项目/成本影响" />
        </el-form-item>
        <el-form-item v-if="editingEcrId" label="状态">
          <el-select v-model="ecrForm.status" style="width: 100%">
            <el-option label="草稿" value="draft" />
            <el-option label="已提交" value="submitted" />
            <el-option label="已批准" value="approved" />
            <el-option label="已驳回" value="rejected" />
            <el-option label="已实施" value="implemented" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ecrDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEcr">保存</el-button>
      </template>
    </el-dialog>

    <!-- ECN Dialog -->
    <el-dialog v-model="ecnDialogVisible" title="新建ECN" width="550">
      <el-form :model="ecnForm" label-width="110">
        <el-form-item label="标题" required>
          <el-input v-model="ecnForm.title" />
        </el-form-item>
        <el-form-item label="关联ECR ID">
          <el-input-number v-model="ecnForm.ecr_id" :min="0" />
        </el-form-item>
        <el-form-item label="产品编码">
          <el-input v-model="ecnForm.product_code" />
        </el-form-item>
        <el-form-item label="变更范围">
          <el-input v-model="ecnForm.change_scope" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="BOM变更明细">
          <el-input v-model="ecnForm.bom_changes" type="textarea" :rows="2" placeholder="JSON格式变更明细" />
        </el-form-item>
        <el-form-item label="CDF影响">
          <el-switch v-model="ecnForm.cdf_impact" />
        </el-form-item>
        <el-form-item label="认证影响">
          <el-switch v-model="ecnForm.certification_impact" />
        </el-form-item>
        <el-form-item label="生效日期">
          <el-date-picker v-model="ecnForm.effective_date" type="date" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ecnDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEcn">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const activeTab = ref('ecr')
const loading = ref(false)
const saving = ref(false)

// ECR
const ecrItems = ref<any[]>([])
const ecrDialogVisible = ref(false)
const editingEcrId = ref<number | null>(null)
const filterEcrStatus = ref('')
const ecrForm = ref<any>({
  title: '', product_code: '', change_type: '', trigger: '',
  description: '', impact_analysis: '', status: ''
})

// ECN
const ecnItems = ref<any[]>([])
const ecnDialogVisible = ref(false)
const ecnForm = ref<any>({
  title: '', ecr_id: null, product_code: '',
  change_scope: '', bom_changes: '',
  cdf_impact: false, certification_impact: false,
  effective_date: null
})

const statusMap: Record<string, string> = {
  draft: '草稿', submitted: '已提交', approved: '已批准',
  rejected: '已驳回', implemented: '已实施'
}
const statusTypeMap: Record<string, string> = {
  draft: 'info', submitted: 'warning', approved: 'success',
  rejected: 'danger', implemented: ''
}

function statusLabel(s: string) { return statusMap[s] || s }
function statusType(s: string): string { return statusTypeMap[s] || 'info' }

async function fetchData() {
  loading.value = true
  try {
    if (activeTab.value === 'ecr') {
      let url = '/certifications/ecrs'
      if (filterEcrStatus.value) url += `?status=${filterEcrStatus.value}`
      const r = await api.get(url)
      ecrItems.value = r.data
    } else {
      const r = await api.get('/certifications/ecns')
      ecnItems.value = r.data
    }
  } finally { loading.value = false }
}

// ECR actions
function openEcrDialog(row?: Record<string, unknown>) {
  if (row) {
    editingEcrId.value = row.id as number
    ecrForm.value = { ...row }
  } else {
    editingEcrId.value = null
    ecrForm.value = { title: '', product_code: '', change_type: '', trigger: '', description: '', impact_analysis: '', status: '' }
  }
  ecrDialogVisible.value = true
}

async function saveEcr() {
  saving.value = true
  try {
    const payload: Record<string, unknown> = { ...ecrForm.value }
    if (editingEcrId.value) {
      await api.patch(`/certifications/ecrs/${editingEcrId.value}`, payload)
      ElMessage.success('更新成功')
    } else {
      delete payload.status
      await api.post('/certifications/ecrs', payload)
      ElMessage.success('创建成功')
    }
    ecrDialogVisible.value = false
    await fetchData()
  } finally { saving.value = false }
}

// ECN actions
function openEcnDialog() {
  ecnForm.value = { title: '', ecr_id: null, product_code: '', change_scope: '', bom_changes: '', cdf_impact: false, certification_impact: false, effective_date: null }
  ecnDialogVisible.value = true
}

async function saveEcn() {
  saving.value = true
  try {
    const payload: Record<string, unknown> = { ...ecnForm.value }
    if (!payload.ecr_id) delete payload.ecr_id
    await api.post('/certifications/ecns', payload)
    ElMessage.success('创建成功')
    ecnDialogVisible.value = false
    await fetchData()
  } finally { saving.value = false }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
</style>
