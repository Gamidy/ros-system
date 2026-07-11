<template>
  <div><h3>产品型号</h3>
    <el-button type="primary" @click="showDialog = true">新建型号</el-button>
    <el-table :data="items" style="margin-top:10px"><el-table-column prop="model_number" label="型号" /><el-table-column prop="name" label="名称" /><el-table-column prop="rated_capacity" label="制冷量(BTU)" /><el-table-column prop="refrigerant" label="冷媒" /><el-table-column prop="status" label="状态" /></el-table>
    <el-dialog v-model="showDialog" title="新建型号"><el-form @submit.prevent="create">
      <el-form-item label="型号编码"><el-input v-model="form.model_number" /></el-form-item>
      <el-form-item label="系列ID"><el-input-number v-model="form.series_id" /></el-form-item>
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
const form = ref({ model_number: '', series_id: 1, name: '' })
onMounted(async () => { const { data } = await api.get('/models'); items.value = data })
async function create() {
  await api.post('/models', form.value)
  showDialog.value = false
  const { data } = await api.get('/models'); items.value = data
}
</script>
