<template>
  <div><h3>项目管理</h3>
    <el-button type="primary" @click="showDialog = true">新建项目</el-button>
    <el-table :data="items" style="margin-top:10px">
      <el-table-column prop="code" label="项目编码" /><el-table-column prop="name" label="项目名称" />
      <el-table-column prop="current_phase" label="当前阶段"><template #default="s"><el-tag>{{ s.row.current_phase }}</el-tag></template></el-table-column>
      <el-table-column prop="status" label="状态" /><el-table-column label="操作"><template #default="s"><el-button text @click="$router.push(`/projects/${s.row.id}`)">详情</el-button></template></el-table-column>
    </el-table>
    <el-dialog v-model="showDialog" title="新建项目"><el-form @submit.prevent="create">
      <el-form-item label="编码"><el-input v-model="form.code" /></el-form-item>
      <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
      <el-button type="primary" native-type="submit">创建</el-button>
    </el-form></el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api'
const items = ref<any[]>([])
const showDialog = ref(false)
const form = ref({ code: '', name: '' })
onMounted(async () => { const { data } = await api.get('/projects'); items.value = data })
async function create() {
  await api.post('/projects', form.value)
  showDialog.value = false; form.value = { code: '', name: '' }
  const { data } = await api.get('/projects'); items.value = data
}
</script>
