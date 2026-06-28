<template>
  <div class="material-step">
    <div class="step-header">
      <h3 class="step-title">❸ 物料与部件清单</h3>
      <el-button size="small" type="primary" plain @click="addMaterialRow">+ 添加物料/部件</el-button>
    </div>
    <el-table :data="materialRows" border size="small" style="width:100%" max-height="420">
      <el-table-column type="index" label="序号" width="50" />
      <el-table-column label="类型" width="100">
        <template #default="{ row }">
          <el-select v-model="row.type" size="small" style="width:100%">
            <el-option label="物料" value="物料" />
            <el-option label="部件" value="部件" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="名称" min-width="180">
        <template #default="{ row }">
          <el-input v-model="row.name" size="small" placeholder="名称" />
        </template>
      </el-table-column>
      <el-table-column label="规格" width="160">
        <template #default="{ row }">
          <el-input v-model="row.spec" size="small" placeholder="规格型号" />
        </template>
      </el-table-column>
      <el-table-column label="数量" width="80">
        <template #default="{ row }">
          <el-input-number v-model="row.qty" :min="1" size="small" controls-position="right" style="width:80px" />
        </template>
      </el-table-column>
      <el-table-column label="候选厂家" min-width="220">
        <template #default="{ row }">
          <el-input
            v-model="row.candidate_suppliers"
            type="textarea"
            :rows="2"
            size="small"
            placeholder="每行一个候选厂家"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="60" fixed="right">
        <template #default="{ $index }">
          <el-button type="danger" size="small" link @click="removeMaterialRow($index)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch, onMounted } from 'vue'

interface MaterialRow {
  id: number
  type: '物料' | '部件'
  name: string
  spec: string
  qty: number
  candidate_suppliers: string
}

const props = defineProps<{
  data: Record<string, unknown>
}>()

const emit = defineEmits<{
  update: [patch: Record<string, unknown>]
}>()

const materialRows = reactive<MaterialRow[]>([])
let materialIdCounter = 0

function addMaterialRow() {
  materialRows.push({
    id: --materialIdCounter,
    type: '部件',
    name: '',
    spec: '',
    qty: 1,
    candidate_suppliers: '',
  })
  emitUpdate()
}

function removeMaterialRow(index: number) {
  materialRows.splice(index, 1)
  emitUpdate()
}

function serializeMaterialData(): string {
  return JSON.stringify(materialRows.map(r => ({
    id: r.id,
    type: r.type,
    name: r.name,
    spec: r.spec,
    qty: r.qty,
    candidate_suppliers: r.candidate_suppliers,
  })))
}

function emitUpdate() {
  emit('update', { material_components: serializeMaterialData() })
}

watch(materialRows, () => emitUpdate(), { deep: true })

function restoreFromData() {
  if (props.data?.material_components) {
    try {
      const parsed = JSON.parse(props.data.material_components as string)
      if (Array.isArray(parsed)) {
        materialRows.length = 0
        parsed.forEach((item: Record<string, unknown>) => {
          materialRows.push({
            id: (item.id as number) || --materialIdCounter,
            type: (item.type as '物料' | '部件') || '部件',
            name: (item.name as string) || '',
            spec: (item.spec as string) || '',
            qty: (item.qty as number) || 1,
            candidate_suppliers: (item.candidate_suppliers as string) || '',
          })
        })
      }
    } catch (e: unknown) {
      // 忽略字符串格式
    }
  }
}

onMounted(() => {
  restoreFromData()
})
</script>

<style scoped>
.material-step { min-height: 200px; }
.step-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.step-title { font-size: 16px; font-weight: 600; color: #303133; margin: 0 0 12px 0; }
</style>
