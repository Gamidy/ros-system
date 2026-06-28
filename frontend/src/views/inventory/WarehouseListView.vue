<template>
  <div class="inventory-page">
    <!-- 头部操作栏 -->
    <div class="page-toolbar">
      <div class="toolbar-left">
        <el-input v-model="search" placeholder="搜索仓库名称/编码" clearable style="width:260px" @clear="fetchData" @keyup.enter="fetchData" />
        <el-select v-model="statusFilter" placeholder="状态" clearable style="width:120px" @change="fetchData">
          <el-option label="启用" value="active" />
          <el-option label="停用" value="inactive" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button type="primary" @click="openCreate">新建仓库</el-button>
      </div>
    </div>

    <!-- 仓库列表 -->
    <el-table :data="warehouses" border stripe v-loading="loading" style="width:100%">
      <el-table-column prop="code" label="仓库编码" width="140" />
      <el-table-column prop="name" label="仓库名称" min-width="160" />
      <el-table-column prop="location" label="位置" min-width="180" />
      <el-table-column prop="manager" label="管理员" width="120" />
      <el-table-column prop="phone" label="联系电话" width="140" />
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
            {{ row.status === 'active' ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="160" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-popconfirm title="确定删除此仓库？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button link type="danger" size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑仓库' : '新建仓库'" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="仓库编码" prop="code">
          <el-input v-model="form.code" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="仓库名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="位置">
          <el-input v-model="form.location" />
        </el-form-item>
        <el-form-item label="管理员">
          <el-input v-model="form.manager" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status">
            <el-option label="启用" value="active" />
            <el-option label="停用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

interface Warehouse {
  id: number; code: string; name: string; location: string | null
  manager: string | null; phone: string | null; status: string
  remark: string | null
}

const warehouses = ref<Warehouse[]>([])
const loading = ref(false)
const search = ref('')
const statusFilter = ref('')
const dialogVisible = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const editId = ref<number | null>(null)

const form = ref<Partial<Warehouse>>({ code: '', name: '', location: '', manager: '', phone: '', status: 'active', remark: '' })
const rules = { code: [{ required: true, message: '请输入仓库编码' }], name: [{ required: true, message: '请输入仓库名称' }] }

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = {}
    if (search.value) params.search = search.value
    if (statusFilter.value) params.status = statusFilter.value
    const res = await api.get('/inventory/warehouses', { params })
    warehouses.value = res.data
  } finally { loading.value = false }
}

function openCreate() {
  isEdit.value = false; editId.value = null
  form.value = { code: '', name: '', location: '', manager: '', phone: '', status: 'active', remark: '' }
  dialogVisible.value = true
}

function openEdit(row: Warehouse) {
  isEdit.value = true; editId.value = row.id
  form.value = { ...row }
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (isEdit.value && editId.value) {
      await api.put(`/inventory/warehouses/${editId.value}`, form.value)
      ElMessage.success('仓库已更新')
    } else {
      await api.post('/inventory/warehouses', form.value)
      ElMessage.success('仓库已创建')
    }
    dialogVisible.value = false
    await fetchData()
  } finally { saving.value = false }
}

async function handleDelete(id: number) {
  await api.delete(`/inventory/warehouses/${id}`)
  ElMessage.success('仓库已删除')
  await fetchData()
}

onMounted(fetchData)
</script>
