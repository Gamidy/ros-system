<template>
  <div class="tests-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>实验与测试</span>
          <el-button type="primary" @click="showTestDialog = true">新建测试申请</el-button>
        </div>
      </template>

      <el-table :data="testList" stripe border>
        <el-table-column prop="request_no" label="申请编号" width="150" />
        <el-table-column prop="title" label="测试项目" min-width="200" />
        <el-table-column prop="test_type" label="类型" width="100" />
        <el-table-column prop="priority" label="优先级" width="80">
          <template #default="{ row }">
            <el-tag :type="priorityType(row.priority)" size="small">{{ row.priority }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="testStatusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ng_count" label="NG次数" width="80" />
      </el-table>
    </el-card>

    <el-dialog v-model="showTestDialog" title="新建测试申请" width="600">
      <el-form :model="testForm" label-width="100">
        <el-form-item label="测试标题"><el-input v-model="testForm.title" /></el-form-item>
        <el-form-item label="测试类型">
          <el-select v-model="testForm.test_type">
            <el-option label="噪音" value="噪音" />
            <el-option label="性能" value="性能" />
            <el-option label="可靠性" value="可靠性" />
            <el-option label="安规" value="安规" />
            <el-option label="寿命" value="寿命" />
          </el-select>
        </el-form-item>
        <el-form-item label="申请人"><el-input v-model="testForm.requester" /></el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="testForm.priority">
            <el-option label="普通" value="normal" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="urgent" />
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

const testList = ref<any[]>([])
const saving = ref(false)
const showTestDialog = ref(false)
const testForm = ref({ title: '', test_type: '性能', requester: '', priority: 'normal' })

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

async function fetchAll() {
  try {
    const res = await api.get('/tests')
    testList.value = res.data
  } catch {}
}

async function saveTest() {
  saving.value = true
  try {
    await api.post('/tests', testForm.value)
    ElMessage.success('提交成功')
    showTestDialog.value = false
    testForm.value = { title: '', test_type: '性能', requester: '', priority: 'normal' }
    await fetchAll()
  } finally { saving.value = false }
}

onMounted(fetchAll)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
</style>
