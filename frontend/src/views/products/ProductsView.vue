<template>
  <div class="products-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>产品主线 · Platform → Product → Version + Market + Variant</span>
          <el-button type="primary" @click="fetchAll">刷新</el-button>
        </div>
      </template>

      <el-tabs v-model="tab" @tab-change="onTabChange">
        <!-- ═══════════════ 平台管理 ═══════════════ -->
        <el-tab-pane label="平台" name="platforms">
          <div class="toolbar">
            <el-button type="primary" size="small" @click="showPlatformDialog = true">新建平台</el-button>
            <el-select v-model="platformTypeFilter" placeholder="按类型筛选" clearable size="small" style="width:140px;margin-left:8px">
              <el-option label="室内机 IDU" value="IDU" />
              <el-option label="室外机 ODU" value="ODU" />
            </el-select>
          </div>
          <el-table :data="filteredPlatforms" stripe border size="small">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="code" label="编码" width="120" />
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="platform_type" label="类型" width="80">
              <template #default="{ row }"><el-tag size="small" :type="row.platform_type==='IDU'?'success':'warning'">{{ row.platform_type }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="dimensions" label="尺寸约束" />
            <el-table-column prop="status" label="状态" width="90" />
          </el-table>
        </el-tab-pane>

        <!-- ═══════════════ 产品管理 ═══════════════ -->
        <el-tab-pane label="产品" name="products">
          <div class="toolbar">
            <el-button type="primary" size="small" @click="showProductDialog = true">新建产品</el-button>
            <el-select v-model="productPlatformFilter" placeholder="按平台筛选" clearable size="small" style="width:180px;margin-left:8px">
              <el-option v-for="p in platforms" :key="p.id" :label="`${p.code} - ${p.name}`" :value="p.id" />
            </el-select>
          </div>
          <el-table :data="filteredProducts" stripe border size="small">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="code" label="产品编码" width="120" />
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="market_codes" label="目标市场" width="160">
              <template #default="{ row }">
                <el-tag v-for="m in row.market_codes" :key="m" size="small" style="margin:1px">{{ m }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="capacity" label="容量" width="80" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }"><el-tag size="small">{{ row.status }}</el-tag></template>
            </el-table-column>
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <el-button link size="small" type="primary" @click="openVersionManage(row)">版本</el-button>
                <el-button link size="small" type="success" @click="openMarketAssign(row)">市场</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- ═══════════════ 市场字典 ═══════════════ -->
        <el-tab-pane label="市场字典" name="markets">
          <div class="toolbar">
            <el-button type="primary" size="small" @click="showMarketDialog = true">新建市场</el-button>
          </div>
          <el-table :data="markets" stripe border size="small">
            <el-table-column prop="code" label="代码" width="100" />
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="region" label="区域" width="120" />
            <el-table-column prop="is_active" label="启用" width="70">
              <template #default="{ row }"><el-tag :type="row.is_active?'success':'info'" size="small">{{ row.is_active ? '是' : '否' }}</el-tag></template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- ═══════════════ 规则引擎 ═══════════════ -->
        <el-tab-pane label="规则引擎" name="rules">
          <el-card shadow="never" class="rule-card">
            <template #header>评估变更 → 判定是否需创建新Version</template>
            <el-form :model="ruleForm" label-width="120" size="small">
              <el-form-item label="变更描述">
                <el-input v-model="ruleForm.change_description" type="textarea" :rows="2" placeholder="例如：压缩机从转子式改为涡旋式" />
              </el-form-item>
              <el-form-item label="物料等级">
                <el-select v-model="ruleForm.material_level">
                  <el-option label="关键-critical（压缩机/换热器）" value="critical" />
                  <el-option label="重要-major（电机/阀体）" value="major" />
                  <el-option label="一般-minor（外观件/紧固件）" value="minor" />
                </el-select>
              </el-form-item>
              <el-form-item label="变更类别">
                <el-select v-model="ruleForm.change_category">
                  <el-option label="性能变更" value="performance" />
                  <el-option label="结构/外观" value="structural" />
                  <el-option label="认证变更" value="certification" />
                  <el-option label="仅BOM" value="bom_only" />
                  <el-option label="工艺改善" value="process" />
                  <el-option label="设计变更" value="design_change" />
                  <el-option label="零件替换" value="part_change" />
                </el-select>
              </el-form-item>
              <el-form-item label="客户可感知">
                <el-switch v-model="ruleForm.is_customer_perceivable" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="evaluating" @click="evaluateRule">判定</el-button>
              </el-form-item>
            </el-form>
          </el-card>
          <el-card v-if="ruleResult" shadow="never" class="rule-result" :class="ruleResult.should_create ? 'result-create' : 'result-skip'">
            <template #header>判定结果</template>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="是否需创建Version">
                <el-tag :type="ruleResult.should_create ? 'danger' : 'success'">{{ ruleResult.should_create ? '是 → 必须创建' : '否 → 无需创建' }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="产品影响级别">
                <el-tag>{{ ruleResult.product_action || '无影响' }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="变更类型">{{ ruleResult.change_type || '-' }}</el-descriptions-item>
              <el-descriptions-item label="客户可感知">
                <el-tag :type="ruleResult.customer_perceivable ? 'warning' : 'info'">{{ ruleResult.customer_perceivable ? '是' : '否' }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="原因" :span="2">{{ ruleResult.reason }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- Platform Dialog -->
    <el-dialog v-model="showPlatformDialog" title="新建平台" width="520">
      <el-form :model="pfForm" label-width="100" size="small">
        <el-form-item label="平台编码"><el-input v-model="pfForm.code" placeholder="如 IDU900" /></el-form-item>
        <el-form-item label="平台名称"><el-input v-model="pfForm.name" placeholder="室内机900平台" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="pfForm.platform_type"><el-option label="室内机 IDU" value="IDU" /><el-option label="室外机 ODU" value="ODU" /></el-select>
        </el-form-item>
        <el-form-item label="外观尺寸"><el-input v-model="pfForm.dimensions" placeholder="如 900×600×300mm" /></el-form-item>
        <el-form-item label="硬约束"><el-input v-model="pfForm.hard_constraints" type="textarea" :rows="2" placeholder="外观结构件清单" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPlatformDialog = false">取消</el-button>
        <el-button type="primary" @click="savePlatform">保存</el-button>
      </template>
    </el-dialog>

    <!-- Product Dialog -->
    <el-dialog v-model="showProductDialog" title="新建产品" width="520">
      <el-form :model="pdForm" label-width="110" size="small">
        <el-form-item label="产品编码"><el-input v-model="pdForm.code" placeholder="如 EU-09K" /></el-form-item>
        <el-form-item label="产品名称"><el-input v-model="pdForm.name" placeholder="EU系列09K" /></el-form-item>
        <el-form-item label="主平台">
          <el-select v-model="pdForm.platform_id"><el-option v-for="p in platforms" :key="p.id" :label="`${p.code} (${p.platform_type})`" :value="p.id" /></el-select>
        </el-form-item>
        <el-form-item label="室内平台">
          <el-select v-model="pdForm.indoor_platform_id" clearable><el-option v-for="p in iduPlatforms" :key="p.id" :label="p.code" :value="p.id" /></el-select>
        </el-form-item>
        <el-form-item label="室外平台">
          <el-select v-model="pdForm.outdoor_platform_id" clearable><el-option v-for="p in oduPlatforms" :key="p.id" :label="p.code" :value="p.id" /></el-select>
        </el-form-item>
        <el-form-item label="容量"><el-input v-model="pdForm.capacity" placeholder="如 09K/12K" /></el-form-item>
        <el-form-item label="主市场"><el-input v-model="pdForm.market" placeholder="如 EU/VN/CN" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showProductDialog = false">取消</el-button>
        <el-button type="primary" @click="saveProduct">保存</el-button>
      </template>
    </el-dialog>

    <!-- Market Dialog -->
    <el-dialog v-model="showMarketDialog" title="新建市场" width="450">
      <el-form :model="mktForm" label-width="80" size="small">
        <el-form-item label="市场代码"><el-input v-model="mktForm.code" placeholder="如 EU" /></el-form-item>
        <el-form-item label="市场名称"><el-input v-model="mktForm.name" placeholder="如 欧盟" /></el-form-item>
        <el-form-item label="区域"><el-input v-model="mktForm.region" placeholder="如 Europe" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showMarketDialog = false">取消</el-button>
        <el-button type="primary" @click="saveMarket">保存</el-button>
      </template>
    </el-dialog>

    <!-- Market Assign Dialog -->
    <el-dialog v-model="showMarketAssignDialog" title="分配目标市场" width="500">
      <div v-if="currentProduct">
        <div style="margin-bottom:12px">产品: <b>{{ currentProduct.code }}</b></div>
        <el-checkbox-group v-model="selectedMarkets">
          <el-checkbox v-for="m in markets" :key="m.code" :label="m.code" :value="m.code" style="margin:4px 12px 4px 0">{{ m.code }} - {{ m.name }}</el-checkbox>
        </el-checkbox-group>
      </div>
      <template #footer>
        <el-button @click="showMarketAssignDialog = false">取消</el-button>
        <el-button type="primary" @click="saveMarketAssign">保存</el-button>
      </template>
    </el-dialog>

    <!-- Version Dialog -->
    <el-dialog v-model="showVersionDialog" title="新建版本" width="500">
      <el-form :model="verForm" label-width="100" size="small">
        <el-form-item label="产品">{{ currentProduct?.code }} - {{ currentProduct?.name }}</el-form-item>
        <el-form-item label="版本号"><el-input v-model="verForm.version_no" placeholder="如 V1.0" /></el-form-item>
        <el-form-item label="变更原因"><el-input v-model="verForm.reason" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="变更类型">
          <el-select v-model="verForm.change_type" clearable>
            <el-option label="性能" value="performance" /><el-option label="结构" value="structural" />
            <el-option label="认证" value="certification" /><el-option label="功能" value="feature" />
            <el-option label="BOM" value="bom_only" />
          </el-select>
        </el-form-item>
        <el-form-item label="客户可感知"><el-switch v-model="verForm.customer_perceivable" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showVersionDialog = false">取消</el-button>
        <el-button type="primary" @click="saveVersion">保存</el-button>
      </template>
    </el-dialog>

    <!-- Version List Dialog -->
    <el-dialog v-model="showVersionListDialog" :title="`${currentProduct?.code} 版本管理`" width="800">
      <el-table :data="currentVersions" stripe border size="small">
        <el-table-column prop="id" label="ID" width="50" />
        <el-table-column prop="version_no" label="版本号" width="100" />
        <el-table-column prop="status" label="生命周期" width="160">
          <template #default="{ row }">
            <el-select :model-value="row.status" size="small" @change="(v: string) => changeVersionStatus(row.id, v)">
              <el-option v-for="s in versionStatusOptions" :key="s.value" :label="s.label" :value="s.value" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column prop="change_type" label="变更类型" width="90" />
        <el-table-column prop="customer_perceivable" label="客户可感知" width="100">
          <template #default="{ row }"><el-tag :type="row.customer_perceivable?'warning':'info'" size="small">{{ row.customer_perceivable ? '是' : '否' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="reason" label="原因" />
        <el-table-column label="变体" width="160">
          <template #default="{ row }">
            <el-tag v-for="mv in row.manufacturing_variants" :key="mv.id" size="small" style="margin:1px">{{ mv.factory_code }}:{{ mv.mbom_version }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <!-- Variant Manager -->
      <div style="margin-top:16px">
        <el-divider>制造变体（同一Version不同工厂的MBOM）</el-divider>
        <el-form :model="variantForm" inline size="small">
          <el-form-item label="工厂代码"><el-input v-model="variantForm.factory_code" placeholder="如 GREE-ZH" /></el-form-item>
          <el-form-item label="工厂名"><el-input v-model="variantForm.factory_name" placeholder="珠海工厂" /></el-form-item>
          <el-form-item label="MBOM版本"><el-input v-model="variantForm.mbom_version" placeholder="MBOM-V1.0" /></el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveVariant">添加变体</el-button>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="showVersionListDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const tab = ref('platforms')

// Data
const platforms = ref<any[]>([])
const products = ref<any[]>([])
const markets = ref<any[]>([])

// Filters
const platformTypeFilter = ref('')
const productPlatformFilter = ref<number | ''>('')

// Dialog flags
const showPlatformDialog = ref(false)
const showProductDialog = ref(false)
const showMarketDialog = ref(false)
const showVersionDialog = ref(false)
const showVersionListDialog = ref(false)
const showMarketAssignDialog = ref(false)

// Forms
const pfForm = ref({ code: '', name: '', platform_type: 'IDU', dimensions: '', hard_constraints: '' })
const pdForm = ref({ code: '', name: '', platform_id: 0, indoor_platform_id: null as number | null, outdoor_platform_id: null as number | null, capacity: '', market: '' })
const mktForm = ref({ code: '', name: '', region: '' })
const verForm = ref({ version_no: '', reason: '', change_type: '', customer_perceivable: false })
const variantForm = ref({ factory_code: '', factory_name: '', mbom_version: '' })

// State
const currentProduct = ref<any>(null)
const currentVersions = ref<any[]>([])
const selectedMarkets = ref<string[]>([])
const evaluating = ref(false)
const ruleForm = ref({ change_description: '', material_level: 'minor', change_category: 'bom_only', is_customer_perceivable: false })
const ruleResult = ref<any>(null)

// Computed
const iduPlatforms = computed(() => platforms.value.filter((p: any) => p.platform_type === 'IDU'))
const oduPlatforms = computed(() => platforms.value.filter((p: any) => p.platform_type === 'ODU'))
const filteredPlatforms = computed(() => platformTypeFilter.value ? platforms.value.filter((p: any) => p.platform_type === platformTypeFilter.value) : platforms.value)
const filteredProducts = computed(() => productPlatformFilter.value ? products.value.filter((p: any) => p.platform_id === productPlatformFilter.value) : products.value)

const versionStatusOptions = [
  { value: 'draft', label: '草稿' }, { value: 'developing', label: '开发中' },
  { value: 'released', label: '已发布' }, { value: 'production', label: '生产中' },
  { value: 'obsolete', label: '淘汰' }, { value: 'retired', label: '退役' },
]

// Fetch
async function fetchAll() {
  try {
    const [pRes, prodRes, mRes] = await Promise.all([
      api.get('/products/platforms'), api.get('/products'), api.get('/products/markets')
    ])
    platforms.value = pRes.data
    products.value = prodRes.data
    markets.value = mRes.data
  } catch (e: any) {
    ElMessage.error('加载失败: ' + (e?.message || ''))
  }
}

async function onTabChange(name: string) {
  if (name === 'markets') {
    try { const r = await api.get('/products/markets'); markets.value = r.data } catch {}
  }
}

// Platform
async function savePlatform() {
  try {
    await api.post('/products/platforms', pfForm.value)
    ElMessage.success('平台创建成功')
    showPlatformDialog.value = false
    pfForm.value = { code: '', name: '', platform_type: 'IDU', dimensions: '', hard_constraints: '' }
    await fetchAll()
  } catch {}
}

// Product
async function saveProduct() {
  try {
    await api.post('/products', pdForm.value)
    ElMessage.success('产品创建成功')
    showProductDialog.value = false
    pdForm.value = { code: '', name: '', platform_id: 0, indoor_platform_id: null, outdoor_platform_id: null, capacity: '', market: '' }
    await fetchAll()
  } catch {}
}

// Market
async function saveMarket() {
  try {
    await api.post('/products/markets', mktForm.value)
    ElMessage.success('市场创建成功')
    showMarketDialog.value = false
    mktForm.value = { code: '', name: '', region: '' }
    await fetchAll()
  } catch {}
}

// Market Assign
function openMarketAssign(product: any) {
  currentProduct.value = product
  selectedMarkets.value = [...(product.market_codes || [])]  // BUGFIX: use market_codes
  showMarketAssignDialog.value = true
}

async function saveMarketAssign() {
  try {
    await api.post(`/products/${currentProduct.value.id}/markets`, { market_codes: selectedMarkets.value })
    ElMessage.success('市场分配成功')
    showMarketAssignDialog.value = false
    await fetchAll()
  } catch {}
}

// Version
function openVersionManage(product: any) {
  currentProduct.value = product
  showVersionListDialog.value = true
  fetchVersions(product.id)
}

async function fetchVersions(pid: number) {
  try {
    const r = await api.get(`/products/${pid}/versions`)
    currentVersions.value = r.data
  } catch {}
}

async function saveVersion() {
  try {
    await api.post(`/products/${currentProduct.value.id}/versions`, verForm.value)
    ElMessage.success('版本创建成功')
    showVersionDialog.value = false
    verForm.value = { version_no: '', reason: '', change_type: '', customer_perceivable: false }
    await fetchVersions(currentProduct.value.id)
  } catch {}
}

async function changeVersionStatus(vid: number, status: string) {
  try {
    await api.patch(`/products/versions/${vid}/status`, { status })
    ElMessage.success('状态更新成功')
    await fetchVersions(currentProduct.value.id)
  } catch {}
}

// Variant
async function saveVariant() {
  if (!currentVersions.value.length) {
    ElMessage.warning('请先创建版本')
    return
  }
  const vid = currentVersions.value[currentVersions.value.length - 1].id
  try {
    await api.post(`/products/versions/${vid}/variants`, variantForm.value)
    ElMessage.success('制造变体添加成功')
    variantForm.value = { factory_code: '', factory_name: '', mbom_version: '' }
    await fetchVersions(currentProduct.value.id)
  } catch {}
}

// Rule Engine
async function evaluateRule() {
  evaluating.value = true
  try {
    const r = await api.post('/products/rules/evaluate-version', ruleForm.value)
    ruleResult.value = r.data
  } catch {} finally { evaluating.value = false }
}

onMounted(fetchAll)
</script>

<style scoped>
.card-header {
  display: flex; justify-content: space-between; align-items: center; font-weight: bold;
}
.toolbar { margin-bottom: 12px; }
.rule-card { margin-bottom: 16px; }
.rule-result { margin-top: 16px; }
.result-create { border-left: 4px solid #f56c6c; }
.result-skip { border-left: 4px solid #67c23a; }
</style>
