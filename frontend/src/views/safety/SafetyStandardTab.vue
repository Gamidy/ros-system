<template>
  <div>
    <!-- 工具栏 -->
    <div class="toolbar" style="margin-bottom:12px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
      <el-input v-model="searchKeyword" placeholder="搜索标准编号/名称" clearable style="width:240px" @clear="fetchData" @keyup.enter="fetchData" />
      <el-select v-model="filterType" placeholder="标准类型" clearable style="width:130px" @change="fetchData">
        <el-option label="安规" value="safety" />
        <el-option label="能效" value="energy" />
        <el-option label="EMC" value="emc" />
        <el-option label="环保" value="environmental" />
        <el-option label="性能" value="performance" />
      </el-select>
      <el-select v-model="filterStatus" placeholder="状态" clearable style="width:100px" @change="fetchData">
        <el-option label="启用" value="active" />
        <el-option label="草稿" value="draft" />
        <el-option label="废止" value="obsolete" />
      </el-select>
      <el-button type="primary" @click="showCreate">新建标准</el-button>
    </div>

    <!-- 表格 -->
    <el-table :data="standards" v-loading="loading" style="width:100%" stripe>
      <el-table-column prop="standard_code" label="标准编号" width="140" />
      <el-table-column prop="standard_name_cn" label="标准名称" min-width="260" show-overflow-tooltip />
      <el-table-column prop="issuing_body" label="发布机构" width="120" />
      <el-table-column prop="applicable_market" label="适用市场" width="120" />
      <el-table-column prop="standard_type" label="类型" width="70">
        <template #default="{row}">
          <el-tag :type="row.standard_type === 'safety' ? 'danger' : 'info'" size="small">{{ row.standard_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="version" label="版本" width="60" />
      <el-table-column prop="status" label="状态" width="70">
        <template #default="{row}">
          <el-tag :type="row.status === 'active' ? 'success' : row.status === 'obsolete' ? 'danger' : 'warning'" size="small">{{ row.status === 'active' ? '启用' : row.status === 'obsolete' ? '废止' : '草稿' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="inspection_items_count" label="检测项" width="60" align="center" />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{row}">
          <el-button link type="primary" size="small" @click="showEdit(row)">编辑</el-button>
          <el-button v-if="row.status !== 'obsolete'" link type="warning" size="small" @click="handleArchive(row)">归档</el-button>
          <el-popconfirm title="确定删除?" @confirm="handleDelete(row)">
            <template #reference>
              <el-button link type="danger" size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div style="margin-top:12px;text-align:right">
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10,20,50]" layout="total,sizes,prev,pager,next" @change="fetchData" />
    </div>

    <!-- 创建/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑安全标准' : '新建安全标准'" width="700px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="标准编号" prop="standard_code">
              <el-input v-model="form.standard_code" placeholder="如 IEC 60335-2-40" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="发布机构">
              <el-input v-model="form.issuing_body" placeholder="如 IEC/UL/GB" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="中文名称" prop="standard_name_cn">
          <el-input v-model="form.standard_name_cn" />
        </el-form-item>
        <el-form-item label="英文名称">
          <el-input v-model="form.standard_name_en" type="textarea" :rows="2" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="标准类型">
              <el-select v-model="form.standard_type" style="width:100%">
                <el-option label="安规 Safety" value="safety" />
                <el-option label="能效 Energy" value="energy" />
                <el-option label="EMC" value="emc" />
                <el-option label="环保 Environmental" value="environmental" />
                <el-option label="性能 Performance" value="performance" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="版本号">
              <el-input v-model="form.version" placeholder="V1.0" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width:100%">
                <el-option label="启用" value="active" />
                <el-option label="草稿" value="draft" />
                <el-option label="废止" value="obsolete" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="发布日期">
              <el-date-picker v-model="form.publish_date" type="date" style="width:100%" value-format="YYYY-MM-DD" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="生效日期">
              <el-date-picker v-model="form.effective_date" type="date" style="width:100%" value-format="YYYY-MM-DD" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="废止日期">
              <el-date-picker v-model="form.abolish_date" type="date" style="width:100%" value-format="YYYY-MM-DD" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="适用市场">
          <el-input v-model="form.applicable_market" placeholder="如 全球/中国/欧盟/美国" />
        </el-form-item>
        <el-form-item label="标准摘要">
          <el-input v-model="form.summary" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listSafetyStandards, createSafetyStandard, updateSafetyStandard, deleteSafetyStandard, archiveSafetyStandard } from '../../api/safety'
import type { FormInstance } from 'element-plus'
import type { TableRow } from '@/types/common'

const standards = ref<TableRow[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const searchKeyword = ref('')
const filterType = ref('')
const filterStatus = ref('')
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref<FormInstance>()

const form = ref<Record<string, unknown>>({
  standard_code: '', standard_name_cn: '', standard_name_en: '', issuing_body: '',
  applicable_market: '', standard_type: 'safety', version: 'V1.0',
  publish_date: null, effective_date: null, abolish_date: null,
  summary: '', attachment_url: '', status: 'active',
})

const rules = {
  standard_code: [{ required: true, message: '请输入标准编号', trigger: 'blur' }],
  standard_name_cn: [{ required: true, message: '请输入标准中文名称', trigger: 'blur' }],
}

async function fetchData() {
  loading.value = true
  try {
    const { data } = await listSafetyStandards({
      page: page.value, page_size: pageSize.value,
      keyword: searchKeyword.value || undefined,
      standard_type: filterType.value || undefined,
      status: filterStatus.value || undefined,
    })
    standards.value = data.items || []
    total.value = data.total || 0
  } catch { /* */ } finally { loading.value = false }
}

function resetForm() {
  form.value = {
    standard_code: '', standard_name_cn: '', standard_name_en: '', issuing_body: '',
    applicable_market: '', standard_type: 'safety', version: 'V1.0',
    publish_date: null, effective_date: null, abolish_date: null,
    summary: '', attachment_url: '', status: 'active',
  }
}

function showCreate() {
  isEdit.value = false
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

function showEdit(row: TableRow) {
  isEdit.value = true
  editingId.value = row.id
  form.value = { ...row }
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (isEdit.value && editingId.value) {
      await updateSafetyStandard(editingId.value, form.value)
    } else {
      await createSafetyStandard(form.value)
    }
    dialogVisible.value = false
    fetchData()
  } catch { /* */ } finally { saving.value = false }
}

async function handleDelete(row: TableRow) {
  try {
    await deleteSafetyStandard(row.id)
    fetchData()
  } catch { /* */ }
}

async function handleArchive(row: TableRow) {
  try {
    await archiveSafetyStandard(row.id)
    fetchData()
  } catch { /* */ }
}

onMounted(fetchData)
</script>
