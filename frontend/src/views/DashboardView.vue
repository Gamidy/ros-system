<template>
  <div><h3>驾驶舱</h3>
    <el-row :gutter="16">
      <el-col :span="6" v-for="stat in stats" :key="stat.label">
        <el-card><el-statistic :title="stat.label" :value="stat.value" /></el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api'

const stats = ref([{ label: '产品平台', value: 0 }, { label: '产品型号', value: 0 }, { label: '物料', value: 0 }, { label: '项目', value: 0 }])

onMounted(async () => {
  const [p, m, mt, pr] = await Promise.all([
    api.get('/platforms'), api.get('/models'), api.get('/materials'), api.get('/projects')
  ])
  stats.value[0].value = p.data.length
  stats.value[1].value = m.data.length
  stats.value[2].value = mt.data.length
  stats.value[3].value = pr.data.length
})
</script>
