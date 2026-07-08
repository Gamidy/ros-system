<template>
  <el-tabs v-model="activeTab">
    <el-tab-pane label="检查项模板" name="checklist">
      <DFMChecklistTab ref="checklistRef" />
    </el-tab-pane>
    <el-tab-pane label="分析报告" name="reports">
      <DFMReportTab />
    </el-tab-pane>
  </el-tabs>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import DFMChecklistTab from './DFMChecklistTab.vue'
import DFMReportTab from './DFMReportTab.vue'

const activeTab = ref('checklist')

function onTabChange() {