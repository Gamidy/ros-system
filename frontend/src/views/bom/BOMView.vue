<template>
  <div class="bom-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>BOM物料管理</span>
        </div>
      </template>

      <el-row :gutter="16">
        <el-col :span="12">
          <h3>物料主数据</h3>
          <el-button type="primary" size="small" style="margin-bottom: 12px" @click="showPartDialog = true">新建物料</el-button>
          <el-table :data="parts" stripe border max-height="400">
            <el-table-column prop="part_no" label="物料号" width="140" />
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="unit" label="单位" width="60" />
          </el-table>
        </el-col>
        <el-col :span="12">
          <h3>BOM列表</h3>
          <el-button type="primary" size="small" style="margin-bottom: 12px" @click="showBOMDialog = true">新建BOM</el-button>
          <el-table :data="boms" stripe border max-height="400">
            <el-table-column prop="bom_no" label="BOM编号" width="180" />
            <el-table-column prop="product_code" label="产品编码" />
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="loadBOMTree(row.id)">展开</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-col>
      </el-row>
    </el-card>

    <el-dialog v-model="showPartDialog" title="新建物料" width="500">
      <el-form ref="partFormRef" :model="partForm" :rules="partRules" label-width="100">
        <el-form-item label="物料号" prop="part_no"><el-input v-model="partForm.part_no" /></el-form-item>
        <el-form-item label="名称" prop="name"><el-input v-model="partForm.name" /></el-form-item>
        <el-form-item label="单位" prop="unit"><el-input v-model="partForm.unit" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPartDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="savePart">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showBOMDialog" title="新建BOM" width="500">
      <el-form ref="bomFormRef" :model="bomForm" :rules="bomRules" label-width="100">
        <el-form-item label="BOM编号" prop="bom_no"><el-input v-model="bomForm.bom_no" /></el-form-item>
        <el-form-item label="产品编码" prop="product_code"><el-input v-model="bomForm.product_code" placeholder="如 EU-09K" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBOMDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveBOM">保存</el-button>
      </template>
    </el-dialog>

    <!-- BOM 树形层级视图 -->
    <el-dialog v-model="bomTreeVisible" :title="'BOM 层级视图 - ' + (currentBOM?.bom_no || '')" width="1000px" top="5vh" destroy-on-close>
      <div v-if="currentBOM" style="margin-bottom:12px; color:#909399; font-size:13px">
        产品编码：{{ currentBOM.product_code }}
      </div>
      <el-table
        :data="flatTreeData"
        row-key="id"
        :tree-props="{ children: 'children', hasChildren: 'hasChildren' }"
        border
        stripe
        default-expand-all
        max-height="500"
      >
        <el-table-column prop="level" label="层级" width="70" align="center" />
        <el-table-column prop="part_no" label="物料号" width="150" show-overflow-tooltip />
        <el-table-column prop="part_name" label="名称" min-width="140" show-overflow-tooltip />
        <el-table-column prop="item_type" label="物料类型" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="itemTypeTag(row.item_type)" size="small">{{ row.item_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="quantity" label="数量" width="70" align="center" />
        <el-table-column prop="position_no" label="位置号" width="90" align="center" />
        <el-table-column label="采购价格" width="100" align="right">
          <template #default="{ row }">{{ getCostField(row, '采购价格') }}</template>
        </el-table-column>
        <el-table-column label="金额" width="100" align="right">
          <template #default="{ row }">{{ getCostField(row, '金额') }}</template>
        </el-table-column>
        <el-table-column label="采购类型" width="90" align="center">
          <template #default="{ row }">{{ getCostField(row, '采购类型') }}</template>
        </el-table-column>
        <el-table-column label="物料组" width="90" align="center">
          <template #default="{ row }">{{ getCostField(row, '物料组') }}</template>
        </el-table-column>
        <el-table-column label="单位" width="70" align="center">
          <template #default="{ row }">{{ getCostField(row, '单位') }}</template>
        </el-table-column>
        <el-table-column label="工厂" width="80" align="center">
          <template #default="{ row }">{{ getCostField(row, '工厂') }}</template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="bomTreeVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import api from '../../api'

const parts = ref<any[]>([])
const boms = ref<any[]>([])
const saving = ref(false)

const showPartDialog = ref(false)
const partForm = ref({ part_no: '', name: '', unit: '个' })
const showBOMDialog = ref(false)
const bomForm = ref({ bom_no: '', product_code: '' })

// BOM 树形视图
const bomTreeVisible = ref(false)
const currentBOM = ref<any>(null)
const currentBOMTree = ref<any[]>([])
// 为 el-table tree-props 提供可直接渲染的扁平树数据（含 children）
const flatTreeData = ref<any[]>([])

/** 安全解析 remark JSON 并返回指定字段 */
function parseRemark(remark: string | null | undefined): Record<string, any> {
  if (!remark) return {}
  try {
    return JSON.parse(remark)
  } catch {
    return {}
  }
}

/** 从行的 _cost 缓存中提取指定成本字段，容错降级为 '-' */
function getCostField(row: any, key: string): string {
  const v = row._cost?.[key]
  if (v === undefined || v === null || v === '') return '-'
  if (typeof v === 'number') return v.toFixed(2)
  return String(v)
}

/** 物料类型 tag 颜色 */
function itemTypeTag(type: string) {
  const map: Record<string, string> = {
    '成品': 'danger',
    '半成品': 'warning',
    '零件': 'success',
    '原材料': '',
  }
  return map[type] || 'info'
}

async function loadBOMTree(bomId: number) {
  try {
    const r = await api.get(`/bom/${bomId}/tree`)
    currentBOM.value = r.data.bom
    currentBOMTree.value = r.data.tree || []
    const treeData = r.data.tree || []
    // 预解析 remark JSON 缓存到 _cost，避免渲染时重复 JSON.parse
    function preParse(items: any[]) {
      for (const item of items) {
        item._cost = parseRemark(item.remark)
        if (item.children) preParse(item.children)
      }
    }
    preParse(treeData)
    flatTreeData.value = treeData
    bomTreeVisible.value = true
  } catch {
    // 错误由拦截器统一提示
  }
}

const partFormRef = ref<FormInstance>()
const bomFormRef = ref<FormInstance>()

const partRules: FormRules = {
  part_no: [{ required: true, message: '请输入物料号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  unit: [{ required: true, message: '请输入单位', trigger: 'blur' }],
}

const bomRules: FormRules = {
  bom_no: [{ required: true, message: '请输入BOM编号', trigger: 'blur' }],
  product_code: [{ required: true, message: '请输入产品编码', trigger: 'blur' }],
}

async function fetchAll() {
  try {
    const r1 = api.get('/bom/parts')
    const r2 = api.get('/bom')
    parts.value = (await r1).data
    boms.value = (await r2).data
  } catch {}
}

async function savePart() {
  const valid = await partFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await api.post('/bom/parts', partForm.value)
    ElMessage.success('创建成功')
    showPartDialog.value = false
    partForm.value = { part_no: '', name: '', unit: '个' }
    await fetchAll()
  } finally { saving.value = false }
}

async function saveBOM() {
  const valid = await bomFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await api.post('/bom', bomForm.value)
    ElMessage.success('创建成功')
    showBOMDialog.value = false
    bomForm.value = { bom_no: '', product_code: '' }
    await fetchAll()
  } finally { saving.value = false }
}

onMounted(fetchAll)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
h3 { margin: 0 0 12px; color: #303133; }
</style>
