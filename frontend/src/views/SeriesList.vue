<template>
  <div class="page-container">
    <h2>产品系列管理</h2>
    <el-table :data="seriesList" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="code" label="编码" />
      <el-table-column prop="platform_id" label="平台ID" />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api'

const seriesList = ref<any[]>([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const res = await api.get('/series')
    seriesList.value = res.data
  } finally {
    loading.value = false
  }
})
</script>
