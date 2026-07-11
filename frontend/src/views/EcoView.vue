<template>
  <div class="eco-page">
    <div class="page-header">
      <h2>工程变更指令 (ECO)</h2>
      <el-button type="primary" @click="showCreate = true">+ 新建 ECO</el-button>
    </div>

    <div class="filters">
      <el-select v-model="filterStatus" placeholder="按状态筛选" clearable style="width: 160px">
        <el-option label="草稿" value="draft" />
        <el-option label="实施中" value="implementing" />
        <el-option label="已验证" value="verified" />
        <el-option label="已生效" value="effective" />
        <el-option label="已关闭" value="closed" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
    </div>

    <el-table :data="ecoList" v-loading="loading" stripe>
      <el-table-column prop="code" label="编号" width="200" />
      <el-table-column prop="title" label="标题" min-width="200" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="effective_date" label="生效日期" width="120" />
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">
          {{ new Date(row.created_at).toLocaleString('zh-CN') }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="viewDetail(row.id)">详情</el-button>
          <el-button v-if="row.status === 'draft'" size="small" type="warning" @click="implementEco(row.id)">实施</el-button>
          <el-button v-if="row.status === 'implementing'" size="small" type="primary" @click="verifyEco(row.id)">验证</el-button>
          <el-button v-if="row.status === 'verified'" size="small" type="success" @click="effectEco(row.id)">生效</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="page"
        :page-size="20"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="fetchList"
      />
    </div>

    <!-- Create Dialog -->
    <el-dialog v-model="showCreate" title="新建 ECO" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="变更指令标题" />
        </el-form-item>
        <el-form-item label="变更摘要" required>
          <el-input v-model="form.change_summary" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="实施方案">
          <el-input v-model="form.implementation_plan" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="明细项">
          <div v-for="(item, idx) in form.items" :key="idx" class="eco-item-row">
            <el-input v-model="item.object_code" placeholder="对象编码" size="small" style="width: 120px" />
            <el-input v-model="item.object_name" placeholder="对象名称" size="small" style="width: 120px" />
            <el-select v-model="item.change_type" size="small" style="width: 100px">
              <el-option label="新增" value="add" />
              <el-option label="修改" value="modify" />
              <el-option label="删除" value="delete" />
              <el-option label="替换" value="replace" />
            </el-select>
            <el-input v-model="item.old_value" placeholder="原值" size="small" style="width: 100px" />
            <el-input v-model="item.new_value" placeholder="新值" size="small" style="width: 100px" />
            <el-button size="small" type="danger" @click="form.items.splice(idx, 1)">删除</el-button>
          </div>
          <el-button size="small" style="margin-top: 8px" @click="addItem">+ 添加明细项</el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="doCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- Detail Dialog -->
    <el-dialog v-model="showDetail" title="ECO 详情" width="700px">
      <el-descriptions v-if="currentEco" :column="2" border>
        <el-descriptions-item label="编号">{{ currentEco.code }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusType(currentEco.status)">{{ statusLabel(currentEco.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="标题" :span="2">{{ currentEco.title }}</el-descriptions-item>
        <el-descriptions-item label="变更摘要" :span="2">{{ currentEco.change_summary }}</el-descriptions-item>
        <el-descriptions-item v-if="currentEco.effective_date" label="生效日期">{{ currentEco.effective_date }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ new Date(currentEco.created_at).toLocaleString('zh-CN') }}</el-descriptions-item>
      </el-descriptions>

      <!-- Items -->
      <el-table v-if="currentEco?.items?.length" :data="currentEco.items" style="margin-top: 12px">
        <el-table-column prop="object_code" label="对象编码" width="120" />
        <el-table-column prop="object_name" label="对象名称" width="140" />
        <el-table-column prop="change_type" label="变更" width="80">
          <template #default="{ row }">
            <el-tag size="small">{{ changeLabel(row.change_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="old_value" label="原值" width="120" />
        <el-table-column prop="new_value" label="新值" width="120" />
      </el-table>

      <template #footer>
        <el-button @click="showDetail = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ecoApi, type ECOSummary, type ECODetail } from '../api/eco'

const ecoList = ref<ECOSummary[]>([])
const loading = ref(false)
const creating = ref(false)
const page = ref(1)
const total = ref(0)
const filterStatus = ref('')
const showCreate = ref(false)
const showDetail = ref(false)
const currentEco = ref<ECODetail | null>(null)
const form = ref({
  title: '',
  change_summary: '',
  implementation_plan: '',
  items: [] as Array<{
    seq: number; change_type: string; object_type: string
    object_code: string; object_name: string
    old_value: string; new_value: string
  }>,
})

onMounted(() => fetchList())
watch(filterStatus, () => { page.value = 1; fetchList() })

function addItem() {
  form.value.items.push({
    seq: form.value.items.length + 1,
    change_type: 'modify',
    object_type: 'bom',
    object_code: '',
    object_name: '',
    old_value: '',
    new_value: '',
  })
}

async function fetchList() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { skip: (page.value - 1) * 20, limit: 20 }
    if (filterStatus.value) params.status = filterStatus.value
    const { data } = await ecoApi.list(params)
    ecoList.value = data as unknown as ECOSummary[]
    total.value = data.length >= 20 ? (page.value * 20 + 1) : page.value * 20
  } finally {
    loading.value = false
  }
}

async function doCreate() {
  creating.value = true
  try {
    await ecoApi.create(form.value)
    ElMessage.success('ECO 创建成功')
    showCreate.value = false
    form.value = { title: '', change_summary: '', implementation_plan: '', items: [] }
    fetchList()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    ElMessage.error(err?.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

async function viewDetail(id: number) {
  try {
    const { data } = await ecoApi.get(id)
    currentEco.value = data as unknown as ECODetail
    showDetail.value = true
  } catch {
    ElMessage.error('加载 ECO 详情失败')
  }
}

async function implementEco(id: number) {
  try { await ecoApi.implement(id); ElMessage.success('开始实施'); fetchList() }
  catch (e: unknown) { ElMessage.error((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '操作失败') }
}

async function verifyEco(id: number) {
  try { await ecoApi.verify(id); ElMessage.success('已验证'); fetchList() }
  catch (e: unknown) { ElMessage.error((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '操作失败') }
}

async function effectEco(id: number) {
  try { await ecoApi.effect(id); ElMessage.success('已生效'); fetchList() }
  catch (e: unknown) { ElMessage.error((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '操作失败') }
}

function statusLabel(s: string) {
  const map: Record<string, string> = {
    draft: '草稿', implementing: '实施中', verified: '已验证',
    effective: '已生效', closed: '已关闭', cancelled: '已取消',
  }
  return map[s] || s
}

function statusType(s: string) {
  const map: Record<string, string> = {
    draft: 'info', implementing: 'warning', verified: 'primary',
    effective: 'success', closed: '', cancelled: 'danger',
  }
  return map[s] || ''
}

function changeLabel(c: string) {
  const map: Record<string, string> = { add: '新增', modify: '修改', delete: '删除', replace: '替换' }
  return map[c] || c
}
</script>

<style scoped>
.eco-page { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.filters { margin-bottom: 16px; }
.pagination { margin-top: 16px; display: flex; justify-content: flex-end; }
.eco-item-row { display: flex; gap: 6px; margin-bottom: 6px; align-items: center; }
</style>
