<template>
  <el-dialog v-model="visible" title="成本分解结构" width="750px" :close-on-click-modal="false" top="5vh">
    <div class="cost-bd">
      <div v-for="(cat, ci) in categories" :key="ci" class="cost-category">
        <div class="cat-header" @click="cat.expanded = !cat.expanded">
          <span class="cat-toggle">{{ cat.expanded ? '▼' : '▶' }}</span>
          <span class="cat-name">{{ cat.name }}</span>
          <span class="cat-total">目标: {{ formatMoney(catTotal(cat)) }}</span>
        </div>
        <div v-show="cat.expanded" class="cat-items">
          <div v-for="(item, ii) in cat.items" :key="ii" class="cost-row">
            <span class="cost-item-name">{{ item.name }}</span>
            <el-input-number v-model="item.target" :min="0" :precision="2" size="small" style="width:140px" placeholder="目标值" />
            <el-input-number v-model="item.actual" :min="0" :precision="2" size="small" style="width:140px" placeholder="实际值" />
            <span class="cost-remark">
              <el-input v-model="item.remark" placeholder="备注" size="small" style="width:120px" />
            </span>
          </div>
        </div>
      </div>

      <!-- 汇总 -->
      <div class="cost-summary bordered">
        <div class="summary-row">
          <span class="summary-label">物料成本 (BOM)</span>
          <span class="summary-val">{{ formatMoney(catTotal(categories[0])) }}</span>
        </div>
        <div class="summary-row"><span class="summary-label">模具费用</span><span class="summary-val">{{ formatMoney(catTotal(categories[1])) }}</span></div>
        <div class="summary-row"><span class="summary-label">研发费用</span><span class="summary-val">{{ formatMoney(catTotal(categories[2])) }}</span></div>
        <div class="summary-row"><span class="summary-label">样机费用</span><span class="summary-val">{{ formatMoney(catTotal(categories[3])) }}</span></div>
        <div class="summary-row"><span class="summary-label">测试费用</span><span class="summary-val">{{ formatMoney(catTotal(categories[4])) }}</span></div>
        <div class="summary-row"><span class="summary-label">认证费用</span><span class="summary-val">{{ formatMoney(catTotal(categories[5])) }}</span></div>
        <div class="summary-row"><span class="summary-label">人工费用</span><span class="summary-val">{{ formatMoney(catTotal(categories[6])) }}</span></div>
        <div class="summary-row total-row">
          <span class="summary-label">💰 总目标成本</span>
          <span class="summary-val">{{ formatMoney(grandTotal) }}</span>
        </div>
      </div>
    </div>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="handleSave" :loading="saving">保存成本分解</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const props = defineProps<{
  modelValue: boolean
  planId: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'saved'): void
}>()

const visible = ref(false)
const saving = ref(false)

watch(() => props.modelValue, (v) => { visible.value = v })
watch(visible, (v) => { if (!v) emit('update:modelValue', false) })

interface CostItem { name: string; target: number; actual: number; remark: string }
interface CostCategory { name: string; expanded: boolean; items: CostItem[] }

const categories = ref<CostCategory[]>([
  {
    name: '物料成本 (BOM)', expanded: true,
    items: [
      { name: '压缩机', target: 0, actual: 0, remark: '' },
      { name: '冷凝器', target: 0, actual: 0, remark: '' },
      { name: '蒸发器', target: 0, actual: 0, remark: '' },
      { name: '风机组件', target: 0, actual: 0, remark: '' },
      { name: '电控板', target: 0, actual: 0, remark: '' },
      { name: '管路系统', target: 0, actual: 0, remark: '' },
      { name: '外壳/结构件', target: 0, actual: 0, remark: '' },
      { name: '包装', target: 0, actual: 0, remark: '' },
      { name: '其他物料', target: 0, actual: 0, remark: '' },
    ]
  },
  {
    name: '模具费用', expanded: false,
    items: [
      { name: '冷凝器模具', target: 0, actual: 0, remark: '' },
      { name: '蒸发器模具', target: 0, actual: 0, remark: '' },
      { name: '风机模具', target: 0, actual: 0, remark: '' },
      { name: '电控盒模具', target: 0, actual: 0, remark: '' },
      { name: '外壳模具', target: 0, actual: 0, remark: '' },
      { name: '其他模具', target: 0, actual: 0, remark: '' },
    ]
  },
  {
    name: '研发费用', expanded: false,
    items: [
      { name: '方案设计', target: 0, actual: 0, remark: '' },
      { name: '电气设计', target: 0, actual: 0, remark: '' },
      { name: '结构设计', target: 0, actual: 0, remark: '' },
      { name: '软件开发', target: 0, actual: 0, remark: '' },
      { name: '测试验证', target: 0, actual: 0, remark: '' },
    ]
  },
  {
    name: '样机费用', expanded: false,
    items: [
      { name: '样机制作', target: 0, actual: 0, remark: '' },
      { name: '样机物料', target: 0, actual: 0, remark: '' },
      { name: '样机运输', target: 0, actual: 0, remark: '' },
    ]
  },
  {
    name: '测试费用', expanded: false,
    items: [
      { name: '性能测试', target: 0, actual: 0, remark: '' },
      { name: '可靠性测试', target: 0, actual: 0, remark: '' },
      { name: 'EMC测试', target: 0, actual: 0, remark: '' },
      { name: '安规测试', target: 0, actual: 0, remark: '' },
      { name: '噪音测试', target: 0, actual: 0, remark: '' },
    ]
  },
  {
    name: '认证费用', expanded: false,
    items: [
      { name: 'CB认证', target: 0, actual: 0, remark: '' },
      { name: 'CE/UKCA', target: 0, actual: 0, remark: '' },
      { name: '沙特SASO', target: 0, actual: 0, remark: '' },
      { name: '墨西哥NOM', target: 0, actual: 0, remark: '' },
      { name: '巴西INMETRO', target: 0, actual: 0, remark: '' },
      { name: '印度BIS', target: 0, actual: 0, remark: '' },
      { name: '其他认证', target: 0, actual: 0, remark: '' },
    ]
  },
  {
    name: '人工费用', expanded: false,
    items: [
      { name: '研发人工', target: 0, actual: 0, remark: '' },
      { name: '试产人工', target: 0, actual: 0, remark: '' },
      { name: '项目管理', target: 0, actual: 0, remark: '' },
    ]
  },
])

function catTotal(cat: CostCategory): number {
  return cat.items.reduce((s, i) => s + (i.target || 0), 0)
}
const grandTotal = computed(() => categories.value.reduce((s, c) => s + catTotal(c), 0))

function formatMoney(v: number): string {
  return '¥' + v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function handleSave() {
  saving.value = true
  try {
    // 先清空旧的成本记录
    const oldRes = await api.get(`/product-plans/${props.planId}/costs`)
    const oldItems = (oldRes.data as CostItem[]) || []
    for (const old of oldItems) {
      if (old.id) await api.delete(`/product-plans/${props.planId}/costs/${old.id}`)
    }
    // 写入新成本: 每条目标+实际各一条
    const payloads: Record<string, unknown>[] = []
    for (const cat of categories.value) {
      for (const item of cat.items) {
        if (item.target > 0) {
          payloads.push({ item_name: `${cat.name} - ${item.name}`, cost_type: 'target', target_value: item.target, actual_value: 0, currency: 'CNY', remark: item.remark || '' })
        }
        if (item.actual > 0) {
          payloads.push({ item_name: `${cat.name} - ${item.name}`, cost_type: 'actual', target_value: 0, actual_value: item.actual, currency: 'CNY', remark: item.remark || '' })
        }
      }
    }
    if (payloads.length === 0) {
      ElMessage.warning('请至少填写一个成本项')
      return
    }
    for (const p of payloads) {
      await api.post(`/product-plans/${props.planId}/costs`, p)
    }
    ElMessage.success(`已保存 ${payloads.length} 条成本记录，总目标成本 ${formatMoney(grandTotal.value)}`)
    visible.value = false
    emit('saved')
  } catch (e: unknown) {
    const msg = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : null
    ElMessage.error(msg || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.cost-bd { max-height: 70vh; overflow-y: auto; }
.cost-category { margin-bottom: 8px; border: 1px solid #e5dfd3; border-radius: 6px; background: #fffdf7; }
.cat-header { display: flex; align-items: center; gap: 8px; padding: 10px 14px; cursor: pointer; user-select: none; background: #f8f6f0; border-radius: 6px 6px 0 0; }
.cat-toggle { font-size: 10px; color: #999; width: 14px; }
.cat-name { font-weight: 600; font-size: 14px; flex: 1; }
.cat-total { font-size: 12px; color: #b85a2e; }
.cat-items { padding: 8px 14px 12px; }
.cost-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.cost-item-name { width: 100px; font-size: 13px; color: #555; flex-shrink: 0; }
.cost-remark { margin-left: auto; }
.cost-summary { padding: 14px; margin-top: 12px; }
.bordered { border: 1px solid #e5dfd3; border-radius: 6px; background: #faf8f3; }
.summary-row { display: flex; justify-content: space-between; padding: 4px 0; font-size: 13px; }
.total-row { border-top: 2px solid #d97757; margin-top: 6px; padding-top: 8px; font-weight: 700; font-size: 15px; }
.total-row .summary-val { color: #d97757; }
</style>
