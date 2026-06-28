<template>
  <div class="capacity-cost-mgmt">
    <h2>冷量段单价配置</h2>
    <p class="hint">设置各冷量段（BTU）的原型基准单价，用于冷量联动成本重算时的基线计算。</p>

    <!-- 新增按钮 -->
    <div class="toolbar">
      <el-button type="primary" @click="openDialog()">新增冷量段</el-button>
    </div>

    <!-- 表格 -->
    <el-table :data="costs" border stripe v-loading="loading" style="width: 100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="capacity_key" label="冷量段标识" width="120" />
      <el-table-column prop="btu" label="BTU值" width="120" sortable />
      <el-table-column prop="unit_cost_w" label="单价(万元)" width="140" sortable>
        <template #default="{ row }">
          {{ row.unit_cost_w.toFixed(3) }}
        </template>
      </el-table-column>
      <el-table-column label="折合元" width="140">
        <template #default="{ row }">
          <span class="mono">¥{{ (row.unit_cost_w * 10000).toFixed(0) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" min-width="160" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openDialog(row)">编辑</el-button>
          <el-popconfirm title="确定删除?" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button size="small" type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 表单弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑冷量段' : '新增冷量段'" width="420px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" label-position="left">
        <el-form-item label="冷量段标识" prop="capacity_key">
          <el-input v-model="form.capacity_key" placeholder="如：22K" />
        </el-form-item>
        <el-form-item label="BTU值" prop="btu">
          <el-input-number v-model="form.btu" :min="1000" :step="1000" style="width: 100%" />
        </el-form-item>
        <el-form-item label="单价(万元)" prop="unit_cost_w">
          <el-input-number v-model="form.unit_cost_w" :min="0" :step="0.01" :precision="3" style="width: 100%" />
        </el-form-item>
        <el-form-item label="折合(元)">
          <span class="mono">¥{{ (form.unit_cost_w * 10000).toFixed(0) }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import {
  listCapacityCosts, createCapacityCost,
  updateCapacityCost, deleteCapacityCost,
} from '../../api/costAccounting'

interface CapacityCost {
  id: number
  capacity_key: string
  btu: number
  unit_cost_w: number
  created_at?: string
}

const costs = ref<CapacityCost[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)
const formRef = ref<any>(null)

const form = reactive({
  capacity_key: '',
  btu: 9000,
  unit_cost_w: 0.178,
})

const rules = {
  capacity_key: [{ required: true, message: '请输入冷量段标识', trigger: 'blur' }],
  btu: [{ required: true, message: '请输入BTU值', trigger: 'blur' }],
  unit_cost_w: [{ required: true, message: '请输入单价', trigger: 'blur' }],
}

async function fetchData() {
  loading.value = true
  try {
    const res = await listCapacityCosts()
    costs.value = (res as any).data || []
  } catch (e: any) {
    ElMessage.error('加载失败: ' + (e.message || ''))
  } finally {
    loading.value = false
  }
}

function openDialog(row?: CapacityCost) {
  if (row) {
    isEdit.value = true
    editId.value = row.id
    form.capacity_key = row.capacity_key
    form.btu = row.btu
    form.unit_cost_w = row.unit_cost_w
  } else {
    isEdit.value = false
    editId.value = null
    form.capacity_key = ''
    form.btu = 9000
    form.unit_cost_w = 0.178
  }
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload = { capacity_key: form.capacity_key, btu: form.btu, unit_cost_w: form.unit_cost_w }
    if (isEdit.value && editId.value) {
      await updateCapacityCost(editId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await createCapacityCost(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } catch (e: any) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message || ''))
  } finally {
    saving.value = false
  }
}

async function handleDelete(id: number) {
  try {
    await deleteCapacityCost(id)
    ElMessage.success('删除成功')
    await fetchData()
  } catch (e: any) {
    ElMessage.error('删除失败: ' + (e.response?.data?.detail || e.message || ''))
  }
}

onMounted(fetchData)
</script>

<style scoped>
.capacity-cost-mgmt {
  padding: 20px;
}
.hint {
  color: #909399;
  font-size: 13px;
  margin-bottom: 16px;
}
.toolbar {
  margin-bottom: 16px;
}
.mono {
  font-family: 'Courier New', Courier, monospace;
  font-weight: 600;
  color: #d97757;
}
</style>
