<template>
  <div>
    <div style="margin-bottom:12px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
      <el-input v-model="keyword" placeholder="搜索订单号/标题" clearable style="width:220px" @clear="fetchData" @keyup.enter="fetchData" />
      <el-select v-model="filterStatus" placeholder="状态" clearable style="width:110px" @change="fetchData">
        <el-option label="草稿" value="draft" /><el-option label="待确认" value="pending" /><el-option label="进行中" value="in_progress" />
        <el-option label="已交付" value="delivered" /><el-option label="已关闭" value="closed" />
      </el-select>
      <el-button type="primary" @click="showCreate">新建订单</el-button>
    </div>
    <el-table :data="items" v-loading="loading" stripe>
      <el-table-column prop="order_no" label="订单号" width="160" />
      <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
      <el-table-column prop="partner_name" label="外协厂商" width="150" />
      <el-table-column label="类型" width="70"><template #default="{row}">{{ row.order_type }}</template></el-table-column>
      <el-table-column prop="total_amount" label="金额" width="80" align="right" />
      <el-table-column prop="delivery_date" label="交期" width="90" />
      <el-table-column label="状态" width="80"><template #default="{row}">
        <el-tag :type="row.status==='closed'?'success':row.status==='delivered'?'warning':'info'" size="small">{{ statusLabel(row.status) }}</el-tag>
      </template></el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{row}">
          <el-button link type="primary" size="small" @click="showDetail(row)">详情</el-button>
          <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div style="margin-top:12px;text-align:right"><el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" layout="total,prev,pager,next" @change="fetchData" /></div>

    <el-dialog v-model="detailVisible" :title="'订单: '+currentOrder?.order_no" width="700px">
      <template v-if="currentOrder">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="标题">{{ currentOrder.title }}</el-descriptions-item>
          <el-descriptions-item label="外协厂商">{{ currentOrder.partner_name }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ currentOrder.order_type }}</el-descriptions-item>
          <el-descriptions-item label="数量">{{ currentOrder.quantity }}{{ currentOrder.unit }}</el-descriptions-item>
          <el-descriptions-item label="金额">¥{{ currentOrder.total_amount }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ statusLabel(currentOrder.status) }}</el-descriptions-item>
          <el-descriptions-item label="优先级">{{ currentOrder.priority }}</el-descriptions-item>
          <el-descriptions-item label="要求交期">{{ currentOrder.delivery_date||'-' }}</el-descriptions-item>
          <el-descriptions-item label="实际交期">{{ currentOrder.actual_delivery_date||'-' }}</el-descriptions-item>
        </el-descriptions>
        <div style="margin-top:8px;display:flex;gap:8px;">
          <el-button v-if="currentOrder.status==='draft'" size="small" @click="updateStatus('pending')">提交确认</el-button>
          <el-button v-if="currentOrder.status==='pending'" size="small" type="primary" @click="updateStatus('in_progress')">开始生产</el-button>
          <el-button v-if="currentOrder.status==='in_progress'" size="small" type="success" @click="updateStatus('delivered')">完成交付</el-button>
          <el-button v-if="currentOrder.status!=='closed'&&currentOrder.status!=='cancelled'" size="small" @click="updateStatus('closed')">关闭</el-button>
          <el-button size="small" @click="editOrder">编辑</el-button>
        </div>
        <div style="margin-top:12px;"><h4>订单明细</h4>
          <el-table :data="currentOrder.items||[]" size="small">
            <el-table-column prop="part_no" label="物料编码" width="120" />
            <el-table-column prop="part_name" label="名称" width="150" />
            <el-table-column prop="quantity" label="数量" width="60" />
            <el-table-column prop="unit_price" label="单价" width="70" align="right" />
            <el-table-column prop="total_price" label="小计" width="70" align="right" />
            <el-table-column prop="delivery_date" label="交期" width="90" />
          </el-table>
        </div>
        <div v-if="currentOrder.technical_requirements" style="margin-top:8px;"><b>技术要求:</b> {{ currentOrder.technical_requirements }}</div>
        <div v-if="currentOrder.quality_requirements" style="margin-top:4px;"><b>质量要求:</b> {{ currentOrder.quality_requirements }}</div>
      </template>
    </el-dialog>

    <el-dialog v-model="formVisible" :title="isEditForm?'编辑订单':'新建订单'" width="650px">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="标题" prop="title"><el-input v-model="form.title" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="外协厂商" prop="partner_id"><el-select v-model="form.partner_id" style="width:100%" filterable placeholder="选择厂商">
            <el-option v-for="p in partners" :key="p.id" :label="p.name" :value="p.id" />
          </el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="订单类型"><el-select v-model="form.order_type" style="width:100%">
            <el-option label="模具" value="mold" /><el-option label="零件" value="part" /><el-option label="装配" value="assembly" /><el-option label="其他" value="other" />
          </el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8"><el-form-item label="数量"><el-input-number v-model="form.quantity" style="width:100%" :min="1" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="单位"><el-input v-model="form.unit" placeholder="批" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="总金额"><el-input-number v-model="form.total_amount" style="width:100%" :min="0" :precision="2" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="要求交期"><el-date-picker v-model="form.delivery_date" type="date" style="width:100%" value-format="YYYY-MM-DD" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="优先级"><el-select v-model="form.priority" style="width:100%">
            <el-option label="普通" value="normal" /><el-option label="高" value="high" /><el-option label="紧急" value="urgent" />
          </el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="技术要求"><el-input v-model="form.technical_requirements" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="质量要求"><el-input v-model="form.quality_requirements" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="formVisible=false">取消</el-button><el-button type="primary" :loading="saving" @click="saveOrder">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listOutsourceOrders, getOutsourceOrder, createOutsourceOrder, updateOutsourceOrder, deleteOutsourceOrder, listOutsourcePartners } from '../../api/outsource'
import type { FormInstance } from 'element-plus'
import type { TableRow } from '@/types/common'

const items = ref<any[]>([]); const total = ref(0); const page = ref(1); const pageSize = ref(20); const loading = ref(false)
const keyword = ref(''); const filterStatus = ref('')
const detailVisible = ref(false); const currentOrder = ref<any>(null)
const formVisible = ref(false); const isEditForm = ref(false); const editingOrderId = ref<number|null>(null)
const saving = ref(false); const formRef = ref<FormInstance>()
const partners = ref<any[]>([])
const form = ref<any>({ title: '', partner_id: null, order_type: 'part', quantity: 1, unit: '批', total_amount: 0, delivery_date: null, priority: 'normal', technical_requirements: '', quality_requirements: '', remark: '', created_by: '' })
const formRules = { title: [{ required: true, message: '请输入标题' }], partner_id: [{ required: true, message: '请选择外协厂商' }] }

function statusLabel(s: string) { const m: Record<string,string>={draft:'草稿',pending:'待确认',in_progress:'进行中',delivered:'已交付',closed:'已关闭',cancelled:'已取消'}; return m[s]||s }

async function fetchData() { loading.value=true; try { const { data } = await listOutsourceOrders({ page:page.value, page_size:pageSize.value, keyword:keyword.value||undefined, status:filterStatus.value||undefined }); items.value=data.items||[]; total.value=data.total||0 } catch{} finally{loading.value=false} }
async function loadPartners() { try { const { data } = await listOutsourcePartners({ page:1, page_size:200 }); partners.value = data.items||[] } catch{} }

async function showDetail(row: TableRow) { try { const { data } = await getOutsourceOrder(row.id); currentOrder.value=data; detailVisible.value=true } catch{} }
async function updateStatus(status: string) { if(!currentOrder.value) return; try { await updateOutsourceOrder(currentOrder.value.id, { status }); showDetail(currentOrder.value); fetchData() } catch{} }

function showCreate() { isEditForm.value=false; editingOrderId.value=null; form.value={title:'',partner_id:null,order_type:'part',quantity:1,unit:'批',total_amount:0,delivery_date:null,priority:'normal',technical_requirements:'',quality_requirements:'',remark:'',created_by:''}; formVisible.value=true }
function editOrder() { if(!currentOrder.value) return; isEditForm.value=true; editingOrderId.value=currentOrder.value.id; form.value={...currentOrder.value}; formVisible.value=true }

async function saveOrder() { if(!await formRef.value?.validate().catch(()=>false)) return; saving.value=true; try { if(isEditForm.value&&editingOrderId.value) await updateOutsourceOrder(editingOrderId.value, form.value); else await createOutsourceOrder(form.value); formVisible.value=false; fetchData() } catch{} finally{saving.value=false} }
async function handleDelete(row: TableRow) { try{await deleteOutsourceOrder(row.id);fetchData()}catch{} }

onMounted(()=>{fetchData();loadPartners()})
</script>
