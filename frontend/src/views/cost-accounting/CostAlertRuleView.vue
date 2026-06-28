<template>
  <div class="cost-alert-rule-view">
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
      <el-menu-item index="/cost-accounting/alert-rules">成本预警</el-menu-item>
    </el-menu>

    <!-- 双 Tab 布局 -->
    <el-tabs v-model="activeTab" class="cost-tabs">
      <!-- ════════════════════════════════════════════ -->
      <!-- Tab 1：预警规则 -->
      <!-- ════════════════════════════════════════════ -->
      <el-tab-pane label="预警规则" name="rules">
        <div class="toolbar">
          <el-button type="primary" @click="showCreate">新建规则</el-button>
          <el-button :loading="checking" @click="handleManualCheck">手动触发检查</el-button>
        </div>

        <el-table :data="rules" v-loading="loadingRules" stripe border style="width:100%">
          <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip />
          <el-table-column label="阈值%" width="110" align="center">
            <template #default="{ row }">
              {{ row.threshold_pct != null ? Number(row.threshold_pct).toFixed(1) + '%' : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="阈值金额(元)" width="140" align="right">
            <template #default="{ row }">
              {{ row.threshold_amount != null ? '¥' + Number(row.threshold_amount).toLocaleString('zh-CN') : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="project_type" label="产品类型" width="120" align="center">
            <template #default="{ row }">
              {{ projectTypeMap[row.project_type] || row.project_type || '全部' }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
                {{ row.enabled ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="showEdit(row)">编辑</el-button>
              <el-button
                link
                :type="row.enabled ? 'warning' : 'success'"
                size="small"
                @click="handleToggle(row)"
              >
                {{ row.enabled ? '禁用' : '启用' }}
              </el-button>
              <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="!loadingRules && rules.length === 0" description="暂无预警规则" :image-size="60" />
      </el-tab-pane>

      <!-- ════════════════════════════════════════════ -->
      <!-- Tab 2：预警事件 -->
      <!-- ════════════════════════════════════════════ -->
      <el-tab-pane label="预警事件" name="events">
        <div class="toolbar">
          <el-select v-model="eventsFilter.alert_level" placeholder="预警等级" clearable style="width:140px" @change="fetchEvents">
            <el-option label="全部" value="" />
            <el-option label="警告" value="warning" />
            <el-option label="严重" value="critical" />
          </el-select>
          <el-select v-model="eventsFilter.is_resolved" placeholder="处理状态" clearable style="width:140px" @change="fetchEvents">
            <el-option label="全部" value="" />
            <el-option label="未处理" value="false" />
            <el-option label="已处理" value="true" />
          </el-select>
          <el-button type="primary" @click="fetchEvents">查询</el-button>
        </div>

        <el-table :data="events" v-loading="loadingEvents" stripe border style="width:100%">
          <el-table-column prop="rule_name" label="规则名称" min-width="140" show-overflow-tooltip />
          <el-table-column prop="plan_name" label="项目" min-width="140" show-overflow-tooltip />
          <el-table-column label="目标金额" width="120" align="right">
            <template #default="{ row }">
              {{ row.target_amount != null ? '¥' + Number(row.target_amount).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="实际金额" width="120" align="right">
            <template #default="{ row }">
              {{ row.actual_amount != null ? '¥' + Number(row.actual_amount).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="偏差金额" width="120" align="right">
            <template #default="{ row }">
              <span :style="{ color: (row.variance_amount || 0) > 0 ? '#F56C6C' : '#67C23A' }">
                {{ row.variance_amount != null ? '¥' + Number(row.variance_amount).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) : '-' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="偏差%" width="90" align="center">
            <template #default="{ row }">
              <span :style="{ color: Math.abs(row.variance_pct || 0) > 10 ? '#F56C6C' : '#67C23A' }">
                {{ row.variance_pct != null ? Number(row.variance_pct).toFixed(1) + '%' : '-' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="等级" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="row.alert_level === 'critical' ? 'danger' : 'warning'" size="small">
                {{ row.alert_level === 'critical' ? '严重' : '警告' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="已处理" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_resolved ? 'success' : 'danger'" size="small">
                {{ row.is_resolved ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="触发时间" width="170" align="center">
            <template #default="{ row }">
              {{ row.created_at ? formatTime(row.created_at) : '-' }}
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="!loadingEvents && events.length === 0" description="暂无预警事件" :image-size="60" />
      </el-tab-pane>
    </el-tabs>

    <!-- ════════════════════════════════════════════ -->
    <!-- 新建/编辑规则弹窗 -->
    <!-- ════════════════════════════════════════════ -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑预警规则' : '新建预警规则'"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="120px">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入规则名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="阈值" prop="threshold_pct">
          <el-input-number
            v-model="form.threshold_pct"
            :min="0"
            :max="100"
            :precision="1"
            :step="1"
            style="width:100%"
            placeholder="百分比阈值"
          />
          <span style="margin-left:6px;color:#999">%</span>
        </el-form-item>
        <el-form-item label="阈值金额" prop="threshold_amount">
          <el-input-number
            v-model="form.threshold_amount"
            :min="0"
            :precision="2"
            :step="1000"
            style="width:100%"
            placeholder="金额阈值（元）"
          />
        </el-form-item>
        <el-form-item label="产品类型" prop="project_type">
          <el-select v-model="form.project_type" placeholder="请选择产品类型（可选）" clearable style="width:100%">
            <el-option label="全部类型" value="" />
            <el-option v-for="(label, val) in projectTypeMap" :key="val" :label="label" :value="val" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.enabled" active-text="启用" inactive-text="禁用" />
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
import api from '../../api/index'

// ── 产品类型映射 ──
const projectTypeMap: Record<string, string> = {
  split_wall: '分体壁挂',
  ceiling: '天花',
  duct: '风管',
  cabinet: '柜机',
  window: '窗机',
  mobile: '移动空调',
}

// ── 导航菜单 ──
const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => {
  const path = route.path
  if (path.includes('/cost-accounting/alert-rules')) return '/cost-accounting/alert-rules'
  if (path.includes('/cost-accounting/labor-rates')) return '/cost-accounting/labor-rates'
  if (path.includes('/cost-accounting/overhead-rules')) return '/cost-accounting/overhead-rules'
  if (path.includes('/cost-accounting/periods')) return '/cost-accounting/periods'
  if (path.includes('/cost-accounting/analysis')) return '/cost-accounting/analysis'
  return '/cost-accounting'
})

function onMenuSelect(index: string) {
  router.push(index)
}

// ── Tab 切换 ──
const activeTab = ref('rules')

// ══════════════════════════════════════════════════
// 预警规则
// ══════════════════════════════════════════════════
const rules = ref<any[]>([])
const loadingRules = ref(false)

async function fetchRules() {
  loadingRules.value = true
  try {
    const res = await api.get('/cost-alert-rules')
    const data = res.data
    rules.value = Array.isArray(data) ? data : data?.items ?? data?.data ?? []
  } catch (e: unknown) {
    ElMessage.error((e as any)?.message || '加载预警规则失败')
  } finally {
    loadingRules.value = false
  }
}

// ── 弹窗表单 ──
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref<FormInstance>()

const form = ref({
  name: '',
  threshold_pct: 10,
  threshold_amount: 0,
  project_type: '',
  enabled: true,
})

const formRules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  threshold_pct: [{ required: true, message: '请输入阈值百分比', trigger: 'blur' }],
}

function showCreate() {
  isEdit.value = false
  editingId.value = null
  form.value = {
    name: '',
    threshold_pct: 10,
    threshold_amount: 0,
    project_type: '',
    enabled: true,
  }
  dialogVisible.value = true
}

function showEdit(row: any) {
  isEdit.value = true
  editingId.value = Number(row.id) ?? null
  form.value = {
    name: String(row.name ?? ''),
    threshold_pct: Number(row.threshold_pct) ?? 0,
    threshold_amount: Number(row.threshold_amount) ?? 0,
    project_type: String(row.project_type ?? ''),
    enabled: row.enabled === true || row.enabled === 1,
  }
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const payload = { ...form.value }
    if (isEdit.value && editingId.value != null) {
      await api.put(`/cost-alert-rules/${editingId.value}`, payload)
      ElMessage.success('更新成功')
    } else {
      await api.post('/cost-alert-rules', payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchRules()
  } catch (e: unknown) {
    ElMessage.error((e as any)?.message || '操作失败')
  } finally {
    saving.value = false
  }
}

// ── 启用/禁用 ──
async function handleToggle(row: any) {
  const actionLabel = row.enabled ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(
      `确定要${actionLabel}规则「${row.name}」吗？`,
      `${actionLabel}确认`,
      { confirmButtonText: `确定${actionLabel}`, cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }

  try {
    await api.put(`/cost-alert-rules/${row.id}`, { enabled: !row.enabled })
    ElMessage.success(`${actionLabel}成功`)
    await fetchRules()
  } catch (e: unknown) {
    ElMessage.error((e as any)?.message || `${actionLabel}失败`)
  }
}

// ── 删除 ──
async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(
      `确定要删除规则「${row.name}」吗？此操作不可恢复。`,
      '删除确认',
      { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }

  try {
    await api.delete(`/cost-alert-rules/${row.id}`)
    ElMessage.success('删除成功')
    await fetchRules()
  } catch (e: unknown) {
    ElMessage.error((e as any)?.message || '删除失败')
  }
}

// ══════════════════════════════════════════════════
// 手动触发检查
// ══════════════════════════════════════════════════
const checking = ref(false)

async function handleManualCheck() {
  checking.value = true
  try {
    const res = await api.post('/cost-alert-rules/events/check')
    const msg = (res as any)?.data?.message || '检查完成'
    ElMessage.success(msg)
    // 刷新事件列表
    await fetchEvents()
  } catch (e: unknown) {
    ElMessage.error((e as any)?.message || '触发检查失败')
  } finally {
    checking.value = false
  }
}

// ══════════════════════════════════════════════════
// 预警事件
// ══════════════════════════════════════════════════
const events = ref<any[]>([])
const loadingEvents = ref(false)

const eventsFilter = ref({
  alert_level: '',
  is_resolved: '',
})

async function fetchEvents() {
  loadingEvents.value = true
  try {
    const params: Record<string, any> = { limit: 200 }
    if (eventsFilter.value.alert_level) params.alert_level = eventsFilter.value.alert_level
    if (eventsFilter.value.is_resolved !== '') params.is_resolved = eventsFilter.value.is_resolved

    const res = await api.get('/cost-alert-rules/events', { params })
    const data = res.data
    events.value = Array.isArray(data) ? data : data?.items ?? data?.data ?? []
  } catch (e: unknown) {
    ElMessage.error((e as any)?.message || '加载预警事件失败')
  } finally {
    loadingEvents.value = false
  }
}

// ── 工具函数 ──
function formatTime(t: string | number | Date): string {
  if (!t) return '-'
  const d = new Date(t)
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

onMounted(() => {
  fetchRules()
  fetchEvents()
})
</script>

<style scoped>
.cost-alert-rule-view {
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  min-height: calc(100vh - 120px);
}

.cost-nav-menu {
  margin-bottom: 16px;
  border-bottom: 1px solid var(--el-border-color-light);
}

.cost-tabs {
  margin-top: 0;
}

.cost-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}

.toolbar {
  margin-bottom: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
</style>
