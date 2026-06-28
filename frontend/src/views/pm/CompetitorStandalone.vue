<template>
  <div class="competitor-standalone">
    <!-- ========== 页面标题 ========== -->
    <div class="page-header">
      <h2>🔍 竞品对标</h2>
      <p class="page-desc">查看与录入各市场竞品参数对比数据</p>
    </div>

    <!-- ========== 筛选栏 ========== -->
    <div class="filters-bar">
      <div class="filter-item">
        <label>目标市场</label>
        <el-cascader
          v-model="selectedMarketPath"
          :options="marketTree"
          :props="{ expandTrigger: 'hover', value: 'code', label: 'name', children: 'markets' }"
          placeholder="请选择大洲 → 国家/区域"
          clearable
          style="width:100%"
          @change="onMarketChange"
        />
      </div>
      <div class="filter-item">
        <label>品牌</label>
        <el-select
          v-model="selectedBrand"
          placeholder="全部品牌"
          clearable
          @change="fetchData"
        >
          <el-option v-for="b in brandPresets" :key="b" :label="b" :value="b" />
        </el-select>
      </div>
      <div class="filter-item">
        <label>冷量段</label>
        <el-select
          v-model="selectedCapacity"
          placeholder="全部"
          clearable
          @change="fetchData"
        >
          <el-option v-for="c in capacities" :key="c" :label="c" :value="c" />
        </el-select>
      </div>
      <div class="filter-item">
        <label>能效等级</label>
        <el-select
          v-model="selectedEnergyRating"
          placeholder="全部"
          clearable
          @change="fetchData"
        >
          <el-option v-for="r in energyRatings" :key="r" :label="r" :value="r" />
        </el-select>
      </div>
      <div class="filter-item">
        <label>产品类型</label>
        <el-select
          v-model="selectedProductType"
          placeholder="全部"
          clearable
          @change="fetchData"
        >
          <el-option v-for="t in productTypes" :key="t" :label="t" :value="t" />
        </el-select>
      </div>
      <div class="filter-item">
        <label>单冷/冷暖</label>
        <el-select
          v-model="selectedUnitType"
          placeholder="全部"
          clearable
          @change="fetchData"
        >
          <el-option label="单冷" value="单冷" />
          <el-option label="冷暖" value="冷暖" />
        </el-select>
      </div>
      <div class="filter-actions">
        <el-button type="primary" @click="openAddDialog" :icon="Plus">
          新增竞品
        </el-button>
      </div>
    </div>

    <!-- ========== 统计卡片 ========== -->
    <div v-if="selectedMarket && !loading" class="stats-row">
      <div class="stat-card">
        <div class="stat-label">品牌数</div>
        <div class="stat-value">{{ brandCount }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">机型数</div>
        <div class="stat-value">{{ modelCount }}</div>
      </div>
      <div class="stat-card" :class="{ 'stat-incomplete': !allComplete }">
        <div class="stat-label">数据完整性</div>
        <div class="stat-value" :style="{ color: allComplete ? '#67c23a' : '#e6a23c' }">
          {{ allComplete ? '✅ 完整' : '⚠️ 不完整' }}
        </div>
      </div>
    </div>

    <!-- ========== 加载状态 ========== -->
    <div v-if="loading" class="loading-wrap">
      <el-icon class="is-loading" :size="28"><Loading /></el-icon>
      <p>正在加载竞品数据...</p>
    </div>

    <!-- ========== 空状态 ========== -->
    <el-empty
      v-else-if="!selectedMarket"
      description="请选择目标市场查看竞品对标数据"
      :image-size="80"
    />

    <!-- ========== 竞品卡片列表 ========== -->
    <template v-else-if="allItems.length > 0">
      <!-- 操作栏 -->
      <div class="toolbar-row">
        <span class="toolbar-title">共 {{ allItems.length }} 条竞品记录</span>
        <div class="toolbar-actions">
          <el-button size="small" :loading="completenessLoading" @click="checkCompleteness">🔍 校验完整性</el-button>
          <el-button size="small" :loading="templateLoading" @click="downloadTemplate">📥 下载模板</el-button>
          <el-button size="small" type="success" @click="openImportDialog">📤 导入</el-button>
          <el-button size="small" type="warning" :loading="exportLoading" @click="handleExport">📎 导出</el-button>
        </div>
      </div>

      <!-- 竞品卡片 -->
      <div class="competitor-cards">
        <div
          v-for="item in allItems"
          :key="item.id"
          class="competitor-card"
          :class="{ 'card-incomplete': !item.is_complete }"
        >
          <div class="card-header">
            <div class="card-brand-section">
              <span class="card-brand">{{ item.brand }}</span>
              <span class="card-model">{{ item.model }}</span>
              <el-tag v-if="item.is_complete" size="small" type="success" effect="plain">完整</el-tag>
              <el-tag v-else size="small" type="warning" effect="plain">缺{{ item.missing_fields?.length }}项</el-tag>
            </div>
            <div class="card-thumb" v-if="(item as any).image_urls && (item as any).image_urls.length > 0" @click="openDetailDrawer(item)">
              <img :src="(item as any).image_urls[0].url" class="thumb-img" alt="外观" />
            </div>
            <div class="card-actions">
              <el-button size="small" plain @click="openDetailDrawer(item)">详情</el-button>
              <el-button size="small" plain type="primary" @click="openEditDialog(item)">编辑</el-button>
              <el-button size="small" plain type="danger" @click="handleDelete(item)">删除</el-button>
            </div>
          </div>
          <div class="card-params">
            <div class="param-row" v-for="p in effectiveParams" :key="p.key">
              <span class="param-label">{{ p.label }}{{ p.unit ? ` (${p.unit})` : '' }}</span>
              <span class="param-value" :class="{ 'param-missing': getParamValue(item, p.key) === '-' }">
                {{ getParamValue(item, p.key) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- ══════════════ 热力图对标+采纳（有数据时） ═══════════════ -->
      <div v-if="benchmarkData.length > 0" class="benchmark-section">
        <el-divider content-position="left">🔥 参数对比热力图</el-divider>

        <!-- 生成本品策划 -->
        <div v-if="hasAdoptedTargets" class="generate-plan-bar">
          <span class="generate-plan-hint">✅ 已设定 {{ adoptedParamKeys.length }} 项目标参数</span>
          <el-button type="primary" @click="handleGeneratePlan" :loading="generating">
            📋 生成本品策划
          </el-button>
        </div>

        <HeatmapCompare
          :benchmark-data="benchmarkData"
          :brands="brands"
          v-model="ourTargets"
        />
      </div>

      <!-- ========== 可视化对标图表 ========== -->
      <div v-if="chartCompetitors.length > 0" class="chart-section">
        <el-divider content-position="left">📈 雷达图对比</el-divider>
        <div class="chart-card">
          <RadarChart
            :competitors="chartCompetitors as any"
            :loading="chartLoading"
            :empty="chartCompetitors.length === 0"
          />
        </div>
        <el-divider content-position="left">📊 分组柱状图对比</el-divider>
        <div class="chart-card">
          <BarCompare
            :competitors="chartCompetitors as any"
            :loading="chartLoading"
            :empty="chartCompetitors.length === 0"
          />
        </div>
      </div>
    </template>

    <!-- ========== 无数据 ========== -->
    <el-empty v-else description="该市场暂无竞品数据，请点击「新增竞品」添加" :image-size="80" />

    <!-- ========== 编辑/新增弹窗 ========== -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑竞品数据' : '新增竞品'"
      width="680px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="110px"
        label-position="right"
        size="small"
      >
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="品牌" prop="brand">
              <el-input v-model="form.brand" placeholder="如 TCL" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="型号" prop="model">
              <el-input v-model="form.model" placeholder="如 TAC-12CSF" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="6">
            <el-form-item label="目标市场" prop="market">
              <el-select v-model="form.market" placeholder="选择市场" style="width:100%">
                <el-option v-for="m in markets" :key="m" :label="m" :value="m" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="产品类型" prop="product_type">
              <el-select v-model="form.product_type" placeholder="选择类型" style="width:100%">
                <el-option v-for="t in productTypes" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="单冷/冷暖" prop="unit_type">
              <el-select v-model="form.unit_type" placeholder="选择" style="width:100%">
                <el-option label="单冷" value="单冷" />
                <el-option label="冷暖" value="冷暖" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="冷量段" prop="cooling_capacity">
              <el-select v-model="form.cooling_capacity" placeholder="选择冷量" style="width:100%">
                <el-option v-for="c in capacities" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">核心参数</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="制冷量(W)" prop="cooling_capacity_w">
              <el-input-number v-model="form.cooling_capacity_w" :min="0" style="width:100%" placeholder="如 3500" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="制热量(W)" prop="heating_capacity_w">
              <el-input-number v-model="form.heating_capacity_w" :min="0" style="width:100%" placeholder="如 4000" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="能效等级" prop="energy_rating">
              <el-select v-model="form.energy_rating" placeholder="选择" style="width:100%">
                <el-option label="1星" value="1星" />
                <el-option label="2星" value="2星" />
                <el-option label="3星" value="3星" />
                <el-option label="4星" value="4星" />
                <el-option label="5星" value="5星" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="制冷功率(W)" prop="cooling_w">
              <el-input-number v-model="form.cooling_w" :min="0" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="制热功率(W)" prop="heating_w">
              <el-input-number v-model="form.heating_w" :min="0" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="energyLabel" :prop="energyKey">
              <el-input-number v-model="(form as any)[energyKey]" :min="0" :step="0.1" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">噪音 & 风量</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="室内噪音(dB)" prop="noise_indoor_db">
              <el-input-number v-model="form.noise_indoor_db" :min="0" :step="0.5" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="室外噪音(dB)" prop="noise_outdoor_db">
              <el-input-number v-model="form.noise_outdoor_db" :min="0" :step="0.5" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="循环风量(m³/h)" prop="airflow_m3h">
              <el-input-number v-model="form.airflow_m3h" :min="0" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">尺寸 & 价格</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="内机尺寸(mm)" prop="indoor_size_mm">
              <el-input v-model="form.indoor_size_mm" placeholder="如 800×300×200" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="外机尺寸(mm)" prop="outdoor_size_mm">
              <el-input v-model="form.outdoor_size_mm" placeholder="如 800×600×300" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="上市年份" prop="launch_year">
              <el-input-number v-model="form.launch_year" :min="2020" :max="2030" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="备注" prop="notes">
              <el-input v-model="form.notes" placeholder="可选" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">📷 外观外形</el-divider>
        <div class="image-urls-editor">
          <div v-for="(img, ii) in form.imageUrls" :key="ii" class="image-url-row">
            <el-input v-model="img.label" placeholder="标签（如正面、室内机）" style="width:120px;margin-right:8px" size="small" />
            <el-input v-model="img.url" placeholder="图片URL" style="flex:1;margin-right:8px" size="small" />
            <el-button type="danger" size="small" @click="form.imageUrls.splice(ii, 1)">✕</el-button>
          </div>
          <el-button type="primary" size="small" @click="form.imageUrls.push({label: '', url: ''})" style="margin-top:8px">
            + 添加图片
          </el-button>
        </div>

        <!-- ══════════ 市场专有参数（动态） ══════════ -->
        <template v-if="marketParamConfigs.length > 0">
          <el-divider content-position="left">市场专有参数</el-divider>
          <el-row :gutter="16">
            <el-col
              v-for="cfg in marketParamConfigs"
              :key="cfg.param_key"
              :span="8"
            >
              <el-form-item
                :label="cfg.param_label + (cfg.param_unit ? '(' + cfg.param_unit + ')' : '')"
              >
                <el-input-number
                  v-if="cfg.data_type === 'float' || cfg.data_type === 'int'"
                  v-model="form.extraFields[cfg.param_key]"
                  :min="0"
                  :step="cfg.data_type === 'int' ? 1 : 0.1"
                  :precision="cfg.data_type === 'int' ? 0 : 2"
                  style="width:100%"
                />
                <el-input
                  v-else
                  v-model="form.extraFields[cfg.param_key]"
                  style="width:100%"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- ========== 导入弹窗 ========== -->
    <el-dialog
      v-model="importDialogVisible"
      title="导入竞品数据"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-upload
        ref="uploadRef"
        drag
        :accept="'.xlsx,.csv'"
        :auto-upload="false"
        :limit="1"
        :on-change="onImportFileChange"
        :file-list="importFileList"
      >
        <el-icon class="el-icon--upload" :size="40"><UploadFilled /></el-icon>
        <div class="el-upload__text">拖拽文件到此处，或<em>点击选择</em></div>
        <template #tip>
          <div class="el-upload__tip">
            支持 .xlsx 或 .csv 格式，请先<a @click="downloadTemplate" style="cursor:pointer;color:var(--el-color-primary)">下载模板</a>填写
          </div>
        </template>
      </el-upload>
      <div v-if="importResult" class="import-result">
        <p>✅ 导入完成：共 {{ importResult.total }} 行，成功 {{ importResult.imported }} 条</p>
        <p v-if="importResult.errors > 0" style="color:var(--el-color-danger)">
          ⚠️ {{ importResult.errors }} 条失败
        </p>
        <ul v-if="importResult.error_details?.length" class="error-list">
          <li v-for="(err, ei) in importResult.error_details" :key="ei">{{ err }}</li>
        </ul>
      </div>
      <template #footer>
        <el-button @click="closeImportDialog">取消</el-button>
        <el-button type="primary" :loading="importing" @click="submitImport">开始导入</el-button>
      </template>
    </el-dialog>

    <!-- ========== 详情抽屉（参数详情 + 历史版本） ========== -->
    <el-drawer
      v-model="detailDrawerVisible"
      :title="detailTitle"
      size="520px"
      :close-on-click-modal="false"
    >
      <template v-if="detailItem">
        <el-tabs v-model="detailTab">
          <!-- ── 参数详情 Tab ── -->
          <el-tab-pane label="参数详情" name="params">
            <div class="detail-params">
              <!-- 外观图片 -->
              <div v-if="(detailItem as any).image_urls && (detailItem as any).image_urls.length > 0" class="detail-images-section">
                <div class="detail-section-title">📷 外观外形</div>
                <div class="detail-images-grid">
                  <div v-for="(img, ii) in (detailItem as any).image_urls" :key="ii" class="detail-image-item">
                    <el-image :src="img.url" fit="contain" class="detail-image" :preview-src-list="Array.isArray((detailItem as any).image_urls) ? (detailItem as any).image_urls.map((i: any) => i.url) : []" />
                    <div class="detail-image-label">{{ img.label || '外观' }}</div>
                  </div>
                </div>
              </div>
              <div
                v-for="p in effectiveParams"
                :key="p.key"
                class="detail-param-row"
              >
                <span class="detail-param-label">
                  {{ p.label }}{{ p.unit ? ` (${p.unit})` : '' }}
                </span>
                <span class="detail-param-value" :class="{ 'param-missing': getParamValue(detailItem, p.key) === '-' }">
                  {{ getParamValue(detailItem, p.key) }}
                </span>
              </div>
              <div class="detail-param-row">
                <span class="detail-param-label">备注</span>
                <span class="detail-param-value">{{ detailItem.notes || '-' }}</span>
              </div>
            </div>
          </el-tab-pane>

          <!-- ── 历史版本 Tab ── -->
          <el-tab-pane label="历史版本" name="history">
            <div v-if="historyLoading" class="loading-wrap">
              <el-icon class="is-loading" :size="20"><Loading /></el-icon>
              <p>加载中...</p>
            </div>
            <template v-else-if="historyItems.length === 0">
              <el-empty description="暂无历史版本记录" :image-size="60" />
            </template>
            <template v-else>
              <!-- 时间轴 -->
              <div class="history-timeline">
                <el-timeline>
                  <el-timeline-item
                    v-for="h in historyItems"
                    :key="h.id"
                    :timestamp="h.created_at"
                    placement="top"
                    :hollow="!h.changed_fields || Object.keys(h.changed_fields).length === 0"
                  >
                    <div class="timeline-header">
                      <span class="timeline-user">{{ h.changed_by || '系统' }}</span>
                      <el-tag
                        size="small"
                        :type="h.changed_fields && Object.keys(h.changed_fields).length > 0 ? 'warning' : 'info'"
                        effect="plain"
                      >
                        {{ h.changed_fields ? Object.keys(h.changed_fields).length : 0 }} 个变更
                      </el-tag>
                    </div>
                    <!-- 变更字段列表 -->
                    <div
                      v-if="h.changed_fields && Object.keys(h.changed_fields).length > 0"
                      class="timeline-fields"
                    >
                      <div
                        v-for="(change, field) in h.changed_fields"
                        :key="field"
                        class="changed-field-row"
                      >
                        <span class="field-name">{{ getFieldLabel(field) }}</span>
                        <span class="field-old">{{ formatChangeValue(change.old) }}</span>
                        <el-icon :size="12" style="color: var(--c-text-muted)"><ArrowRight /></el-icon>
                        <span class="field-new">{{ formatChangeValue(change.new) }}</span>
                      </div>
                    </div>
                    <div v-else class="timeline-no-change">初始创建 / 无参数变更</div>
                    <!-- 查看此版本快照 -->
                    <el-button
                      v-if="h.snapshot_data"
                      size="small"
                      link
                      type="primary"
                      @click="previewVersion(h)"
                    >
                      查看此版本
                    </el-button>
                  </el-timeline-item>
                </el-timeline>
              </div>
            </template>
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-drawer>

    <!-- ========== 版本快照预览弹窗 ========== -->
    <el-dialog
      v-model="versionPreviewVisible"
      :title="'版本详情 - ' + (versionPreviewItem?.created_at || '')"
      width="540px"
      :close-on-click-modal="false"
    >
      <template v-if="versionPreviewItem?.snapshot_data">
        <div class="version-preview-grid">
          <div
            v-for="p in effectiveParams"
            :key="p.key"
            class="preview-row"
          >
            <span class="preview-label">{{ p.label }}{{ p.unit ? ` (${p.unit})` : '' }}</span>
            <span class="preview-value">{{ formatChangeValue(versionPreviewItem.snapshot_data[p.key]) }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">备注</span>
            <span class="preview-value">{{ versionPreviewItem.snapshot_data.notes || '-' }}</span>
          </div>
        </div>
      </template>
      <div v-else class="preview-empty">版本数据不可用</div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading, Plus, UploadFilled, ArrowRight } from '@element-plus/icons-vue'
import { useRoute } from 'vue-router'
import api from '../../api'
import type { FormInstance, FormRules } from 'element-plus'
import RadarChart from '../../components/competitor/RadarChart.vue'
import BarCompare from '../../components/competitor/BarCompare.vue'
import HeatmapCompare from '../../components/competitor/HeatmapCompare.vue'

interface MarketOption {
  code: string
  name: string
  energy_standard: string
  energy_label: string
}

interface CompetitorFormData {
  brand: string
  model: string
  market: string
  product_type: string
  cooling_capacity: string
  cooling_capacity_w: number | null
  heating_capacity_w: number | null
  energy_rating: string
  cooling_w: number | null
  heating_w: number | null
  eer: number | null
  cspf: number | null
  iseer: number | null
  seer: number | null
  noise_indoor_db: number | null
  noise_outdoor_db: number | null
  airflow_m3h: number | null
  indoor_size_mm: string
  outdoor_size_mm: string
  unit_type: string
  launch_year: number | null
  notes: string
  extraFields: Record<string, number | string | null>
  imageUrls: Array<{label: string; url: string}>
}

interface CompetitorItem extends CompetitorFormData {
  id: number
  is_complete: boolean
  missing_fields?: string[]
  [key: string]: unknown
}

interface VersionChangeField {
  old: string | number | null
  new: string | number | null
}

interface VersionHistoryItem {
  id: number
  changed_fields: Record<string, VersionChangeField> | null
  snapshot_data: Record<string, string | number | null> | null
  changed_by: string | null
  created_at: string
}

// ── 市场 & 冷量段选项 ──────────────────────────────────────────────
const markets = ref<string[]>([])
const marketOptions = ref<MarketOption[]>([])
const marketTree = ref<Array<{code: string; name: string; markets: Array<{code: string; name: string}>}>>([])
const selectedMarketPath = ref<string[]>([])
const completenessLoading = ref(false)
const templateLoading = ref(false)
const exportLoading = ref(false)
const capacities = ['9000BTU', '12000BTU', '18000BTU', '24000BTU']
const energyRatings = ['3星', '4星', '5星', 'A+', 'A++', 'A+++']
const productTypes = ['壁挂分体机']
const brandPresets = ['AUX', 'TCL', 'Midea', 'Gree', 'Haier', 'Hisense', 'Chigo']

const selectedMarket = ref('')
const selectedBrand = ref('')
const selectedCapacity = ref('')
const selectedEnergyRating = ref('')
const selectedProductType = ref('')
const selectedUnitType = ref('')

const route = useRoute()

// ── 市场能效配置（动态从API获取）───────────────────────────────────
const MARKET_ENERGY_MAP = ref<Record<string, { key: string; label: string }>>({})

// 从API加载市场列表（含区域/大洲信息）
async function fetchMarkets() {
  try {
    const res = await api.get('/pm/markets/all')
    const data = (res.data || []) as Array<{ code: string; name: string; region: string; energy_standard: string; energy_label: string }>
    marketOptions.value = data.map((m) => ({ code: m.code, name: m.name, energy_standard: m.energy_standard, energy_label: m.energy_label }))
    markets.value = data.map((m) => m.name)

    // 构建大洲 → 国家两级树
    const regionLabels: Record<string, string> = { SEA: '东南亚', CA: '中亚', SA: '南亚', ME: '中东', GCC: '海湾', AM: '美洲', EU: '欧洲', CIS: '独联体', AF: '非洲' }
    const groups: Record<string, Array<{code: string; name: string}>> = {}
    for (const m of data) {
      if (!m.region) continue
      const regionName = regionLabels[m.region] || m.region
      if (!groups[regionName]) groups[regionName] = []
      groups[regionName].push({ code: m.name, name: m.name })
    }
    marketTree.value = Object.entries(groups).map(([name, markets]) => ({
      code: name, name, markets
    }))

    // 构建能效映射
    const map: Record<string, { key: string; label: string }> = {}
    for (const m of data) {
      map[m.name] = { key: m.energy_standard, label: m.energy_label }
    }
    MARKET_ENERGY_MAP.value = map
  } catch {
    // fallback 硬编码（API不可用时）
    const fallback = ['越南','印度尼西亚','马来西亚','巴基斯坦','乌兹别克斯坦','吉尔吉斯斯坦','塔吉克斯坦','沙特','阿联酋','科威特','巴林','以色列','伊朗','伊拉克','美国','加拿大','墨西哥','哥伦比亚','巴西','阿根廷','俄罗斯','白俄罗斯','乌克兰','英国','阿塞拜疆','南非','阿尔及利亚','尼日利亚','意大利','欧盟']
    markets.value = fallback
  }
}

const energyConfig = computed(() => {
  return MARKET_ENERGY_MAP.value[selectedMarket.value] || { key: 'eer', label: 'EER' }
})
const energyKey = computed(() => energyConfig.value.key)
const energyLabel = computed(() => energyConfig.value.label)

// ── 参数列定义（动态适配市场） ──────────────────────────────────
const BASE_PARAMS = [
  { key: 'cooling_capacity_w', label: '制冷量', unit: 'W' },
  { key: 'heating_capacity_w', label: '制热量', unit: 'W' },
  { key: 'cooling_w', label: '制冷功率', unit: 'W' },
  { key: 'heating_w', label: '制热功率', unit: 'W' },
  { key: 'noise_indoor_db', label: '室内噪音(声压)', unit: 'dB' },
  { key: 'noise_outdoor_db', label: '室外噪音(声压)', unit: 'dB' },
  { key: 'airflow_m3h', label: '循环风量', unit: 'm³/h' },
  { key: 'indoor_size_mm', label: '内机尺寸', unit: 'mm' },
  { key: 'outdoor_size_mm', label: '外机尺寸', unit: 'mm' },
  { key: 'unit_type', label: '单冷/冷暖', unit: '' },
  { key: 'launch_year', label: '上市年份', unit: '' },
  { key: 'energy_rating', label: '能效等级', unit: '' },
]

// 来自 API 的市场参数配置（extra_fields 字段定义）
const marketParamConfigs = ref<Array<{param_key: string; param_label: string; param_unit: string; data_type: string}>>([])

const effectiveParams = computed(() => {
  const params = [...BASE_PARAMS]
  // 插入市场适配的能效参数（在能效等级前面）
  const ec = energyConfig.value
  params.splice(11, 0, { key: ec.key, label: ec.label, unit: 'W/W' })
  // 追加市场专有参数（从 extra_fields 读取）
  for (const cfg of marketParamConfigs.value) {
    // 不重复已存在的key
    if (!params.some(p => p.key === cfg.param_key)) {
      params.push({ key: cfg.param_key, label: cfg.param_label, unit: cfg.param_unit })
    }
  }
  return params
})

// ── 数据状态 ──────────────────────────────────────────────────────
const loading = ref(false)
const allItems = ref<CompetitorItem[]>([])
const allComplete = ref(false)

// ── 我方目标参数（热力图采纳用） ─────────────────────────────────
const LS_PREFIX = 'competitor_our_targets_'

function loadOurTargets(market: string): Record<string, string | number> {
  try {
    const raw = localStorage.getItem(LS_PREFIX + market)
    return raw ? (JSON.parse(raw) as Record<string, string | number>) : {}
  } catch {
    return {}
  }
}

function saveOurTargets(market: string, targets: Record<string, string | number>): void {
  try {
    localStorage.setItem(LS_PREFIX + market, JSON.stringify(targets))
  } catch {
    // localStorage 满或不可用时静默失败
  }
}

const ourTargets = ref<Record<string, string | number>>({})

// 已采纳目标的状态
const hasAdoptedTargets = computed(() => {
  return Object.keys(ourTargets.value).length > 0
})
const adoptedParamKeys = computed(() => {
  return Object.keys(ourTargets.value)
})
const generating = ref(false)

async function handleGeneratePlan() {
  if (!selectedMarket.value || !hasAdoptedTargets.value) return
  generating.value = true
  try {
    // 收集每个参数的来源信息
    const sources: Record<string, { brand: string; model: string; value: number | string }> = {}
    for (const [key, targetVal] of Object.entries(ourTargets.value)) {
      const isConfig = marketParamConfigs.value.some(c => c.param_key === key)
      for (const item of allItems.value) {
        let itemVal: unknown
        if (isConfig) {
          const ef = (item as Record<string, unknown>)['extra_fields'] as Record<string, unknown> | undefined
          itemVal = ef ? ef[key] : undefined
        } else {
          itemVal = (item as Record<string, unknown>)[key]
        }
        if (itemVal !== undefined && itemVal !== null && String(itemVal) === String(targetVal)) {
          sources[key] = { brand: item.brand, model: item.model, value: typeof targetVal === 'number' ? targetVal : String(targetVal) }
          break
        }
      }
    }

    const res = await api.post('/pm/create-plan-from-benchmark', {
      market: selectedMarket.value,
      targets: { ...ourTargets.value },
      competitor_sources: Object.keys(sources).length > 0 ? sources : undefined,
    })
    const data = res.data as { plan_id: string; plan_name: string; message: string }
    ElMessage.success(`✅ 策划「${data.plan_name}」已生成`)
    // 询问是否跳转到策划详情页
    ElMessageBox.confirm(data.message, '策划已生成', {
      confirmButtonText: '去完善',
      cancelButtonText: '留在本页',
      type: 'success',
    }).then(() => {
      window.open(`/product-plans/${data.plan_id}`, '_blank')
    }).catch(() => {
      // 留在本页
    })
  } catch (e: unknown) {
    const errMsg = e && typeof e === 'object' && 'response' in e
      ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail || '生成失败'
      : '生成失败'
    ElMessage.error(errMsg)
  } finally {
    generating.value = false
  }
}

// 市场变化时加载对应目标值
watch(() => selectedMarket.value, (market) => {
  if (market) {
    ourTargets.value = loadOurTargets(market)
  } else {
    ourTargets.value = {}
  }
})

// 目标值变化时持久化
watch(ourTargets, (targets) => {
  if (selectedMarket.value) {
    saveOurTargets(selectedMarket.value, targets)
  }
}, { deep: true })

// ── 统计 ──────────────────────────────────────────────────────────
const brandCount = computed(() => {
  const brands = new Set(allItems.value.map((it: CompetitorItem) => it.brand))
  return brands.size
})
const modelCount = computed(() => allItems.value.length)

// ── 品牌列表 ──────────────────────────────────────────────────────
const brands = computed(() => {
  const brandSet = new Set<string>()
  for (const row of benchmarkData.value) {
    Object.keys(row.competitors).forEach(b => brandSet.add(b))
  }
  return Array.from(brandSet)
})

// ── 对比数据转换 ──────────────────────────────────────────────────
interface CompetitorEntry {
  value: number | string
  model?: string
}
interface BenchmarkRow {
  param_key: string
  param_name: string
  our_target: string
  competitors: Record<string, CompetitorEntry>
}

function transformToBenchmark(items: CompetitorItem[]): BenchmarkRow[] {
  if (!items || items.length === 0) return []
  const paramDefs = effectiveParams.value
  return paramDefs.map((p) => {
    const row: BenchmarkRow = {
      param_key: p.key,
      param_name: p.unit ? `${p.label} (${p.unit})` : p.label,
      our_target: '—',
      competitors: {},
    }
    const isConfigParam = marketParamConfigs.value.some(c => c.param_key === p.key)
    for (const item of items) {
      let rawVal: unknown
      if (isConfigParam) {
        const ef = (item as Record<string, unknown>)['extra_fields'] as Record<string, unknown> | undefined
        rawVal = ef ? ef[p.key] : undefined
      } else {
        rawVal = (item as Record<string, unknown>)[p.key]
      }
      if (rawVal !== undefined && rawVal !== null && rawVal !== '') {
        if (!row.competitors[item.brand]) {
          const numVal = Number(rawVal)
          const safeValue: string | number = Number.isNaN(numVal) ? String(rawVal) : numVal
          row.competitors[item.brand] = {
            value: safeValue,
            model: item.model || '',
          }
        }
      }
    }
    return row
  })
}

const benchmarkData = computed(() => transformToBenchmark(allItems.value))

function getParamValue(item: Record<string, unknown>, key: string): string {
  // 市场专有参数从 extra_fields 读取
  const isConfigParam = marketParamConfigs.value.some(c => c.param_key === key)
  if (isConfigParam) {
    const ef = item['extra_fields'] as Record<string, unknown> | undefined
    const val = ef ? ef[key] : undefined
    return val !== undefined && val !== null && val !== '' ? String(val) : '-'
  }
  // 能效参数用市场适配的key
  if (key === energyKey.value) {
    const val = item[energyKey.value]
    return val !== undefined && val !== null && val !== '' ? String(val) : '-'
  }
  const val = item[key]
  return val !== undefined && val !== null && val !== '' ? String(val) : '-'
}

// ── 数据获取 ──────────────────────────────────────────────────────
async function fetchData() {
  if (!selectedMarket.value) {
    allItems.value = []
    return
  }
  loading.value = true
  try {
    const params: Record<string, string | number> = {
      market: selectedMarket.value,
      page: 1,
      page_size: 200,
    }
    if (selectedBrand.value) params.brand = selectedBrand.value
    if (selectedCapacity.value) params.capacity = selectedCapacity.value
    if (selectedEnergyRating.value) params.energy_rating = selectedEnergyRating.value
    if (selectedProductType.value) params.product_type = selectedProductType.value
    if (selectedUnitType.value) params.unit_type = selectedUnitType.value

    const res = await api.get('/pm/competitors', { params })
    allItems.value = res.data.items || []
    // 读取市场参数配置（extra_fields 字段定义）
    marketParamConfigs.value = res.data.param_configs || []
    // 检查完整性
    allComplete.value = allItems.value.every((it) => it.is_complete)
  } catch {
    allItems.value = []
  } finally {
    loading.value = false
  }
  // 联动刷新图表数据
  await fetchBenchmarkData()
}

// ── 图表数据（benchmark 专用端点） ──────────────────────────────
const chartLoading = ref(false)
const chartCompetitors = ref<Record<string, unknown>[]>([])

async function fetchBenchmarkData() {
  if (!selectedMarket.value) {
    chartCompetitors.value = []
    return
  }
  chartLoading.value = true
  try {
    const res = await api.get('/pm/competitors/benchmark', {
      params: { market: selectedMarket.value },
    })
    chartCompetitors.value = (res.data.competitors || []) as Record<string, unknown>[]
  } catch {
    chartCompetitors.value = []
  } finally {
    chartLoading.value = false
  }
}

async function checkCompleteness() {
  if (!selectedMarket.value) {
    ElMessage.warning('请先选择市场')
    return
  }
  completenessLoading.value = true
  try {
    const res = await api.get('/pm/competitors/check-completeness', {
      params: { market: selectedMarket.value }
    })
    const data = res.data as { all_complete: boolean; details: Array<{ is_complete: boolean; brand: string }> }
    if (data.all_complete) {
      ElMessage.success('✅ 所有竞品数据完整！')
    } else {
      const incomplete = data.details.filter((d) => !d.is_complete)
      const brands = incomplete.map((d) => d.brand).join(', ')
      ElMessage.warning(`⚠️ 有 ${incomplete.length} 条数据不完整: ${brands}`)
    }
  } catch (e: unknown) {
    const msg = e && typeof e === 'object' && 'response' in e ? (e as any).response?.data?.detail : null
    ElMessage.error(msg || '校验失败，请确认后端API可用')
  } finally {
    completenessLoading.value = false
  }
}

function onMarketChange(val: string[] | undefined) {
  if (val && val.length >= 2) {
    selectedMarket.value = val[1]
  } else {
    selectedMarket.value = ''
    allItems.value = []
  }
  selectedBrand.value = ''
  selectedCapacity.value = ''
  selectedEnergyRating.value = ''
  selectedProductType.value = ''
  selectedUnitType.value = ''
  if (selectedMarket.value) fetchData()
}

watch(() => selectedMarket.value, (newMarket) => {
  if (newMarket) fetchData()
  else allItems.value = []
}, { immediate: false })

// 初始化从DB加载市场列表
onMounted(async () => {
  await fetchMarkets()

  // 从查询参数自动选中市场和产品类型
  if (route.query.market) {
    const market = route.query.market as string
    const type = (route.query.type as string) || ''
    selectedProductType.value = type
    selectedMarket.value = market
    form.value.market = market
    form.value.product_type = type
    // 找到级联路径
    for (const group of marketTree.value) {
      if (group.markets.some((m) => m.code === market)) {
        selectedMarketPath.value = [group.code, market]
        break
      }
    }
    // watch on selectedMarket 会自动触发 fetchData()
  }
})

// ── 弹窗 & 表单 ──────────────────────────────────────────────────
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref<FormInstance | null>(null)

const defaultForm = () => ({
  brand: '',
  model: '',
  market: '',
  product_type: '',
  cooling_capacity: '',
  cooling_capacity_w: null,
  heating_capacity_w: null,
  energy_rating: '',
  cooling_w: null,
  heating_w: null,
  eer: null,
  cspf: null,
  iseer: null,
  seer: null,
  noise_indoor_db: null,
  noise_outdoor_db: null,
  airflow_m3h: null,
  indoor_size_mm: '',
  outdoor_size_mm: '',

  unit_type: '',
  launch_year: null as number | null,
  notes: '',
  extraFields: {} as Record<string, number | string | null>,
  imageUrls: [],
})

const form = ref<CompetitorFormData>(defaultForm())

// 所有必填字段的校验规则
const formRules: FormRules = {
  brand: [{ required: true, message: '请输入品牌', trigger: 'blur' }],
  model: [{ required: true, message: '请输入型号', trigger: 'blur' }],
  market: [{ required: true, message: '请选择目标市场', trigger: 'change' }],
  product_type: [{ required: true, message: '请选择产品类型', trigger: 'change' }],
  cooling_capacity: [{ required: true, message: '请选择冷量段', trigger: 'change' }],
  cooling_capacity_w: [{ required: true, message: '请输入制冷量', trigger: 'blur' }],
  heating_capacity_w: [{ required: true, message: '请输入制热量', trigger: 'blur' }],
  energy_rating: [{ required: true, message: '请选择能效等级', trigger: 'change' }],
  cooling_w: [{ required: true, message: '请输入制冷功率', trigger: 'blur' }],
  heating_w: [{ required: true, message: '请输入制热功率', trigger: 'blur' }],
  noise_indoor_db: [{ required: true, message: '请输入室内噪音', trigger: 'blur' }],
  noise_outdoor_db: [{ required: true, message: '请输入室外噪音', trigger: 'blur' }],
  airflow_m3h: [{ required: true, message: '请输入循环风量', trigger: 'blur' }],
  indoor_size_mm: [{ required: true, message: '请输入内机尺寸', trigger: 'blur' }],
  outdoor_size_mm: [{ required: true, message: '请输入外机尺寸', trigger: 'blur' }],

  launch_year: [{ required: true, message: '请输入上市年份', trigger: 'blur' }],
}

// ── 详情抽屉 ──────────────────────────────────────────────────────
const detailDrawerVisible = ref(false)
const detailTab = ref('params')
const detailItem = ref<CompetitorItem | null>(null)

const detailTitle = computed(() => {
  if (!detailItem.value) return '竞品详情'
  return `${detailItem.value.brand} ${detailItem.value.model}`
})

// ── 历史版本 ──────────────────────────────────────────────────────
const historyItems = ref<VersionHistoryItem[]>([])
const historyLoading = ref(false)

const FIELD_LABEL_MAP: Record<string, string> = {
  brand: '品牌',
  model: '型号',
  market: '目标市场',
  product_type: '产品类型',
  cooling_capacity: '冷量段',
  cooling_capacity_w: '制冷量(W)',
  heating_capacity_w: '制热量(W)',
  energy_rating: '能效等级',
  cooling_w: '制冷功率(W)',
  heating_w: '制热功率(W)',
  eer: 'EER',
  cspf: 'CSPF',
  noise_indoor_db: '室内噪音(dB)',
  noise_outdoor_db: '室外噪音(dB)',
  airflow_m3h: '循环风量(m³/h)',
  indoor_size_mm: '内机尺寸(mm)',
  outdoor_size_mm: '外机尺寸(mm)',
  unit_type: '单冷/冷暖',
  launch_year: '上市年份',
  notes: '备注',
}

function getFieldLabel(field: string): string {
  return FIELD_LABEL_MAP[field] || field
}

function formatChangeValue(val: string | number | null | undefined): string {
  if (val === null || val === undefined) return '-'
  return String(val)
}

function openDetailDrawer(item: CompetitorItem) {
  detailItem.value = item
  detailTab.value = 'params'
  detailDrawerVisible.value = true
  fetchHistory(item.id)
}

async function fetchHistory(competitorId: number) {
  historyLoading.value = true
  historyItems.value = []
  try {
    const res = await api.get(`/pm/competitors/${competitorId}/history`)
    const data = res.data as { versions: VersionHistoryItem[] }
    historyItems.value = data.versions || []
  } catch {
    historyItems.value = []
  } finally {
    historyLoading.value = false
  }
}

// ── 版本快照预览 ──────────────────────────────────────────────────
const versionPreviewVisible = ref(false)
const versionPreviewItem = ref<VersionHistoryItem | null>(null)

function previewVersion(item: VersionHistoryItem) {
  versionPreviewItem.value = item
  versionPreviewVisible.value = true
}

function openAddDialog() {
  editingId.value = null
  form.value = { ...defaultForm(), market: selectedMarket.value }
  // 用当前市场的参数配置初始化 extraFields 的 keys
  const extra: Record<string, number | string | null> = {}
  for (const cfg of marketParamConfigs.value) {
    extra[cfg.param_key] = null
  }
  form.value.extraFields = extra
  form.value.imageUrls = []
  dialogVisible.value = true
}

function openEditDialog(item: CompetitorItem) {
  editingId.value = item.id
  const extraFields: Record<string, number | string | null> = {}
  const ef = (item as Record<string, unknown>)['extra_fields'] as Record<string, unknown> | undefined
  if (ef) {
    for (const [k, v] of Object.entries(ef)) {
      if (v !== undefined && v !== null) {
        extraFields[k] = v as number | string
      }
    }
  }
  form.value = {
    brand: item.brand || '',
    model: item.model || '',
    market: item.market || '',
    product_type: item.product_type || '',
    cooling_capacity: item.cooling_capacity || '',
    cooling_capacity_w: item.cooling_capacity_w ?? null,
    heating_capacity_w: item.heating_capacity_w ?? null,
    energy_rating: item.energy_rating || '',
    cooling_w: item.cooling_w ?? null,
    heating_w: item.heating_w ?? null,
    eer: item.eer ?? null,
    cspf: item.cspf ?? null,
    iseer: item.iseer ?? null,
    seer: item.seer ?? null,
    noise_indoor_db: item.noise_indoor_db ?? null,
    noise_outdoor_db: item.noise_outdoor_db ?? null,
    airflow_m3h: item.airflow_m3h ?? null,
    indoor_size_mm: item.indoor_size_mm || '',
    outdoor_size_mm: item.outdoor_size_mm || '',
    unit_type: item.unit_type || '',

    launch_year: item.launch_year ?? null,
    notes: item.notes || '',
    extraFields,
    imageUrls: (item as Record<string, unknown>)['image_urls'] as Array<{label: string; url: string}> || [],
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    ElMessage.warning('请填写所有必填字段')
    return
  }
  saving.value = true
  try {
    // 只提交有值的字段
    const payload: Record<string, unknown> = {}
    const fields: (keyof CompetitorFormData)[] = [
      'brand', 'model', 'market', 'product_type', 'cooling_capacity',
      'cooling_capacity_w', 'heating_capacity_w', 'energy_rating',
      'cooling_w', 'heating_w', 'eer', 'cspf',
      'noise_indoor_db', 'noise_outdoor_db', 'airflow_m3h',
      'indoor_size_mm', 'outdoor_size_mm', 'unit_type',
      'launch_year', 'notes',
    ]
    for (const f of fields) {
      if (form.value[f] !== null && form.value[f] !== '') {
        payload[f] = form.value[f]
      }
    }
    // 提交 image_urls
    if (form.value.imageUrls && form.value.imageUrls.length > 0) {
      payload['image_urls'] = form.value.imageUrls.filter(u => u.url.trim() !== '')
    }
    // 提交 extra_fields
    const extraFields = form.value.extraFields
    const hasExtra = Object.keys(extraFields).length > 0 && Object.values(extraFields).some(v => v !== null && v !== '')
    if (hasExtra) {
      const cleaned: Record<string, unknown> = {}
      for (const [k, v] of Object.entries(extraFields)) {
        if (v !== null && v !== '') cleaned[k] = v
      }
      payload['extra_fields'] = cleaned
    }

    if (editingId.value) {
      await api.put(`/pm/competitors/${editingId.value}`, payload)
      ElMessage.success('更新成功')
    } else {
      await api.post('/pm/competitors', payload)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    await fetchData()
  } catch (e: unknown) {
    const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : null
    ElMessage.error(_err || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(item: CompetitorItem) {
  try {
    await ElMessageBox.confirm(`确定删除 ${item.brand} ${item.model}？`, '确认删除', {
      type: 'warning',
    })
    await api.delete(`/pm/competitors/${item.id}`)
    ElMessage.success('已删除')
    await fetchData()
  } catch {
    // cancelled or error
  }
}

// ── 导入导出 ──────────────────────────────────────────────────────

interface ImportResult {
  total: number
  imported: number
  errors: number
  error_details?: string[]
  items: Record<string, unknown>[]
}

const importDialogVisible = ref(false)
const importFileList = ref<{ name: string; raw?: File }[]>([])
const importFile = ref<File | null>(null)
const importing = ref(false)
const importResult = ref<ImportResult | null>(null)

function openImportDialog() {
  importDialogVisible.value = true
  importFileList.value = []
  importFile.value = null
  importResult.value = null
}

function closeImportDialog() {
  importDialogVisible.value = false
  importFileList.value = []
  importFile.value = null
  importResult.value = null
}

function onImportFileChange(file: { raw: File; name: string }) {
  importFile.value = file.raw
}

async function submitImport() {
  if (!importFile.value) {
    ElMessage.warning('请选择要导入的文件')
    return
  }
  importing.value = true
  importResult.value = null
  try {
    const formData = new FormData()
    formData.append('file', importFile.value)
    const res = await api.post('/pm/competitors/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    importResult.value = res.data as ImportResult
    if (res.data.imported > 0) {
      ElMessage.success(`成功导入 ${res.data.imported} 条竞品数据`)
      await fetchData()
    }
  } catch {
    ElMessage.error('导入失败')
  } finally {
    importing.value = false
  }
}

async function downloadTemplate() {
  templateLoading.value = true
  try {
    const res = await api.get('/pm/competitors/template', {
      responseType: 'blob',
    })
    const url = URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = `竞品导入模板${selectedMarket.value ? '_' + selectedMarket.value : ''}.xlsx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e: unknown) {
    const msg = e && typeof e === 'object' && 'response' in e ? (e as any).response?.data?.detail : null
    ElMessage.error(msg || '下载模板失败，请确认后端API可用')
  } finally {
    templateLoading.value = false
  }
}

async function handleExport() {
  exportLoading.value = true
  try {
    const params: Record<string, string> = {}
    if (selectedMarket.value) params.market = selectedMarket.value
    const res = await api.get('/pm/competitors/export', {
      params,
      responseType: 'blob',
    })
    const filename = `竞品数据${selectedMarket.value ? '_' + selectedMarket.value : ''}.xlsx`
    const url = URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e: unknown) {
    const msg = e && typeof e === 'object' && 'response' in e ? (e as any).response?.data?.detail : null
    ElMessage.error(msg || '导出失败，请确认后端API可用')
  } finally {
    exportLoading.value = false
  }
}
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════════════
   Claude 暖纸色风格
   ═══════════════════════════════════════════════════════════════════ */
.competitor-standalone {
  --c-bg-page: #f5f4ed;
  --c-bg-card: #fffdf7;
  --c-accent: #d97757;
  --c-text: #4a3f35;
  --c-text-muted: #8c8279;
  --c-border: #e5dfd3;
  --c-danger: #e74c3c;
  --c-warning: #e6a23c;
  --c-success: #67c23a;

  min-height: calc(100vh - 80px);
  padding: 24px 28px;
  background: var(--c-bg-page);
  color: var(--c-text);
}
.page-header { margin-bottom: 20px; }
.page-header h2 { margin: 0 0 4px; font-size: 22px; font-weight: 700; color: var(--c-text); }
.page-desc { margin: 0; font-size: 13px; color: var(--c-text-muted); }

/* ── 筛选栏 ────────────────────────────────────────────────────── */
.filters-bar {
  display: flex; gap: 20px; margin-bottom: 18px; flex-wrap: wrap;
  align-items: flex-end;
}
.filter-item {
  display: flex; flex-direction: column; gap: 4px;
}
.filter-item label {
  font-size: 12px; font-weight: 600; color: var(--c-text-muted);
  text-transform: uppercase; letter-spacing: 0.5px;
}
.filter-item :deep(.el-select) { width: 180px; }
.filter-actions { margin-left: auto; }

/* ── 统计卡片 ──────────────────────────────────────────────────── */
.stats-row { display: flex; gap: 16px; margin-bottom: 18px; }
.stat-card {
  background: var(--c-bg-card); border: 1px solid var(--c-border);
  border-radius: 8px; padding: 14px 24px; min-width: 120px; text-align: center;
}
.stat-incomplete { border-color: var(--c-warning); }
.stat-label { font-size: 12px; color: var(--c-text-muted); margin-bottom: 4px; }
.stat-value { font-size: 26px; font-weight: 700; color: var(--c-accent); }

/* ── 工具栏 ────────────────────────────────────────────────────── */
.toolbar-row {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 14px;
}
.toolbar-title { font-size: 14px; font-weight: 600; color: var(--c-text); }

/* ── 竞品卡片列表 ──────────────────────────────────────────────── */
.competitor-cards { display: flex; flex-direction: column; gap: 12px; }
.competitor-card {
  background: var(--c-bg-card); border: 1px solid var(--c-border);
  border-radius: 10px; padding: 16px;
}
.competitor-card.card-incomplete { border-left: 4px solid var(--c-warning); }
.card-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 12px; padding-bottom: 10px;
  border-bottom: 1px solid var(--c-border);
  gap: 10px;
}
.card-brand-section { display: flex; align-items: center; gap: 10px; }
.card-brand { font-size: 16px; font-weight: 700; color: var(--c-text); }
.card-model { font-size: 14px; color: var(--c-text-muted); }
.card-actions { display: flex; gap: 8px; }
.card-params {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 8px 16px;
}
.param-row {
  display: flex; flex-direction: column; gap: 2px;
}
.param-label { font-size: 11px; color: var(--c-text-muted); }
.param-value { font-size: 14px; font-weight: 600; color: var(--c-text); }
.param-value.param-missing { color: var(--c-danger); font-style: italic; }

/* ── 生成本品策划栏 ─────────────────────────────────────────────── */
.generate-plan-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  margin-bottom: 14px;
  background: #f0f9eb;
  border: 1px solid #e1f3d8;
  border-radius: 8px;
}
.generate-plan-hint {
  font-size: 14px;
  font-weight: 600;
  color: #67c23a;
}

/* ── 对标对比表 ────────────────────────────────────────────────── */
.benchmark-section { margin-top: 24px; }
.table-card {
  background: var(--c-bg-card); border: 1px solid var(--c-border);
  border-radius: 10px; padding: 16px; overflow-x: auto;
}
.bench-table { font-size: 13px; }
.bench-table :deep(.el-table__body tr:hover > td) { background: #fdfaf3 !important; }
.cell-value { font-variant-numeric: tabular-nums; color: var(--c-text); }

/* ── 图表区 ────────────────────────────────────────────────────── */
.chart-section { margin-top: 24px; }
.chart-card {
  background: var(--c-bg-card);
  border: 1px solid var(--c-border);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 8px;
}

/* ── 加载/空状态 ────────────────────────────────────────────────── */
.loading-wrap { text-align: center; padding: 48px 0; color: var(--c-text-muted); }
.loading-wrap p { margin-top: 10px; font-size: 13px; }

/* ── Select 下拉面板暖色 ────────────────────────────────────────── */
:deep(.el-select-dropdown__item.selected) { color: var(--c-accent); font-weight: 600; }
:deep(.el-select-dropdown__item:hover) { background: #fdf6ee; }
:deep(.el-empty__description p) { color: var(--c-text-muted); }

/* ── 详情抽屉 ────────────────────────────────────────────────────── */
.detail-params {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 20px;
}
.detail-param-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.detail-param-label {
  font-size: 11px;
  color: var(--c-text-muted);
}
.detail-param-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text);
}
.detail-param-value.param-missing {
  color: var(--c-danger);
  font-style: italic;
}

/* ── 历史时间线 ──────────────────────────────────────────────────── */
.history-timeline {
  padding: 4px 0;
}
.timeline-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.timeline-user {
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text);
}
.timeline-fields {
  margin: 6px 0;
  padding: 8px 10px;
  background: #faf8f3;
  border-radius: 6px;
  border: 1px solid var(--c-border);
}
.changed-field-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 3px 0;
}
.changed-field-row + .changed-field-row {
  border-top: 1px dashed var(--c-border);
}
.field-name {
  font-weight: 600;
  color: var(--c-text);
  min-width: 80px;
}
.field-old {
  color: var(--c-danger);
  text-decoration: line-through;
  font-size: 12px;
}
.field-new {
  color: var(--c-success);
  font-weight: 600;
  font-size: 12px;
}
.timeline-no-change {
  font-size: 12px;
  color: var(--c-text-muted);
  font-style: italic;
}

/* ── 版本快照预览 ────────────────────────────────────────────────── */
.version-preview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 16px;
}
.preview-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.preview-label {
  font-size: 11px;
  color: var(--c-text-muted);
}
.preview-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text);
}
/* ── 外观图片 ────────────────────────────────────────────────────── */
.card-thumb {
  width: 60px;
  height: 60px;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  flex-shrink: 0;
  border: 1px solid var(--c-border);
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
}
.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.detail-images-section {
  grid-column: 1 / -1;
  margin-bottom: 8px;
}
.detail-section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text);
  margin-bottom: 8px;
}
.detail-images-grid {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.detail-image-item {
  width: 180px;
  text-align: center;
}
.detail-image {
  width: 180px;
  height: 180px;
  border-radius: 6px;
  border: 1px solid var(--c-border);
  background: #f5f5f5;
}
.detail-image-label {
  font-size: 11px;
  color: var(--c-text-muted);
  margin-top: 4px;
}
.image-urls-editor {
  padding: 0 8px;
}
.image-url-row {
  display: flex;
  align-items: center;
  margin-bottom: 6px;
  gap: 0;
}
.preview-empty {
  text-align: center;
  padding: 32px 0;
  color: var(--c-text-muted);
}
</style>
