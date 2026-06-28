<template>
  <div class="knowledge-view">
    <el-page-header title="知识库" @back="$router.push('/dashboard')" />

    <el-row :gutter="16" class="main-row">
      <!-- 左侧分类树 -->
      <el-col :span="5">
        <el-card class="tree-card" shadow="hover">
          <template #header>
            <div class="tree-header">
              <span>分类目录</span>
              <el-button type="primary" link size="small" @click="loadCategoryTree" :loading="treeLoading">
                刷新
              </el-button>
            </div>
          </template>
          <el-tree
            :data="categoryTree"
            :props="{ label: 'name', children: 'children' }"
            node-key="id"
            highlight-current
            default-expand-all
            @node-click="onCategoryClick"
          />
        </el-card>
      </el-col>

      <!-- 右侧列表 -->
      <el-col :span="19">
        <!-- 搜索栏 -->
        <el-card class="filter-card">
          <el-form :inline="true" :model="query" size="small">
            <el-form-item label="分类">
              <el-input
                v-model="query.category"
                disabled
                placeholder="点击左侧分类树"
                style="width: 160px"
                clearable
                @clear="query.category = ''; search()"
              />
            </el-form-item>
            <el-form-item label="搜索">
              <el-input
                v-model="query.q"
                placeholder="搜索名称/编码/标签/内容..."
                clearable
                style="width: 260px"
                @keyup.enter="search"
              >
                <template #prefix><el-icon><Search /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="search">查询</el-button>
              <el-button @click="resetQuery">重置</el-button>
            </el-form-item>
            <el-form-item>
              <el-button type="success" @click="openCreate">+ 新建</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 表格 -->
        <el-card class="table-card">
          <el-table :data="page.items" v-loading="loading" stripe highlight-current-row border>
            <el-table-column prop="code" label="编码" width="140" sortable />
            <el-table-column prop="name" label="名称" min-width="200" show-overflow-tooltip />
            <el-table-column prop="category" label="分类" width="160" show-overflow-tooltip />
            <el-table-column label="标签" width="160">
              <template #default="{ row }">
                <template v-if="row.tags">
                  <el-tag
                    v-for="t in (row.tags || '').split(',').filter(Boolean)"
                    :key="t"
                    size="small"
                    style="margin-right: 4px; margin-bottom: 2px"
                  >
                    {{ t.trim() }}
                  </el-tag>
                </template>
                <span v-else class="text-muted">—</span>
              </template>
            </el-table-column>
            <el-table-column prop="version" label="版本" width="70" align="center" />
            <el-table-column prop="status" label="状态" width="80" align="center">
              <template #default="{ row }">
                <el-tag
                  :type="row.status === 'active' ? 'success' : row.status === 'draft' ? 'info' : 'danger'"
                  size="small"
                >
                  {{ row.status === 'active' ? '启用' : row.status === 'draft' ? '草稿' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="updated_at" label="更新日期" width="120" />
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="openDetail(row)">详情</el-button>
                <el-button type="warning" link size="small" @click="openEdit(row)">编辑</el-button>
                <el-popconfirm title="确认删除？" @confirm="handleDelete(row.id)" width="180">
                  <template #reference>
                    <el-button type="danger" link size="small">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="page.page"
              v-model:page-size="page.size"
              :total="page.total"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next"
              @change="loadData"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 新建/编辑 弹窗 -->
    <el-dialog
      v-model="formVisible"
      :title="formMode === 'create' ? '新建知识条目' : '编辑知识条目'"
      width="680px"
      :close-on-click-modal="false"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="90px"
        size="small"
      >
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="分类" prop="category">
              <el-cascader
                v-model="form.category"
                :options="cascaderOptions"
                :props="{ label: 'name', value: 'id', children: 'children', expandTrigger: 'hover' }"
                placeholder="选择分类"
                clearable
                filterable
                class="full-width"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="编码" prop="code">
              <el-input v-model="form.code" placeholder="唯一编码" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="知识条目名称" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="form.tags" placeholder="标签，多个用英文逗号分隔" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="6"
            placeholder="知识条目内容（支持 Markdown 格式）"
          />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="排序">
              <el-input-number v-model="form.sort_order" :min="0" :max="9999" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="备注">
              <el-input v-model="form.remark" placeholder="备注说明" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button size="small" @click="formVisible = false">取消</el-button>
        <el-button type="primary" size="small" :loading="saving" @click="handleSave">
          {{ formMode === 'create' ? '创建' : '保存' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="知识条目详情" width="700px" :close-on-click-modal="false">
      <template v-if="detailItem">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="编码" span="2">{{ detailItem.code }}</el-descriptions-item>
          <el-descriptions-item label="名称" span="2">{{ detailItem.name }}</el-descriptions-item>
          <el-descriptions-item label="分类">{{ detailItem.category }}</el-descriptions-item>
          <el-descriptions-item label="版本">v{{ detailItem.version }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag
              :type="detailItem.status === 'active' ? 'success' : detailItem.status === 'draft' ? 'info' : 'danger'"
              size="small"
            >
              {{ detailItem.status === 'active' ? '启用' : detailItem.status === 'draft' ? '草稿' : '停用' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="排序">{{ detailItem.sort_order }}</el-descriptions-item>
          <el-descriptions-item label="创建人">{{ detailItem.created_by || '—' }}</el-descriptions-item>
          <el-descriptions-item label="更新人">{{ detailItem.updated_by || '—' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ detailItem.created_at || '—' }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ detailItem.updated_at || '—' }}</el-descriptions-item>
          <el-descriptions-item label="标签" span="2">
            <template v-if="detailItem.tags">
              <el-tag
                v-for="t in detailItem.tags.split(',').filter(Boolean)"
                :key="t"
                size="small"
                style="margin-right: 4px"
              >
                {{ t.trim() }}
              </el-tag>
            </template>
            <span v-else class="text-muted">—</span>
          </el-descriptions-item>
          <el-descriptions-item label="备注" span="2">{{ detailItem.remark || '—' }}</el-descriptions-item>
        </el-descriptions>
        <el-divider content-position="left">内容</el-divider>
        <div class="detail-content">
          <pre v-if="detailItem.content">{{ detailItem.content }}</pre>
          <span v-else class="text-muted">无内容</span>
        </div>
      </template>
      <template #footer>
        <el-button size="small" @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'
import type {
  KnowledgeItem,
  KnowledgeSearchResult,
  KnowledgeCreate,
  KnowledgeUpdate,
  CategoryTreeNode,
} from '@/api/knowledge'
import {
  searchKnowledge,
  getKnowledgeItem,
  getCategoryTree,
  createKnowledgeItem,
  updateKnowledgeItem,
  deleteKnowledgeItem,
} from '@/api/knowledge'

// ── 状态 ──

const loading = ref(false)
const treeLoading = ref(false)
const saving = ref(false)

// 分类树
const categoryTree = ref<CategoryTreeNode[]>([])

// 分类级联选择器选项（将树转成 cascader 格式）
interface CascaderItem { value: string; label: string; children?: CascaderItem[] }
const cascaderOptions = computed(() => {
  function flatten(nodes: CategoryTreeNode[]): CascaderItem[] {
    return nodes.map(n => ({
      value: n.id,
      label: n.name,
      children: n.children?.length ? flatten(n.children) : undefined,
    }))
  }
  return flatten(categoryTree.value)
})

// 查询条件
const query = reactive({
  q: '',
  category: '',
  page: 1,
  size: 20,
})

// 分页数据
const page = reactive<KnowledgeSearchResult>({ items: [], total: 0, page: 1, size: 20 })

// 表单
const formVisible = ref(false)
const formMode = ref<'create' | 'edit'>('create')
const editId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const form = reactive<KnowledgeCreate>({
  category: '',
  code: '',
  name: '',
  content: null,
  content_type: 'text',
  tags: null,
  sort_order: 0,
  remark: null,
})

const formRules = {
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  code: [{ required: true, message: '请输入编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
}

// 详情
const detailVisible = ref(false)
const detailItem = ref<KnowledgeItem | null>(null)

// ── 方法 ──

async function loadCategoryTree() {
  treeLoading.value = true
  try {
    categoryTree.value = await getCategoryTree()
  } finally {
    treeLoading.value = false
  }
}

async function loadData() {
  loading.value = true
  try {
    const res = await searchKnowledge({
      q: query.q || undefined,
      category: query.category || undefined,
      page: query.page,
      size: query.size,
    })
    Object.assign(page, res)
  } finally {
    loading.value = false
  }
}

function search() {
  query.page = 1
  loadData()
}

function resetQuery() {
  query.q = ''
  query.category = ''
  query.page = 1
  loadData()
}

function onCategoryClick(node: CategoryTreeNode) {
  query.category = node.id
  query.page = 1
  loadData()
}

// ── 新建 / 编辑 ──

function openCreate() {
  formMode.value = 'create'
  editId.value = null
  resetForm()
  formVisible.value = true
}

async function openEdit(row: KnowledgeItem) {
  formMode.value = 'edit'
  editId.value = row.id
  form.category = row.category
  form.code = row.code
  form.name = row.name
  form.content = row.content
  form.content_type = row.content_type || 'text'
  form.tags = row.tags
  form.sort_order = row.sort_order ?? 0
  form.remark = row.remark
  formVisible.value = true
}

function resetForm() {
  form.category = ''
  form.code = ''
  form.name = ''
  form.content = null
  form.content_type = 'text'
  form.tags = null
  form.sort_order = 0
  form.remark = null
  formRef.value?.clearValidate()
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (formMode.value === 'create') {
      const payload: KnowledgeCreate = {
        category: form.category,
        code: form.code,
        name: form.name,
        content: form.content || null,
        content_type: 'text',
        tags: form.tags || null,
        sort_order: form.sort_order ?? 0,
        remark: form.remark || null,
      }
      await createKnowledgeItem(payload)
      ElMessage.success('创建成功')
    } else {
      const payload: KnowledgeUpdate = {
        category: form.category,
        code: form.code,
        name: form.name,
        content: form.content || null,
        content_type: form.content_type,
        tags: form.tags || null,
        sort_order: form.sort_order,
        remark: form.remark || null,
      }
      if (editId.value !== null) {
        await updateKnowledgeItem(editId.value, payload)
        ElMessage.success('更新成功')
      }
    }
    formVisible.value = false
    loadData()
    loadCategoryTree() // 分类可能变化，刷新树
  } finally {
    saving.value = false
  }
}

// ── 详情 ──

async function openDetail(row: KnowledgeItem) {
  detailItem.value = null
  detailVisible.value = true
  try {
    detailItem.value = await getKnowledgeItem(row.id)
  } catch {
    detailVisible.value = false
  }
}

// ── 删除 ──

async function handleDelete(id: number) {
  try {
    await deleteKnowledgeItem(id)
    ElMessage.success('已删除')
    loadData()
    loadCategoryTree()
  } catch (e: unknown) { /* error already handled by interceptor */ }
}

// ── 初始化 ──

onMounted(() => {
  loadCategoryTree()
  loadData()
})
</script>

<style scoped>
.knowledge-view {
  padding: 16px;
}

.main-row {
  margin-top: 16px;
}

.tree-card {
  height: 100%;
  min-height: 500px;
}

.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.filter-card {
  margin-bottom: 16px;
}

.table-card {
  min-height: 400px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.text-muted {
  color: #999;
}

.detail-content {
  background: #f5f7fa;
  border-radius: 4px;
  padding: 12px 16px;
  max-height: 300px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.6;
}

.full-width {
  width: 100%;
}
</style>
