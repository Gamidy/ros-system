<template>
  <div class="market-mgmt">
    <div class="page-header">
      <h2>🌍 市场信息维护</h2>
      <p class="page-desc">管理销售国家/市场列表及各国能效标准、认证要求、温度范围等国家级参数</p>
    </div>

    <!-- 筛选栏 -->
    <div class="filters-bar">
      <div class="filter-item">
        <label>区域</label>
        <el-select v-model="filterRegion" placeholder="全部区域" clearable style="width:140px" @change="applyFilters">
          <el-option v-for="(l,k) in REGION_LABELS" :key="k" :label="l" :value="k" />
        </el-select>
      </div>
      <div class="filter-item">
        <label>状态</label>
        <el-select v-model="filterStatus" placeholder="全部" clearable style="width:110px" @change="applyFilters">
          <el-option label="激活" value="true" />
          <el-option label="停用" value="false" />
        </el-select>
      </div>
      <div class="filter-item">
        <label>搜索</label>
        <el-input v-model="filterSearch" placeholder="名称/代码" clearable style="width:180px" @input="applyFilters" />
      </div>
      <div class="filter-actions">
        <el-button type="primary" @click="openAddDialog" :icon="Plus">新增市场</el-button>
        <el-button @click="fetchMarkets" :icon="Refresh">刷新</el-button>
        <span class="filter-hint">共 {{ filteredMarkets.length }} 个市场</span>
      </div>
    </div>

    <!-- 市场表格 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="filteredMarkets" border size="small" style="width:100%">
        <el-table-column prop="code" label="代码" width="70" />
        <el-table-column prop="name" label="国家/市场" min-width="110" />
        <el-table-column prop="region" label="区域" width="80">
          <template #default="{ row }">
            <el-tag size="small">{{ regionLabel(row.region) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="energy_label" label="能效指标" width="80">
          <template #default="{ row }">
            <el-tag :type="energyTagType(row.energy_standard)" size="small">{{ row.energy_label || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="制热指标" width="80">
          <template #default="{ row }">
            <el-tag :type="heatingTagType(row.heating_energy_standard)" size="small">{{ row.heating_energy_label || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="national_standard" label="国家标准" width="110" />
        <el-table-column prop="voltage_freq" label="电压频率" width="100">
          <template #default="{ row }">{{ row.voltage_freq || '-' }}</template>
        </el-table-column>
        <el-table-column prop="min_voltage" label="最低电压" width="80">
          <template #default="{ row }">{{ row.min_voltage ? row.min_voltage + 'V' : '-' }}</template>
        </el-table-column>
        <el-table-column label="温度范围" width="130">
          <template #default="{ row }">
            <span v-if="row.cooling_max_temp || row.heating_min_temp">
              制冷≤{{ row.cooling_max_temp ?? '-' }}°C / 制热≥{{ row.heating_min_temp ?? '-' }}°C
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="refrigerant" label="制冷剂" width="70">
          <template #default="{ row }">{{ row.refrigerant || '-' }}</template>
        </el-table-column>
        <el-table-column prop="structure_type" label="机型结构" width="110">
          <template #default="{ row }">{{ structureTypeLabel(row.structure_type) }}</template>
        </el-table-column>
        <el-table-column prop="main_selling_model" label="主销机型" width="130" show-overflow-tooltip />
        <el-table-column prop="is_active" label="状态" width="70">
          <template #default="{ row }">
            <el-tag :type="row.is_active === 'true' ? 'success' : 'info'" size="small">
              {{ row.is_active === 'true' ? '激活' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="openEditDialog(row)">编辑</el-button>
            <el-button size="small" type="primary" link @click="openStandardConfig(row)">标准</el-button>
            <el-button size="small" type="success" link @click="openCertDialog(row)">认证</el-button>
            <el-button size="small" type="warning" link @click="openCompressorDialog(row)">关键元器件</el-button>
            <el-button size="small" :type="row.is_active === 'true' ? 'warning' : 'success'" link @click="toggleActive(row)">
              {{ row.is_active === 'true' ? '停用' : '激活' }}
            </el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑/新增弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingCode ? '编辑市场' : '新增市场'" width="700px" :close-on-click-modal="false">
      <el-form :model="form" label-width="130px" size="small">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="国家/市场名称" required>
              <el-input v-model="form.name" placeholder="如: 越南" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="区域" required>
              <el-select v-model="form.region" placeholder="选择区域" style="width:100%">
                <el-option label="东南亚 SEA" value="SEA" />
                <el-option label="中亚 CA" value="CA" />
                <el-option label="南亚 SA" value="SA" />
                <el-option label="中东 ME" value="ME" />
                <el-option label="GCC海湾" value="GCC" />
                <el-option label="美洲 AM" value="AM" />
                <el-option label="欧洲 EU" value="EU" />
                <el-option label="独联体 CIS" value="CIS" />
                <el-option label="非洲 AF" value="AF" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="能效标准代码" required>
              <el-select v-model="form.energy_standard" placeholder="选择标准" style="width:100%">
                <el-option label="CSPF（越南/印尼/伊朗）" value="cspf" />
                <el-option label="SEER（GCC/美洲/英国等）" value="seer" />
                <el-option label="ISEER（泰国）" value="iseer" />
                <el-option label="APF（马来西亚/巴基斯坦）" value="cspf" />
                <el-option label="EER（多国常规）" value="eer" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="能效显示名称" required>
              <el-input v-model="form.energy_label" placeholder="如: CSPF/SEER/EER" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="能效单位" required>
              <el-select v-model="form.energy_unit" style="width:100%">
                <el-option label="W/W" value="W/W" />
                <el-option label="BTU/Wh" value="BTU/Wh" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="能效标准细分" required>
              <el-input v-model="form.energy_standard_detail" placeholder="如: 2025新标准/MEPS 3级" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="国家标准编号" required>
              <el-input v-model="form.national_standard" placeholder="如: GB/T 7725" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="制热标准代码" required>
              <el-select v-model="form.heating_energy_standard" placeholder="选择制热标准" style="width:100%">
                <el-option label="COP" value="COP" />
                <el-option label="SCOP" value="SCOP" />
                <el-option label="HSPF" value="HSPF" />
                <el-option label="APF" value="APF" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="制热显示名称" required>
              <el-input v-model="form.heating_energy_label" placeholder="如: COP/HSPF/SCOP" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="制热单位" required>
              <el-select v-model="form.heating_energy_unit" placeholder="选择制热单位" style="width:100%">
                <el-option label="W/W" value="W/W" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-divider content-position="left">电气与温度参数（全部必填）</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="电压/频率" required>
              <el-input v-model="form.voltage_freq" placeholder="如: 220V/50Hz" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最低电压(V)" required>
              <el-input-number v-model="form.min_voltage" :min="100" :max="500" :step="10" controls-position="right" style="width:100%" placeholder="如: 220" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16" style="margin-top:0">
          <el-col :span="12">
            <el-form-item label="制冷最高温度°C" required>
              <el-input-number v-model="form.cooling_max_temp" :min="-50" :max="80" :step="0.5" controls-position="right" style="width:100%" placeholder="如: 46" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="制热最低温度°C" required>
              <el-input-number v-model="form.heating_min_temp" :min="-50" :max="80" :step="0.5" controls-position="right" style="width:100%" placeholder="如: -7" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-divider content-position="left">产品参数</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="主要制冷剂" required>
              <el-select v-model="form.refrigerant" placeholder="选择制冷剂" style="width:100%">
                <el-option label="R32" value="R32" />
                <el-option label="R410A" value="R410A" />
                <el-option label="R290" value="R290" />
                <el-option label="R454B" value="R454B" />
                <el-option label="R22" value="R22" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="机型结构" required>
              <el-select v-model="form.structure_type" placeholder="选择结构" style="width:100%">
                <el-option label="分体壁挂" value="split_wall" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="主销机型">
          <el-input v-model="form.main_selling_model" type="textarea" :rows="2" placeholder="描述该市场主销机型，如: 12K分体壁挂R32 220V/50Hz" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 认证要求管理弹窗 -->
    <el-dialog v-model="certDialogVisible" :title="`认证要求 - ${certMarketName}`" width="700px" :close-on-click-modal="false">
      <div class="toolbar" style="margin-bottom:12px">
        <el-button type="primary" size="small" @click="openAddCert">新增认证要求</el-button>
      </div>
      <el-table :data="certifications" border size="small" style="width:100%">
        <el-table-column prop="cert_type" label="认证类型" width="120">
          <template #default="{ row }">
            <el-tag :type="certTypeTag(row.cert_type)" size="small">{{ certTypeLabel(row.cert_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="cert_standard" label="标准/要求" min-width="180" />
        <el-table-column prop="description" label="说明" min-width="150" show-overflow-tooltip />
        <el-table-column prop="is_required" label="强制" width="60">
          <template #default="{ row }">
            <el-tag :type="row.is_required === 'true' ? 'danger' : 'info'" size="small">{{ row.is_required === 'true' ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="openEditCert(row)">编辑</el-button>
            <el-button size="small" type="danger" link @click="handleDeleteCert(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="certDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 认证要求编辑子弹窗 -->
    <el-dialog v-model="certEditVisible" :title="editingCertId ? '编辑认证要求' : '新增认证要求'" width="500px" :close-on-click-modal="false">
      <el-form :model="certForm" label-width="100px" size="small">
        <el-form-item label="认证类型" prop="cert_type">
          <el-select v-model="certForm.cert_type" placeholder="选择类型" style="width:100%">
            <el-option label="安规 Safety" value="safety" />
            <el-option label="能效 Energy" value="energy" />
            <el-option label="EMC电磁兼容" value="emc" />
            <el-option label="环保 Environmental" value="environmental" />
          </el-select>
        </el-form-item>
        <el-form-item label="标准/要求" prop="cert_standard">
          <el-input v-model="certForm.cert_standard" placeholder="如: IEC 60335-2-40" />
        </el-form-item>
        <el-form-item label="详细说明">
          <el-input v-model="certForm.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="是否强制">
          <el-switch v-model="certForm.is_required" active-value="true" inactive-value="false" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="certEditVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveCert" :loading="savingCert">保存</el-button>
      </template>
    </el-dialog>

    <!-- 关键元器件限制信息弹窗 -->
    <el-dialog v-model="compDialogVisible" :title="`关键元器件限制信息 - ${compMarketName}`" width="700px" :close-on-click-modal="false">
      <div class="toolbar" style="margin-bottom:12px">
        <el-button type="primary" size="small" @click="openAddComp">新增限制记录</el-button>
      </div>
      <el-table :data="compressors" border size="small" style="width:100%">
        <el-table-column prop="manufacturer" label="元器件类别" width="130" />
        <el-table-column prop="model" label="限制类型" min-width="120" />
        <el-table-column prop="capacity_range" label="受限对象" width="120" />
        <el-table-column prop="notes" label="详细说明" min-width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="openEditComp(row)">编辑</el-button>
            <el-button size="small" type="danger" link @click="handleDeleteComp(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="compDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 关键元器件限制编辑子弹窗 -->
    <el-dialog v-model="compEditVisible" :title="editingCompId ? '编辑限制记录' : '新增限制记录'" width="500px" :close-on-click-modal="false">
      <el-form :model="compForm" label-width="100px" size="small">
        <el-form-item label="元器件类别" prop="manufacturer">
          <el-input v-model="compForm.manufacturer" placeholder="如: 压缩机/风机/换热器/电控板" />
        </el-form-item>
        <el-form-item label="限制类型">
          <el-input v-model="compForm.model" placeholder="如: 不接受品牌/不接受结构/特殊要求" />
        </el-form-item>
        <el-form-item label="受限对象">
          <el-input v-model="compForm.capacity_range" placeholder="如: 格力/涡旋式/铝制换热器" />
        </el-form-item>
        <el-form-item label="详细说明">
          <el-input v-model="compForm.notes" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="compEditVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveComp" :loading="savingComp">保存</el-button>
      </template>
    </el-dialog>

    <StandardConfigDialog
      v-if="stdConfigDialogVisible"
      :market-code="stdConfigMarketCode"
      :market-name="stdConfigMarketName"
      @close="stdConfigDialogVisible = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import api from '../../api'

interface MarketItem {
  code: string
  name: string
  region: string
  energy_standard: string
  energy_label: string
  energy_unit: string
  energy_standard_detail: string | null
  national_standard: string | null
  voltage_freq: string | null
  cooling_max_temp: number | null
  heating_min_temp: number | null
  structure_type: string | null
  main_selling_model: string | null
  refrigerant: string | null
  refrigerant_charge: number | null
  min_voltage: number | null
  is_active: string
  heating_energy_standard: string | null
  heating_energy_label: string | null
  heating_energy_unit: string | null
}

interface CertificationItem {
  id: number
  market_code: string
  cert_type: string
  cert_standard: string
  description: string | null
  is_required: string
  sort_order: number
}

interface CompressorItem {
  id: number
  market_code: string
  manufacturer: string
  model: string | null
  capacity_range: string | null
  notes: string | null
}

interface MarketForm {
  code: string
  name: string
  region: string
  energy_standard: string
  energy_label: string
  energy_unit: string
  energy_standard_detail: string
  national_standard: string
  voltage_freq: string | null
  min_voltage: number | null
  cooling_max_temp: number | null
  heating_min_temp: number | null
  structure_type: string | null
  main_selling_model: string | null
  refrigerant: string | null
  heating_energy_standard: string
  heating_energy_label: string
  heating_energy_unit: string
}

interface CertForm {
  cert_type: string
  cert_standard: string
  description: string
  is_required: string
  sort_order?: number
}

interface CompressorForm {
  manufacturer: string
  model: string
  capacity_range: string
  notes: string
}

const markets = ref<MarketItem[]>([])
const dialogVisible = ref(false)
const editingCode = ref<string | null>(null)
const saving = ref(false)
const form = ref<MarketForm>({
  code: '', name: '', region: '',
  energy_standard: 'eer', energy_label: 'EER', energy_unit: 'W/W',
  energy_standard_detail: '', national_standard: '',
  voltage_freq: null, min_voltage: null, cooling_max_temp: null, heating_min_temp: null,
  structure_type: null, main_selling_model: null,
  refrigerant: null,
  heating_energy_standard: '',
  heating_energy_label: '',
  heating_energy_unit: '',
})

// ── 认证管理 ──
const certDialogVisible = ref(false)
const certMarketCode = ref('')
const certMarketName = ref('')
const certifications = ref<CertificationItem[]>([])
const certEditVisible = ref(false)
const editingCertId = ref<number | null>(null)
const savingCert = ref(false)
const certForm = ref<CertForm>({ cert_type: 'safety', cert_standard: '', description: '', is_required: 'true' })

// ── 关键元器件管理 ──
const compDialogVisible = ref(false)
const compMarketCode = ref('')
const compMarketName = ref('')
const compressors = ref<CompressorItem[]>([])
const compEditVisible = ref(false)
const editingCompId = ref<number | null>(null)
const savingComp = ref(false)
const compForm = ref<CompressorForm>({ manufacturer: '', model: '', capacity_range: '', notes: '' })

// ── 筛选 ──
const filterRegion = ref('')
const filterStatus = ref('')
const filterSearch = ref('')
const filteredMarkets = computed(() => {
  let list = markets.value
  if (filterRegion.value) {
    list = list.filter(m => m.region === filterRegion.value)
  }
  if (filterStatus.value !== '') {
    list = list.filter(m => m.is_active === filterStatus.value)
  }
  if (filterSearch.value) {
    const q = filterSearch.value.toLowerCase()
    list = list.filter(m => m.code.toLowerCase().includes(q) || m.name.toLowerCase().includes(q))
  }
  return list
})
function applyFilters() { /* reactivity handles it via computed */ }

// ── 标准配置弹窗（独立组件 StandardConfigDialog）──
const stdConfigDialogVisible = ref(false)
const stdConfigMarketName = ref('')
const stdConfigMarketCode = ref('')

const REGION_LABELS: Record<string, string> = {
  SEA: '东南亚', CA: '中亚', SA: '南亚',
  ME: '中东', GCC: '海湾', AM: '美洲',
  EU: '欧洲', CIS: '独联体', AF: '非洲',
}

function regionLabel(code: string): string {
  return REGION_LABELS[code] || code
}

function energyTagType(std: string): string {
  const map: Record<string, string> = { cspf: 'success', seer: 'primary', iseer: 'warning', eer: 'info' }
  return map[std] || 'info'
}

const STRUCTURE_LABELS: Record<string, string> = {
  split_wall: '分体壁挂',
  ceiling: '天花机',
  duct: '风管机',
  cabinet: '柜机',
  window: '窗机',
  portable: '移动空调',
}

function structureTypeLabel(val: string | null): string {
  return (val && STRUCTURE_LABELS[val]) || val || '-'
}

function heatingTagType(std: string): string {
  const map: Record<string, string> = { scop: 'success', hspf: 'primary', apf: 'warning', cop: 'info' }
  return map[std] || 'info'
}

function certTypeLabel(type: string): string {
  const map: Record<string, string> = {
    safety: '安规 Safety',
    energy: '能效 Energy',
    emc: 'EMC电磁兼容',
    environmental: '环保 Environmental',
  }
  return map[type] || type
}

function certTypeTag(type: string): string {
  const map: Record<string, string> = { safety: 'danger', energy: 'warning', emc: 'primary', environmental: 'success' }
  return map[type] || 'info'
}

async function fetchMarkets() {
  try {
    const res = await api.get('/pm/markets/all')
    markets.value = res.data || []
  } catch (e: unknown) {
    ElMessage.error('加载市场列表失败')
  }
}

function openAddDialog() {
  editingCode.value = null
  form.value = {
    code: '', name: '', region: '',
    energy_standard: 'eer', energy_label: 'EER', energy_unit: 'W/W',
    energy_standard_detail: '', national_standard: '', min_voltage: null,
    voltage_freq: null, cooling_max_temp: null, heating_min_temp: null,
    structure_type: null, main_selling_model: null,
    refrigerant: null,
    heating_energy_standard: '',
    heating_energy_label: '',
    heating_energy_unit: '',
  }
  dialogVisible.value = true
}

function openEditDialog(item: MarketItem) {
  editingCode.value = item.code
  form.value = {
    code: item.code,
    name: item.name,
    region: item.region,
    energy_standard: item.energy_standard,
    energy_label: item.energy_label,
    energy_unit: item.energy_unit,
    energy_standard_detail: item.energy_standard_detail ?? '',
    national_standard: item.national_standard ?? '',
    voltage_freq: item.voltage_freq ?? null,
    min_voltage: item.min_voltage ?? null,
    cooling_max_temp: item.cooling_max_temp ?? null,
    heating_min_temp: item.heating_min_temp ?? null,
    structure_type: item.structure_type ?? null,
    main_selling_model: item.main_selling_model ?? null,
    refrigerant: item.refrigerant ?? null,
    heating_energy_standard: item.heating_energy_standard ?? '',
    heating_energy_label: item.heating_energy_label ?? '',
    heating_energy_unit: item.heating_energy_unit ?? '',
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.value.name) {
    ElMessage.warning('请填写市场名称')
    return
  }
  if (!form.value.region) {
    ElMessage.warning('请选择区域')
    return
  }
  if (!form.value.energy_standard) {
    ElMessage.warning('请选择能效标准代码')
    return
  }
  if (!form.value.energy_label) {
    ElMessage.warning('请填写能效显示名称')
    return
  }
  if (!form.value.energy_unit) {
    ElMessage.warning('请选择能效单位')
    return
  }
  if (!form.value.energy_standard_detail) {
    ElMessage.warning('请填写能效标准细分')
    return
  }
  if (!form.value.national_standard) {
    ElMessage.warning('请填写国家标准编号')
    return
  }
  if (!form.value.heating_energy_standard) {
    ElMessage.warning('请选择制热标准代码')
    return
  }
  if (!form.value.heating_energy_label) {
    ElMessage.warning('请填写制热显示名称')
    return
  }
  if (!form.value.heating_energy_unit) {
    ElMessage.warning('请选择制热单位')
    return
  }
  if (!form.value.voltage_freq) {
    ElMessage.warning('请填写电压/频率')
    return
  }
  if (form.value.min_voltage === null || form.value.min_voltage === undefined) {
    ElMessage.warning('请填写最低电压要求')
    return
  }
  if (form.value.cooling_max_temp === null || form.value.cooling_max_temp === undefined) {
    ElMessage.warning('请填写制冷最高环境温度')
    return
  }
  if (form.value.heating_min_temp === null || form.value.heating_min_temp === undefined) {
    ElMessage.warning('请填写制热最低环境温度')
    return
  }
  saving.value = true
  try {
    if (editingCode.value) {
      await api.put(`/pm/markets/${editingCode.value}`, form.value)
      ElMessage.success('更新成功')
    } else {
      // 新增时自动用名称作为市场代码
      const payload = { ...form.value }
      if (!payload.code) payload.code = payload.name
      await api.post('/pm/markets', payload)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    await fetchMarkets()
  } catch (e: unknown) {
    const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : null
    ElMessage.error(_err || '操作失败')
  } finally {
    saving.value = false
  }
}

async function toggleActive(item: MarketItem) {
  const newActive = item.is_active === 'true' ? 'false' : 'true'
  const label = newActive === 'true' ? '激活' : '停用'
  try {
    await ElMessageBox.confirm(`确定${label}市场「${item.name}」？`, '确认操作', { type: 'info' })
    await api.put(`/pm/markets/${item.code}`, { is_active: newActive })
    ElMessage.success(`已${label}`)
    await fetchMarkets()
  } catch { /* cancelled */ }
}

async function handleDelete(item: MarketItem) {
  try {
    await ElMessageBox.confirm(`确定删除市场「${item.name}」？`, '确认删除', { type: 'warning' })
    await api.delete(`/pm/markets/${item.code}`)
    ElMessage.success('已删除')
    await fetchMarkets()
  } catch { /* cancelled */ }
}

// ── 认证要求 CRUD ──

async function openCertDialog(item: MarketItem) {
  certMarketCode.value = item.code
  certMarketName.value = item.name
  certDialogVisible.value = true
  await fetchCertifications()
}

async function fetchCertifications() {
  if (!certMarketCode.value) return
  try {
    const res = await api.get(`/pm/markets/${certMarketCode.value}/certifications`)
    certifications.value = res.data || []
  } catch (e: unknown) {
    ElMessage.error('加载认证要求失败')
  }
}

function openAddCert() {
  editingCertId.value = null
  certForm.value = { cert_type: 'safety', cert_standard: '', description: '', is_required: 'true' }
  certEditVisible.value = true
}

function openEditCert(item: CertificationItem) {
  editingCertId.value = item.id
  certForm.value = {
    cert_type: item.cert_type,
    cert_standard: item.cert_standard,
    description: item.description || '',
    is_required: item.is_required,
    sort_order: item.sort_order || 0,
  }
  certEditVisible.value = true
}

async function handleSaveCert() {
  if (!certForm.value.cert_type || !certForm.value.cert_standard) {
    ElMessage.warning('请填写认证类型和标准')
    return
  }
  savingCert.value = true
  try {
    if (editingCertId.value) {
      await api.put(`/pm/markets/${certMarketCode.value}/certifications/${editingCertId.value}`, certForm.value)
      ElMessage.success('更新成功')
    } else {
      await api.post(`/pm/markets/${certMarketCode.value}/certifications`, certForm.value)
      ElMessage.success('新增成功')
    }
    certEditVisible.value = false
    await fetchCertifications()
  } catch (e: unknown) {
    const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : null
    ElMessage.error(_err || '操作失败')
  } finally {
    savingCert.value = false
  }
}

async function handleDeleteCert(item: CertificationItem) {
  try {
    await ElMessageBox.confirm('确定删除该认证要求？', '确认删除', { type: 'warning' })
    await api.delete(`/pm/markets/${certMarketCode.value}/certifications/${item.id}`)
    ElMessage.success('已删除')
    await fetchCertifications()
  } catch { /* cancelled */ }
}

// ── 关键元器件 CRUD ──

async function openCompressorDialog(item: MarketItem) {
  compMarketCode.value = item.code
  compMarketName.value = item.name
  compDialogVisible.value = true
  await fetchCompressors()
}

async function fetchCompressors() {
  if (!compMarketCode.value) return
  try {
    const res = await api.get(`/pm/markets/${compMarketCode.value}/compressors`)
    compressors.value = res.data || []
  } catch (e: unknown) {
    ElMessage.error('加载元器件信息失败')
  }
}

function openAddComp() {
  editingCompId.value = null
  compForm.value = { manufacturer: '', model: '', capacity_range: '', notes: '' }
  compEditVisible.value = true
}

function openEditComp(item: CompressorItem) {
  editingCompId.value = item.id
  compForm.value = {
    manufacturer: item.manufacturer,
    model: item.model || '',
    capacity_range: item.capacity_range || '',
    notes: item.notes || '',
  }
  compEditVisible.value = true
}

async function handleSaveComp() {
  if (!compForm.value.manufacturer) {
    ElMessage.warning('请填写元器件制造商')
    return
  }
  savingComp.value = true
  try {
    if (editingCompId.value) {
      await api.put(`/pm/markets/${compMarketCode.value}/compressors/${editingCompId.value}`, compForm.value)
      ElMessage.success('更新成功')
    } else {
      await api.post(`/pm/markets/${compMarketCode.value}/compressors`, compForm.value)
      ElMessage.success('新增成功')
    }
    compEditVisible.value = false
    await fetchCompressors()
  } catch (e: unknown) {
    const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : null
    ElMessage.error(_err || '操作失败')
  } finally {
    savingComp.value = false
  }
}

async function handleDeleteComp(item: CompressorItem) {
  try {
    await ElMessageBox.confirm('确定删除该元器件信息？', '确认删除', { type: 'warning' })
    await api.delete(`/pm/markets/${compMarketCode.value}/compressors/${item.id}`)
    ElMessage.success('已删除')
    await fetchCompressors()
  } catch { /* cancelled */ }
}

// ── 标准配置弹窗 ──
function openStandardConfig(item: MarketItem) {
  stdConfigMarketName.value = item.name
  stdConfigMarketCode.value = item.code
  stdConfigDialogVisible.value = true
}

onMounted(fetchMarkets)
</script>

<style scoped>
.market-mgmt {
  min-height: calc(100vh - 80px);
  padding: 24px 28px;
  background: #f5f4ed;
  color: #4a3f35;
}
.page-header { margin-bottom: 20px; }
.page-header h2 { margin: 0 0 4px; font-size: 22px; font-weight: 700; }
.page-desc { margin: 0; font-size: 13px; color: #8c8279; }
.toolbar { margin-bottom: 16px; display: flex; gap: 8px; }
.table-card {
  background: #fffdf7;
  border: 1px solid #e5dfd3;
  border-radius: 10px;
}
.filters-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 16px;
  padding: 14px 18px;
  background: #fffdf7;
  border: 1px solid #e5dfd3;
  border-radius: 10px;
}
.filter-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.filter-item label {
  font-size: 12px;
  color: #8c8279;
}
.filter-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}
.filter-hint {
  font-size: 12px;
  color: #b8aea3;
}
</style>
