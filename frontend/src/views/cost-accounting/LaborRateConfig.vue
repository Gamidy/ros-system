<template>
  <div class="labor-rate-config">
    <!-- 顶部导航 tab -->
    <el-tabs v-model="activeTab" @tab-click="onTabChange">
      <el-tab-pane label="核算单" name="sheets" />
      <el-tab-pane label="工时费率" name="labor-rates" />
      <el-tab-pane label="分摊规则" name="overhead-rules" />
      <el-tab-pane label="核算期间" name="periods" />
      <el-tab-pane label="差异分析" name="analysis" />
    </el-tabs>

    <!-- 工具栏 -->
    <div class="toolbar">
      <el-button type="primary" @click="showCreate">新增工时费率</el-button>
    </div>

    <!-- 表格 -->
    <el-table :data="items" v-loading="loading" stripe border style="width:100%">
      <el-table-column prop="operation_code" label="工序编码" min-width="140" show-overflow-tooltip />
      <el-table-column prop="operation_name" label="工序名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="hourly_rate" label="工时费率(元/小时)" width="160" align="center">
        <template #default="{ row }">
          {{ row.hourly_rate != null ? Number(row.hourly_rate).toFixed(2) : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
            {{ row.status === 'active' ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="showEdit(row)">编辑</el-button>
          <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态 -->
    <el-empty v-if="!loading && items.length === 0" description="暂无工时费率数据" :image-size="60" />

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑工时费率' : '新增工时费率'"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="工序编码" prop="operation_code">
          <el-input v-model="form.operation_code" placeholder="请输入工序编码" maxlength="50" />
        </el-form-item>
        <el-form-item label="工序名称" prop="operation_name">
          <el-input v-model="form.operation_name" placeholder="请输入工序名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="工时费率" prop="hourly_rate">
          <el-input-number
            v-model="form.hourly_rate"
            :min="0"
            :precision="2"
            :step="0.5"
            style="width:100%"
            placeholder="请输入工时费率"
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
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'
import type { TableRow } from '@/types/common'
import {
  listLaborRates,
  createLaborRate,
  updateLaborRate,
  deleteLaborRate,
} from '../../api/costAccounting'

// ── Tab 导航 ──
const route = useRoute()
const router = useRouter()
const activeTab = ref<string>('labor-rates')

const tabRouteMap: Record<string, string> = {
  'sheets': '/cost-accounting',
  'labor-rates': '/cost-accounting/labor-rates',
  'overhead-rules': '/cost-accounting/overhead-rules',
  'periods': '/cost-accounting/periods',
  'analysis': '/cost-accounting/analysis',
}

function onTabChange() {
  const path = tabRouteMap[activeTab.value]
  if (path) {
    router.push(path)
  }
}

// 从当前路由名推断激活tab
if (route.name === 'CostLaborRates') {
  activeTab.value = 'labor-rates'
} else if (route.path.includes('sheets')) {
  activeTab.value = 'sheets'
} else if (route.path.includes('overhead-rules')) {
  activeTab.value = 'overhead-rules'
} else if (route.path.includes('periods')) {
  activeTab.value = 'periods'
} else if (route.path.includes('analysis')) {
  activeTab.value = 'analysis'
}

// ── 表格数据 ──
const items = ref<any[]>([])
const loading = ref(false)

async function fetchData() {
  loading.value = true
  try {
    const { data } = await listLaborRates()
    items.value = Array.isArray(data) ? data : data?.items ?? []
  } catch (e: unknown) {
    ElMessage.error((e as any)?.message || '加载工时费率失败')
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
  operation_code: '',
  operation_name: '',
  hourly_rate: 0,
})

const rules = {
  operation_code: [{ required: true, message: '请输入工序编码', trigger: 'blur' }],
  operation_name: [{ required: true, message: '请输入工序名称', trigger: 'blur' }],
  hourly_rate: [{ required: true, message: '请输入工时费率', trigger: 'blur' }],
}

function showCreate() {
  isEdit.value = false
  editingId.value = null
  form.value = { operation_code: '', operation_name: '', hourly_rate: 0 }
  dialogVisible.value = true
}

function showEdit(row: TableRow) {
  isEdit.value = true
  editingId.value = Number(row.id) ?? null
  form.value = {
    operation_code: String(row.operation_code ?? ''),
    operation_name: String(row.operation_name ?? ''),
    hourly_rate: Number(row.hourly_rate) ?? 0,
  }
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (isEdit.value && editingId.value != null) {
      await updateLaborRate(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await createLaborRate(form.value)
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

async function handleDelete(row: TableRow) {
  try {
    await ElMessageBox.confirm(
      `确定要删除工序「${row.operation_name}」(编码: ${row.operation_code}) 吗？`,
      '删除确认',
      { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return // 用户取消
  }

  try {
    await deleteLaborRate(Number(row.id) ?? 0)
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
.labor-rate-config {
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  min-height: calc(100vh - 120px);
}

.toolbar {
  margin-bottom: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
</style>
