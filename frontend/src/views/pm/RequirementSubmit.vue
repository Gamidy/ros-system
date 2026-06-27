<template>
  <div class="requirement-submit">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>需求录入</span>
        </div>
      </template>

      <!-- 提交成功公告 -->
      <el-result v-if="submitted" icon="success" title="需求已提交" sub-title="需求已提交，PM将审核">
        <template #extra>
          <el-button type="primary" @click="goHome">返回首页</el-button>
        </template>
      </el-result>

      <!-- 需求表单 -->
      <el-form
        v-else
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="110px"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="市场" prop="market_id">
          <el-select v-model="form.market_id" placeholder="请选择市场" filterable style="width:100%">
            <el-option v-for="m in markets" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="客户" prop="customer">
              <el-input v-model="form.customer" placeholder="请输入客户名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="联系人" prop="contact">
              <el-input v-model="form.contact" placeholder="请输入联系人" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="产品类型" prop="product_type">
              <el-select v-model="form.product_type" placeholder="请选择产品类型" style="width:100%">
                <el-option label="壁挂分体机" value="壁挂分体机" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标冷量" prop="target_capacity">
              <el-input v-model="form.target_capacity" placeholder="如 3.5kW">
                <template #suffix>kW</template>
              </el-input>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="目标价格" prop="target_price">
              <el-input-number v-model="form.target_price" :min="0" :precision="2" style="width:100%" placeholder="元" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="能效标准" prop="energy_standard">
              <el-select v-model="form.energy_standard" placeholder="请选择能效标准" style="width:100%">
                <el-option label="EER" value="EER" />
                <el-option label="COP" value="COP" />
                <el-option label="APF" value="APF" />
                <el-option label="CSPF" value="CSPF" />
                <el-option label="SEER" value="SEER" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="年销量预测" prop="annual_forecast">
          <el-input-number v-model="form.annual_forecast" :min="0" :step="100" style="width:100%" placeholder="台" />
        </el-form-item>

        <el-form-item label="补充说明" prop="notes">
          <el-input v-model="form.notes" type="textarea" :rows="4" placeholder="补充说明（可选）" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading">提交</el-button>
          <el-button @click="$router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { type FormInstance, type FormRules } from 'element-plus'
import { submitRequirement, fetchAllMarkets } from '../../api/productPlan'

const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)
const submitted = ref(false)

interface MarketItem {
  id: number
  name: string
  code?: string
}
const markets = ref<MarketItem[]>([])

interface RequirementForm {
  market_id: number | null
  customer: string
  contact: string
  product_type: string
  target_capacity: string
  target_price: number | null
  energy_standard: string
  annual_forecast: number | null
  notes: string
}

const form = reactive<RequirementForm>({
  market_id: null,
  customer: '',
  contact: '',
  product_type: '',
  target_capacity: '',
  target_price: null,
  energy_standard: '',
  annual_forecast: null,
  notes: '',
})

const rules: FormRules = {
  market_id: [{ required: true, message: '请选择市场', trigger: 'change' }],
  customer: [{ required: true, message: '请输入客户名称', trigger: 'blur' }],
  contact: [{ required: true, message: '请输入联系人', trigger: 'blur' }],
  product_type: [{ required: true, message: '请选择产品类型', trigger: 'change' }],
  target_price: [{ required: true, message: '请输入目标价格', trigger: 'blur' }],
  energy_standard: [{ required: true, message: '请选择能效标准', trigger: 'change' }],
}

onMounted(async () => {
  try {
    const res = await fetchAllMarkets()
    markets.value = res.data || []
  } catch {
    // 静默失败
  }
})

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await submitRequirement({
      market_id: form.market_id,
      customer: form.customer,
      contact: form.contact,
      product_type: form.product_type,
      target_capacity: form.target_capacity,
      target_price: form.target_price,
      energy_standard: form.energy_standard,
      annual_forecast: form.annual_forecast,
      notes: form.notes,
    })
    submitted.value = true
  } catch {
    // 错误由 axios 拦截器处理
  } finally {
    loading.value = false
  }
}

function goHome() {
  router.push('/')
}
</script>

<style scoped>
.requirement-submit {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}
.card-header {
  font-size: 16px;
  font-weight: 600;
}
</style>
