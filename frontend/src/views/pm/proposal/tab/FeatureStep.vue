<template>
  <div class="feature-step">
    <div class="step-header">
      <h3 class="step-title">❹ 附件与功能配置</h3>
      <el-button size="small" @click="loadMarketPresets" :loading="loadingPresets" :disabled="!targetMarket">
        <el-icon style="margin-right:4px"><Refresh /></el-icon>
        从市场预设加载
      </el-button>
    </div>

    <el-alert
      title="从市场预设加载附件/功能配置，勾选需要的选项"
      type="info"
      show-icon
      :closable="false"
      style="margin-bottom:12px"
    />

    <el-row :gutter="24">
      <el-col :span="12">
        <el-card shadow="never" class="config-card">
          <template #header>
            <span>📦 附件配置</span>
          </template>
          <div v-if="accessoryItems.length === 0" class="empty-hint">
            点击上方按钮加载市场预设
          </div>
          <el-checkbox-group v-model="selectedAccessories" v-else>
            <div v-for="item in accessoryItems" :key="item.id" style="margin-bottom:8px">
              <el-checkbox :label="item.id" :value="item.id">
                {{ item.name }}
              </el-checkbox>
            </div>
          </el-checkbox-group>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="config-card">
          <template #header>
            <span>⚙️ 功能配置</span>
          </template>
          <div v-if="featureItems.length === 0" class="empty-hint">
            点击上方按钮加载市场预设
          </div>
          <el-checkbox-group v-model="selectedFeatures" v-else>
            <div v-for="item in featureItems" :key="item.id" style="margin-bottom:8px">
              <el-checkbox :label="item.id" :value="item.id">
                {{ item.name }}
              </el-checkbox>
            </div>
          </el-checkbox-group>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import api from '../../../../api'

interface PresetItem {
  id: number
  name: string
  category: 'accessory' | 'feature'
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

const accessoryItems = reactive<PresetItem[]>([])
const featureItems = reactive<PresetItem[]>([])
const selectedAccessories = reactive<number[]>([])
const selectedFeatures = reactive<number[]>([])
const loadingPresets = ref(false)

async function loadMarketPresets() {
  if (!targetMarket.value) {
    ElMessage.warning('请先在项目概述中选择目标市场')
    return
  }
  loadingPresets.value = true
  try {
    const res = await api.get('/pm/market-presets', {
      params: { target_market: targetMarket.value },
    })
    const items: PresetItem[] = res.data?.items || res.data || []
    accessoryItems.length = 0
    featureItems.length = 0
    items.forEach(item => {
      if (item.category === 'accessory') accessoryItems.push({ ...item })
      else if (item.category === 'feature') featureItems.push({ ...item })
    })
    ElMessage.success(`已加载 ${accessoryItems.length} 附件 + ${featureItems.length} 功能配置`)
    emitUpdate()
  } catch (e: unknown) {
    // API 不可用时退回到静态预设
    ElMessage.info('使用默认附件/功能预设')
    loadDefaultPresets()
  } finally {
    loadingPresets.value = false
  }
}

function loadDefaultPresets() {
  accessoryItems.length = 0
  featureItems.length = 0
  accessoryItems.push(
    { id: 1, name: '遥控器', category: 'accessory' },
    { id: 2, name: '安装支架', category: 'accessory' },
    { id: 3, name: '排水管', category: 'accessory' },
    { id: 4, name: '电源线', category: 'accessory' },
    { id: 5, name: '过滤网（备用）', category: 'accessory' },
    { id: 6, name: '安装说明书', category: 'accessory' },
  )
  featureItems.push(
    { id: 101, name: 'WiFi 智能控制', category: 'feature' },
    { id: 102, name: '自清洁功能', category: 'feature' },
    { id: 103, name: '睡眠模式', category: 'feature' },
    { id: 104, name: '定时开关机', category: 'feature' },
    { id: 105, name: '静音模式', category: 'feature' },
    { id: 106, name: '防冷风功能', category: 'feature' },
    { id: 107, name: '除湿模式', category: 'feature' },
    { id: 108, name: '辅热功能', category: 'feature' },
  )
}

function serializeAccessoryConfig(): string {
  const selected = [
    ...accessoryItems.filter(a => selectedAccessories.includes(a.id)).map(a => a.name),
    ...featureItems.filter(f => selectedFeatures.includes(f.id)).map(f => f.name),
  ]
  return JSON.stringify({
    accessories: accessoryItems.map(a => ({
      ...a,
      selected: selectedAccessories.includes(a.id),
    })),
    features: featureItems.map(f => ({
      ...f,
      selected: selectedFeatures.includes(f.id),
    })),
    selected_names: selected,
  })
}

function emitUpdate() {
  emit('update', {
    accessory_config: serializeAccessoryConfig(),
    feature_config: serializeAccessoryConfig(),
  })
}

watch([selectedAccessories, selectedFeatures], () => emitUpdate(), { deep: true })

function restoreFromData() {
  if (props.data?.accessory_config) {
    try {
      const parsed = JSON.parse(props.data.accessory_config as string)
      if (parsed.accessories && Array.isArray(parsed.accessories)) {
        accessoryItems.length = 0
        selectedAccessories.length = 0
        parsed.accessories.forEach((a: Record<string, unknown>) => {
          accessoryItems.push({ id: a.id as number, name: a.name as string, category: 'accessory' })
          if (a.selected) selectedAccessories.push(a.id as number)
        })
      }
      if (parsed.features && Array.isArray(parsed.features)) {
        featureItems.length = 0
        selectedFeatures.length = 0
        parsed.features.forEach((f: Record<string, unknown>) => {
          featureItems.push({ id: f.id as number, name: f.name as string, category: 'feature' })
          if (f.selected) selectedFeatures.push(f.id as number)
        })
      }
    } catch (e: unknown) {
      // 忽略字符串格式
    }
  }
}

onMounted(async () => {
  restoreFromData()
  if (targetMarket.value && accessoryItems.length === 0 && featureItems.length === 0) {
    await loadMarketPresets()
  }
})
</script>

<style scoped>
.feature-step { min-height: 200px; }
.step-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.step-title { font-size: 16px; font-weight: 600; color: #303133; margin: 0 0 12px 0; }
.config-card { margin-bottom: 12px; }
.empty-hint { text-align: center; padding: 24px 0; color: #909399; font-size: 13px; }
</style>
