<template>
  <!-- 标准配置弹窗（测试要求 + 标准要求） -->
  <el-dialog v-model="dialogVisible" :title="`标准配置 - ${marketName}`" width="750px" :close-on-click-modal="false" destroy-on-close>
    <el-tabs v-model="activeStdTab">
      <el-tab-pane label="📋 测试要求" name="tests">
        <div class="toolbar" style="margin-bottom:10px">
          <el-button type="primary" size="small" @click="openAddTest">新增测试项</el-button>
        </div>
        <el-table :data="testItems" border size="small" style="width:100%">
          <el-table-column prop="test_category" label="测试分类" width="120">
            <template #default="{ row }">
              <el-tag size="small">{{ row.test_category || '-' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="standard" label="测试标准" min-width="180" />
          <el-table-column prop="is_required" label="是否强制" width="80">
            <template #default="{ row }">
              <el-tag :type="row.is_required ? 'danger' : 'info'" size="small">{{ row.is_required ? '是' : '否' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="110">
            <template #default="{ row }">
              <el-button size="small" type="primary" link @click="openEditTest(row)">编辑</el-button>
              <el-button size="small" type="danger" link @click="handleDeleteTest(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="📄 标准要求" name="standards">
        <div class="toolbar" style="margin-bottom:10px">
          <el-button type="primary" size="small" @click="openAddStandard">新增标准项</el-button>
        </div>
        <el-table :data="standardItems" border size="small" style="width:100%">
          <el-table-column prop="standard_code" label="标准编号" width="120" />
          <el-table-column prop="standard_name" label="标准名称" min-width="220" show-overflow-tooltip />
          <el-table-column prop="is_core" label="核心标准" width="80">
            <template #default="{ row }">
              <el-tag :type="row.is_core ? 'primary' : 'info'" size="small">{{ row.is_core ? '是' : '否' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="110">
            <template #default="{ row }">
              <el-button size="small" type="primary" link @click="openEditStandard(row)">编辑</el-button>
              <el-button size="small" type="danger" link @click="handleDeleteStandard(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="⚡ 能效等级" name="energy-levels">
        <EnergyLevelManager ref="energyLevelRef" :market-code="marketCode" />
      </el-tab-pane>
    </el-tabs>
    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
    </template>
  </el-dialog>

  <!-- 测试项编辑子弹窗 -->
  <el-dialog v-model="testEditVisible" :title="editingTestId ? '编辑测试项' : '新增测试项'" width="500px" :close-on-click-modal="false">
    <el-form :model="testForm" label-width="100px" size="small">
      <el-form-item label="测试分类" prop="test_category">
        <el-select v-model="testForm.test_category" placeholder="选择分类" style="width:100%">
          <el-option label="性能测试 Performance" value="performance" />
          <el-option label="可靠性 Reliability" value="reliability" />
          <el-option label="噪音 Noise" value="noise" />
          <el-option label="电气安全 Electrical" value="electrical" />
          <el-option label="EMC电磁兼容" value="emc" />
          <el-option label="环境 Environmental" value="environmental" />
          <el-option label="其他 Other" value="other" />
        </el-select>
      </el-form-item>
      <el-form-item label="测试标准" prop="standard">
        <el-input v-model="testForm.standard" placeholder="如: EN 14511" />
      </el-form-item>
      <el-form-item label="是否强制">
        <el-switch v-model="testForm.is_required" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="testEditVisible = false">取消</el-button>
      <el-button type="primary" @click="handleSaveTest" :loading="savingTest">保存</el-button>
    </template>
  </el-dialog>

  <!-- 标准项编辑子弹窗 -->
  <el-dialog v-model="stdEditVisible" :title="editingStdId ? '编辑标准项' : '新增标准项'" width="500px" :close-on-click-modal="false">
    <el-form :model="stdForm" label-width="100px" size="small">
      <el-form-item label="标准编号" prop="standard_code">
        <el-input v-model="stdForm.standard_code" placeholder="如: IEC 60335-2-40" />
      </el-form-item>
      <el-form-item label="标准名称" prop="standard_name">
        <el-input v-model="stdForm.standard_name" placeholder="标准全称" />
      </el-form-item>
      <el-form-item label="核心标准">
        <el-switch v-model="stdForm.is_core" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="stdEditVisible = false">取消</el-button>
      <el-button type="primary" @click="handleSaveStandard" :loading="savingStd">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'
import EnergyLevelManager from './EnergyLevelManager.vue'

// ── Props & Emits ──
const props = defineProps<{
  marketCode: string
  marketName: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

// ── Internal state ──
const dialogVisible = ref(true)
const activeStdTab = ref('tests')
const targetMarketId = ref<number | null>(null)

// ── Interfaces ──
interface TestForm {
  test_category: string
  standard: string
  is_required: boolean
}

interface TestItem {
  id: number
  target_market_id: number
  test_category: string
  standard: string
  is_required: boolean
  sort_order: number
}

interface StandardForm {
  standard_code: string
  standard_name: string
  is_core: boolean
}

interface StandardItem {
  id: number
  target_market_id: number
  standard_code: string
  standard_name: string
  is_core: boolean
  sort_order: number
}

// ── 测试项 ──
const testItems = ref<TestItem[]>([])
const testEditVisible = ref(false)
const editingTestId = ref<number | null>(null)
const savingTest = ref(false)
const testForm = ref<TestForm>({ test_category: 'performance', standard: '', is_required: true })

// ── 标准项 ──
const standardItems = ref<StandardItem[]>([])
const stdEditVisible = ref(false)
const editingStdId = ref<number | null>(null)
const savingStd = ref(false)
const stdForm = ref<StandardForm>({ standard_code: '', standard_name: '', is_core: true })

// ── 能效等级 ──
const energyLevelRef = ref()

// ── 关闭 ──
function handleClose() {
  emit('close')
}

// ── 确保 target_market 存在 ──
async function ensureTargetMarket(marketCode: string): Promise<number> {
  const res = await api.get(`/target-markets?market_code=${marketCode}`)
  const list = res.data || []
  if (list.length > 0) return list[0].id
  const marketName = props.marketCode === marketCode ? props.marketName : marketCode
  const createRes = await api.post('/target-markets', {
    market_code: marketCode,
    market_name: marketName,
  })
  return createRes.data.id
}

// ── 初始化 ──
async function init() {
  try {
    targetMarketId.value = await ensureTargetMarket(props.marketCode)
    await Promise.all([fetchTests(), fetchStandards()])
    if (energyLevelRef.value) await energyLevelRef.value.fetchData(props.marketCode)
  } catch (e: unknown) {
    ElMessage.error('加载标准配置失败')
  }
}

// ── 测试项 CRUD ──
async function fetchTests() {
  if (!targetMarketId.value) return
  try {
    const res = await api.get(`/target-markets/${targetMarketId.value}/tests`)
    testItems.value = res.data || []
  } catch (e: unknown) {
    ElMessage.error('加载测试要求失败')
  }
}

function openAddTest() {
  editingTestId.value = null
  testForm.value = { test_category: 'performance', standard: '', is_required: true }
  testEditVisible.value = true
}

function openEditTest(item: TestItem) {
  editingTestId.value = item.id
  testForm.value = {
    test_category: item.test_category,
    standard: item.standard,
    is_required: item.is_required,
  }
  testEditVisible.value = true
}

async function handleSaveTest() {
  if (!testForm.value.test_category || !testForm.value.standard) {
    ElMessage.warning('请填写测试分类和标准')
    return
  }
  savingTest.value = true
  try {
    if (editingTestId.value) {
      await api.put(`/target-markets/${targetMarketId.value}/tests/${editingTestId.value}`, testForm.value)
    } else {
      await api.post(`/target-markets/${targetMarketId.value}/tests`, testForm.value)
    }
    ElMessage.success('保存成功')
    testEditVisible.value = false
    await fetchTests()
  } catch (e: unknown) {
    const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : null
    ElMessage.error(_err || '操作失败')
  } finally {
    savingTest.value = false
  }
}

async function handleDeleteTest(item: TestItem) {
  try {
    await ElMessageBox.confirm('确定删除该测试项？', '确认删除', { type: 'warning' })
    await api.delete(`/target-markets/${targetMarketId.value}/tests/${item.id}`)
    ElMessage.success('已删除')
    await fetchTests()
  } catch { /* cancelled */ }
}

// ── 标准项 CRUD ──
async function fetchStandards() {
  if (!targetMarketId.value) return
  try {
    const res = await api.get(`/target-markets/${targetMarketId.value}/standards`)
    standardItems.value = res.data || []
  } catch (e: unknown) {
    ElMessage.error('加载标准要求失败')
  }
}

function openAddStandard() {
  editingStdId.value = null
  stdForm.value = { standard_code: '', standard_name: '', is_core: true }
  stdEditVisible.value = true
}

function openEditStandard(item: StandardItem) {
  editingStdId.value = item.id
  stdForm.value = {
    standard_code: item.standard_code,
    standard_name: item.standard_name,
    is_core: item.is_core,
  }
  stdEditVisible.value = true
}

async function handleSaveStandard() {
  if (!stdForm.value.standard_code) {
    ElMessage.warning('请填写标准编号')
    return
  }
  savingStd.value = true
  try {
    if (editingStdId.value) {
      await api.put(`/target-markets/${targetMarketId.value}/standards/${editingStdId.value}`, stdForm.value)
    } else {
      await api.post(`/target-markets/${targetMarketId.value}/standards`, stdForm.value)
    }
    ElMessage.success('保存成功')
    stdEditVisible.value = false
    await fetchStandards()
  } catch (e: unknown) {
    const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : null
    ElMessage.error(_err || '操作失败')
  } finally {
    savingStd.value = false
  }
}

async function handleDeleteStandard(item: StandardItem) {
  try {
    await ElMessageBox.confirm('确定删除该标准项？', '确认删除', { type: 'warning' })
    await api.delete(`/target-markets/${targetMarketId.value}/standards/${item.id}`)
    ElMessage.success('已删除')
    await fetchStandards()
  } catch { /* cancelled */ }
}

// ── 启动 ──
init()
</script>

<style scoped>
.toolbar { margin-bottom: 16px; display: flex; gap: 8px; }
</style>
