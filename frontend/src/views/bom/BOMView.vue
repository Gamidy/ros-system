<template>
  <div class="bom-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>BOM物料管理</span>
        </div>
      </template>

      <el-row :gutter="16">
        <el-col :span="12">
          <h3>物料主数据</h3>
          <el-button type="primary" size="small" style="margin-bottom: 12px" @click="showPartDialog = true">新建物料</el-button>
          <el-table :data="parts" stripe border max-height="400">
            <el-table-column prop="part_no" label="物料号" width="140" />
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="unit" label="单位" width="60" />
          </el-table>
        </el-col>
        <el-col :span="12">
          <h3>BOM列表</h3>
          <el-button type="primary" size="small" style="margin-bottom: 12px" @click="showBOMDialog = true">新建BOM</el-button>
          <el-table :data="boms" stripe border max-height="400">
            <el-table-column prop="bom_no" label="BOM编号" width="180" />
            <el-table-column prop="product_code" label="产品编码" />
          </el-table>
        </el-col>
      </el-row>
    </el-card>

    <el-dialog v-model="showPartDialog" title="新建物料" width="500">
      <el-form :model="partForm" label-width="100">
        <el-form-item label="物料号"><el-input v-model="partForm.part_no" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="partForm.name" /></el-form-item>
        <el-form-item label="单位"><el-input v-model="partForm.unit" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPartDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="savePart">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showBOMDialog" title="新建BOM" width="500">
      <el-form :model="bomForm" label-width="100">
        <el-form-item label="BOM编号"><el-input v-model="bomForm.bom_no" /></el-form-item>
        <el-form-item label="产品编码"><el-input v-model="bomForm.product_code" placeholder="如 EU-09K" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBOMDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveBOM">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const parts = ref<any[]>([])
const boms = ref<any[]>([])
const saving = ref(false)

const showPartDialog = ref(false)
const partForm = ref({ part_no: '', name: '', unit: '个' })
const showBOMDialog = ref(false)
const bomForm = ref({ bom_no: '', product_code: '' })

async function fetchAll() {
  try {
    const r1 = api.get('/bom/parts')
    const r2 = api.get('/bom')
    parts.value = (await r1).data
    boms.value = (await r2).data
  } catch {}
}

async function savePart() {
  saving.value = true
  try {
    await api.post('/bom/parts', partForm.value)
    ElMessage.success('创建成功')
    showPartDialog.value = false
    partForm.value = { part_no: '', name: '', unit: '个' }
    await fetchAll()
  } finally { saving.value = false }
}

async function saveBOM() {
  saving.value = true
  try {
    await api.post('/bom', bomForm.value)
    ElMessage.success('创建成功')
    showBOMDialog.value = false
    bomForm.value = { bom_no: '', product_code: '' }
    await fetchAll()
  } finally { saving.value = false }
}

onMounted(fetchAll)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
h3 { margin: 0 0 12px; color: #303133; }
</style>
