<template>
  <div class="complaint-page">
    <div class="page-header">
      <h2>📢 客户投诉管理</h2>
      <el-button type="primary" size="small" @click="showDialog=true">新建投诉</el-button>
    </div>

    <el-card shadow="never" class="filter-card">
      <el-row :gutter="12">
        <el-col :span="6"><el-input v-model="filters.customer" placeholder="客户名称" size="small" clearable @change="fetchData" /></el-col>
        <el-col :span="4"><el-select v-model="filters.severity" placeholder="严重程度" clearable size="small" style="width:100%" @change="fetchData">
          <el-option label="紧急" value="critical" /><el-option label="高" value="high" /><el-option label="中" value="medium" /><el-option label="低" value="low" />
        </el-select></el-col>
        <el-col :span="4"><el-select v-model="filters.status" placeholder="状态" clearable size="small" style="width:100%" @change="fetchData">
          <el-option label="待处理" value="open" /><el-option label="调查中" value="investigation" />
          <el-option label="整改中" value="action" /><el-option label="验证中" value="verify" /><el-option label="已关闭" value="closed" />
        </el-select></el-col>
      </el-row>
    </el-card>

    <el-table :data="list" stripe border size="small" v-loading="loading" @row-click="openDetail" style="margin-top:12px">
      <el-table-column prop="complaint_no" label="编号" width="140" />
      <el-table-column prop="title" label="投诉标题" min-width="160" />
      <el-table-column prop="customer_name" label="客户" width="120" />
      <el-table-column label="严重程度" width="80">
        <template #default="{row}"><el-tag :type="sevTag(row.severity)" size="small">{{ {critical:'紧急',high:'高',medium:'中',low:'低'}[row.severity] || row.severity }}</el-tag></template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{row}"><el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="handler" label="处理人" width="80" />
      <el-table-column prop="complain_date" label="投诉日期" width="100" />
    </el-table>

    <!-- Create Dialog -->
    <el-dialog v-model="showDialog" title="新建投诉" width="600px" destroy-on-close>
      <el-form label-position="top" size="small">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="客户名称"><el-input v-model="form.customer_name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="产品型号"><el-input v-model="form.product_code" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="投诉标题"><el-input v-model="form.title" /></el-form-item>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="类型"><el-select v-model="form.complaint_type" style="width:100%">
            <el-option label="质量问题" value="quality" /><el-option label="交付问题" value="delivery" />
            <el-option label="服务问题" value="service" /><el-option label="其他" value="other" />
          </el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="严重程度"><el-select v-model="form.severity" style="width:100%">
            <el-option label="紧急" value="critical" /><el-option label="高" value="high" />
            <el-option label="中" value="medium" /><el-option label="低" value="low" />
          </el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="处理人"><el-input v-model="form.handler" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="投诉描述"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog=false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- Detail -->
    <el-drawer v-model="showDetail" title="投诉详情" size="500px" v-if="current">
      <div class="detail-section">
        <div class="info-bar">
          <span>{{ current.complaint_no }}</span>
          <el-tag :type="sevTag(current.severity)" size="small">{{ current.severity }}</el-tag>
          <el-tag :type="statusTag(current.status)" size="small">{{ statusLabel(current.status) }}</el-tag>
        </div>
        <el-divider />
        <div class="detail-grid">
          <div><span class="label">客户</span>{{ current.customer_name }}</div>
          <div><span class="label">产品</span>{{ current.product_code || '-' }}</div>
          <div><span class="label">批次</span>{{ current.batch_no || '-' }}</div>
          <div><span class="label">涉及数量</span>{{ current.qty_involved || '-' }}</div>
          <div><span class="label">处理人</span>{{ current.handler || '-' }}</div>
          <div><span class="label">投诉日期</span>{{ current.complain_date || '-' }}</div>
        </div>
        <h4>投诉描述</h4>
        <p>{{ current.description || '无' }}</p>
        <h4>根本原因</h4>
        <p>{{ current.root_cause || '待分析' }}</p>
        <h4>纠正措施</h4>
        <p>{{ current.corrective_action || '待制定' }}</p>
        <div class="detail-actions">
          <el-button type="primary" size="small" @click="updateStatus('investigation')" v-if="current.status==='open'">开始调查</el-button>
          <el-button type="warning" size="small" @click="updateStatus('action')" v-if="current.status==='investigation'">制定措施</el-button>
          <el-button type="success" size="small" @click="updateStatus('verify')" v-if="current.status==='action'">申请验证</el-button>
          <el-button type="success" size="small" @click="updateStatus('closed')" v-if="current.status==='verify'">关闭投诉</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const loading = ref(false)
const list = ref<any[]>([])
const showDialog = ref(false)
const showDetail = ref(false)
const current = ref<any>(null)
const filters = reactive({ customer: '', severity: '', status: '' })
const form = reactive<any>({ customer_name: '', product_code: '', title: '', complaint_type: 'quality', severity: 'medium', handler: '', description: '' })

function sevTag(s: string) { return { critical: 'danger', high: 'warning', medium: 'info', low: 'info' }[s] || 'info' }
function statusTag(s: string) { return { open: 'danger', investigation: 'warning', action: 'primary', verify: 'info', closed: 'success' }[s] || 'info' }
function statusLabel(s: string) { return { open: '待处理', investigation: '调查中', action: '整改中', verify: '验证中', closed: '已关闭' }[s] || s }

async function fetchData() {
  loading.value = true
  try {
    const params: any = {}
    if (filters.customer) params.customer = filters.customer
    if (filters.severity) params.severity = filters.severity
    if (filters.status) params.status = filters.status
    const r = await api.get('/quality/complaints', { params })
    list.value = r.data || []
  } catch { ElMessage.error('加载失败') }
  finally { loading.value = false }
}

async function save() {
  try { await api.post('/quality/complaints', form); ElMessage.success('已创建'); showDialog.value = false; await fetchData() }
  catch { ElMessage.error('保存失败') }
}

async function openDetail(row: any) {
  try { const r = await api.get(`/quality/complaints/${row.id}`); current.value = r.data; showDetail.value = true }
  catch { ElMessage.error('加载失败') }
}

async function updateStatus(status: string) {
  if (!current.value) return
  try { await api.put(`/quality/complaints/${current.value.id}`, { status }); ElMessage.success('状态已更新'); await openDetail(current.value); await fetchData() }
  catch { ElMessage.error('更新失败') }
}

onMounted(fetchData)
</script>

<style scoped>
.complaint-page { padding: 16px 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.filter-card { margin-bottom: 12px; }
.detail-section { padding: 8px; }
.info-bar { display: flex; gap: 12px; align-items: center; }
.detail-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 16px; }
.detail-grid .label { display: block; font-size: 12px; color: #909399; }
h4 { margin: 12px 0 4px; font-size: 14px; color: #303133; }
p { color: #606266; font-size: 13px; line-height: 1.6; white-space: pre-wrap; }
.detail-actions { margin-top: 20px; display: flex; gap: 8px; }
</style>
