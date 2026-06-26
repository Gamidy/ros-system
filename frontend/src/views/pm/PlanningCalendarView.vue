<template>
  <div class="planning-calendar-view">
    <div class="page-header">
      <h2>🗓️ 年度规划日历</h2>
      <el-button type="primary" @click="$router.push('/pm-workspace')">← 返回工作台</el-button>
    </div>
    <el-card shadow="never">
      <p style="text-align:center;padding:60px 0;font-size:16px;color:#909399">
        年度规划日历功能正在独立部署中，请稍候...
      </p>
    </el-card>
  </div>
</template>

<style scoped>
.planning-calendar-view {
  padding: 0;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}
</style>
