<template>
  <div class="page">
    <!-- 加载中 -->
    <div v-if="loading" style="text-align:center;padding:60px"><el-icon class="is-loading" :size="32"><Loading /></el-icon></div>

    <template v-if="!loading && eco">
      <!-- ═══════ 头部操作区 ═══════ -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <div>
          <el-button @click="$router.push('/eco')">← 返回列表</el-button>
        </div>
        <div>
          <!-- DRAFT -->
          <el-button v-if="eco.status === 'draft'" type="primary" @click="handleImplement">实施</el-button>
          <el-button v-if="eco.status === 'draft'" @click="openEditDialog">编辑</el-button>
          <el-button v-if="eco.status === 'draft'" type="danger" plain @click="handleDelete">删除</el-button>
          <!-- IMPLEMENTING -->
          <el-button v-if="eco.status === 'implementing'" type="success" @click="handleVerify">验证通过</el-button>
          <el-button v-if="eco.status === 'implementing'" type="warning" plain @click="handleCancel">取消</el-button>
          <!-- VERIFIED -->
          <el-button v-if="eco.status === 'verified'" type="primary" @click="handleEffective">生效</el-button>
          <el-button v-if="eco.status === 'verified'" type="warning" plain @click="handleCancel">取消</el-button>
          <!-- EFFECTIVE -->
          <el-button v-if="eco.status === 'effective'" @click="handleClose">关闭</el-button>
        </div>
      </div>

      <!-- ═══════ 基本信息卡片 ═══════ -->
      <el-card shadow="never" style="margin-bottom:16px">
        <template #header><span>基本信息</span></template>
        <el-descriptions :column="3" border>
          <el-descriptions-item label="ECO编号">{{ eco.code }}</el-descriptions-item>
          <el-descriptions-item label="标题">{{ eco.title }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(eco.status)" size="small">{{ statusLabel(eco.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="变更摘要" :span="2">{{ eco.change_summary }}</el-descriptions-item>
          <el-descriptions-item label="明细项数">{{ eco.item_count }}</el-descriptions-item>
          <el-descriptions-item label="实施方案" :span="2">{{ eco.implementation_plan || '-' }}</el-descriptions-item>
          <el-descriptions-item label="生效日期">{{ eco.effective_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建人">{{ (eco as any).created_by_name || eco.created_by }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ eco.created_at }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ eco.updated_at }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- ═══════ 关联ECR信息 ═══════ -->
      <el-card v-if="eco.ecr_id" shadow="never" style="margin-bottom:16px">
        <template #header><span>关联ECR</span></template>
        <el-descriptions :column="3" border>
          <el-descriptions-item label="ECR编号">
            <el-button link type="primary" @click="$router.push(`/ecr/${eco.ecr_id}`)">
              {{ eco.ecr_code || eco.ecr_id }}
            </el-button>
          </el-descriptions-item>
          <el-descriptions-item label="ECR标题" :span="2">{{ eco.ecr_title || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- ═══════ 明细项表格 ═══════ -->
      <el-card shadow="never" style="margin-bottom:16px">
        <template #header>
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span>变更明细项</span>
            <el-button v-if="canEditItems" type="primary" size="small" @click="addItem">新增明细</el-button>
          </div>
        </template>
        <el-table :data="items" stripe border v-loading="itemsLoading" style="width:100%">
          <el-table-column type="index" label="序号" width="60" />
          <el-table-column label="变更类型" width="120">
            <template #default="{ row, $index }">
              <el-select
                v-if="canEditItems && editingItemIndex === $index"
                v-model="row.change_type"
                size="small"
                style="width:100%"
              >
                <el-option label="新增" value="add" />
                <el-option label="修改" value="modify" />
                <el-option label="替换" value="replace" />
                <el-option label="删除" value="delete" />
                <el-option label="禁用" value="disable" />
              </el-select>
              <span v-else>{{ changeTypeLabel(row.change_type) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="对象类型" width="110">
            <template #default="{ row, $index }">
              <el-select
                v-if="canEditItems && editingItemIndex === $index"
                v-model="row.object_type"
                size="small"
                style="width:100%"
              >
                <el-option label="物料" value="part" />
                <el-option label="BOM" value="bom" />
                <el-option label="文档" value="document" />
                <el-option label="认证" value="certification" />
                <el-option label="工艺" value="process" />
                <el-option label="其他" value="other" />
              </el-select>
              <span v-else>{{ objectTypeLabel(row.object_type) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="对象编码" width="130">
            <template #default="{ row, $index }">
              <el-input v-if="canEditItems && editingItemIndex === $index" v-model="row.object_code" size="small" />
              <span v-else>{{ row.object_code || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="对象名称" width="150">
            <template #default="{ row, $index }">
              <el-input v-if="canEditItems && editingItemIndex === $index" v-model="row.object_name" size="small" />
              <span v-else>{{ row.object_name || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="原值" min-width="160">
            <template #default="{ row, $index }">
              <el-input v-if="canEditItems && editingItemIndex === $index" v-model="row.old_value" size="small" />
              <span v-else>{{ row.old_value || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="新值" min-width="160">
            <template #default="{ row, $index }">
              <el-input v-if="canEditItems && editingItemIndex === $index" v-model="row.new_value" size="small" />
              <span v-else>{{ row.new_value || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="描述" min-width="160">
            <template #default="{ row, $index }">
              <el-input v-if="canEditItems && editingItemIndex === $index" v-model="row.description" size="small" />
              <span v-else>{{ row.description || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right" v-if="canEditItems">
            <template #default="{ row, $index }">
              <template v-if="editingItemIndex === $index">
                <el-button link type="success" size="small" @click="saveItem(row, $index)">保存</el-button>
                <el-button link size="small" @click="cancelEditItem">取消</el-button>
              </template>
              <template v-else>
                <el-button link type="primary" size="small" @click="startEditItem($index)">编辑</el-button>
                <el-button link type="danger" size="small" @click="removeItem(row, $index)">删除</el-button>
              </template>
            </template>
          </el-table-column>
        </el-table>

        <!-- 新增行（内联） -->
        <div v-if="showNewRow" style="margin-top:12px;padding:12px;border:1px dashed #dcdfe6;border-radius:4px">
          <el-row :gutter="12">
            <el-col :span="3">
              <el-select v-model="newItem.change_type" placeholder="变更类型" size="small" style="width:100%">
                <el-option label="新增" value="add" />
                <el-option label="修改" value="modify" />
                <el-option label="替换" value="replace" />
                <el-option label="删除" value="delete" />
                <el-option label="禁用" value="disable" />
              </el-select>
            </el-col>
            <el-col :span="3">
              <el-select v-model="newItem.object_type" placeholder="对象类型" size="small" style="width:100%">
                <el-option label="物料" value="part" />
                <el-option label="BOM" value="bom" />
                <el-option label="文档" value="document" />
                <el-option label="认证" value="certification" />
                <el-option label="工艺" value="process" />
                <el-option label="其他" value="other" />
              </el-select>
            </el-col>
            <el-col :span="3"><el-input v-model="newItem.object_code" placeholder="对象编码" size="small" /></el-col>
            <el-col :span="3"><el-input v-model="newItem.object_name" placeholder="对象名称" size="small" /></el-col>
            <el-col :span="4"><el-input v-model="newItem.old_value" placeholder="原值" size="small" /></el-col>
            <el-col :span="4"><el-input v-model="newItem.new_value" placeholder="新值" size="small" /></el-col>
            <el-col :span="2">
              <el-button type="primary" size="small" @click="confirmAddItem" :loading="savingItem">保存</el-button>
            </el-col>
            <el-col :span="2">
              <el-button size="small" @click="showNewRow = false">取消</el-button>
            </el-col>
          </el-row>
        </div>
      </el-card>

      <!-- ═══════ 状态流时间线 ═══════ -->
      <el-card shadow="never">
        <template #header><span>状态流</span></template>
        <el-timeline>
          <el-timeline-item
            v-for="(evt, i) in statusEvents"
            :key="i"
            :timestamp="evt.time"
            :type="evt.type"
            :hollow="!evt.active"
            placement="top"
          >
            {{ evt.label }}
          </el-timeline-item>
        </el-timeline>
      </el-card>
    </template>

    <!-- ═══════ 编辑基本信息 Dialog ═══════ -->
    <el-dialog v-model="editDialogVisible" title="编辑ECO" width="600" destroy-on-close>
      <el-form :model="editForm" label-width="110">
        <el-form-item label="标题" required>
          <el-input v-model="editForm.title" />
        </el-form-item>
        <el-form-item label="变更摘要" required>
          <el-input v-model="editForm.change_summary" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="实施方案">
          <el-input v-model="editForm.implementation_plan" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="生效日期">
          <el-date-picker v-model="editForm.effective_date" type="date" style="width:100%" value-format="YYYY-MM-DD" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="confirmEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import {
  fetchECO,
  deleteECO,
  updateECO,
  implementECO,
  verifyECO,
  effectiveECO,
  closeECO,
  cancelECO,
  addECOItem,
  updateECOItem,
  deleteECOItem,
  type ECODetailOut,
  type ECOItemOut,
  type ECOItemCreate,
} from '../../api/eco'

const route = useRoute()
const router = useRouter()
const ecoId = computed(() => Number(route.params.id))

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
const changeTypeMap: Record<string, string> = {
  add: '新增',
  modify: '修改',
  replace: '替换',
  delete: '删除',
  disable: '禁用',
}
const objectTypeMap: Record<string, string> = {
  part: '物料',
  bom: 'BOM',
  document: '文档',
  certification: '认证',
  process: '工艺',
  other: '其他',
}
function statusLabel(s: string) { return statusMap[s] || s }
function statusType(s: string) { return statusTypeMap[s] || 'info' }
function changeTypeLabel(s: string) { return changeTypeMap[s] || s }
function objectTypeLabel(s: string) { return objectTypeMap[s] || s }

// ── 数据 ──
const loading = ref(false)
const eco = ref<ECODetailOut | null>(null)
const items = ref<ECOItemOut[]>([])
const itemsLoading = ref(false)

// ── 明细项编辑状态 ──
const canEditItems = computed(() => eco.value && (eco.value.status === 'draft' || eco.value.status === 'implementing'))
const editingItemIndex = ref<number | null>(null)
const editingItemBackup = ref<any>(null)

// 新增行
const showNewRow = ref(false)
const savingItem = ref(false)
const newItem = ref<ECOItemCreate>({
  change_type: 'modify',
  object_type: 'part',
  object_code: '',
  object_name: '',
  old_value: '',
  new_value: '',
  description: '',
})

async function fetchDetail() {
  loading.value = true
  try {
    const res = await fetchECO(ecoId.value)
    eco.value = res
    items.value = res.items || []
  } finally {
    loading.value = false
  }
}

// ── 明细项 CRUD ──
function startEditItem(index: number) {
  editingItemIndex.value = index
  editingItemBackup.value = { ...items.value[index] }
}
function cancelEditItem() {
  if (editingItemIndex.value !== null && editingItemBackup.value) {
    items.value[editingItemIndex.value] = editingItemBackup.value
  }
  editingItemIndex.value = null
  editingItemBackup.value = null
}
async function saveItem(row: ECOItemOut, _index: number) {
  savingItem.value = true
  try {
    const payload: Partial<ECOItemCreate> = {
      change_type: row.change_type,
      object_type: row.object_type,
      object_code: row.object_code,
      object_name: row.object_name,
      old_value: row.old_value,
      new_value: row.new_value,
      description: row.description,
    }
    await updateECOItem(ecoId.value, row.id, payload)
    ElMessage.success('更新成功')
    editingItemIndex.value = null
    editingItemBackup.value = null
  } finally {
    savingItem.value = false
  }
}
function addItem() {
  showNewRow.value = true
  newItem.value = {
    change_type: 'modify',
    object_type: 'part',
    object_code: '',
    object_name: '',
    old_value: '',
    new_value: '',
    description: '',
  }
}
async function confirmAddItem() {
  if (!newItem.value.change_type || !newItem.value.object_type) {
    ElMessage.warning('请选择变更类型和对象类型')
    return
  }
  savingItem.value = true
  try {
    const created = await addECOItem(ecoId.value, newItem.value)
    items.value.push(created)
    ElMessage.success('新增成功')
    showNewRow.value = false
  } finally {
    savingItem.value = false
  }
}
async function removeItem(row: ECOItemOut, index: number) {
  await ElMessageBox.confirm('确定删除该明细项吗？', '确认', { type: 'warning' })
  await deleteECOItem(ecoId.value, row.id)
  items.value.splice(index, 1)
  ElMessage.success('删除成功')
}

// ── 状态操作 ──
async function handleImplement() {
  await ElMessageBox.confirm('确定开始实施该ECO吗？', '确认', { type: 'info' })
  await implementECO(ecoId.value)
  ElMessage.success('已开始实施')
  await fetchDetail()
}
async function handleVerify() {
  await ElMessageBox.confirm('确定验证通过吗？', '确认', { type: 'info' })
  await verifyECO(ecoId.value)
  ElMessage.success('已验证通过')
  await fetchDetail()
}
async function handleEffective() {
  await ElMessageBox.confirm('确定生效该ECO吗？', '确认', { type: 'info' })
  await effectiveECO(ecoId.value)
  ElMessage.success('已生效')
  await fetchDetail()
}
async function handleClose() {
  await ElMessageBox.confirm('确定关闭该ECO吗？', '确认', { type: 'info' })
  await closeECO(ecoId.value)
  ElMessage.success('已关闭')
  await fetchDetail()
}
async function handleCancel() {
  await ElMessageBox.confirm('确定取消该ECO吗？', '确认', { type: 'warning' })
  await cancelECO(ecoId.value)
  ElMessage.success('已取消')
  await fetchDetail()
}
async function handleDelete() {
  await ElMessageBox.confirm(`确定删除 ECO「${eco.value?.code}」吗？此操作不可恢复。`, '确认删除', { type: 'warning' })
  await deleteECO(ecoId.value)
  ElMessage.success('已删除')
  router.push('/eco')
}

// ── 编辑基本信息 ──
const editDialogVisible = ref(false)
const saving = ref(false)
const editForm = ref({ title: '', change_summary: '', implementation_plan: '', effective_date: '' })
function openEditDialog() {
  if (!eco.value) return
  editForm.value = {
    title: eco.value.title,
    change_summary: eco.value.change_summary,
    implementation_plan: eco.value.implementation_plan || '',
    effective_date: eco.value.effective_date || '',
  }
  editDialogVisible.value = true
}
async function confirmEdit() {
  if (!editForm.value.title || !editForm.value.change_summary) {
    ElMessage.warning('标题和变更摘要为必填')
    return
  }
  saving.value = true
  try {
    await updateECO(ecoId.value, {
      title: editForm.value.title,
      change_summary: editForm.value.change_summary,
      implementation_plan: editForm.value.implementation_plan || undefined,
      effective_date: editForm.value.effective_date || undefined,
    })
    ElMessage.success('更新成功')
    editDialogVisible.value = false
    await fetchDetail()
  } finally {
    saving.value = false
  }
}

// ── 状态流时间线 ──
const statusFlowOrder = ['draft', 'implementing', 'verified', 'effective', 'closed']
const statusFlowLabels: Record<string, string> = {
  draft: '创建草稿',
  implementing: '开始实施',
  verified: '验证通过',
  effective: '已生效',
  closed: '已关闭',
  cancelled: '已取消',
}
const statusFlowType: Record<string, string> = {
  draft: 'info',
  implementing: 'warning',
  verified: 'primary',
  effective: 'success',
  closed: 'info',
  cancelled: 'danger',
}
const statusEvents = computed(() => {
  if (!eco.value) return []
  const currentStatus = eco.value.status
  const events: { label: string; time: string; type: string; active: boolean }[] = []
  // Cancelled is a terminal state that breaks the normal flow
  if (currentStatus === 'cancelled') {
    events.push({
      label: '已取消',
      time: eco.value.updated_at,
      type: 'danger',
      active: true,
    })
    return events
  }
  for (const s of statusFlowOrder) {
    const passed = statusFlowOrder.indexOf(currentStatus) >= statusFlowOrder.indexOf(s)
    events.push({
      label: statusFlowLabels[s],
      time: passed ? eco.value.updated_at : '-',
      type: statusFlowType[s] as any,
      active: s === currentStatus,
    })
    if (s === currentStatus) break
  }
  return events
})

onMounted(fetchDetail)
</script>

<style scoped>
.page { padding: 0; }
</style>
