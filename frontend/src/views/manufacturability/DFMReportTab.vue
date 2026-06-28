<template>
  <div>
    <div style="margin-bottom:12px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
      <el-input v-model="keyword" placeholder="搜索报告编号/标题" clearable style="width:220px" @clear="fetchData" @keyup.enter="fetchData" />
      <el-select v-model="filterStatus" placeholder="状态" clearable style="width:100px" @change="fetchData">
        <el-option label="草稿" value="draft" />
        <el-option label="进行中" value="in_progress" />
        <el-option label="已完成" value="completed" />
      </el-select>
      <el-button type="primary" @click="showCreateReport">新建报告</el-button>
    </div>

    <el-table :data="reports" v-loading="loading" style="width:100%" stripe @row-click="openReportDetail">
      <el-table-column prop="report_no" label="报告编号" width="160" />
      <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
      <el-table-column prop="product_type" label="产品类型" width="100" />
      <el-table-column prop="total_score" label="总分" width="70" align="center">
        <template #default="{row}">
          <el-tag v-if="row.total_score != null" :type="row.total_score >= 80 ? 'success' : row.total_score >= 60 ? 'warning' : 'danger'" size="small">{{ row.total_score }}</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{row}">
          <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'in_progress' ? 'warning' : 'info'" size="small">
            {{ row.status === 'completed' ? '已完成' : row.status === 'in_progress' ? '进行中' : '草稿' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right" @click.stop>
        <template #default="{row}">
          <el-button link type="primary" size="small" @click.stop="openReportDetail(row)">详情</el-button>
          <el-popconfirm title="确定删除?" @confirm="handleDeleteReport(row)">
            <template #reference><el-button link type="danger" size="small">删除</el-button></template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <div style="margin-top:12px;text-align:right">
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10,20,50]" layout="total,sizes,prev,pager,next" @change="fetchData" />
    </div>

    <!-- 报告详情抽屉 -->
    <el-drawer v-model="detailVisible" :title="currentReport?.report_no + ' - ' + currentReport?.title" size="70%" direction="rtl">
      <template v-if="currentReport">
        <div style="margin-bottom:16px;display:flex;gap:16px;flex-wrap:wrap;">
          <div>状态: <el-tag :type="currentReport.status === 'completed' ? 'success' : 'warning'" size="small">{{ currentReport.status }}</el-tag></div>
          <div v-if="currentReport.total_score != null">
            DFM评分: <el-tag :type="currentReport.total_score >= 80 ? 'success' : currentReport.total_score >= 60 ? 'warning' : 'danger'" size="large">{{ currentReport.total_score }}/100</el-tag>
          </div>
          <div>产品类型: {{ currentReport.product_type || '-' }}</div>
          <div>版本: {{ currentReport.version || '-' }}</div>
        </div>

        <!-- 操作栏 -->
        <div style="margin-bottom:12px;display:flex;gap:8px;">
          <el-button type="primary" size="small" @click="showAddItem">添加问题项</el-button>
          <el-button size="small" @click="refreshScore">刷新评分</el-button>
          <el-button v-if="currentReport.status !== 'completed'" size="small" type="success" @click="completeReport">完成报告</el-button>
          <el-button v-if="currentReport.status !== 'draft'" size="small" @click="editReport">编辑报告</el-button>
        </div>

        <!-- 评分概览 -->
        <el-card v-if="scoreResult" style="margin-bottom:12px;">
          <div style="display:flex;gap:24px;flex-wrap:wrap;">
            <div><b>总分</b>: {{ scoreResult.total_score }}/100</div>
            <div><b>问题项</b>: {{ scoreResult.item_count }}</div>
            <div><b style="color:#f56c6c">严重</b>: {{ scoreResult.critical_count }}</div>
            <div><b style="color:#e6a23c">主要</b>: {{ scoreResult.major_count }}</div>
            <div><b style="color:#909399">轻微</b>: {{ scoreResult.minor_count }}</div>
          </div>
        </el-card>

        <!-- 问题项列表 -->
        <div v-for="item in currentReport.items" :key="item.id" style="border:1px solid #ebeef5;border-radius:4px;padding:12px;margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;align-items:start;">
            <div>
              <el-tag :type="item.severity === 'critical' ? 'danger' : item.severity === 'major' ? 'warning' : 'info'" size="small" style="margin-right:8px;">{{ severityLabel(item.severity) }}</el-tag>
              <el-tag v-if="item.dfm_category" size="small" style="margin-right:8px;">{{ catLabel(item.dfm_category) }}</el-tag>
              <strong>{{ item.issue_desc }}</strong>
            </div>
            <div style="display:flex;gap:4px;flex-shrink:0;">
              <el-tag :type="item.status === 'verified' ? 'success' : item.status === 'resolved' ? 'warning' : 'info'" size="small">
                {{ item.status === 'verified' ? '已验证' : item.status === 'resolved' ? '已解决' : '待处理' }}
              </el-tag>
            </div>
          </div>
          <div v-if="item.suggestion" style="margin-top:6px;color:#666;font-size:13px;">建议: {{ item.suggestion }}</div>
          <div v-if="item.responsible_person" style="margin-top:4px;color:#999;font-size:12px;">责任人: {{ item.responsible_person }}</div>
          <div style="margin-top:8px;display:flex;gap:4px;">
            <el-button v-if="item.status === 'pending'" size="small" link @click="updateItemStatus(item, 'resolved')">标记已解决</el-button>
            <el-button v-if="item.status === 'resolved'" size="small" link @click="updateItemStatus(item, 'verified')">验证通过</el-button>
            <el-button v-if="item.status !== 'pending'" size="small" link @click="updateItemStatus(item, 'pending')">重开</el-button>
            <el-button size="small" link @click="editItem(item)">编辑</el-button>
            <el-popconfirm title="确定删除?" @confirm="deleteItem(item)">
              <template #reference><el-button size="small" link type="danger">删除</el-button></template>
            </el-popconfirm>
          </div>
        </div>
        <div v-if="!currentReport.items?.length" style="text-align:center;padding:40px;color:#999;">暂无问题项，点击"添加问题项"开始</div>
      </template>
    </el-drawer>

    <!-- 新建报告弹窗 -->
    <el-dialog v-model="reportDialogVisible" :title="isEditReport ? '编辑报告' : '新建DFM报告'" width="550px">
      <el-form ref="reportFormRef" :model="reportForm" :rules="reportRules" label-width="100px">
        <el-form-item label="报告标题" prop="title"><el-input v-model="reportForm.title" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="关联项目"><el-input-number v-model="reportForm.project_id" style="width:100%" :min="0" placeholder="项目ID" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="关联样机"><el-input-number v-model="reportForm.prototype_id" style="width:100%" :min="0" placeholder="样机ID" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="产品类型"><el-select v-model="reportForm.product_type" style="width:100%">
            <el-option label="分体空调" value="split_ac" /><el-option label="移动空调" value="portable_ac" /><el-option label="除湿机" value="dehumidifier" />
          </el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="版本"><el-input v-model="reportForm.version" placeholder="V1.0" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="创建人"><el-input v-model="reportForm.created_by" /></el-form-item>
        <el-form-item label="总结说明"><el-input v-model="reportForm.summary" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reportDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingReport" @click="saveReport">保存</el-button>
      </template>
    </el-dialog>

    <!-- 添加/编辑问题项弹窗 -->
    <el-dialog v-model="itemDialogVisible" :title="isEditItem ? '编辑问题项' : '添加问题项'" width="550px">
      <el-form ref="itemFormRef" :model="itemForm" :rules="itemRules" label-width="100px">
        <el-form-item label="问题描述" prop="issue_desc"><el-input v-model="itemForm.issue_desc" type="textarea" :rows="2" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="分类"><el-select v-model="itemForm.dfm_category" style="width:100%">
            <el-option label="结构DFM" value="structural" /><el-option label="工艺DFM" value="process" />
            <el-option label="装配DFM" value="assembly" /><el-option label="电气DFM" value="electrical" /><el-option label="模具DFM" value="mold" />
          </el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="等级"><el-select v-model="itemForm.severity" style="width:100%">
            <el-option label="严重" value="critical" /><el-option label="主要" value="major" /><el-option label="轻微" value="minor" />
          </el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="建议方案"><el-input v-model="itemForm.suggestion" type="textarea" :rows="2" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="责任人"><el-input v-model="itemForm.responsible_person" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="排序"><el-input-number v-model="itemForm.sort_order" style="width:100%" :min="0" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="itemDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingItem" @click="saveItem">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  listDFMReports, getDFMReport, createDFMReport, updateDFMReport, deleteDFMReport,
  getDFMReportScore, createDFMReportItem, updateDFMReportItem, deleteDFMReportItem
} from '../../api/manufacturability'
import type { FormInstance } from 'element-plus'
import type { TableRow } from '@/types/common'

const reports = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const keyword = ref('')
const filterStatus = ref('')
const detailVisible = ref(false)
const currentReport = ref<any>(null)
const scoreResult = ref<any>(null)
const reportDialogVisible = ref(false)
const isEditReport = ref(false)
const editingReportId = ref<number | null>(null)
const savingReport = ref(false)
const reportFormRef = ref<FormInstance>()
const itemDialogVisible = ref(false)
const isEditItem = ref(false)
const editingItemId = ref<number | null>(null)
const savingItem = ref(false)
const itemFormRef = ref<FormInstance>()

const reportForm = ref<any>({ title: '', project_id: null, prototype_id: null, product_type: '', version: 'V1.0', summary: '', created_by: '' })
const reportRules = { title: [{ required: true, message: '请输入报告标题' }] }

const itemForm = ref<any>({ report_id: 0, issue_desc: '', dfm_category: '', severity: 'major', suggestion: '', responsible_person: '', sort_order: 0 })
const itemRules = { issue_desc: [{ required: true, message: '请输入问题描述' }] }

function catLabel(c: string) { const m: Record<string, string> = { structural: '结构', process: '工艺', assembly: '装配', electrical: '电气', mold: '模具' }; return m[c] || c }
function severityLabel(s: string) { const m: Record<string, string> = { critical: '严重', major: '主要', minor: '轻微' }; return m[s] || s }

async function fetchData() {
  loading.value = true
  try {
    const { data } = await listDFMReports({ page: page.value, page_size: pageSize.value, status: filterStatus.value || undefined, keyword: keyword.value || undefined })
    reports.value = data.items || []; total.value = data.total || 0
  } catch {} finally { loading.value = false }
}

function showCreateReport() { isEditReport.value = false; editingReportId.value = null; reportForm.value = { title: '', project_id: null, prototype_id: null, product_type: '', version: 'V1.0', summary: '', created_by: '' }; reportDialogVisible.value = true }

function editReport() {
  if (!currentReport.value) return
  isEditReport.value = true; editingReportId.value = currentReport.value.id
  reportForm.value = { title: currentReport.value.title, project_id: currentReport.value.project_id, prototype_id: currentReport.value.prototype_id, product_type: currentReport.value.product_type, version: currentReport.value.version, summary: currentReport.value.summary, created_by: currentReport.value.created_by }
  reportDialogVisible.value = true
}

async function saveReport() {
  const valid = await reportFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingReport.value = true
  try {
    if (isEditReport.value && editingReportId.value) {
      await updateDFMReport(editingReportId.value, reportForm.value)
    } else {
      await createDFMReport(reportForm.value)
    }
    reportDialogVisible.value = false; fetchData()
  } catch {} finally { savingReport.value = false }
}

async function openReportDetail(row: TableRow) {
  currentReport.value = null; scoreResult.value = null
  try {
    const { data } = await getDFMReport(row.id as number)
    currentReport.value = data
    detailVisible.value = true
    refreshScore()
  } catch {}
}

async function refreshScore() {
  if (!currentReport.value) return
  try {
    const { data } = await getDFMReportScore(currentReport.value.id)
    scoreResult.value = data
  } catch {}
}

async function completeReport() {
  if (!currentReport.value) return
  try {
    await updateDFMReport(currentReport.value.id, { status: 'completed' })
    openReportDetail(currentReport.value)
    fetchData()
  } catch {}
}

async function handleDeleteReport(row: TableRow) {
  try { await deleteDFMReport(row.id as number); fetchData() } catch {}
}

function showAddItem() {
  if (!currentReport.value) return
  isEditItem.value = false; editingItemId.value = null
  itemForm.value = { report_id: currentReport.value.id, issue_desc: '', dfm_category: '', severity: 'major', suggestion: '', responsible_person: '', sort_order: currentReport.value.items?.length || 0 }
  itemDialogVisible.value = true
}

function editItem(item: TableRow) {
  isEditItem.value = true; editingItemId.value = item.id as number
  itemForm.value = { ...item }
  itemDialogVisible.value = true
}

async function saveItem() {
  const valid = await itemFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingItem.value = true
  try {
    if (isEditItem.value && editingItemId.value) {
      await updateDFMReportItem(editingItemId.value, itemForm.value)
    } else {
      await createDFMReportItem(itemForm.value)
    }
    itemDialogVisible.value = false
    // Reload current report
    if (currentReport.value) openReportDetail(currentReport.value)
  } catch {} finally { savingItem.value = false }
}

async function deleteItem(item: TableRow) {
  try { await deleteDFMReportItem(item.id as number); if (currentReport.value) openReportDetail(currentReport.value) } catch {}
}

async function updateItemStatus(item: TableRow, newStatus: string) {
  try {
    await updateDFMReportItem(item.id as number, { status: newStatus })
    if (currentReport.value) openReportDetail(currentReport.value)
  } catch {}
}

onMounted(fetchData)
</script>
