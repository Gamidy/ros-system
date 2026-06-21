<template>
  <div class="market-mgmt">
    <div class="page-header">
      <h2>🌍 市场信息维护</h2>
      <p class="page-desc">管理销售国家/市场列表及各国能效标准</p>
    </div>

    <!-- 操作栏 -->
    <div class="toolbar">
      <el-button type="primary" @click="openAddDialog" :icon="Plus">新增市场</el-button>
      <el-button @click="fetchMarkets" :icon="Refresh">刷新</el-button>
    </div>

    <!-- 市场表格 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="markets" border size="small" style="width:100%">
        <el-table-column prop="code" label="代码" width="80" />
        <el-table-column prop="name" label="国家/市场" min-width="120" />
        <el-table-column prop="region" label="区域" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ regionLabel(row.region) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="energy_label" label="能效指标" width="100">
          <template #default="{ row }">
            <el-tag :type="energyTagType(row.energy_standard)" size="small">{{ row.energy_label || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="energy_unit" label="单位" width="80" />
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active === 'true' ? 'success' : 'info'" size="small">
              {{ row.is_active === 'true' ? '激活' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="openEditDialog(row)">编辑</el-button>
            <el-button size="small" :type="row.is_active === 'true' ? 'warning' : 'success'" link @click="toggleActive(row)">
              {{ row.is_active === 'true' ? '停用' : '激活' }}
            </el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑/新增弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingCode ? '编辑市场' : '新增市场'" width="520px" :close-on-click-modal="false">
      <el-form :model="form" label-width="120px" size="small">
        <el-form-item label="市场代码" prop="code">
          <el-input v-model="form.code" :disabled="!!editingCode" placeholder="如: VN（两位大写字母）" maxlength="10" />
        </el-form-item>
        <el-form-item label="国家/市场名称" prop="name">
          <el-input v-model="form.name" placeholder="如: 越南" />
        </el-form-item>
        <el-form-item label="区域" prop="region">
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
        <el-form-item label="能效标准代码">
          <el-select v-model="form.energy_standard" placeholder="选择标准" style="width:100%">
            <el-option label="CSPF（越南/印尼/伊朗）" value="cspf" />
            <el-option label="SEER（GCC/美洲/英国等）" value="seer" />
            <el-option label="ISEER（泰国）" value="iseer" />
            <el-option label="APF（马来西亚/巴基斯坦）" value="cspf" />
            <el-option label="EER（多国常规）" value="eer" />
          </el-select>
        </el-form-item>
        <el-form-item label="能效显示名称">
          <el-input v-model="form.energy_label" placeholder="如: CSPF/SEER/EER" />
        </el-form-item>
        <el-form-item label="能效单位">
          <el-select v-model="form.energy_unit" style="width:100%">
            <el-option label="W/W" value="W/W" />
            <el-option label="BTU/Wh" value="BTU/Wh" />
          </el-select>
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
import { ref, onMounted } from 'vue'
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
  is_active: string
}

const markets = ref<MarketItem[]>([])
const dialogVisible = ref(false)
const editingCode = ref<string | null>(null)
const saving = ref(false)
const form = ref({
  code: '',
  name: '',
  region: '',
  energy_standard: 'eer',
  energy_label: 'EER',
  energy_unit: 'W/W',
})

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

async function fetchMarkets() {
  try {
    const res = await api.get('/pm/markets/all')
    markets.value = res.data || []
  } catch {
    ElMessage.error('加载市场列表失败')
  }
}

function openAddDialog() {
  editingCode.value = null
  form.value = { code: '', name: '', region: '', energy_standard: 'eer', energy_label: 'EER', energy_unit: 'W/W' }
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
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.value.code || !form.value.name) {
    ElMessage.warning('请填写市场代码和名称')
    return
  }
  saving.value = true
  try {
    if (editingCode.value) {
      await api.put(`/pm/markets/${editingCode.value}`, form.value)
      ElMessage.success('更新成功')
    } else {
      await api.post('/pm/markets', form.value)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    await fetchMarkets()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
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
</style>
