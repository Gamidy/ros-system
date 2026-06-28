<template>
  <div class="safety-step">
    <div class="step-header">
      <h3 class="step-title">❷ 安全合规要求</h3>
      <div style="display:flex;gap:8px;align-items:center">
        <el-button size="small" @click="loadSafetyStandards" :loading="loadingStandards" :disabled="!targetMarket">
          <el-icon style="margin-right:4px"><Refresh /></el-icon>
          从标准库加载
        </el-button>
        <el-button size="small" type="primary" plain @click="addSafetyRow">+ 添加行</el-button>
        <el-tag v-if="!targetMarket" type="warning" size="small" effect="plain">
          请先在项目概述中选择目标市场
        </el-tag>
      </div>
    </div>
    <el-table :data="safetyRows" border size="small" style="width:100%" max-height="420">
      <el-table-column type="index" label="序号" width="50" />
      <el-table-column prop="standard" label="标准" width="160">
        <template #default="{ row }">
          <el-input v-model="row.standard" size="small" placeholder="标准编号/名称" />
        </template>
      </el-table-column>
      <el-table-column prop="key_requirement" label="关键要求" min-width="200">
        <template #default="{ row }">
          <el-input v-model="row.key_requirement" type="textarea" :rows="1" size="small" placeholder="关键要求描述" />
        </template>
      </el-table-column>
      <el-table-column prop="involved_parts" label="涉及部件" width="180">
        <template #default="{ row }">
          <el-input v-model="row.involved_parts" size="small" placeholder="涉及零部件" />
        </template>
      </el-table-column>
      <el-table-column prop="cert_cycle" label="认证周期" width="120">
        <template #default="{ row }">
          <el-input v-model="row.cert_cycle" size="small" placeholder="如: 6周" />
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" width="180">
        <template #default="{ row }">
          <el-input v-model="row.remark" size="small" placeholder="备注" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="60" fixed="right">
        <template #default="{ $index }">
          <el-button type="danger" size="small" link @click="removeSafetyRow($index)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div v-if="safetyRows.length === 0" style="text-align:center;padding:32px;color:#909399">
      点击「从标准库加载」获取目标市场的安全合规标准，或手动添加行
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import api from '../../../../api'

interface SafetyRow {
  id: number
  standard: string
  key_requirement: string
  involved_parts: string
  cert_cycle: string
  remark: string
  _readonly_standard: boolean
}

const props = defineProps<{
  data: Record<string, unknown>
}>()

const emit = defineEmits<{
  update: [patch: Record<string, unknown>]
}>()

const targetMarket = computed(() => {
  return (props.data?.target_market as string) || (props.data?.market as string) || ''
})

const safetyRows = reactive<SafetyRow[]>([])
const loadingStandards = ref(false)
let safetyIdCounter = 0

function addSafetyRow() {
  safetyRows.push({
    id: --safetyIdCounter,
    standard: '',
    key_requirement: '',
    involved_parts: '',
    cert_cycle: '',
    remark: '',
    _readonly_standard: false,
  })
  emitUpdate()
}

function removeSafetyRow(index: number) {
  safetyRows.splice(index, 1)
  emitUpdate()
}

async function loadSafetyStandards() {
  if (!targetMarket.value) {
    ElMessage.warning('请先在项目概述中选择目标市场')
    return
  }
  loadingStandards.value = true
  try {
    const res = await api.get('/pm/safety-compliance-standards', {
      params: { target_market: targetMarket.value },
    })
    const items: Record<string, unknown>[] = res.data?.items || res.data || []
    safetyRows.length = 0
    items.forEach((item: Record<string, unknown>) => {
      safetyRows.push({
        id: (item.id as number) || ++safetyIdCounter,
        standard: (item.standard as string) || (item.standard_name as string) || '',
        key_requirement: (item.key_requirement as string) || (item.requirement as string) || '',
        involved_parts: (item.involved_parts as string) || '',
        cert_cycle: (item.cert_cycle as string) || '',
        remark: (item.remark as string) || '',
        _readonly_standard: true,
      })
    })
    ElMessage.success(`已加载 ${safetyRows.length} 条安全合规标准`)
    emitUpdate()
  } catch (e: unknown) {
    // API 不可用时退回到静态预设
    ElMessage.info('使用默认安全合规预设')
    safetyRows.length = 0
    const presets = getSafetyPresets(targetMarket.value)
    presets.forEach((p: Record<string, unknown>) => {
      safetyRows.push({
        id: ++safetyIdCounter,
        standard: p.standard as string,
        key_requirement: p.key_requirement as string,
        involved_parts: '',
        cert_cycle: '',
        remark: '',
        _readonly_standard: true,
      })
    })
    emitUpdate()
  } finally {
    loadingStandards.value = false
  }
}

/** 静态安全合规预设（API 不可用时回退） */
function getSafetyPresets(market: string) {
  const m = market.toLowerCase()
  if (m.includes('eu') || m.includes('europe') || m.includes('ce')) {
    return [
      { standard: 'EN 60335-1', key_requirement: '家用及类似用途电器安全 — 通用要求' },
      { standard: 'EN 60335-2-40', key_requirement: '热泵、空调器和除湿机特殊要求' },
      { standard: 'EN 55014-1', key_requirement: '电磁兼容发射限值' },
      { standard: 'EN 55014-2', key_requirement: '电磁兼容抗扰度' },
      { standard: 'EU 2016/2281', key_requirement: '空调器能效标志指令 (Lot 21)' },
      { standard: 'REACH', key_requirement: '化学品注册、评估、授权和限制' },
      { standard: 'RoHS', key_requirement: '有害物质限制' },
      { standard: 'WEEE', key_requirement: '废弃电子电气设备指令' },
    ]
  }
  if (m.includes('us') || m.includes('america') || m.includes('north')) {
    return [
      { standard: 'UL 1995', key_requirement: '加热与冷却设备安全标准' },
      { standard: 'UL 60335-1', key_requirement: '家用电器安全通用要求' },
      { standard: 'FCC Part 15', key_requirement: '电磁辐射与传导发射限值' },
      { standard: 'DOE 10 CFR 430', key_requirement: '美国能源部能效标准' },
      { standard: 'ASHRAE 90.1', key_requirement: '建筑节能标准（商用空调）' },
      { standard: 'EPA SNAP', key_requirement: '制冷剂替代政策' },
    ]
  }
  if (m.includes('saudi') || m.includes('gulf') || m.includes('gcc') || m.includes('middle')) {
    return [
      { standard: 'SASO 2663', key_requirement: '空调器能效标签与最低要求' },
      { standard: 'GSO IEC 60335-2-40', key_requirement: '空调安全特殊要求（海湾标准）' },
      { standard: 'SASO EER', key_requirement: '能效等级 EER 限值' },
    ]
  }
  // 中国默认
  return [
    { standard: 'GB 4706.1', key_requirement: '家用和类似用途电器安全 通用要求' },
    { standard: 'GB 4706.32', key_requirement: '热泵、空调器和除湿机特殊要求' },
    { standard: 'GB 4343.1', key_requirement: '电磁兼容 家用电器发射限值' },
    { standard: 'GB 4343.2', key_requirement: '电磁兼容 抗扰度' },
    { standard: 'GB 21455', key_requirement: '房间空调器能效限定值及能效等级' },
    { standard: 'GB/T 7725', key_requirement: '房间空气调节器' },
  ]
}

function serializeSafetyData(): string {
  return JSON.stringify(safetyRows.map(r => ({
    id: r.id,
    standard: r.standard,
    key_requirement: r.key_requirement,
    involved_parts: r.involved_parts,
    cert_cycle: r.cert_cycle,
    remark: r.remark,
  })))
}

function emitUpdate() {
  emit('update', { safety_compliance: serializeSafetyData() })
}

watch(safetyRows, () => emitUpdate(), { deep: true })

function restoreFromData() {
  if (props.data?.safety_compliance) {
    try {
      const parsed = JSON.parse(props.data.safety_compliance as string)
      if (Array.isArray(parsed)) {
        safetyRows.length = 0
        parsed.forEach((item: Record<string, unknown>) => {
          safetyRows.push({
            id: (item.id as number) || ++safetyIdCounter,
            standard: (item.standard as string) || '',
            key_requirement: (item.key_requirement as string) || '',
            involved_parts: (item.involved_parts as string) || '',
            cert_cycle: (item.cert_cycle as string) || '',
            remark: (item.remark as string) || '',
            _readonly_standard: !!item._readonly_standard,
          })
        })
      }
    } catch (e: unknown) {
      // 忽略字符串格式
    }
  }
}

onMounted(async () => {
  restoreFromData()
  if (targetMarket.value && safetyRows.length === 0) {
    await loadSafetyStandards()
  }
})
</script>

<style scoped>
.safety-step { min-height: 200px; }
.step-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.step-title { font-size: 16px; font-weight: 600; color: #303133; margin: 0 0 12px 0; }
</style>
