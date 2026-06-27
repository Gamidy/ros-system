<template>
  <div class="tests-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>实验与测试</span>
          <el-button type="primary" @click="showTestDialog = true">新建测试申请</el-button>
        </div>
      </template>

      <el-table :data="testList" stripe border v-loading="loading">
        <el-table-column prop="request_no" label="申请编号" width="150" />
        <el-table-column prop="title" label="测试项目" min-width="180" />
        <el-table-column prop="test_type" label="类型" width="100" />
        <el-table-column label="实验分类" width="110">
          <template #default="{ row }">
            <el-tag size="small">{{ row.test_category || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="关联VR" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.related_vr_code" size="small" type="info">{{ row.related_vr_code }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="关联样机" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.related_prototype_no" size="small" type="success">{{ row.related_prototype_no }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="80">
          <template #default="{ row }">
            <el-tag :type="priorityType(row.priority)" size="small">{{ row.priority }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="结果" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.result" :type="resultType(row.result)" size="small">{{ row.result }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="testStatusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ng_count" label="NG次数" width="80" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="editTest(row)">编辑</el-button>
            <el-button link type="success" size="small" @click="showDetail(row)">执行</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 执行详情面板 -->
    <el-card v-if="selectedTest" shadow="never" style="margin-top: 16px">
      <template #header>
        <div class="card-header">
          <span>执行详情 - {{ selectedTest.title }}</span>
          <el-button size="small" @click="selectedTest = null">关闭</el-button>
        </div>
      </template>
      <TestExecutionPanel
        :test-request-id="selectedTest.id"
        @refresh="fetchAll"
      />
    </el-card>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="showTestDialog" :title="editingTestId ? '编辑测试申请' : '新建测试申请'" width="650">
      <el-form :model="testForm" label-width="110">
        <el-form-item label="测试标题" required>
          <el-input v-model="testForm.title" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="测试类型">
              <el-select v-model="testForm.test_type" style="width: 100%">
                <el-option label="噪音" value="噪音" />
                <el-option label="性能" value="性能" />
                <el-option label="可靠性" value="可靠性" />
                <el-option label="安规" value="安规" />
                <el-option label="寿命" value="寿命" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="实验分类">
              <el-select v-model="testForm.test_category" clearable style="width: 100%">
                <el-option label="性能测试" value="performance" />
                <el-option label="能效测试" value="energy" />
                <el-option label="噪音" value="noise" />
                <el-option label="凝露" value="condensation" />
                <el-option label="潮态" value="damp_heat" />
                <el-option label="高温制冷" value="high_temp_cool" />
                <el-option label="低温制热" value="low_temp_heat" />
                <el-option label="冻结融霜" value="frost_defrost" />
                <el-option label="长时间运行" value="long_run" />
                <el-option label="电气安全预验证" value="elec_safety_pre" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="关联VR">
          <el-select v-model="testForm.related_vr_id" clearable filterable placeholder="选择验证需求" style="width: 100%">
            <el-option v-for="vr in vrList" :key="vr.id" :label="`${vr.vr_code || vr.id} - ${vr.title}`" :value="vr.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联样机">
          <el-select v-model="testForm.related_prototype_id" clearable filterable placeholder="选择样机" style="width: 100%">
            <el-option v-for="p in protoList" :key="p.id" :label="`${p.proto_no || p.id} - ${p.product_code || ''}`" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="申请人">
              <el-input v-model="testForm.requester" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="优先级">
              <el-select v-model="testForm.priority">
                <el-option label="普通" value="normal" />
                <el-option label="高" value="high" />
                <el-option label="紧急" value="urgent" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="结果判定">
          <el-select v-model="testForm.result" clearable placeholder="选择判定结果" style="width: 100%">
            <el-option label="通过 (PASS)" value="PASS" />
            <el-option label="不通过 (FAIL)" value="FAIL" />
            <el-option label="豁免 (WAIVER)" value="WAIVER" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTestDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveTest">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'
import TestExecutionPanel from './TestExecutionPanel.vue'

const testList = ref<any[]>([])
const vrList = ref<any[]>([])
const protoList = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const showTestDialog = ref(false)
const editingTestId = ref<number | null>(null)
const selectedTest = ref<any>(null)

const testForm = ref<any>({
  title: '', test_type: '性能', test_category: '',
  requester: '', priority: 'normal',
  related_vr_id: null, related_prototype_id: null,
  result: '',
})

function priorityType(p: string) {
  const map: Record<string, string> = { normal: 'info', high: 'warning', urgent: 'danger' }
  return map[p] || 'info'
}

function testStatusType(s: string | null) {
  if (!s || s === 'pending') return 'info'
  if (s === 'passed') return 'success'
  if (s === 'ng') return 'danger'
  return 'warning'
}

function resultType(r: string) {
  if (r === 'PASS') return 'success'
  if (r === 'FAIL') return 'danger'
  if (r === 'WAIVER') return 'warning'
  return 'info'
}

async function fetchAll() {
  loading.value = true
  try {
    const res = await api.get('/tests')
    testList.value = res.data
  } finally { loading.value = false }
}

async function fetchVrList() {
  try {
    const res = await api.get('/verification-requirements')
    vrList.value = res.data
  } catch { /* optional */ }
}

async function fetchProtoList() {
  try {
    const res = await api.get('/certifications/prototypes')
    protoList.value = res.data
  } catch { /* optional */ }
}

function editTest(row: Record<string, unknown>) {
  editingTestId.value = row.id
  testForm.value = {
    title: row.title || '',
    test_type: row.test_type || '性能',
    test_category: row.test_category || '',
    requester: row.requester || '',
    priority: row.priority || 'normal',
    related_vr_id: row.related_vr_id || null,
    related_prototype_id: row.related_prototype_id || null,
    result: row.result || '',
  }
  showTestDialog.value = true
}

function showDetail(row: Record<string, unknown>) {
  selectedTest.value = row
}

async function saveTest() {
  saving.value = true
  try {
    const payload = { ...testForm.value }
    // Convert empty strings to null for optional foreign keys
    if (!payload.related_vr_id) delete payload.related_vr_id
    if (!payload.related_prototype_id) delete payload.related_prototype_id
    if (!payload.result) delete payload.result

    if (editingTestId.value) {
      await api.put(`/tests/${editingTestId.value}`, payload)
      ElMessage.success('更新成功')
    } else {
      await api.post('/tests', payload)
      ElMessage.success('提交成功')
    }
    showTestDialog.value = false
    editingTestId.value = null
    testForm.value = { title: '', test_type: '性能', test_category: '', requester: '', priority: 'normal', related_vr_id: null, related_prototype_id: null, result: '' }
    await fetchAll()
  } finally { saving.value = false }
}

onMounted(() => {
  fetchAll()
  fetchVrList()
  fetchProtoList()
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
</style>
