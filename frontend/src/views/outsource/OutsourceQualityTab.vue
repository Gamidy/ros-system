<template>
  <div>
    <div style="margin-bottom:12px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
      <el-select v-model="filterOrderId" placeholder="选择订单" clearable filterable style="width:200px" @change="fetchData">
        <el-option v-for="o in orders" :key="o.id" :label="o.order_no+' - '+o.title" :value="o.id" />
      </el-select>
      <el-select v-model="filterResult" placeholder="结果" clearable style="width:100px" @change="fetchData">
        <el-option label="通过" value="pass" /><el-option label="不通过" value="fail" /><el-option label="有条件" value="conditional" />
      </el-select>
      <el-button type="primary" @click="showCreate">新建质检记录</el-button>
    </div>
    <el-table :data="items" v-loading="loading" stripe>
      <el-table-column prop="order_title" label="关联订单" min-width="180" show-overflow-tooltip />
      <el-table-column label="质检类型" width="80"><template #default="{row}">{{ row.inspect_type==='incoming'?'来料':row.inspect_type==='process'?'过程':'最终' }}</template></el-table-column>
      <el-table-column prop="inspect_date" label="检验日期" width="100" />
      <el-table-column prop="inspector" label="检验员" width="80" />
      <el-table-column prop="sample_qty" label="抽检数" width="60" align="center" />
      <el-table-column prop="defect_qty" label="不合格" width="60" align="center" />
      <el-table-column label="结果" width="70"><template #default="{row}">
        <el-tag :type="row.result==='pass'?'success':row.result==='fail'?'danger':'warning'" size="small">{{ row.result==='pass'?'通过':row.result==='fail'?'不通过':'有条件' }}</el-tag>
      </template></el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{row}">
          <el-button link type="primary" size="small" @click="showEdit(row)">编辑</el-button>
          <el-popconfirm title="确定删除?" @confirm="handleDelete(row)"><template #reference><el-button link type="danger" size="small">删除</el-button></template></el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
    <div style="margin-top:12px;text-align:right"><el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" layout="total,prev,pager,next" @change="fetchData" /></div>

    <el-dialog v-model="dialogVisible" :title="isEdit?'编辑质检记录':'新建质检记录'" width="550px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="关联订单" prop="order_id"><el-select v-model="form.order_id" filterable style="width:100%">
          <el-option v-for="o in orders" :key="o.id" :label="o.order_no+' - '+o.title" :value="o.id" />
        </el-select></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="质检类型"><el-select v-model="form.inspect_type" style="width:100%">
            <el-option label="来料检验" value="incoming" /><el-option label="过程检验" value="process" /><el-option label="最终检验" value="final" />
          </el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="检验日期"><el-date-picker v-model="form.inspect_date" type="date" style="width:100%" value-format="YYYY-MM-DD" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="检验员"><el-input v-model="form.inspector" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="结果"><el-select v-model="form.result" style="width:100%">
            <el-option label="通过" value="pass" /><el-option label="不通过" value="fail" /><el-option label="有条件" value="conditional" />
          </el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="抽检数量"><el-input-number v-model="form.sample_qty" style="width:100%" :min="0" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="不合格数"><el-input-number v-model="form.defect_qty" style="width:100%" :min="0" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="缺陷描述"><el-input v-model="form.defect_description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="检验结论"><el-input v-model="form.conclusion" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" :loading="saving" @click="handleSave">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import type { TableRow } from '@/types/common'
import { ref, onMounted } from 'vue'
import { listOutsourceQualityRecords, createOutsourceQualityRecord, updateOutsourceQualityRecord, deleteOutsourceQualityRecord, listOutsourceOrders } from '../../api/outsource'
import type { FormInstance } from 'element-plus'

const items = ref<any[]>([]); const total = ref(0); const page = ref(1); const pageSize = ref(20); const loading = ref(false)
const filterOrderId = ref<number|null>(null); const filterResult = ref('')
const dialogVisible = ref(false); const isEdit = ref(false); const editingId = ref<number|null>(null); const saving = ref(false); const formRef = ref<FormInstance>()
const orders = ref<any[]>([])
const form = ref<any>({ order_id: null, inspect_type: 'incoming', inspect_date: '', inspector: '', result: 'pass', sample_qty: 0, defect_qty: 0, defect_description: '', conclusion: '' })
const rules = { order_id: [{ required: true, message: '请选择订单' }] }

async function fetchData() { loading.value=true; try { const { data } = await listOutsourceQualityRecords({ page:page.value, page_size:pageSize.value, order_id:filterOrderId.value||undefined, result:filterResult.value||undefined }); items.value=data.items||[]; total.value=data.total||0 } catch{} finally{loading.value=false} }
async function loadOrders() { try { const { data } = await listOutsourceOrders({ page:1, page_size:200 }); orders.value=data.items||[] } catch{} }
function showCreate() { isEdit.value=false; editingId.value=null; form.value={order_id:null,inspect_type:'incoming',inspect_date:'',inspector:'',result:'pass',sample_qty:0,defect_qty:0,defect_description:'',conclusion:''}; dialogVisible.value=true }
function showEdit(row: TableRow) { isEdit.value=true; editingId.value=row.id as number; form.value={...row}; dialogVisible.value=true }
async function handleSave() { if(!await formRef.value?.validate().catch(()=>false)) return; saving.value=true; try { if(isEdit.value&&editingId.value) await updateOutsourceQualityRecord(editingId.value, form.value); else await createOutsourceQualityRecord(form.value); dialogVisible.value=false; fetchData() } catch{} finally{saving.value=false} }
async function handleDelete(row: TableRow) { try{await deleteOutsourceQualityRecord(row.id as number);fetchData()}catch{} }

onMounted(()=>{fetchData();loadOrders()})
</script>
