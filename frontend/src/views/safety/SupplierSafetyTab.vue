<template>
  <div>
    <div class="toolbar" style="margin-bottom:12px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
      <el-input v-model="searchKeyword" placeholder="搜索证书编号/资质类型" clearable style="width:220px" @clear="fetchData" @keyup.enter="fetchData" />
      <el-select v-model="filterStatus" placeholder="资质状态" clearable style="width:120px" @change="fetchData">
        <el-option label="有效" value="active" />
        <el-option label="已过期" value="expired" />
        <el-option label="已注销" value="revoked" />
      </el-select>
      <el-select v-model="filterAuditStatus" placeholder="审核状态" clearable style="width:120px" @change="fetchData">
        <el-option label="待审核" value="pending" />
        <el-option label="已通过" value="approved" />
        <el-option label="已拒绝" value="rejected" />
      </el-select>
      <el-button type="primary" @click="showCreate">新建资质</el-button>
      <el-button :type="filterExpirySoon ? 'warning' : 'default'" @click="toggleExpiryFilter">{{ filterExpirySoon ? `${filterExpirySoon}天内到期` : '到期预警' }}</el-button>
    </div>

    <el-table :data="qualifications" v-loading="loading" style="width:100%" stripe>
      <el-table-column prop="supplier_name" label="供应商" width="150" />
      <el-table-column prop="qualification_type" label="资质类型" width="120" />
      <el-table-column prop="cert_no" label="证书编号" width="150" />
      <el-table-column prop="issuing_body" label="发证机构" width="140" />
      <el-table-column prop="issue_date" label="发证日期" width="100" />
      <el-table-column prop="expiry_date" label="有效期至" width="100">
        <template #default="{row}">
          <span :style="{ color: isExpiringSoon(row.expiry_date) ? '#f56c6c' : undefined, fontWeight: isExpiringSoon(row.expiry_date) ? 'bold' : undefined }">
            {{ row.expiry_date || '-' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="资质状态" width="80">
        <template #default="{row}">
          <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
            {{ row.status === 'active' ? '有效' : row.status === 'expired' ? '过期' : '注销' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="审核状态" width="80">
        <template #default="{row}">
          <el-tag :type="row.audit_status === 'approved' ? 'success' : row.audit_status === 'rejected' ? 'danger' : 'warning'" size="small">
            {{ row.audit_status === 'approved' ? '通过' : row.audit_status === 'rejected' ? '拒绝' : '待审' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{row}">
          <el-button link type="primary" size="small" @click="showEdit(row)">编辑</el-button>
          <el-button link type="success" size="small" @click="showAuditDialog(row)">审核</el-button>
          <el-popconfirm title="确定删除?" @confirm="handleDelete(row)">
            <template #reference>
              <el-button link type="danger" size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <div style="margin-top:12px;text-align:right">
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10,20,50]" layout="total,sizes,prev,pager,next" @change="fetchData" />
    </div>

    <!-- 创建/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑供应商安规资质' : '新建供应商安规资质'" width="600px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="供应商ID" prop="supplier_id">
              <el-input-number v-model="form.supplier_id" style="width:100%" :min="1" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="资质类型" prop="qualification_type">
              <el-select v-model="form.qualification_type" style="width:100%">
                <el-option label="ISO9001" value="ISO9001" />
                <el-option label="UL认证" value="UL" />
                <el-option label="CCC认证" value="CCC" />
                <el-option label="CE认证" value="CE" />
                <el-option label="CB认证" value="CB" />
                <el-option label="SAA认证" value="SAA" />
                <el-option label="其他" value="other" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="证书编号">
              <el-input v-model="form.cert_no" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="发证机构">
              <el-input v-model="form.issuing_body" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="发证日期">
              <el-date-picker v-model="form.issue_date" type="date" style="width:100%" value-format="YYYY-MM-DD" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="有效期至">
              <el-date-picker v-model="form.expiry_date" type="date" style="width:100%" value-format="YYYY-MM-DD" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="审核意见">
          <el-input v-model="form.audit_comment" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 审核弹窗 -->
    <el-dialog v-model="auditDialogVisible" title="安规资质审核" width="500px">
      <el-form ref="auditFormRef" :model="auditForm" :rules="auditRules" label-width="100px">
        <el-form-item label="审核结果" prop="result">
          <el-radio-group v-model="auditForm.result">
            <el-radio value="pass">通过 Pass</el-radio>
            <el-radio value="fail">不通过 Fail</el-radio>
            <el-radio value="conditional">有条件通过 Conditional</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="审核人">
          <el-input v-model="auditForm.auditor" />
        </el-form-item>
        <el-form-item label="审核日期">
          <el-date-picker v-model="auditForm.audit_date" type="date" style="width:100%" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="发现项">
          <el-input v-model="auditForm.findings" type="textarea" :rows="3" placeholder="JSON格式或文本描述" />
        </el-form-item>
        <el-form-item label="下次审核日期">
          <el-date-picker v-model="auditForm.next_audit_date" type="date" style="width:100%" value-format="YYYY-MM-DD" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="auditDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="auditing" @click="handleAuditSubmit">提交审核</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listSupplierQualifications, createSupplierQualification, updateSupplierQualification, deleteSupplierQualification, createAuditRecord } from '../../api/safety'
import type { FormInstance } from 'element-plus'
import type { TableRow } from '@/types/common'

const qualifications = ref<TableRow[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const searchKeyword = ref('')
const filterStatus = ref('')
const filterAuditStatus = ref('')
const filterExpirySoon = ref<number | null>(null)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref<FormInstance>()
const auditDialogVisible = ref(false)
const auditFormRef = ref<FormInstance>()
const auditing = ref(false)
const currentQualId = ref<number | null>(null)

const form = ref<Record<string, unknown>>({
  supplier_id: null, qualification_type: 'ISO9001', cert_no: '',
  issuing_body: '', issue_date: null, expiry_date: null,
  attachments: null, status: 'active', audit_status: 'pending', audit_comment: '',
})

const rules = {
  supplier_id: [{ required: true, message: '请输入供应商ID', trigger: 'blur' }],
  qualification_type: [{ required: true, message: '请选择资质类型', trigger: 'change' }],
}

const auditForm = ref<Record<string, unknown>>({
  qualification_id: null, audit_date: '', auditor: '', result: 'pass',
  findings: '', next_audit_date: null,
})

const auditRules = {
  result: [{ required: true, message: '请选择审核结果', trigger: 'change' }],
}

function isExpiringSoon(dateStr: string) {
  if (!dateStr) return false
  const days = (new Date(dateStr).getTime() - Date.now()) / (1000 * 86400)
  return days <= 30 && days > 0
}

function toggleExpiryFilter() {
  filterExpirySoon.value = filterExpirySoon.value ? null : 30
  page.value = 1
  fetchData()
}

async function fetchData() {
  loading.value = true
  try {
    const { data } = await listSupplierQualifications({
      page: page.value, page_size: pageSize.value,
      keyword: searchKeyword.value || undefined,
      status: filterStatus.value || undefined,
      audit_status: filterAuditStatus.value || undefined,
      expiry_soon: filterExpirySoon.value || undefined,
    })
    qualifications.value = data.items || []
    total.value = data.total || 0
  } catch { /* */ } finally { loading.value = false }
}

function showCreate() {
  isEdit.value = false
  editingId.value = null
  form.value = {
    supplier_id: null, qualification_type: 'ISO9001', cert_no: '',
    issuing_body: '', issue_date: null, expiry_date: null,
    attachments: null, status: 'active', audit_status: 'pending', audit_comment: '',
  }
  dialogVisible.value = true
}

function showEdit(row: TableRow) {
  isEdit.value = true
  editingId.value = row.id as number
  form.value = { ...row, attachments: null }
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (isEdit.value && editingId.value) {
      await updateSupplierQualification(editingId.value, form.value)
    } else {
      await createSupplierQualification(form.value)
    }
    dialogVisible.value = false
    fetchData()
  } catch { /* */ } finally { saving.value = false }
}

async function handleDelete(row: TableRow) {
  try {
    await deleteSupplierQualification(row.id as number)
    fetchData()
  } catch { /* */ }
}

function showAuditDialog(row: TableRow) {
  currentQualId.value = row.id as number
  auditForm.value = {
    qualification_id: row.id as number,
    audit_date: new Date().toISOString().slice(0, 10),
    auditor: '', result: 'pass', findings: '', next_audit_date: null,
  }
  auditDialogVisible.value = true
}

async function handleAuditSubmit() {
  const valid = await auditFormRef.value?.validate().catch(() => false)
  if (!valid) return
  auditing.value = true
  try {
    await createAuditRecord(auditForm.value)
    auditDialogVisible.value = false
    fetchData()
  } catch { /* */ } finally { auditing.value = false }
}

onMounted(fetchData)
</script>
