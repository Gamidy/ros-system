<template>
  <div class="cost-period-manage">
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
      <el-button type="primary" @click="showCreate">新增核算期间</el-button>
    </div>

    <!-- 表格 -->
    <el-table :data="items" v-loading="loading" stripe border style="width:100%">
      <el-table-column prop="period_name" label="期间名称" min-width="180" show-overflow-tooltip />
      <el-table-column prop="start_date" label="开始日期" width="140" align="center" />
      <el-table-column prop="end_date" label="结束日期" width="140" align="center" />
      <el-table-column label="状态" width="120" align="center">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button
            link
            type="warning"
            size="small"
            :disabled="row.status === 'closed'"
            @click="handleClosePeriod(row)"
          >
            关闭期间
          </el-button>
          <el-button link type="danger" size="small" @click="handleDelete(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态 -->
    <el-empty v-if="!loading && items.length === 0" description="暂无核算期间数据" :image-size="60" />

    <!-- 新增对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="新增核算期间"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="期间名称" prop="period_name">
          <el-input v-model="form.period_name" placeholder="请输入期间名称，如 2025年Q1" maxlength="100" />
        </el-form-item>
        <el-form-item label="开始日期" prop="start_date">
          <el-date-picker
            v-model="form.start_date"
            type="date"
            placeholder="选择开始日期"
            value-format="YYYY-MM-DD"
            style="width:100%"
          />
        </el-form-item>
        <el-form-item label="结束日期" prop="end_date">
          <el-date-picker
            v-model="form.end_date"
            type="date"
            placeholder="选择结束日期"
            value-format="YYYY-MM-DD"
            style="width:100%"
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
import {
  listPeriods,
  createPeriod,
  deletePeriod,
  closePeriod,
} from '../../api/costAccounting'

// ── Tab 导航 ──
const route = useRoute()
const router = useRouter()
const activeTab = ref<string>('periods')

const tabRouteMap: Record<string, string> = {
  sheets: '/cost-accounting',
  'labor-rates': '/cost-accounting/labor-rates',
  'overhead-rules': '/cost-accounting/overhead-rules',
  periods: '/cost-accounting/periods',
  analysis: '/cost-accounting/analysis',
}

function onTabChange() {
  const path = tabRouteMap[activeTab.value]
  if (path) {
    router.push(path)
  }
}

// 从当前路由名推断激活 tab
if (route.name === 'CostPeriods') {
  activeTab.value = 'periods'
} else if (route.path.includes('sheets')) {
  activeTab.value = 'sheets'
} else if (route.path.includes('labor-rates')) {
  activeTab.value = 'labor-rates'
} else if (route.path.includes('overhead-rules')) {
  activeTab.value = 'overhead-rules'
} else if (route.path.includes('analysis')) {
  activeTab.value = 'analysis'
}

// ── 状态映射 ──
const statusMap: Record<string, string> = {
  draft: '草稿',
  active: '进行中',
  closed: '已关闭',
}
const statusTypeMap: Record<string, string> = {
  draft: 'info',
  active: 'warning',
  closed: 'success',
}

function statusLabel(status: string): string {
  return statusMap[status] || status || '-'
}

function statusType(status: string): any {
  return statusTypeMap[status] || 'info'
}

// ── 表格数据 ──
const items = ref<any[]>([])
const loading = ref(false)

async function fetchData() {
  loading.value = true
  try {
    const { data } = await listPeriods()
    items.value = Array.isArray(data) ? data : data?.items ?? []
  } catch (e: any) {
    ElMessage.error(e?.message || '加载核算期间失败')
  } finally {
    loading.value = false
  }
}

// ── 表单对话框 ──
const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref<FormInstance>()

const form = ref({
  period_name: '',
  start_date: '',
  end_date: '',
})

const rules = {
  period_name: [{ required: true, message: '请输入期间名称', trigger: 'blur' }],
  start_date: [{ required: true, message: '请选择开始日期', trigger: 'change' }],
  end_date: [{ required: true, message: '请选择结束日期', trigger: 'change' }],
}

function showCreate() {
  form.value = { period_name: '', start_date: '', end_date: '' }
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    await createPeriod(form.value)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e?.message || '创建失败')
  } finally {
    saving.value = false
  }
}

// ── 关闭期间 ──
async function handleClosePeriod(row: any) {
  try {
    await ElMessageBox.confirm(
      `确定要关闭核算期间「${row.period_name}」吗？关闭后将无法进行该期间的核算操作。`,
      '关闭确认',
      { confirmButtonText: '确定关闭', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }

  try {
    await closePeriod(row.id)
    ElMessage.success('期间已关闭')
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e?.message || '关闭失败')
  }
}

// ── 删除 ──
async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(
      `确定要删除核算期间「${row.period_name}」吗？此操作不可恢复。`,
      '删除确认',
      { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }

  try {
    await deletePeriod(row.id)
    ElMessage.success('删除成功')
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e?.message || '删除失败')
  }
}

// ── 初始化 ──
onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.cost-period-manage {
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
