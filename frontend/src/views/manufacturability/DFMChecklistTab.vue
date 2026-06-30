<template>
  <div>
    <div style="margin-bottom:12px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
      <el-input v-model="keyword" placeholder="搜索编码/名称" clearable style="width:200px" @clear="fetchData" @keyup.enter="fetchData" />
      <el-select v-model="filterCategory" placeholder="分类" clearable style="width:130px" @change="fetchData">
        <el-option label="结构DFM" value="structural" />
        <el-option label="工艺DFM" value="process" />
        <el-option label="装配DFM" value="assembly" />
        <el-option label="电气DFM" value="electrical" />
        <el-option label="模具DFM" value="mold" />
      </el-select>
      <el-select v-model="filterSeverity" placeholder="等级" clearable style="width:100px" @change="fetchData">
        <el-option label="Critical" value="critical" />
        <el-option label="Major" value="major" />
        <el-option label="Minor" value="minor" />
      </el-select>
      <el-button type="primary" @click="showCreate">新建检查项</el-button>
      <el-button @click="showWeights = true">权重配置</el-button>
    </div>

    <el-table :data="items" v-loading="loading" style="width:100%" stripe>
      <el-table-column prop="item_code" label="编码" width="100" />
      <el-table-column prop="item_name" label="检查项名称" min-width="220" show-overflow-tooltip />
      <el-table-column label="分类" width="80">
        <template #default="{row}">{{ catLabel(row.dfm_category) }}</template>
      </el-table-column>
      <el-table-column label="等级" width="70">
        <template #default="{row}">
          <el-tag :type="row.severity === 'critical' ? 'danger' : row.severity === 'major' ? 'warning' : 'info'" size="small">{{ row.severity }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="applicable_product_types" label="适用产品" width="150" show-overflow-tooltip />
      <el-table-column prop="weight" label="权重" width="60" align="center" />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{row}">
          <el-button link type="primary" size="small" @click="showEdit(row)">编辑</el-button>
          <el-popconfirm title="确定删除?" @confirm="handleDelete(row)">
            <template #reference><el-button link type="danger" size="small">删除</el-button></template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <div style="margin-top:12px;text-align:right">
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10,20,50]" layout="total,sizes,prev,pager,next" @change="fetchData" />
    </div>

    <!-- 创建/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑检查项' : '新建检查项'" width="600px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="编码" prop="item_code"><el-input v-model="form.item_code" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="分类"><el-select v-model="form.dfm_category" style="width:100%">
            <el-option label="结构DFM" value="structural" /><el-option label="工艺DFM" value="process" />
            <el-option label="装配DFM" value="assembly" /><el-option label="电气DFM" value="electrical" /><el-option label="模具DFM" value="mold" />
          </el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="名称" prop="item_name"><el-input v-model="form.item_name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="8"><el-form-item label="等级"><el-select v-model="form.severity" style="width:100%">
            <el-option label="Critical" value="critical" /><el-option label="Major" value="major" /><el-option label="Minor" value="minor" />
          </el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="权重"><el-input-number v-model="form.weight" style="width:100%" :min="0" :max="10" :step="0.1" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="排序"><el-input-number v-model="form.sort_order" style="width:100%" :min="0" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="适用产品"><el-input v-model="form.applicable_product_types" placeholder="如 split_ac,portable_ac" /></el-form-item>
        <el-form-item label="参考标准"><el-input v-model="form.reference_standard" /></el-form-item>
        <el-form-item label="检查方法"><el-input v-model="form.check_method" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 权重配置弹窗 -->
    <el-dialog v-model="showWeights" title="DFM评分权重配置" width="500px">
      <div style="margin-bottom:8px;display:flex;gap:8px;">
        <el-select v-model="weightProductType" placeholder="选择产品类型" style="width:200px">
          <el-option label="分体空调" value="split_ac" />
        </el-select>
        <el-button type="primary" @click="loadWeights">加载</el-button>
      </div>
      <el-table :data="weights" stripe>
        <el-table-column label="分类" prop="dfm_category" width="120">
          <template #default="{row}">{{ catLabel(row.dfm_category) }}</template>
        </el-table-column>
        <el-table-column label="权重">
          <template #default="{row}">
            <el-input-number v-model="row.weight" :min="0" :max="1" :step="0.05" size="small" style="width:120px" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{row}">
            <el-button link type="primary" size="small" @click="saveWeight(row)">保存</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top:8px;">
        <el-button size="small" @click="addWeight">新增行</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listDFMChecklist, createDFMChecklist, updateDFMChecklist, deleteDFMChecklist, listDFMScoreWeights, createDFMScoreWeight, updateDFMScoreWeight } from '../../api/manufacturability'
import type { FormInstance } from 'element-plus'
import type { TableRow } from '@/types/common'

const items = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const keyword = ref('')
const filterCategory = ref('')
const filterSeverity = ref('')
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref<FormInstance>()
const showWeights = ref(false)
const weightProductType = ref('split_ac')
const weights = ref<any[]>([])

const form = ref<any>({ item_code: '', item_name: '', description: '', dfm_category: 'structural', severity: 'major', applicable_product_types: '', reference_standard: '', check_method: '', weight: 1.0, sort_order: 0, status: 'active' })
const rules = { item_code: [{ required: true, message: '请输入编码' }], item_name: [{ required: true, message: '请输入名称' }] }

function catLabel(c: string) { const m: Record<string, string> = { structural: '结构', process: '工艺', assembly: '装配', electrical: '电气', mold: '模具' }; return m[c] || c }

async function fetchData() {
  loading.value = true
  try {
    const { data } = await listDFMChecklist({ page: page.value, page_size: pageSize.value, dfm_category: filterCategory.value || undefined, severity: filterSeverity.value || undefined, keyword: keyword.value || undefined })
    items.value = data.items || []; total.value = data.total || 0
  } catch {} finally { loading.value = false }
}

function showCreate() { isEdit.value = false; editingId.value = null; form.value = { item_code: '', item_name: '', description: '', dfm_category: 'structural', severity: 'major', applicable_product_types: '', reference_standard: '', check_method: '', weight: 1.0, sort_order: 0, status: 'active' }; dialogVisible.value = true }
function showEdit(row: TableRow) { isEdit.value = true; editingId.value = row.id as number; form.value = { ...row }; dialogVisible.value = true }

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (isEdit.value && editingId.value) await updateDFMChecklist(editingId.value, form.value)
    else await createDFMChecklist(form.value)
    dialogVisible.value = false; fetchData()
  } catch {} finally { saving.value = false }
}
async function handleDelete(row: TableRow) { try { await deleteDFMChecklist(row.id as number); fetchData() } catch {} }

async function loadWeights() {
  try {
    const { data } = await listDFMScoreWeights(weightProductType.value)
    weights.value = data.items || []
  } catch {}
}
async function saveWeight(row: TableRow) {
  try {
    if (row.id) await updateDFMScoreWeight(row.id as number, { weight: row.weight })
    else await createDFMScoreWeight({ product_type: weightProductType.value, dfm_category: row.dfm_category, weight: row.weight })
  } catch {}
}
function addWeight() {
  weights.value.push({ product_type: weightProductType.value, dfm_category: '', weight: 0.2, id: null })
}

onMounted(fetchData)
</script>
