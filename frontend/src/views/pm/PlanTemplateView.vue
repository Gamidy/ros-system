<template>
  <div class="plan-template-page">
    <div class="page-header">
      <h2>📋 计划模板管理</h2>
      <div class="header-actions">
        <el-select v-model="filterProductType" placeholder="产品类型" clearable size="small" style="width:130px" @change="fetchData">
          <el-option label="分体壁挂" value="分体壁挂" />
        </el-select>
        <el-select v-model="filterMarket" placeholder="市场" clearable size="small" style="width:120px" @change="fetchData">
          <el-option label="美国" value="美国" />
          <el-option label="欧盟" value="欧盟" />
          <el-option label="东南亚" value="东南亚" />
          <el-option label="中东" value="中东" />
          <el-option label="拉美" value="拉美" />
          <el-option label="非洲" value="非洲" />
          <el-option label="澳洲" value="澳洲" />
        </el-select>
        <el-button size="small" type="primary" @click="openCreate">新建模板</el-button>
      </div>
    </div>

    <el-table :data="list" stripe border size="small" v-loading="loading" style="width:100%">
      <el-table-column prop="name" label="名称" min-width="150" />
      <el-table-column prop="product_type" label="产品类型" width="120" />
      <el-table-column prop="market" label="市场" width="100" />
      <el-table-column prop="description" label="描述" min-width="180" show-overflow-tooltip />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160" />
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{ row }">
          <el-popconfirm title="确认删除此模板？" @confirm="removeTemplate(row.id)">
            <template #reference>
              <el-button text size="small" type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create / Edit Dialog -->
    <el-dialog v-model="showDialog" title="新建模板" width="600px" destroy-on-close>
      <el-form label-position="top" size="small">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="名称">
              <el-input v-model="form.name" placeholder="模板名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="产品类型">
              <el-select v-model="form.product_type" placeholder="选择产品类型" style="width:100%">
                <el-option label="分体壁挂" value="分体壁挂" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="市场">
              <el-select v-model="form.market" placeholder="选择市场" style="width:100%">
                <el-option label="美国" value="美国" />
                <el-option label="欧盟" value="欧盟" />
                <el-option label="东南亚" value="东南亚" />
                <el-option label="中东" value="中东" />
                <el-option label="拉美" value="拉美" />
                <el-option label="非洲" value="非洲" />
                <el-option label="澳洲" value="澳洲" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="启用">
              <el-switch v-model="form.is_active" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="模板描述" />
        </el-form-item>
        <el-form-item label="预置字段 (JSON)">
          <el-input v-model="form.preset_fields" type="textarea" :rows="4" placeholder='[{"field":"model","label":"型号"},{"field":"spec","label":"规格"}]' />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="saveTemplate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

interface PlanTemplate {
  id: number
  product_type: string
  market: string
  name: string
  description: string
  preset_fields: string
  is_active: boolean
  created_at: string
}

const loading = ref(false)
const list = ref<PlanTemplate[]>([])
const showDialog = ref(false)
const filterProductType = ref('')
const filterMarket = ref('')

const form = reactive({
  name: '',
  product_type: '',
  market: '',
  description: '',
  preset_fields: '',
  is_active: true,
})

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (filterProductType.value) params.product_type = filterProductType.value
    if (filterMarket.value) params.market = filterMarket.value
    const r = await api.get('/plan-templates', { params })
    list.value = r.data || []
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.name = ''
  form.product_type = ''
  form.market = ''
  form.description = ''
  form.preset_fields = ''
  form.is_active = true
  showDialog.value = true
}

async function saveTemplate() {
  if (!form.name || !form.product_type || !form.market) {
    ElMessage.warning('请填写名称、产品类型和市场')
    return
  }
  try {
    await api.post('/plan-templates', {
      name: form.name,
      product_type: form.product_type,
      market: form.market,
      description: form.description,
      preset_fields: form.preset_fields,
      is_active: form.is_active,
    })
    ElMessage.success('创建成功')
    showDialog.value = false
    await fetchData()
  } catch {
    ElMessage.error('保存失败')
  }
}

async function removeTemplate(id: number) {
  try {
    await api.delete(`/plan-templates/${id}`)
    ElMessage.success('删除成功')
    await fetchData()
  } catch {
    ElMessage.error('删除失败')
  }
}

onMounted(fetchData)
</script>

<style scoped>
.plan-template-page { padding: 16px 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
.header-actions { display: flex; gap: 8px; }
</style>
