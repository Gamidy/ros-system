<template>
  <div class="overhead-rule-config">
    <!-- 顶部导航 tab（el-menu 水平模式） -->
    <el-menu
      mode="horizontal"
      :default-active="activeMenu"
      class="cost-nav-menu"
      @select="onMenuSelect"
    >
      <el-menu-item index="/cost-accounting">核算单</el-menu-item>
      <el-menu-item index="/cost-accounting/labor-rates">工时费率</el-menu-item>
      <el-menu-item index="/cost-accounting/overhead-rules">分摊规则</el-menu-item>
      <el-menu-item index="/cost-accounting/periods">核算期间</el-menu-item>
      <el-menu-item index="/cost-accounting/analysis">成本分析</el-menu-item>
    </el-menu>

    <!-- 工具栏 -->
    <div class="toolbar">
      <el-button type="primary" @click="showCreate">新增分摊规则</el-button>
    </div>

    <!-- 表格 -->
    <el-table :data="items" v-loading="loading" stripe border style="width:100%">
      <el-table-column prop="rule_name" label="规则名称" min-width="160" show-overflow-tooltip />
      <el-table-column label="分摊基准" width="140" align="center">
        <template #default="{ row }">
          {{ allocationBaseMap[row.allocation_base] || row.allocation_base }}
        </template>
      </el-table-column>
      <el-table-column prop="allocation_rate" label="分摊比例%" width="130" align="center">
        <template #default="{ row }">
          {{ row.allocation_rate != null ? Number(row.allocation_rate).toFixed(1) + '%' : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="priority" label="优先级" width="90" align="center" />
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.is_active === 1 ? 'success' : 'info'" size="small">
            {{ row.is_active === 1 ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="showEdit(row)">编辑</el-button>
          <el-button
            link
            :type="row.is_active === 1 ? 'warning' : 'success'"
            size="small"
            @click="handleToggle(row)"
          >
            {{ row.is_active === 1 ? '禁用' : '启用' }}
          </el-button>
          <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态 -->
    <el-empty v-if="!loading && items.length === 0" description="暂无分摊规则数据" :image-size="60" />

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑分摊规则' : '新增分摊规则'"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="规则名称" prop="rule_name">
          <el-input v-model="form.rule_name" placeholder="请输入规则名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="分摊基准" prop="allocation_base">
          <el-select v-model="form.allocation_base" placeholder="请选择分摊基准" style="width:100%">
            <el-option label="直接人工" value="direct_labor" />
            <el-option label="直接材料" value="direct_material" />
            <el-option label="总成本" value="total_cost" />
            <el-option label="产品数量" value="quantity" />
          </el-select>
        </el-form-item>
        <el-form-item label="分摊比例" prop="allocation_rate">
          <el-input-number
            v-model="form.allocation_rate"
            :min="0"
            :max="100"
            :precision="1"
            :step="1"
            style="width:100%"
            placeholder="请输入分摊比例"
          />
          <span style="margin-left:6px;color:#999">%</span>
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-input-number
            v-model="form.priority"
            :min="1"
            :max="9999"
            :step="1"
            style="width:100%"
            placeholder="请输入优先级（数字越小越优先）"
          />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入规则描述（选填）"
            maxlength="500"
            show-word-limit
          />
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
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'
import type { TableRow } from '@/types/common'
import {
  listOverheadRules,
  createOverheadRule,
  updateOverheadRule,
  deleteOverheadRule,
  toggleOverheadRule,
} from '../../api/costAccounting'

// ── 分摊基准中文映射 ──
const allocationBaseMap: Record<string, string> = {
  direct_labor: '直接人工',
  direct_material: '直接材料',
  total_cost: '总成本',
  quantity: '产品数量',
}

// ── Menu 导航 ──
const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => {
  const path = route.path
  if (path.includes('/cost-accounting/overhead-rules')) return '/cost-accounting/overhead-rules'
  if (path.includes('/cost-accounting/labor-rates')) return '/cost-accounting/labor-rates'
  if (path.includes('/cost-accounting/periods')) return '/cost-accounting/periods'
  if (path.includes('/cost-accounting/analysis')) return '/cost-accounting/analysis'
  return '/cost-accounting'
})

function onMenuSelect(index: string) {
  router.push(index)
}

// ── 表格数据 ──
const items = ref<any[]>([])
const loading = ref(false)

async function fetchData() {
  loading.value = true
  try {
    const { data } = await listOverheadRules()
    items.value = Array.isArray(data) ? data : data?.items ?? []
  } catch (e: unknown) {
    ElMessage.error((e as any)?.message || '加载分摊规则失败')
  } finally {
    loading.value = false
  }
}

// ── 表单对话框 ──
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref<FormInstance>()

const form = ref({
  rule_name: '',
  allocation_base: '',
  allocation_rate: 0,
  priority: 1,
  description: '',
})

const rules = {
  rule_name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  allocation_base: [{ required: true, message: '请选择分摊基准', trigger: 'change' }],
  allocation_rate: [{ required: true, message: '请输入分摊比例', trigger: 'blur' }],
  priority: [{ required: true, message: '请输入优先级', trigger: 'blur' }],
}

function showCreate() {
  isEdit.value = false
  editingId.value = null
  form.value = {
    rule_name: '',
    allocation_base: '',
    allocation_rate: 0,
    priority: 1,
    description: '',
  }
  dialogVisible.value = true
}

function showEdit(row: TableRow) {
  isEdit.value = true
  editingId.value = Number(row.id) ?? null
  form.value = {
    rule_name: String(row.rule_name ?? ''),
    allocation_base: String(row.allocation_base ?? ''),
    allocation_rate: Number(row.allocation_rate) ?? 0,
    priority: Number(row.priority) ?? 1,
    description: String(row.description ?? ''),
  }
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (isEdit.value && editingId.value != null) {
      await updateOverheadRule(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await createOverheadRule(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } catch (e: unknown) {
    ElMessage.error((e as any)?.message || '操作失败')
  } finally {
    saving.value = false
  }
}

// ── 启用/禁用切换 ──
async function handleToggle(row: TableRow) {
  const actionLabel = row.is_active === 1 ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(
      `确定要${actionLabel}规则「${row.rule_name}」吗？`,
      `${actionLabel}确认`,
      { confirmButtonText: `确定${actionLabel}`, cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }

  try {
    await toggleOverheadRule(Number(row.id) ?? 0)
    ElMessage.success(`${actionLabel}成功`)
    await fetchData()
  } catch (e: unknown) {
    ElMessage.error((e as any)?.message || `${actionLabel}失败`)
  }
}

// ── 删除 ──
async function handleDelete(row: TableRow) {
  try {
    await ElMessageBox.confirm(
      `确定要删除规则「${row.rule_name}」吗？此操作不可恢复。`,
      '删除确认',
      { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }

  try {
    await deleteOverheadRule(row.id as number)
    ElMessage.success('删除成功')
    await fetchData()
  } catch (e: unknown) {
    ElMessage.error((e as any)?.message || '删除失败')
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.overhead-rule-config {
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  min-height: calc(100vh - 120px);
}

.cost-nav-menu {
  margin-bottom: 16px;
  border-bottom: 1px solid var(--el-border-color-light);
}

.toolbar {
  margin-bottom: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
</style>
