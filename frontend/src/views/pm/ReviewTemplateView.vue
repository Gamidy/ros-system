<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>复盘模板配置</span>
          <el-button type="primary" @click="openDialog()">新建模板</el-button>
        </div>
      </template>

      <!-- 筛选栏 -->
      <el-form :inline="true" size="small" style="margin-bottom: 16px">
        <el-form-item label="产品类型">
          <el-select
            v-model="filterProductType"
            clearable
            placeholder="全部"
            style="width: 160px"
            @change="onFilterChange"
          >
            <el-option
              v-for="pt in productTypeOptions"
              :key="pt.value"
              :label="pt.label"
              :value="pt.value"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <!-- 表格 -->
      <el-table
        :data="templates"
        stripe
        border
        v-loading="loading"
        max-height="600"
      >
        <el-table-column prop="name" label="名称" min-width="180" />
        <el-table-column label="产品类型" width="140">
          <template #default="{ row }">
            {{ productTypeLabel(row.product_type) }}
          </template>
        </el-table-column>
        <el-table-column label="字段数" width="80" align="center">
          <template #default="{ row }">
            {{ (row.template_fields || []).length }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag
              :type="row.is_active ? 'success' : 'danger'"
              size="small"
              effect="plain"
            >
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="danger"
              size="small"
              @click="removeTemplate(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建模板弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      title="新建复盘模板"
      width="720"
      :close-on-click-modal="false"
    >
      <el-form :model="form" label-width="100">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="模板名称" required>
              <el-input
                v-model="form.name"
                placeholder="请输入模板名称"
                maxlength="100"
                show-word-limit
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="产品类型" required>
              <el-select v-model="form.product_type" placeholder="请选择产品类型" style="width: 100%">
                <el-option
                  v-for="pt in productTypeOptions"
                  :key="pt.value"
                  :label="pt.label"
                  :value="pt.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider>模板字段</el-divider>

        <div
          v-for="(field, idx) in form.template_fields"
          :key="idx"
          class="field-row"
        >
          <el-row :gutter="8" align="middle">
            <el-col :span="6">
              <el-input
                v-model="field.field"
                placeholder="字段名"
                size="small"
                maxlength="64"
                show-word-limit
              />
            </el-col>
            <el-col :span="6">
              <el-input
                v-model="field.label"
                placeholder="标签"
                size="small"
                maxlength="64"
                show-word-limit
              />
            </el-col>
            <el-col :span="4" style="text-align: center">
              <el-switch
                v-model="field.required"
                active-text="必选"
                size="small"
              />
            </el-col>
            <el-col :span="5">
              <el-input-number
                v-model="field.max_length"
                :min="0"
                :max="1000"
                :step="10"
                size="small"
                placeholder="最大长度"
                style="width: 100%"
              />
            </el-col>
            <el-col :span="3" style="text-align: right">
              <el-button
                link
                type="danger"
                size="small"
                @click="form.template_fields.splice(idx, 1)"
              >
                删除
              </el-button>
            </el-col>
          </el-row>
        </div>

        <el-button
          type="primary"
          size="small"
          @click="addField"
          style="margin-top: 8px"
        >
          + 添加字段
        </el-button>

        <el-divider />

        <el-form-item label="启用状态">
          <el-switch v-model="form.is_active" active-text="启用" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'
import type { TableRow } from '@/types/common'

interface TemplateField {
  field: string
  label: string
  required: boolean
  max_length: number
}

interface TemplateForm {
  name: string
  product_type: string
  template_fields: TemplateField[]
  is_active: boolean
}

interface ReviewTemplate extends TableRow {
  id: number
  name: string
  product_type: string
  template_fields: TemplateField[]
  is_active: boolean
  created_at: string
}

const productTypeOptions = [
  { value: 'split_wall', label: '分体壁挂' },
]

const productTypeMap = new Map(productTypeOptions.map((p) => [p.value, p.label] as [string, string]))

function productTypeLabel(val: string): string {
  return productTypeMap.get(val) ?? val
}

// 数据
const templates = ref<ReviewTemplate[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const filterProductType = ref('')

// 表单
const form = ref<TemplateForm>({
  name: '',
  product_type: '',
  template_fields: [],
  is_active: true,
})

function addField() {
  form.value.template_fields.push({
    field: '',
    label: '',
    required: false,
    max_length: 255,
  })
}

function openDialog() {
  form.value = {
    name: '',
    product_type: '',
    template_fields: [],
    is_active: true,
  }
  dialogVisible.value = true
}

function onFilterChange() {
  fetchTemplates()
}

async function fetchTemplates() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (filterProductType.value) {
      params.product_type = filterProductType.value
    }
    const res = await api.get('/review-templates', { params })
    templates.value = res.data
  } finally {
    loading.value = false
  }
}

async function save() {
  // 简单校验
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入模板名称')
    return
  }
  if (!form.value.product_type) {
    ElMessage.warning('请选择产品类型')
    return
  }

  saving.value = true
  try {
    await api.post('/review-templates', form.value)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    await fetchTemplates()
  } finally {
    saving.value = false
  }
}

async function removeTemplate(row: ReviewTemplate) {
  try {
    await ElMessageBox.confirm(
      `确定删除模板「${row.name}」？删除后不可恢复。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await api.delete(`/review-templates/${row.id}`)
    ElMessage.success('删除成功')
    await fetchTemplates()
  } catch {
    // 用户取消或操作失败
  }
}

onMounted(() => {
  fetchTemplates()
})
</script>

<style scoped>
.page {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.field-row {
  border: 1px solid #ebeef5;
  padding: 10px 12px;
  margin-bottom: 8px;
  border-radius: 4px;
  background: #fafafa;
}
</style>
