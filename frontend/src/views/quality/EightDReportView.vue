<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>8D报告管理</span>
          <el-button type="primary" @click="openDialog()">新建8D报告</el-button>
        </div>
      </template>

      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="6">
          <el-select v-model="filterStatus" placeholder="状态筛选" clearable @change="fetchData" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option label="待分析" value="open" />
            <el-option label="分析中" value="analysis" />
            <el-option label="遏制中" value="containment" />
            <el-option label="纠正中" value="corrective" />
            <el-option label="验证中" value="verify" />
            <el-option label="已关闭" value="closed" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filterSeverity" placeholder="严重度" clearable @change="fetchData" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option label="A级-致命" value="A" />
            <el-option label="B级-严重" value="B" />
            <el-option label="C级-轻微" value="C" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-input v-model="keyword" placeholder="搜索编号/标题/产品" clearable @clear="fetchData">
            <template #append>
              <el-button @click="fetchData">搜索</el-button>
            </template>
          </el-input>
        </el-col>
      </el-row>

      <el-table :data="items" stripe border max-height="500" v-loading="loading">
        <el-table-column prop="report_no" label="报告编号" width="160" />
        <el-table-column prop="issue_title" label="问题标题" min-width="180" show-overflow-tooltip />
        <el-table-column prop="product_info" label="关联产品" width="120" />
        <el-table-column prop="severity" label="严重度" width="80">
          <template #default="{ row }">
            <el-tag :type="severityType(row.severity)" size="small">{{ row.severity }}级</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="responsible_person" label="负责人" width="90" />
        <el-table-column prop="target_date" label="目标日期" width="110" />
        <el-table-column prop="closed_date" label="关闭日期" width="110" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button link type="primary" size="small" @click="handleStatus(row)">流转</el-button>
            <el-popconfirm title="确认删除?" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 16px; text-align: right">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <!-- 新建/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑8D报告' : '新建8D报告'" width="700" top="5vh">
      <el-form :model="form" label-width="120" label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="报告编号" required>
              <el-input v-model="form.report_no" placeholder="留空自动生成" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="严重度" required>
              <el-select v-model="form.severity" style="width: 100%">
                <el-option label="A级-致命" value="A" />
                <el-option label="B级-严重" value="B" />
                <el-option label="C级-轻微" value="C" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="问题标题" required>
          <el-input v-model="form.issue_title" placeholder="简要描述问题" />
        </el-form-item>
        <el-form-item label="问题描述">
          <el-input v-model="form.issue_desc" type="textarea" :rows="3" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="关联产品/物料">
              <el-input v-model="form.product_info" placeholder="产品编码/物料号" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="负责人">
              <el-input v-model="form.responsible_person" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="目标关闭日期">
              <el-date-picker v-model="form.target_date" type="date" style="width: 100%" value-format="YYYY-MM-DD" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-divider>8D流程内容</el-divider>
        <el-form-item label="D1-组建团队">
          <el-input v-model="form.d1_team" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="D2-问题描述">
          <el-input v-model="form.d2_problem_desc" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="D3-遏制措施">
          <el-input v-model="form.d3_containment" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="D4-根因分析">
          <el-input v-model="form.d4_root_cause" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="D5-纠正措施">
          <el-input v-model="form.d5_corrective_action" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="D6-措施实施">
          <el-input v-model="form.d6_implement" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="D7-预防措施">
          <el-input v-model="form.d7_prevention" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="D8-总结关闭">
          <el-input v-model="form.d8_closure" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 状态流转弹窗 -->
    <el-dialog v-model="statusDialogVisible" title="状态流转" width="400">
      <el-form label-width="100">
        <el-form-item label="当前状态">
          <el-tag>{{ statusLabel(statusForm.currentStatus) }}</el-tag>
        </el-form-item>
        <el-form-item label="目标状态" required>
          <el-select v-model="statusForm.targetStatus" style="width: 100%">
            <el-option
              v-for="s in statusForm.allowedTransitions"
              :key="s.value"
              :label="s.label"
              :value="s.value"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="statusDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleStatusConfirm" :loading="statusSaving">确认流转</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

interface EightDReport {
  id: number
  report_no: string
  issue_title: string
  issue_desc: string | null
  severity: string
  product_info: string | null
  d1_team: string | null
  d2_problem_desc: string | null
  d3_containment: string | null
  d4_root_cause: string | null
  d5_corrective_action: string | null
  d6_implement: string | null
  d7_prevention: string | null
  d8_closure: string | null
  status: string
  responsible_person: string | null
  target_date: string | null
  closed_date: string | null
  remark: string | null
}

const loading = ref(false)
const saving = ref(false)
const items = ref<EightDReport[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterStatus = ref('')
const filterSeverity = ref('')
const keyword = ref('')
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)

const defaultForm = {
  report_no: '',
  issue_title: '',
  issue_desc: '',
  severity: 'C',
  product_info: '',
  d1_team: '',
  d2_problem_desc: '',
  d3_containment: '',
  d4_root_cause: '',
  d5_corrective_action: '',
  d6_implement: '',
  d7_prevention: '',
  d8_closure: '',
  responsible_person: '',
  target_date: null as string | null,
  remark: '',
}
const form = reactive({ ...defaultForm })

// 状态流转
const statusDialogVisible = ref(false)
const statusSaving = ref(false)
const statusForm = reactive({
  currentStatus: '',
  targetStatus: '',
  allowedTransitions: [] as { value: string; label: string }[],
  reportId: 0,
})

const STATUS_MAP: Record<string, { label: string; type: string; transitions: string[] }> = {
  open: { label: '待分析', type: 'info', transitions: ['analysis'] },
  analysis: { label: '分析中', type: 'warning', transitions: ['containment', 'open'] },
  containment: { label: '遏制中', type: 'warning', transitions: ['corrective', 'analysis'] },
  corrective: { label: '纠正中', type: 'warning', transitions: ['verify', 'containment'] },
  verify: { label: '验证中', type: 'primary', transitions: ['closed', 'corrective'] },
  closed: { label: '已关闭', type: 'success', transitions: [] },
}

function statusLabel(s: string): string {
  return STATUS_MAP[s]?.label ?? s
}

function statusType(s: string): string {
  return STATUS_MAP[s]?.type ?? 'info'
}

function severityType(s: string): string {
  if (s === 'A') return 'danger'
  if (s === 'B') return 'warning'
  return 'info'
}

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value }
    if (filterStatus.value) params.status = filterStatus.value
    if (filterSeverity.value) params.severity = filterSeverity.value
    if (keyword.value) params.keyword = keyword.value

    const res = await api.get('/api/quality/8d-reports', { params })
    items.value = res.data.items
    total.value = res.data.total
  } catch (e) {
    console.error('fetch 8d reports error', e)
  } finally {
    loading.value = false
  }
}

function openDialog(row?: EightDReport) {
  editingId.value = row?.id ?? null
  if (row) {
    Object.assign(form, {
      report_no: row.report_no,
      issue_title: row.issue_title,
      issue_desc: row.issue_desc ?? '',
      severity: row.severity,
      product_info: row.product_info ?? '',
      d1_team: row.d1_team ?? '',
      d2_problem_desc: row.d2_problem_desc ?? '',
      d3_containment: row.d3_containment ?? '',
      d4_root_cause: row.d4_root_cause ?? '',
      d5_corrective_action: row.d5_corrective_action ?? '',
      d6_implement: row.d6_implement ?? '',
      d7_prevention: row.d7_prevention ?? '',
      d8_closure: row.d8_closure ?? '',
      responsible_person: row.responsible_person ?? '',
      target_date: row.target_date ?? null,
      remark: row.remark ?? '',
    })
  } else {
    Object.assign(form, { ...defaultForm })
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.issue_title) {
    ElMessage.warning('请输入问题标题')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await api.put(`/api/quality/8d-reports/${editingId.value}`, form)
      ElMessage.success('更新成功')
    } else {
      await api.post('/api/quality/8d-reports', form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '操作失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(id: number) {
  try {
    await api.delete(`/api/quality/8d-reports/${id}`)
    ElMessage.success('删除成功')
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '删除失败')
  }
}

function handleStatus(row: EightDReport) {
  const info = STATUS_MAP[row.status]
  if (!info || info.transitions.length === 0) {
    ElMessage.info('当前状态无可流转目标')
    return
  }
  statusForm.currentStatus = row.status
  statusForm.reportId = row.id
  statusForm.targetStatus = ''
  statusForm.allowedTransitions = info.transitions.map((t) => ({
    value: t,
    label: statusLabel(t),
  }))
  statusDialogVisible.value = true
}

async function handleStatusConfirm() {
  if (!statusForm.targetStatus) {
    ElMessage.warning('请选择目标状态')
    return
  }
  statusSaving.value = true
  try {
    await api.put(`/api/quality/8d-reports/${statusForm.reportId}/status`, {
      status: statusForm.targetStatus,
    })
    ElMessage.success('状态流转成功')
    statusDialogVisible.value = false
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '流转失败')
  } finally {
    statusSaving.value = false
  }
}

onMounted(() => fetchData())
</script>

<style scoped>
.page {
  padding: 16px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
