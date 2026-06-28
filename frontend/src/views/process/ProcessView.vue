<template>
  <div class="process-page">
    <el-tabs v-model="tab">
      <el-tab-pane label="📄 SOP管理" name="sop">
        <div class="toolbar">
          <el-select v-model="sopFilter.product_model" placeholder="产品型号" clearable size="small" style="width:140px" @change="fetchSop" />
          <el-select v-model="sopFilter.status" placeholder="状态" clearable size="small" style="width:100px" @change="fetchSop">
            <el-option label="草稿" value="draft" /><el-option label="已发布" value="published" /><el-option label="已废弃" value="obsolete" />
          </el-select>
          <el-input v-model="sopFilter.keyword" placeholder="搜索SOP..." size="small" style="width:180px" clearable @keyup.enter="fetchSop" />
          <el-button size="small" type="primary" @click="showSopDialog=true">新建SOP</el-button>
        </div>
        <el-table :data="sops" stripe border size="small" v-loading="sopLoading">
          <el-table-column prop="code" label="编号" width="100" />
          <el-table-column prop="name" label="名称" min-width="150" />
          <el-table-column prop="product_model" label="产品型号" width="100" />
          <el-table-column prop="process_name" label="工序" width="100" />
          <el-table-column prop="step_no" label="步骤" width="60" />
          <el-table-column prop="standard_time" label="工时(秒)" width="80" />
          <el-table-column prop="version" label="版本" width="70" />
          <el-table-column label="状态" width="80">
            <template #default="{row}"><el-tag :type="sopStatusTag(row.status)" size="small">{{ sopStatusLabel(row.status) }}</el-tag></template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{row}">
              <el-button text size="small" @click="editSop(row)">编辑</el-button>
              <el-popconfirm title="确定删除?" @confirm="deleteSop(row.id)">
                <template #reference><el-button text size="small" type="danger">删除</el-button></template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="🔧 工艺路线" name="routes">
        <div class="toolbar">
          <el-select v-model="routeFilter.product_model" placeholder="产品型号" clearable size="small" style="width:140px" @change="fetchRoutes" />
          <el-button size="small" type="primary" @click="showRouteDialog=true">新建路线</el-button>
        </div>
        <el-table :data="routes" stripe border size="small" v-loading="routeLoading">
          <el-table-column prop="code" label="编号" width="100" />
          <el-table-column prop="name" label="路线名称" min-width="150" />
          <el-table-column prop="product_model" label="产品型号" width="100" />
          <el-table-column prop="version" label="版本" width="70" />
          <el-table-column prop="total_time" label="总工时(秒)" width="100" />
          <el-table-column label="工序数" width="80">
            <template #default="{row}">{{ stepCount(row.steps) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{row}">
              <el-button text size="small" @click="editRoute(row)">编辑</el-button>
              <el-popconfirm title="确定删除?" @confirm="deleteRoute(row.id)">
                <template #reference><el-button text size="small" type="danger">删除</el-button></template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- SOP Dialog -->
    <el-dialog v-model="showSopDialog" :title="editingSop?'编辑SOP':'新建SOP'" width="600px" destroy-on-close>
      <el-form label-position="top" size="small">
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="编号"><el-input v-model="sopForm.code" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="版本"><el-input v-model="sopForm.version" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="产品型号"><el-input v-model="sopForm.product_model" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="SOP名称"><el-input v-model="sopForm.name" /></el-form-item>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="工序名称"><el-input v-model="sopForm.process_name" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="步骤序号"><el-input-number v-model="sopForm.step_no" :min="1" style="width:100%" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="标准工时(秒)"><el-input-number v-model="sopForm.standard_time" :min="0" style="width:100%" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="操作描述"><el-input v-model="sopForm.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="工装工具"><el-input v-model="sopForm.tools" /></el-form-item>
        <el-form-item label="质量标准"><el-input v-model="sopForm.quality_standard" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="编制人"><el-input v-model="sopForm.author" style="width:200px" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSopDialog=false">取消</el-button>
        <el-button type="primary" @click="saveSop">保存</el-button>
      </template>
    </el-dialog>

    <!-- Route Dialog -->
    <el-dialog v-model="showRouteDialog" :title="editingRoute?'编辑路线':'新建工艺路线'" width="600px" destroy-on-close>
      <el-form label-position="top" size="small">
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="编号"><el-input v-model="routeForm.code" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="路线名称"><el-input v-model="routeForm.name" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="产品型号"><el-input v-model="routeForm.product_model" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="编制人"><el-input v-model="routeForm.author" style="width:200px" /></el-form-item>
        <el-divider>工序列表</el-divider>
        <div v-for="(step, i) in routeForm.steps" :key="i" class="step-row">
          <el-input-number v-model="step.seq" :min="1" size="small" style="width:60px" />
          <el-input v-model="step.name" placeholder="工序名称" size="small" style="width:150px" />
          <el-input-number v-model="step.std_time" :min="0" size="small" style="width:100px" placeholder="工时(秒)" />
          <el-input v-model="step.workstation" placeholder="工位" size="small" style="width:100px" />
          <el-button text size="small" type="danger" @click="routeForm.steps.splice(i,1)">✕</el-button>
        </div>
        <el-button size="small" @click="routeForm.steps.push({seq:routeForm.steps.length+1,name:'',std_time:0,workstation:''})">+ 添加工序</el-button>
      </el-form>
      <template #footer>
        <el-button @click="showRouteDialog=false">取消</el-button>
        <el-button type="primary" @click="saveRoute">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const tab = ref('sop')
// SOP
const sopLoading = ref(false); const sops = ref<any[]>([])
const showSopDialog = ref(false); const editingSop = ref(false)
const sopFilter = reactive({ product_model: '', status: '', keyword: '' })
const sopForm = reactive<any>({ code: '', name: '', product_model: '', process_name: '', step_no: 1, standard_time: 0, description: '', tools: '', quality_standard: '', version: 'V1.0', author: '', status: 'draft' })
// Routes
const routeLoading = ref(false); const routes = ref<any[]>([])
const showRouteDialog = ref(false); const editingRoute = ref(false)
const routeFilter = reactive({ product_model: '' })
const routeForm = reactive<any>({ code: '', name: '', product_model: '', author: '', steps: [] })

function sopStatusTag(s: string) { return { draft: 'info', published: 'success', obsolete: 'danger' }[s] || 'info' }
function sopStatusLabel(s: string) { return { draft: '草稿', published: '已发布', obsolete: '已废弃' }[s] || s }
function stepCount(steps: string) { try { return JSON.parse(steps || '[]').length } catch { return 0 } }

async function fetchSop() {
  sopLoading.value = true
  try {
    const params: any = {}
    if (sopFilter.product_model) params.product_model = sopFilter.product_model
    if (sopFilter.status) params.status = sopFilter.status
    if (sopFilter.keyword) params.keyword = sopFilter.keyword
    const r = await api.get('/process/sops', { params })
    sops.value = r.data || []
  } catch { ElMessage.error('加载SOP失败') }
  finally { sopLoading.value = false }
}
async function fetchRoutes() {
  routeLoading.value = true
  try {
    const params: any = {}
    if (routeFilter.product_model) params.product_model = routeFilter.product_model
    const r = await api.get('/process/routes', { params })
    routes.value = r.data || []
  } catch { ElMessage.error('加载工艺路线失败') }
  finally { routeLoading.value = false }
}
function editSop(row: any) { Object.assign(sopForm, row); editingSop.value = true; showSopDialog.value = true }
async function saveSop() {
  try {
    if (editingSop.value) { await api.put(`/process/sops/${sopForm.id}`, sopForm); ElMessage.success('已更新') }
    else { await api.post('/process/sops', sopForm); ElMessage.success('已创建') }
    showSopDialog.value = false; editingSop.value = false; await fetchSop()
  } catch { ElMessage.error('保存失败') }
}
async function deleteSop(id: number) { try { await api.delete(`/process/sops/${id}`); ElMessage.success('已删除'); await fetchSop() } catch { ElMessage.error('删除失败') } }
function editRoute(row: any) { Object.assign(routeForm, row); try { routeForm.steps = JSON.parse(row.steps || '[]') } catch { routeForm.steps = [] }; editingRoute.value = true; showRouteDialog.value = true }
async function saveRoute() {
  try {
    const data = { ...routeForm, steps: JSON.stringify(routeForm.steps) }
    if (editingRoute.value) { await api.put(`/process/routes/${routeForm.id}`, data); ElMessage.success('已更新') }
    else { await api.post('/process/routes', data); ElMessage.success('已创建') }
    showRouteDialog.value = false; editingRoute.value = false; await fetchRoutes()
  } catch { ElMessage.error('保存失败') }
}
async function deleteRoute(id: number) { try { await api.delete(`/process/routes/${id}`); ElMessage.success('已删除'); await fetchRoutes() } catch { ElMessage.error('删除失败') } }

onMounted(() => { fetchSop(); fetchRoutes() })
</script>

<style scoped>
.process-page { padding: 16px 24px; }
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.step-row { display: flex; gap: 8px; margin-bottom: 8px; align-items: center; }
</style>
