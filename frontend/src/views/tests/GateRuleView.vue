<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>Gate规则引擎</span>
          <el-button type="primary" @click="openDialog()">新建规则</el-button>
        </div>
      </template>

      <el-table :data="rules" stripe border v-loading="loading" max-height="500">
        <el-table-column prop="name" label="规则名称" min-width="160" />
        <el-table-column prop="product_line" label="产品线" width="120" />
        <el-table-column prop="customer" label="客户" width="120" />
        <el-table-column prop="gate_code" label="Gate编号" width="100" />
        <el-table-column label="全部通过" width="100">
          <template #default="{ row }">
            <el-tag :type="row.all_pass ? 'success' : 'info'" size="small">{{ row.all_pass ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="自动阻塞" width="100">
          <template #default="{ row }">
            <el-tag :type="row.auto_block ? 'warning' : 'info'" size="small">{{ row.auto_block ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="80" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button
              link :type="row.is_active ? 'warning' : 'success'" size="small"
              @click="toggleActive(row)"
            >{{ row.is_active ? '停用' : '启用' }}</el-button>
            <el-button link type="danger" size="small" @click="removeRule(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 评估面板 -->
    <el-card shadow="never" style="margin-top: 16px">
      <template #header>
        <div class="card-header">
          <span>Gate评估</span>
          <el-button type="success" :loading="evaluating" @click="evaluateGate">执行评估</el-button>
        </div>
      </template>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-select v-model="evalProject" placeholder="选择项目" style="width: 100%" @change="clearEvalResult">
            <el-option v-for="p in projects" :key="p.id" :label="p.name || p.project_code" :value="p.id" />
          </el-select>
        </el-col>
        <el-col :span="8">
          <el-select v-model="evalGate" placeholder="选择Gate" style="width: 100%" @change="clearEvalResult">
            <el-option label="M4" value="M4" />
            <el-option label="M5" value="M5" />
            <el-option label="M6" value="M6" />
            <el-option label="M7" value="M7" />
            <el-option label="M8" value="M8" />
            <el-option label="M9" value="M9" />
          </el-select>
        </el-col>
      </el-row>
      <div v-if="evalResult" style="margin-top: 16px">
        <el-alert
          :title="evalResult.passed ? '✅ 全部通过 - Gate可放行' : '❌ 存在未满足条件 - Gate阻塞'"
          :type="evalResult.passed ? 'success' : 'error'"
          show-icon
          :closable="false"
        />
        <el-table :data="evalResult.details || []" stripe border size="small" style="margin-top: 12px">
          <el-table-column prop="rule_name" label="规则名称" min-width="150" />
          <el-table-column label="结果" width="120">
            <template #default="{ row: d }">
              <el-tag :type="d.passed ? 'success' : d.warning ? 'warning' : 'danger'" size="small">
                {{ d.passed ? '通过' : d.warning ? '警告' : '未通过' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="message" label="说明" min-width="200" />
        </el-table>
      </div>
    </el-card>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑规则' : '新建规则'" width="700">
      <el-form :model="form" label-width="120">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="规则名称" required>
              <el-input v-model="form.name" placeholder="规则名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="优先级">
              <el-input-number v-model="form.priority" :min="0" :max="999" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="产品线">
              <el-input v-model="form.product_line" placeholder="如 R32" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="客户">
              <el-input v-model="form.customer" placeholder="客户名称" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="Gate编号" required>
          <el-select v-model="form.gate_code" style="width: 100%">
            <el-option label="M4" value="M4" />
            <el-option label="M5" value="M5" />
            <el-option label="M6" value="M6" />
            <el-option label="M7" value="M7" />
            <el-option label="M8" value="M8" />
            <el-option label="M9" value="M9" />
          </el-select>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="全部通过">
              <el-switch v-model="form.all_pass" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="自动阻塞">
              <el-switch v-model="form.auto_block" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider>规则条目</el-divider>
        <div v-for="(item, idx) in form.items" :key="idx" style="border: 1px solid #eee; padding: 12px; margin-bottom: 8px; border-radius: 4px;">
          <el-row :gutter="12" align="middle">
            <el-col :span="7">
              <el-select v-model="item.required_vr_category" placeholder="VR分类" clearable style="width: 100%">
                <el-option v-for="(label, key) in categoryMap" :key="key" :label="label" :value="key" />
              </el-select>
            </el-col>
            <el-col :span="7">
              <el-select v-model="item.required_prototype_type" placeholder="样机版本" clearable style="width: 100%">
                <el-option label="P0" value="P0" />
                <el-option label="P1" value="P1" />
                <el-option label="P2" value="P2" />
                <el-option label="P3" value="P3" />
              </el-select>
            </el-col>
            <el-col :span="5">
              <el-switch v-model="item.is_required" active-text="必须" />
            </el-col>
            <el-col :span="5" style="text-align: right">
              <el-button link type="danger" size="small" @click="form.items.splice(idx, 1)">删除</el-button>
            </el-col>
          </el-row>
        </div>
        <el-button type="primary" size="small" @click="form.items.push({ required_vr_category: '', required_prototype_type: '', is_required: true })">+ 添加条目</el-button>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'

const rules = ref<any[]>([])
const projects = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const evaluating = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const evalProject = ref<number | null>(null)
const evalGate = ref('')
const evalResult = ref<any>(null)

const form = ref<any>({
  name: '', product_line: '', customer: '', gate_code: '',
  all_pass: false, auto_block: false, priority: 0,
  items: [] as any[]
})

const categoryMap: Record<string, string> = {
  performance: '性能测试',
  energy: '能效测试',
  noise: '噪音',
  condensation: '凝露',
  damp_heat: '潮态',
  high_temp_cool: '高温制冷',
  low_temp_heat: '低温制热',
  frost_defrost: '冻结融霜',
  long_run: '长时间运行',
  elec_safety_pre: '电气安全预验证',
}

async function fetchRules() {
  loading.value = true
  try {
    const res = await api.get('/gate-rules')
    rules.value = res.data
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
      name: row.name || '',
      product_line: row.product_line || '',
      customer: row.customer || '',
      gate_code: row.gate_code || '',
      all_pass: row.all_pass ?? false,
      auto_block: row.auto_block ?? false,
      priority: row.priority ?? 0,
      items: (row.items || []).map((i: any) => ({
        required_vr_category: i.required_vr_category || '',
        required_prototype_type: i.required_prototype_type || '',
        is_required: i.is_required ?? true,
      })),
    }
  } else {
    editingId.value = null
    form.value = { name: '', product_line: '', customer: '', gate_code: '', all_pass: false, auto_block: false, priority: 0, items: [] }
  }
  dialogVisible.value = true
}

async function save() {
  saving.value = true
  try {
    const payload = { ...form.value }
    if (editingId.value) {
      await api.put(`/gate-rules/${editingId.value}`, payload)
      ElMessage.success('更新成功')
    } else {
      await api.post('/gate-rules', payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchRules()
  } finally { saving.value = false }
}

async function removeRule(row: any) {
  try {
    await ElMessageBox.confirm('确定删除此规则？', '确认', { type: 'warning' })
    await api.delete(`/gate-rules/${row.id}`)
    ElMessage.success('删除成功')
    await fetchRules()
  } catch { /* cancelled */ }
}

async function toggleActive(row: any) {
  try {
    if (row.is_active) {
      await api.post(`/gate-rules/${row.id}/deactivate`)
    } else {
      await api.post(`/gate-rules/${row.id}/activate`)
    }
    ElMessage.success(row.is_active ? '已停用' : '已启用')
    await fetchRules()
  } catch { /* handled */ }
}

function clearEvalResult() {
  evalResult.value = null
}

async function evaluateGate() {
  if (!evalProject.value || !evalGate.value) {
    ElMessage.warning('请先选择项目和Gate')
    return
  }
  evaluating.value = true
  try {
    const res = await api.post('/gate-rules/evaluate', {
      project_id: evalProject.value,
      gate_code: evalGate.value,
    })
    evalResult.value = res.data
  } finally { evaluating.value = false }
}

onMounted(() => {
  fetchRules()
  fetchProjects()
})
</script>

<style scoped>
.page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
</style>
