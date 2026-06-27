<template>
  <div>
    <div style="margin-bottom:12px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
      <el-input v-model="keyword" placeholder="搜索厂商编码/名称" clearable style="width:220px" @clear="fetchData" @keyup.enter="fetchData" />
      <el-select v-model="filterType" placeholder="外协类型" clearable style="width:120px" @change="fetchData">
        <el-option label="模具外协" value="mold" /><el-option label="电控外协" value="electrical" />
        <el-option label="系统外协" value="system" /><el-option label="结构外协" value="structural" />
      </el-select>
      <el-button type="primary" @click="showCreate">新建厂商</el-button>
    </div>
    <el-table :data="items" v-loading="loading" stripe>
      <el-table-column prop="code" label="编码" width="100" />
      <el-table-column prop="name" label="厂商名称" min-width="180" />
      <el-table-column label="类型" width="80"><template #default="{row}">{{ typeLabel(row.partner_type) }}</template></el-table-column>
      <el-table-column prop="contact_person" label="联系人" width="100" />
      <el-table-column prop="contact_phone" label="电话" width="120" />
      <el-table-column label="资质" width="60"><template #default="{row}"><el-tag size="small">{{ row.qualification_level }}</el-tag></template></el-table-column>
      <el-table-column prop="rating" label="评分" width="60" align="center" />
      <el-table-column prop="orders_count" label="订单数" width="60" align="center" />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{row}">
          <el-button link type="primary" size="small" @click="showEdit(row)">编辑</el-button>
          <el-popconfirm title="确定删除?" @confirm="handleDelete(row)"><template #reference><el-button link type="danger" size="small">删除</el-button></template></el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
    <div style="margin-top:12px;text-align:right"><el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" layout="total,prev,pager,next" @change="fetchData" /></div>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑厂商' : '新建厂商'" width="550px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="16"><el-col :span="12"><el-form-item label="编码" prop="code"><el-input v-model="form.code" /></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="名称" prop="name"><el-input v-model="form.name" /></el-form-item></el-col></el-row>
        <el-row :gutter="16"><el-col :span="12"><el-form-item label="外协类型"><el-select v-model="form.partner_type" style="width:100%"><el-option label="模具" value="mold" /><el-option label="电控" value="electrical" /><el-option label="系统" value="system" /><el-option label="结构" value="structural" /><el-option label="其他" value="other" /></el-select></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="资质等级"><el-select v-model="form.qualification_level" style="width:100%"><el-option label="A" value="A" /><el-option label="B" value="B" /><el-option label="C" value="C" /></el-select></el-form-item></el-col></el-row>
        <el-row :gutter="16"><el-col :span="12"><el-form-item label="联系人"><el-input v-model="form.contact_person" /></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="电话"><el-input v-model="form.contact_phone" /></el-form-item></el-col></el-row>
        <el-form-item label="地址"><el-input v-model="form.address" /></el-form-item>
        <el-form-item label="业务范围"><el-input v-model="form.business_scope" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" :loading="saving" @click="handleSave">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import type { TableRow } from '@/types/common'
import { computed, ref, onMounted } from 'vue'
import { listOutsourcePartners, createOutsourcePartner, updateOutsourcePartner, deleteOutsourcePartner } from '../../api/outsource'
import type { FormInstance } from 'element-plus'

const items = ref<any[]>([]); const total = ref(0); const page = ref(1); const pageSize = ref(20); const loading = ref(false)
const keyword = ref(''); const filterType = ref(''); const dialogVisible = ref(false); const isEdit = ref(false); const editingId = ref<number|null>(null); const saving = ref(false); const formRef = ref<FormInstance>()
const form = ref<any>({ code: '', name: '', partner_type: 'other', contact_person: '', contact_phone: '', address: '', business_scope: '', qualification_level: 'B', rating: null, remark: '' })
const rules = { code: [{ required: true, message: '请输入编码' }], name: [{ required: true, message: '请输入名称' }] }
function typeLabel(t: string) { const m: Record<string,string>={mold:'模具',electrical:'电控',system:'系统',structural:'结构',other:'其他'}; return m[t]||t }

async function fetchData() { loading.value=true; try { const { data } = await listOutsourcePartners({ page:page.value, page_size:pageSize.value, keyword:keyword.value||undefined, partner_type:filterType.value||undefined }); items.value=data.items||[]; total.value=data.total||0 } catch{} finally{loading.value=false} }
function showCreate() { isEdit.value=false; editingId.value=null; form.value={code:'',name:'',partner_type:'other',contact_person:'',contact_phone:'',address:'',business_scope:'',qualification_level:'B',rating:null,remark:''}; dialogVisible.value=true }
function showEdit(row: TableRow) { isEdit.value=true; editingId.value=row.id; form.value={...row}; dialogVisible.value=true }
async function handleSave() { if(!await formRef.value?.validate().catch(()=>false)) return; saving.value=true; try { if(isEdit.value&&editingId.value) await updateOutsourcePartner(editingId.value, form.value); else await createOutsourcePartner(form.value); dialogVisible.value=false; fetchData() } catch{} finally{saving.value=false} }
async function handleDelete(row: TableRow) { try{await deleteOutsourcePartner(row.id);fetchData()}catch{} }
onMounted(fetchData)
</script>
