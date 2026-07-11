<template>
  <div><h3>产品平台</h3>
    <el-button type="primary" @click="showDialog = true">新建平台</el-button>
    <el-table :data="items" style="margin-top:10px"><el-table-column prop="code" label="编码" /><el-table-column prop="name" label="名称" /><el-table-column prop="description" label="描述" /></el-table>
    <el-dialog v-model="showDialog" title="新建平台"><el-form @submit.prevent="create">
      <el-form-item label="编码"><el-input v-model="form.code" /></el-form-item>
      <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
      <el-button type="primary" native-type="submit">保存</el-button>
    </el-form></el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api'
const items = ref<any[]>([])
const showDialog = ref(false)
const form = ref({ code: '', name: '' })

onMounted(async () => { const { data } = await api.get('/platforms'); items.value = data })
async function create() {
  await api.post('/platforms', form.value)
  showDialog.value = false; form.value = { code: '', name: '' }
  const { data } = await api.get('/platforms'); items.value = data
}
</script>
