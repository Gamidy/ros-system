<template>
  <div class="procurement-dashboard">
    <!-- KPI -->
    <el-row :gutter="16" class="kpi-row">
      <el-col :span="6"><el-card shadow="never" class="kpi-card">
        <div class="kpi-value" style="color:#409eff">{{ stats.activeRfq }}</div>
        <div class="kpi-label">进行中询价</div>
      </el-card></el-col>
      <el-col :span="6"><el-card shadow="never" class="kpi-card">
        <div class="kpi-value" style="color:#e6a23c">{{ stats.pendingOrders }}</div>
        <div class="kpi-label">待收货订单</div>
      </el-card></el-col>
      <el-col :span="6"><el-card shadow="never" class="kpi-card">
        <div class="kpi-value" style="color:#67c23a">{{ stats.evaluatedSuppliers }}</div>
        <div class="kpi-label">已评估供应商</div>
      </el-card></el-col>
      <el-col :span="6"><el-card shadow="never" class="kpi-card">
        <div class="kpi-value" style="color:#f56c6c">{{ stats.overdueRfq }}</div>
        <div class="kpi-label">逾期询价</div>
      </el-card></el-col>
    </el-row>

    <!-- 快捷操作 -->
    <el-card shadow="never" class="section-card">
      <template #header><span>⚡ 快捷操作</span></template>
      <div class="quick-actions">
        <el-button type="primary" @click="$router.push('/purchase/rfqs')">💰 新建询价</el-button>
        <el-button type="success" @click="$router.push('/purchase/rfqs')">📊 比价</el-button>
      </div>
    </el-card>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="never" class="section-card">
          <template #header><span>📋 进行中询价 ({{ stats.activeRfq }})</span></template>
          <div v-if="activeRfqs.length === 0" class="empty">暂无进行中询价</div>
          <div v-for="r in activeRfqs.slice(0, 5)" :key="r.id" class="todo-item" @click="$router.push('/purchase/rfqs')">
            <div class="todo-title">{{ r.title }}</div>
            <div class="todo-meta">{{ r.rfq_no }} | 截止: {{ r.deadline || '-' }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="section-card">
          <template #header><span>🏆 供应商评分 TOP5</span></template>
          <div v-if="topSuppliers.length === 0" class="empty">暂无评估数据</div>
          <div v-for="(s, i) in topSuppliers.slice(0, 5)" :key="s.id" class="todo-item">
            <div class="rank-badge">{{ ['🥇','🥈','🥉','4','5'][i] }}</div>
            <div class="todo-title">{{ s.supplier_name }}</div>
            <div class="todo-meta">综合 {{ s.total_score }}分 | <el-tag size="small" :type="gradeTag(s.grade)">{{ s.grade }}级</el-tag></div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'

const stats = ref({ activeRfq: 0, pendingOrders: 0, evaluatedSuppliers: 0, overdueRfq: 0 })
const activeRfqs = ref<any[]>([])
const topSuppliers = ref<any[]>([])

function gradeTag(g: string) { return { A: 'success', B: 'primary', C: 'warning', D: 'danger' }[g] || 'info' }

async function loadData() {
  try {
    const [rfqRes, evalRes] = await Promise.all([
      api.get('/purchase/rfqs').catch(() => ({ data: [] })),
      api.get('/purchase/supplier-evaluations').catch(() => ({ data: [] })),
    ])
    activeRfqs.value = (rfqRes.data || []).filter((r: any) => ['sent', 'quoting'].includes(r.status))
    topSuppliers.value = (evalRes.data || []).sort((a: any, b: any) => b.total_score - a.total_score)
    const now = new Date()
    stats.value = {
      activeRfq: activeRfqs.value.length,
      pendingOrders: 0,
      evaluatedSuppliers: topSuppliers.value.length,
      overdueRfq: activeRfqs.value.filter((r: any) => r.deadline && new Date(r.deadline) < now).length,
    }
  } catch { /* ignore */ }
}
onMounted(loadData)
</script>

<style scoped>
.procurement-dashboard { padding: 16px; }
.kpi-row { margin-bottom: 16px; }
.kpi-card { text-align: center; cursor: default; }
.kpi-card :deep(.el-card__body) { padding: 20px 16px; }
.kpi-value { font-size: 32px; font-weight: 700; }
.kpi-label { font-size: 13px; color: #909399; margin-top: 4px; }
.section-card { margin-bottom: 16px; }
.quick-actions { display: flex; gap: 12px; }
.todo-item { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-bottom: 1px solid #f0f0f0; cursor: pointer; transition: background 0.15s; }
.todo-item:hover { background: #f5f7fa; }
.todo-item:last-child { border-bottom: none; }
.todo-title { font-weight: 600; font-size: 14px; color: #303133; flex: 1; }
.todo-meta { font-size: 12px; color: #909399; margin-top: 4px; }
.rank-badge { font-size: 20px; }
.empty { color: #909399; font-size: 13px; padding: 20px; text-align: center; }
</style>
