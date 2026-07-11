<template>
  <div><h3>物料管理</h3>
    <el-table :data="items"><el-table-column prop="material_code" label="物料编码" /><el-table-column prop="name" label="名称" /><el-table-column prop="category" label="类别" /><el-table-column prop="unit" label="单位" /><el-table-column prop="status" label="状态" /></el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api'
const items = ref<any[]>([])
onMounted(async () => { const { data } = await api.get('/materials'); items.value = data })
</script>
