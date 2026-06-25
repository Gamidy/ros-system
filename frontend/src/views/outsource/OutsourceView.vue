<template>
  <el-tabs v-model="activeTab">
    <el-tab-pane label="外协厂商" name="partners">
      <OutsourcePartnerTab />
    </el-tab-pane>
    <el-tab-pane label="外协订单" name="orders">
      <OutsourceOrderTab />
    </el-tab-pane>
    <el-tab-pane label="外协质检" name="quality">
      <OutsourceQualityTab />
    </el-tab-pane>
  </el-tabs>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import OutsourcePartnerTab from './OutsourcePartnerTab.vue'
import OutsourceOrderTab from './OutsourceOrderTab.vue'
import OutsourceQualityTab from './OutsourceQualityTab.vue'

const activeTab = ref('partners')
</script>
