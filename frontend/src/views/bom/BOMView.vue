<template>
  <div class="bom-page">
    <!-- ========== BOM树可视化区域 ========== -->
    <el-card shadow="never" class="tree-card">
      <template #header>
        <div class="card-header">
          <span>BOM树可视化</span>
          <el-select
            v-model="selectedBomId"
            placeholder="请选择BOM查看树结构"
            clearable
            filterable
            @change="onBomSelect"
            style="width: 320px"
          >
            <el-option
              v-for="b in boms"
              :key="b.id"
              :label="`${b.bom_no} — ${b.product_code}`"
              :value="b.id"
            />
          </el-select>
        </div>
      </template>

      <!-- 统计卡片 -->
      <el-row :gutter="12" class="stats-row">
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-label">总节点数</div>
            <div class="stat-value">{{ treeStats.totalNodes }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-label">最大层级</div>
            <div class="stat-value">{{ treeStats.maxDepth }}</div>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="stat-card">
            <div class="stat-label">物料类型分布</div>
            <div class="stat-value">
              <span v-if="Object.keys(treeStats.typeDist).length === 0" class="stat-empty">—</span>
              <template v-else>
                <el-tag
                  v-for="(count, type) in treeStats.typeDist"
                  :key="type"
                  size="small"
                  class="type-tag"
                >{{ type }}: {{ count }}</el-tag>
              </template>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- BOM树 -->
      <div class="tree-wrapper">
        <el-tree
          v-if="treeData.length"
          :data="treeData"
          node-key="id"
          :props="treeProps"
          default-expand-all
          highlight-current
          :expand-on-click-node="false"
          @node-click="onNodeClick"
        >
          <template #default="{ data }">
            <span class="tree-node">
              <span class="node-part-no">[{{ data.part_no }}]</span>
              <span class="node-name">{{ data.part_name }}</span>
              <span class="node-qty">×{{ data.quantity }}</span>
              <el-tag size="small" type="info" class="node-type-tag">{{ data.item_type }}</el-tag>
            </span>
          </template>
        </el-tree>
        <el-empty v-else description="请选择一个BOM查看其树结构" :image-size="80" />
      </div>
    </el-card>

    <!-- ========== 原有：BOM物料管理（保持不变） ========== -->
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
          </el-table>
        </el-col>
      </el-row>
    </el-card>

    <!-- ========== 节点详情弹窗（新增） ========== -->
    <el-dialog v-model="showNodeDetail" title="节点详情" width="460">
      <el-descriptions v-if="selectedNode" :column="1" border size="small">
        <el-descriptions-item label="节点ID">{{ selectedNode.id }}</el-descriptions-item>
        <el-descriptions-item label="物料号">{{ selectedNode.part_no }}</el-descriptions-item>
        <el-descriptions-item label="物料名称">{{ selectedNode.part_name }}</el-descriptions-item>
        <el-descriptions-item label="物料类型">
          <el-tag size="small">{{ selectedNode.item_type }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="数量">{{ selectedNode.quantity }}</el-descriptions-item>
        <el-descriptions-item label="层级">{{ selectedNode.level }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="showNodeDetail = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- ========== 原有：对话框（保持不变） ========== -->
    <el-dialog v-model="showPartDialog" title="新建物料" width="500">
      <el-form :model="partForm" label-width="100">
        <el-form-item label="物料号"><el-input v-model="partForm.part_no" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="partForm.name" /></el-form-item>
        <el-form-item label="单位"><el-input v-model="partForm.unit" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPartDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="savePart">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showBOMDialog" title="新建BOM" width="500">
      <el-form :model="bomForm" label-width="100">
        <el-form-item label="BOM编号"><el-input v-model="bomForm.bom_no" /></el-form-item>
        <el-form-item label="产品编码"><el-input v-model="bomForm.product_code" placeholder="如 EU-09K" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBOMDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveBOM">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

// ——— 原有：物料 & BOM ———
const parts = ref<any[]>([])
const boms = ref<any[]>([])
const saving = ref(false)

const showPartDialog = ref(false)
const partForm = ref({ part_no: '', name: '', unit: '个' })
const showBOMDialog = ref(false)
const bomForm = ref({ bom_no: '', product_code: '' })

// ——— 新增：BOM树可视化 ———
const selectedBomId = ref<number | string | null>(null)
const treeData = ref<any[]>([])
const selectedNode = ref<any>(null)
const showNodeDetail = ref(false)

const treeProps = { children: 'children', label: 'part_name' }

/** 递归遍历树节点 */
function walkTree(nodes: any[], level: number, fn: (node: any, level: number) => void) {
  for (const node of nodes) {
    fn(node, level)
    if (node.children && node.children.length) {
      walkTree(node.children, level + 1, fn)
    }
  }
}

/** 统计卡片计算属性 */
const treeStats = computed(() => {
  let totalNodes = 0
  let maxDepth = 0
  const typeDist: Record<string, number> = {}

  walkTree(treeData.value, 1, (node, level) => {
    totalNodes++
    if (level > maxDepth) maxDepth = level
    const t = node.item_type || '未知'
    typeDist[t] = (typeDist[t] || 0) + 1
  })

  return { totalNodes, maxDepth, typeDist }
})

/** BOM选择器变更 */
function onBomSelect(bomId: number | string | null) {
  if (!bomId && bomId !== 0) {
    treeData.value = []
    return
  }
  fetchBomTree(bomId)
}

/** 获取BOM树 */
async function fetchBomTree(bomId: number | string) {
  try {
    const res = await api.get(`/bom/${bomId}/tree`)
    treeData.value = res.data.tree || []
  } catch {
    treeData.value = []
    ElMessage.error('获取BOM树失败')
  }
}

/** 树节点点击 */
function onNodeClick(data: any) {
  selectedNode.value = data
  showNodeDetail.value = true
}

// ——— 原有函数（保持不变） ———
async function fetchAll() {
  try {
    const r1 = api.get('/bom/parts')
    const r2 = api.get('/bom')
    parts.value = (await r1).data
    boms.value = (await r2).data
  } catch {}
}

async function savePart() {
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

/* ——— BOM树可视化样式 ——— */
.tree-card { margin-bottom: 16px; }

.stats-row { margin-bottom: 16px; }

.stat-card {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 12px 16px;
  height: 100%;
  text-align: center;
}
.stat-label { font-size: 12px; color: #909399; margin-bottom: 4px; }
.stat-value { font-size: 20px; font-weight: 600; color: #303133; }
.stat-empty { font-size: 16px; color: #c0c4cc; }
.type-tag { margin: 2px 4px 2px 0; }

.tree-wrapper {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 8px;
  min-height: 120px;
}

/* el-tree 节点样式 */
.tree-wrapper :deep(.el-tree-node__content) {
  height: 32px;
  font-size: 13px;
}
.tree-wrapper :deep(.el-tree-node__expand-icon) {
  font-size: 14px;
}
.tree-wrapper :deep(.el-tree-node__label) {
  overflow: visible;
}

.tree-node {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  line-height: 1;
}

.node-part-no {
  color: #909399;
  font-family: 'Menlo', 'Consolas', monospace;
  font-size: 12px;
}

.node-name {
  color: #303133;
  font-weight: 500;
}

.node-qty {
  color: #409eff;
  font-weight: 600;
  font-size: 12px;
}

.node-type-tag {
  font-size: 11px;
}
</style>
