<template>
  <div>
    <div class="toolbar" style="margin-bottom:10px">
      <el-button type="primary" size="small" @click="openAdd">新增能效等级</el-button>
    </div>
    <el-table :data="energyLevels" border size="small" style="width:100%">
      <el-table-column prop="sort_order" label="排序" width="55" />
      <el-table-column prop="level_name" label="等级名称" width="120" />
      <el-table-column label="主销" width="55">
        <template #default="{ row }">
          <el-tag :type="row.is_primary === 'true' ? 'success' : 'info'" size="small">{{ row.is_primary === 'true' ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="seer_min" label="最低SEER" width="90">
        <template #default="{ row }">{{ row.seer_min ?? '-' }}</template>
      </el-table-column>
      <el-table-column prop="eer_min" label="最低EER" width="90">
        <template #default="{ row }">{{ row.eer_min ?? '-' }}</template>
      </el-table-column>
      <el-table-column prop="cspf_min" label="最低CSPF" width="100">
        <template #default="{ row }">{{ row.cspf_min ?? '-' }}</template>
      </el-table-column>
      <el-table-column prop="cop_min" label="最低COP" width="90">
        <template #default="{ row }">{{ row.cop_min ?? '-' }}</template>
      </el-table-column>
      <el-table-column prop="hspf_min" label="最低HSPF" width="100">
        <template #default="{ row }">{{ row.hspf_min ?? '-' }}</template>
      </el-table-column>
      <el-table-column prop="scop_min" label="最低SCOP" width="100">
        <template #default="{ row }">{{ row.scop_min ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="110">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" link @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 编辑子弹窗 -->
    <el-dialog v-model="editVisible" :title="editingId ? '编辑能效等级' : '新增能效等级'" width="500px" :close-on-click-modal="false">
      <el-form :model="form" label-width="110px" size="small">
        <el-form-item label="等级名称" prop="level_name">
          <el-input v-model="form.level_name" placeholder="如: 一级/Grade A/Class 1" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="最低SEER" prop="seer_min">
              <el-input-number v-model="form.seer_min" :min="0" :max="20" :step="0.1" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="最低EER" prop="eer_min">
              <el-input-number v-model="form.eer_min" :min="0" :max="20" :step="0.1" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="最低CSPF" prop="cspf_min">
              <el-input-number v-model="form.cspf_min" :min="0" :max="20" :step="0.1" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="最低COP" prop="cop_min">
              <el-input-number v-model="form.cop_min" :min="0" :max="20" :step="0.1" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="最低HSPF" prop="hspf_min">
              <el-input-number v-model="form.hspf_min" :min="0" :max="20" :step="0.1" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="最低SCOP" prop="scop_min">
              <el-input-number v-model="form.scop_min" :min="0" :max="20" :step="0.1" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" :max="99" style="width:120px" />
        </el-form-item>
        <el-form-item label="主销等级">
          <el-switch v-model="form.is_primary" :active-value="'true'" :inactive-value="'false'" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'

interface EnergyLevelItem {
  id: number
  market_code: string
  level_name: string
  sort_order: number
  seer_min: number | null
  eer_min: number | null
  cspf_min: number | null
  cop_min: number | null
  hspf_min: number | null
  scop_min: number | null
  is_primary: string
}

const props = defineProps<{ marketCode: string }>()

const energyLevels = ref<EnergyLevelItem[]>([])
const editVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = ref({
  level_name: '',
  sort_order: 0,
  seer_min: null as number | null,
  eer_min: null as number | null,
  cspf_min: null as number | null,
  cop_min: null as number | null,
  hspf_min: null as number | null,
  scop_min: null as number | null,
  is_primary: 'false',
})

watch(() => props.marketCode, (code) => {
  if (code) fetchData(code)
}, { immediate: false })

async function fetchData(code: string) {
  try {
    const res = await api.get(`/pm/markets/${code}/energy-levels`)
    energyLevels.value = res.data || []
  } catch (e: unknown) { /* silent */ }
}

function openAdd() {
  editingId.value = null
  form.value = { level_name: '', sort_order: 0, seer_min: null, eer_min: null, cspf_min: null, cop_min: null, hspf_min: null, scop_min: null, is_primary: 'false' }
  editVisible.value = true
}

function openEdit(item: EnergyLevelItem) {
  editingId.value = item.id
  form.value = {
    level_name: item.level_name,
    sort_order: item.sort_order,
    seer_min: item.seer_min,
    eer_min: item.eer_min,
    cspf_min: item.cspf_min,
    cop_min: item.cop_min,
    hspf_min: item.hspf_min,
    scop_min: item.scop_min,
    is_primary: item.is_primary,
  }
  editVisible.value = true
}

async function handleSave() {
  if (!form.value.level_name) {
    ElMessage.warning('请填写等级名称')
    return
  }
  saving.value = true
  try {
    const code = props.marketCode
    if (editingId.value) {
      await api.put(`/pm/markets/${code}/energy-levels/${editingId.value}`, form.value)
    } else {
      await api.post(`/pm/markets/${code}/energy-levels`, form.value)
    }
    ElMessage.success('保存成功')
    editVisible.value = false
    await fetchData(code)
  } catch (e: unknown) {
    const _err = e && typeof e === 'object' && 'response' in e
      ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : null
    ElMessage.error(_err || '操作失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(item: EnergyLevelItem) {
  try {
    await ElMessageBox.confirm('确定删除该能效等级？', '确认删除', { type: 'warning' })
    await api.delete(`/pm/markets/${props.marketCode}/energy-levels/${item.id}`)
    ElMessage.success('已删除')
    await fetchData(props.marketCode)
  } catch (e: unknown) { /* cancelled */ }
}

defineExpose({ fetchData })
</script>
