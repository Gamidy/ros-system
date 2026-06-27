<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>ECO 变更指令</span>
          <el-button type="primary" @click="openCreateDialog">新建ECO</el-button>
        </div>
      </template>

      <!-- 筛选栏 -->
      <el-row :gutter="12" style="margin-bottom: 16px">
        <el-col :span="5">
          <el-select v-model="filter.status" placeholder="状态筛选" clearable style="width:100%" @change="fetchData(1)">
            <el-option label="全部" value="" />
            <el-option label="草稿" value="draft" />
            <el-option label="实施中" value="implementing" />
            <el-option label="已验证" value="verified" />
            <el-option label="已生效" value="effective" />
            <el-option label="已关闭" value="closed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-input v-model="filter.keyword" placeholder="搜索标题 / 编号" clearable size="default" @change="fetchData(1)" />
        </el-col>
      </el-row>

      <!-- 表格 -->
      <el-table :data="list" stripe border v-loading="loading" style="width:100%">
        <el-table-column prop="code" label="ECO编号" width="140" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="item_count" label="明细项数" width="90" align="center" />
        <el-table-column prop="effective_date" label="生效日期" width="110" />
        <el-table-column prop="created_by_name" label="创建人" width="100" />
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="$router.push(`/eco/${row.id}`)">详情</el-button>
            <el-button v-if="canEdit(row)" link type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button v-if="canDelete(row)" link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div style="display:flex;justify-content:flex-end;margin-top:16px">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData(1)"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <!-- 创建 / 编辑 Dialog -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑ECO' : '新建ECO'" width="650" :close-on-click-modal="false" destroy-on-close>
      <el-form :model="form" label-width="110" :rules="rules" ref="formRef">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="变更摘要" prop="change_summary">
          <el-input v-model="form.change_summary" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="实施方案">
          <el-input v-model="form.implementation_plan" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="生效日期">
          <el-date-picker v-model="form.effective_date" type="date" style="width:100%" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="关联ECR">
          <el-input-number v-model="form.ecr_id" :min="0" :max="999999" placeholder="ECR ID（可选）" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchECOs, createECO, updateECO, deleteECO, type ECOOut, type ECOCreate, type ECOUpdate } from '../../api/eco'

// ── 状态映射 ──
const statusMap: Record<string, string> = {
  draft: '草稿',
  implementing: '实施中',
  verified: '已验证',
  effective: '已生效',
  closed: '已关闭',
  cancelled: '已取消',
}
const statusTypeMap: Record<string, string> = {
  draft: 'info',
  implementing: 'warning',
  verified: 'primary',
  effective: 'success',
  closed: 'info',
  cancelled: 'danger',
}
function statusLabel(s: string) { return statusMap[s] || s }
function statusType(s: string) { return statusTypeMap[s] || 'info' }

// ── 可操作判断 ──
function canEdit(row: ECOOut) { return row.status === 'draft' }
function canDelete(row: ECOOut) { return row.status === 'draft' }

// ── 数据 ──
const loading = ref(false)
const list = ref<ECOOut[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filter = reactive({ status: '', keyword: '' })

async function fetchData(p?: number) {
  if (p) page.value = p
  loading.value = true
  try {
    const res = await fetchECOs({
      status: filter.status || undefined,
      keyword: filter.keyword || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    list.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

// ── 创建 / 编辑 ──
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref<any>(null)
const form = reactive<ECOCreate & { ecr_id?: number }>({
  title: '',
  change_summary: '',
  implementation_plan: '',
  effective_date: undefined,
  ecr_id: undefined,
})
const rules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  change_summary: [{ required: true, message: '请输入变更摘要', trigger: 'blur' }],
}

function openCreateDialog() {
  editingId.value = null
  form.title = ''
  form.change_summary = ''
  form.implementation_plan = ''
  form.effective_date = undefined
  form.ecr_id = undefined
  dialogVisible.value = true
}

function openEditDialog(row: ECOOut) {
  editingId.value = row.id
  form.title = row.title
  form.change_summary = row.change_summary
  form.implementation_plan = row.implementation_plan || ''
  form.effective_date = row.effective_date || undefined
  form.ecr_id = (row as ECOOut).ecr_id || undefined
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload: ECOCreate = {
      title: form.title,
      change_summary: form.change_summary,
      implementation_plan: form.implementation_plan || undefined,
      effective_date: form.effective_date || undefined,
    }
    if (editingId.value) {
      await updateECO(editingId.value, payload as ECOUpdate)
      ElMessage.success('更新成功')
    } else {
      if (form.ecr_id) payload.ecr_id = form.ecr_id
      await createECO(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } finally {
    saving.value = false
  }
}

// ── 删除 ──
async function handleDelete(row: ECOOut) {
  await ElMessageBox.confirm(`确定删除 ECO「${row.code}」吗？`, '确认删除', { type: 'warning' })
  await deleteECO(row.id)
  ElMessage.success('删除成功')
  await fetchData()
}

onMounted(() => fetchData())
</script>

<style scoped>
.page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
