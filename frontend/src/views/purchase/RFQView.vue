<template>
  <div class="rfq-page">
    <div class="page-header">
      <h2>💰 询比价管理</h2>
      <div class="header-actions">
        <el-select v-model="filterStatus" placeholder="状态" clearable size="small" style="width:120px" @change="fetchData">
          <el-option label="草稿" value="draft" /><el-option label="已发送" value="sent" />
          <el-option label="报价中" value="quoting" /><el-option label="已关闭" value="closed" />
        </el-select>
        <el-button size="small" type="primary" @click="showDialog=true">新建询价</el-button>
      </div>
    </div>

    <el-table :data="list" stripe border size="small" v-loading="loading" @row-click="openDetail">
      <el-table-column prop="rfq_no" label="询价单号" width="140" />
      <el-table-column prop="title" label="标题" min-width="150" />
      <el-table-column label="状态" width="90">
        <template #default="{row}"><el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="deadline" label="截止日期" width="100" />
      <el-table-column prop="created_by" label="创建人" width="80" />
    </el-table>

    <!-- Create Dialog -->
    <el-dialog v-model="showDialog" title="新建询价单" width="600px" destroy-on-close>
      <el-form label-position="top" size="small">
        <el-form-item label="标题"><el-input v-model="form.title" /></el-form-item>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="截止日期"><el-date-picker v-model="form.deadline" type="date" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item></el-col>
        </el-row>
        <el-divider>物料清单</el-divider>
        <div v-for="(item, i) in form.items" :key="i" class="item-row">
          <el-input v-model="item.part_code" placeholder="物料编码" size="small" style="width:130px" />
          <el-input v-model="item.part_name" placeholder="物料名称" size="small" style="width:140px" />
          <el-input-number v-model="item.qty" :min="1" size="small" style="width:100px" />
          <el-button text size="small" type="danger" @click="form.items.splice(i,1)">✕</el-button>
        </div>
        <el-button size="small" @click="form.items.push({part_code:'',part_name:'',qty:1})">+ 添加物料</el-button>
        <el-divider>邀请供应商</el-divider>
        <div v-for="(s, i) in form.suppliers" :key="i" class="item-row">
          <el-input v-model="s.supplier_name" placeholder="供应商名称" size="small" style="width:180px" />
          <el-input v-model="s.contact" placeholder="联系人" size="small" style="width:120px" />
          <el-button text size="small" type="danger" @click="form.suppliers.splice(i,1)">✕</el-button>
        </div>
        <el-button size="small" @click="form.suppliers.push({supplier_name:'',contact:''})">+ 添加供应商</el-button>
      </el-form>
      <template #footer>
        <el-button @click="showDialog=false">取消</el-button>
        <el-button type="primary" @click="saveRfq">保存</el-button>
      </template>
    </el-dialog>

    <!-- Detail Drawer -->
    <el-drawer v-model="showDetail" title="询价明细" size="550px" v-if="current">
      <div class="detail-section">
        <div class="info-bar">
          <span>{{ current.rfq_no }}</span><el-tag :type="statusTag(current.status)" size="small">{{ statusLabel(current.status) }}</el-tag>
          <span>截止: {{ current.deadline || '-' }}</span>
        </div>
        <el-divider />
        <h4>📦 物料清单</h4>
        <div v-for="(item, i) in parseItems(current.items)" :key="i" class="item-display">{{ item.part_code }} {{ item.part_name }} x {{ item.qty }}</div>
        <el-divider />
        <h4>📊 报价对比</h4>
        <div v-if="current.price_analysis" class="price-analysis">
          <el-statistic title="最低价" :value="current.price_analysis.min" />
          <el-statistic title="最高价" :value="current.price_analysis.max" />
          <el-statistic title="平均价" :value="current.price_analysis.avg" />
          <el-statistic title="报价数" :value="current.price_analysis.quotation_count" />
        </div>
        <el-table :data="current.quotations || []" stripe border size="small">
          <el-table-column prop="supplier_name" label="供应商" width="120" />
          <el-table-column prop="total_amount" label="总价" width="100" />
          <el-table-column prop="delivery_days" label="交期(天)" width="80" />
          <el-table-column prop="payment_terms" label="付款条件" width="100" />
        </el-table>
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
const filterStatus = ref('')
const form = reactive<any>({ title: '', deadline: null, remark: '', items: [], suppliers: [] })

function statusTag(s: string) { return { draft: 'info', sent: 'primary', quoting: 'warning', closed: 'success' }[s] || 'info' }
function statusLabel(s: string) { return { draft: '草稿', sent: '已发送', quoting: '报价中', closed: '已关闭' }[s] || s }
function parseItems(json: string) { try { return JSON.parse(json || '[]') } catch { return [] } }

async function fetchData() {
  loading.value = true
  try {
    const params: any = {}
    if (filterStatus.value) params.status = filterStatus.value
    const r = await api.get('/purchase/rfqs', { params })
    list.value = r.data || []
  } catch { ElMessage.error('加载失败') }
  finally { loading.value = false }
}

async function saveRfq() {
  try {
    await api.post('/purchase/rfqs', {
      title: form.title, deadline: form.deadline, remark: form.remark,
      items: JSON.stringify(form.items), suppliers: JSON.stringify(form.suppliers),
    })
    ElMessage.success('创建成功')
    showDialog.value = false
    await fetchData()
  } catch { ElMessage.error('保存失败') }
}

async function openDetail(row: any) {
  try {
    const r = await api.get(`/purchase/rfqs/${row.id}`)
    current.value = r.data
    showDetail.value = true
  } catch { ElMessage.error('加载失败') }
}

onMounted(fetchData)
</script>

<style scoped>
.rfq-page { padding: 16px 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
.header-actions { display: flex; gap: 8px; }
.item-row { display: flex; gap: 8px; margin-bottom: 8px; align-items: center; }
.detail-section { padding: 8px; }
.info-bar { display: flex; gap: 16px; align-items: center; }
.price-analysis { display: flex; gap: 24px; margin-bottom: 12px; }
.item-display { padding: 4px 0; font-size: 13px; color: #606266; }
</style>
