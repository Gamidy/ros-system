<template>
  <div class="iqc-page">
    <div class="page-header">
      <h2>🔬 来料检验 IQC</h2>
      <div class="header-actions">
        <el-input v-model="filters.supplier" placeholder="供应商" size="small" style="width:140px" clearable @change="fetchData" />
        <el-input v-model="filters.part_code" placeholder="物料编码" size="small" style="width:140px" clearable @change="fetchData" />
        <el-select v-model="filters.verdict" placeholder="判定" clearable size="small" style="width:100px" @change="fetchData">
          <el-option label="待检" value="pending" /><el-option label="合格" value="accept" />
          <el-option label="不合格" value="reject" /><el-option label="让步接收" value="conditional" />
        </el-select>
        <el-button size="small" type="primary" @click="showDialog=true">新建检验</el-button>
      </div>
    </div>

    <el-table :data="records" stripe border size="small" @row-click="showDetail" v-loading="loading">
      <el-table-column prop="receipt_no" label="单号" width="130" />
      <el-table-column prop="supplier" label="供应商" min-width="120" />
      <el-table-column prop="part_code" label="物料编码" width="100" />
      <el-table-column prop="part_name" label="物料名称" min-width="120" />
      <el-table-column prop="batch_no" label="批次" width="90" />
      <el-table-column label="数量" width="80">
        <template #default="{row}">{{ row.sample_qty }}/{{ row.quantity }}</template>
      </el-table-column>
      <el-table-column label="合格率" width="80">
        <template #default="{row}">{{ row.defect_rate }}%</template>
      </el-table-column>
      <el-table-column label="判定" width="90">
        <template #default="{row}">
          <el-tag :type="verdictTag(row.verdict)" size="small">{{ verdictLabel(row.verdict) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="inspector" label="检验员" width="80" />
      <el-table-column prop="inspect_date" label="日期" width="100" />
    </el-table>

    <!-- Create Dialog -->
    <el-dialog v-model="showDialog" title="新建IQC记录" width="650px" destroy-on-close>
      <el-form label-position="top" size="small">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="供应商"><el-input v-model="form.supplier" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="物料编码"><el-input v-model="form.part_code" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="物料名称"><el-input v-model="form.part_name" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="批次号"><el-input v-model="form.batch_no" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="收货单号"><el-input v-model="form.receipt_no" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="6"><el-form-item label="送检数量"><el-input-number v-model="form.quantity" :min="0" style="width:100%" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="抽样数量"><el-input-number v-model="form.sample_qty" :min="0" style="width:100%" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="AQL"><el-select v-model="form.aql" style="width:100%"><el-option label="0.65" value="0.65" /><el-option label="1.0" value="1.0" /><el-option label="2.5" value="2.5" /><el-option label="4.0" value="4.0" /></el-select></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="检验水平"><el-select v-model="form.inspection_level" style="width:100%"><el-option label="I" value="I" /><el-option label="II" value="II" /><el-option label="III" value="III" /></el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="判定">
          <el-select v-model="form.verdict" style="width:200px">
            <el-option label="待检" value="pending" /><el-option label="合格接收" value="accept" />
            <el-option label="不合格退回" value="reject" /><el-option label="让步接收" value="conditional" />
          </el-select>
        </el-form-item>
        <el-divider>检验项目</el-divider>
        <div v-for="(item, i) in form.items" :key="i" class="iqc-item-row">
          <el-input v-model="item.item_name" placeholder="检验项" size="small" style="width:150px" />
          <el-input v-model="item.spec" placeholder="规格要求" size="small" style="width:150px" />
          <el-input v-model="item.measured" placeholder="实测值" size="small" style="width:130px" />
          <el-select v-model="item.result" size="small" style="width:90px">
            <el-option label="合格" value="pass" /><el-option label="不合格" value="fail" /><el-option label="N/A" value="na" />
          </el-select>
          <el-button text size="small" type="danger" @click="form.items.splice(i,1)">✕</el-button>
        </div>
        <el-button size="small" @click="form.items.push({item_name:'',spec:'',measured:'',result:'pass'})">+ 添加检验项</el-button>
      </el-form>
      <template #footer>
        <el-button @click="showDialog=false">取消</el-button>
        <el-button type="primary" @click="saveRecord">保存</el-button>
      </template>
    </el-dialog>

    <!-- Detail Drawer -->
    <el-drawer v-model="showDetailDrawer" title="检验明细" size="500px" v-if="currentRecord">
      <div class="detail-section">
        <div class="detail-grid">
          <div><span class="label">供应商</span>{{ currentRecord.supplier }}</div>
          <div><span class="label">物料</span>{{ currentRecord.part_code }} {{ currentRecord.part_name }}</div>
          <div><span class="label">批次</span>{{ currentRecord.batch_no || '-' }}</div>
          <div><span class="label">判定</span><el-tag :type="verdictTag(currentRecord.verdict)">{{ verdictLabel(currentRecord.verdict) }}</el-tag></div>
          <div><span class="label">抽样</span>{{ currentRecord.sample_qty }}/{{ currentRecord.quantity }}</div>
          <div><span class="label">合格率</span>{{ currentRecord.defect_rate }}%</div>
        </div>
        <el-divider />
        <h4>检验项目</h4>
        <el-table :data="currentRecord.items || []" stripe border size="small">
          <el-table-column prop="item_name" label="检验项" />
          <el-table-column prop="spec" label="规格" />
          <el-table-column prop="measured" label="实测" />
          <el-table-column label="结果">
            <template #default="{row}"><el-tag :type="row.result==='pass'?'success':'danger'" size="small">{{ row.result==='pass'?'合格':'不合格' }}</el-tag></template>
          </el-table-column>
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
const records = ref<any[]>([])
const showDialog = ref(false)
const showDetailDrawer = ref(false)
const currentRecord = ref<any>(null)
const filters = reactive({ supplier: '', part_code: '', verdict: '' })
const form = reactive<any>({
  supplier: '', part_code: '', part_name: '', batch_no: '', receipt_no: '',
  quantity: 100, sample_qty: 20, aql: '0.65', inspection_level: 'II',
  verdict: 'pending', items: [],
})

function verdictTag(v: string) { return { pending: 'info', accept: 'success', reject: 'danger', conditional: 'warning' }[v] || 'info' }
function verdictLabel(v: string) { return { pending: '待检', accept: '合格', reject: '不合格', conditional: '让步接收' }[v] || v }

async function fetchData() {
  loading.value = true
  try {
    const params: any = {}
    if (filters.supplier) params.supplier = filters.supplier
    if (filters.part_code) params.part_code = filters.part_code
    if (filters.verdict) params.verdict = filters.verdict
    const r = await api.get('/quality/iqc', { params })
    records.value = r.data || []
  } catch { ElMessage.error('加载失败') }
  finally { loading.value = false }
}

async function saveRecord() {
  try {
    await api.post('/quality/iqc', form)
    ElMessage.success('创建成功')
    showDialog.value = false
    form.items = []
    await fetchData()
  } catch { ElMessage.error('保存失败') }
}

async function showDetail(row: any) {
  try {
    const r = await api.get(`/quality/iqc/${row.id}`)
    currentRecord.value = r.data
    showDetailDrawer.value = true
  } catch { ElMessage.error('加载明细失败') }
}

onMounted(fetchData)
</script>

<style scoped>
.iqc-page { padding: 16px 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
.header-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.iqc-item-row { display: flex; gap: 8px; margin-bottom: 8px; align-items: center; }
.detail-section { padding: 8px; }
.detail-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.detail-grid .label { display: block; font-size: 12px; color: #909399; }
</style>
