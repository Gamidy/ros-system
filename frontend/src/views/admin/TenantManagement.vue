<template>
  <div class="tenant-management">
    <div class="page-header">
      <h2>🏢 多租户管理</h2>
      <el-button type="primary" @click="openCreateDialog">+ 新建组织</el-button>
    </div>

    <!-- 组织列表 -->
    <el-card shadow="never">
      <el-table
        :data="tenants"
        border
        size="small"
        v-loading="loading"
        @expand-change="onExpandChange"
        row-key="id"
      >
        <el-table-column type="expand" width="40">
          <template #default="{ row }">
            <div class="expanded-content">
              <h4 style="margin: 0 0 8px;">👥 成员列表 — {{ row.name }}</h4>
              <TenantMemberManager
                :org-id="row.id"
                :org-name="row.name"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="组织名称" min-width="160" />
        <el-table-column prop="code" label="组织代码" width="120" />
        <el-table-column prop="contact_person" label="联系人" width="120" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="user_count" label="用户数" width="80" align="center" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button
              link
              :type="row.is_active ? 'warning' : 'success'"
              size="small"
              @click="toggleStatus(row)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建/编辑弹窗 -->
    <el-dialog
      :title="dialogMode === 'create' ? '新建组织' : '编辑组织'"
      v-model="dialogVisible"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="90px"
        size="small"
      >
        <el-form-item label="组织名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入组织名称" />
        </el-form-item>
        <el-form-item label="组织代码" prop="code">
          <el-input v-model="form.code" placeholder="请输入组织代码（英文缩写）" :disabled="dialogMode === 'edit'" />
        </el-form-item>
        <el-form-item label="联系人" prop="contact_person">
          <el-input v-model="form.contact_person" placeholder="联系人姓名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="联系邮箱" />
        </el-form-item>
        <el-form-item label="电话" prop="phone">
          <el-input v-model="form.phone" placeholder="联系电话" />
        </el-form-item>
        <el-form-item label="地址" prop="address">
          <el-input v-model="form.address" type="textarea" :rows="2" placeholder="组织地址" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button size="small" @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" size="small" @click="submitForm" :loading="submitting">
          {{ dialogMode === 'create' ? '创建' : '保存' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import api from '../../api'
import TenantMemberManager from './TenantMemberManager.vue'

interface Tenant {
  id: number
  name: string
  code: string
  contact_person: string
  email: string
  phone: string
  address: string
  is_active: boolean
  user_count: number
}

const loading = ref(false)
const submitting = ref(false)
const tenants = ref<Tenant[]>([])
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const form = reactive({
  name: '',
  code: '',
  contact_person: '',
  email: '',
  phone: '',
  address: '',
})

const formRules: FormRules = {
  name: [{ required: true, message: '请输入组织名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入组织代码', trigger: 'blur' }],
  contact_person: [{ required: true, message: '请输入联系人', trigger: 'blur' }],
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
}

async function fetchTenants() {
  loading.value = true
  try {
    const res = await api.get('/admin/tenants')
    tenants.value = (res.data?.data || res.data || []) as Tenant[]
  } catch {
    // error handled by interceptor
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  dialogMode.value = 'create'
  editingId.value = null
  form.name = ''
  form.code = ''
  form.contact_person = ''
  form.email = ''
  form.phone = ''
  form.address = ''
  dialogVisible.value = true
}

function openEditDialog(row: Tenant) {
  dialogMode.value = 'edit'
  editingId.value = row.id
  form.name = row.name
  form.code = row.code
  form.contact_person = row.contact_person
  form.email = row.email
  form.phone = row.phone
  form.address = row.address
  dialogVisible.value = true
}

async function submitForm() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      await api.post('/admin/tenants', form)
      ElMessage.success('组织创建成功')
    } else {
      await api.patch(`/admin/tenants/${editingId.value}`, form)
      ElMessage.success('组织更新成功')
    }
    dialogVisible.value = false
    await fetchTenants()
  } catch {
    // error handled by interceptor
  } finally {
    submitting.value = false
  }
}

async function toggleStatus(row: Tenant) {
  const action = row.is_active ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确定${action}组织「${row.name}」？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await api.patch(`/admin/tenants/${row.id}`, { is_active: !row.is_active })
    ElMessage.success(`${action}成功`)
    await fetchTenants()
  } catch {
    // cancelled or error
  }
}

function onExpandChange(row: Tenant, expandedRows: Tenant[]) {
  // Trigger member load when expanded
  const isExpanded = expandedRows.some(r => r.id === row.id)
  if (isExpanded) {
    // find the member manager component and trigger load
    // the TenantMemberManager handles its own loading via watch/onMounted
  }
}

onMounted(() => {
  fetchTenants()
})
</script>

<style scoped>
.tenant-management {
  padding: 16px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
  font-size: 18px;
}
.expanded-content {
  padding: 12px 12px 12px 40px;
}
</style>
