<template>
  <div class="tenant-member-manager">
    <div class="member-toolbar">
      <el-button type="primary" size="small" @click="openAddDialog">+ 添加成员</el-button>
    </div>

    <el-table :data="members" border size="small" v-loading="loading" style="width: 100%">
      <el-table-column prop="username" label="用户名" min-width="140" />
      <el-table-column label="角色" width="200">
        <template #default="{ row }">
          <el-select
            v-model="row.role"
            size="small"
            @change="(val: string) => changeRole(row, val)"
            style="width: 100%"
          >
            <el-option
              v-for="r in availableRoles"
              :key="r.value"
              :label="r.label"
              :value="r.value"
            />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column prop="joined_at" label="加入时间" width="180">
        <template #default="{ row }">
          {{ formatTime(row.joined_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="90" fixed="right">
        <template #default="{ row }">
          <el-button link type="danger" size="small" @click="removeMember(row)">移除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加成员弹窗 -->
    <el-dialog
      title="添加成员"
      v-model="addDialogVisible"
      width="420px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="addFormRef"
        :model="addForm"
        :rules="addFormRules"
        label-width="80px"
        size="small"
      >
        <el-form-item label="用户" prop="user_id">
          <el-select
            v-model="addForm.user_id"
            filterable
            remote
            reserve-keyword
            placeholder="搜索用户"
            :remote-method="searchUsers"
            :loading="userSearchLoading"
            style="width: 100%"
          >
            <el-option
              v-for="u in userOptions"
              :key="u.id"
              :label="`${u.username}${u.full_name ? ' (' + u.full_name + ')' : ''}`"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="addForm.role" placeholder="选择角色" style="width: 100%">
            <el-option
              v-for="r in availableRoles"
              :key="r.value"
              :label="r.label"
              :value="r.value"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button size="small" @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" size="small" @click="submitAddMember" :loading="addingMember">
          添加
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import api from '../../api'
import { ROLE_LABELS } from '../../types/roles'

const props = defineProps<{
  orgId: number
  orgName: string
}>()

interface Member {
  user_id: number
  username: string
  full_name: string | null
  role: string
  joined_at: string
}

interface UserOption {
  id: number
  username: string
  full_name: string | null
}

const loading = ref(false)
const members = ref<Member[]>([])
const addDialogVisible = ref(false)
const addingMember = ref(false)
const userSearchLoading = ref(false)
const userOptions = ref<UserOption[]>([])
const addFormRef = ref<FormInstance>()

const addForm = ref({
  user_id: null as number | null,
  role: '',
})

const addFormRules: FormRules = {
  user_id: [{ required: true, message: '请选择用户', trigger: 'change' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

// 组织内可用角色（不包括 admin、general_manager 等全局角色）
const availableRoles = Object.entries(ROLE_LABELS)
  .filter(([key]) => !['admin', 'general_manager', 'security_officer', 'finance_manager', 'procurement_director', 'process_manager'].includes(key))
  .map(([value, label]) => ({ value, label }))

function formatTime(t: string) {
  if (!t) return '-'
  const d = new Date(t)
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function fetchMembers() {
  if (!props.orgId) return
  loading.value = true
  try {
    const res = await api.get(`/admin/tenants/${props.orgId}/members`)
    members.value = (res.data?.data || res.data || []) as Member[]
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

async function searchUsers(query: string) {
  if (!query.trim()) {
    userOptions.value = []
    return
  }
  userSearchLoading.value = true
  try {
    const res = await api.get('/admin/users/search', { params: { q: query } })
    userOptions.value = (res.data?.data || res.data || []) as UserOption[]
  } catch {
    userOptions.value = []
  } finally {
    userSearchLoading.value = false
  }
}

function openAddDialog() {
  addForm.value = { user_id: null, role: '' }
  userOptions.value = []
  addDialogVisible.value = true
}

async function submitAddMember() {
  const valid = await addFormRef.value?.validate().catch(() => false)
  if (!valid) return
  addingMember.value = true
  try {
    await api.post(`/admin/tenants/${props.orgId}/members`, {
      user_id: addForm.value.user_id,
      role: addForm.value.role,
    })
    ElMessage.success('成员添加成功')
    addDialogVisible.value = false
    await fetchMembers()
  } catch {
    // handled by interceptor
  } finally {
    addingMember.value = false
  }
}

async function changeRole(row: Member, newRole: string) {
  try {
    await api.post(`/admin/tenants/${props.orgId}/members`, {
      user_id: row.user_id,
      role: newRole,
    })
    ElMessage.success('角色已更新')
    await fetchMembers()
  } catch {
    // handled by interceptor; re-fetch to reset select
    await fetchMembers()
  }
}

async function removeMember(row: Member) {
  try {
    await ElMessageBox.confirm(
      `确定将用户「${row.username}」从组织「${props.orgName}」中移除？`,
      '确认移除',
      {
        confirmButtonText: '移除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    await api.delete(`/admin/tenants/${props.orgId}/members/${row.user_id}`)
    ElMessage.success('成员已移除')
    await fetchMembers()
  } catch {
    // cancelled or error
  }
}

watch(() => props.orgId, () => {
  if (props.orgId) fetchMembers()
})

onMounted(() => {
  if (props.orgId) fetchMembers()
})
</script>

<style scoped>
.tenant-member-manager {
  width: 100%;
}
.member-toolbar {
  margin-bottom: 8px;
}
</style>
