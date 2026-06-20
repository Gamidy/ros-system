<template>
  <el-container class="layout-container">
    <el-aside :width="isCollapse ? '64px' : '220px'" class="layout-aside">
      <div class="logo" @click="router.push('/dashboard')">
        <span class="logo-text" v-show="!isCollapse">ROS 系统</span>
        <span class="logo-mini" v-show="isCollapse">R</span>
      </div>
      <el-menu
        :default-active="route.path"
        :collapse="isCollapse"
        :router="true"
        background-color="#001529"
        text-color="#ffffffb3"
        active-text-color="#fff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Monitor /></el-icon>
          <template #title>驾驶舱</template>
        </el-menu-item>
        <el-menu-item index="/products">
          <el-icon><Goods /></el-icon>
          <template #title>产品主线</template>
        </el-menu-item>
        <el-menu-item index="/bom">
          <el-icon><List /></el-icon>
          <template #title>BOM物料管理</template>
        </el-menu-item>
        <el-menu-item index="/projects">
          <el-icon><Folder /></el-icon>
          <template #title>项目管理</template>
        </el-menu-item>
        <el-menu-item index="/tests">
          <el-icon><Document /></el-icon>
          <template #title>实验与测试</template>
        </el-menu-item>
        <el-menu-item index="/alerts">
          <el-icon><WarningFilled /></el-icon>
          <template #title>预警体系</template>
        </el-menu-item>
        <el-menu-item index="/certifications">
          <el-icon><Stamp /></el-icon>
          <template #title>认证管理</template>
        </el-menu-item>
        <el-menu-item index="/prototypes">
          <el-icon><Cpu /></el-icon>
          <template #title>样机管理</template>
        </el-menu-item>
        <el-menu-item index="/quality">
          <el-icon><WarnTriangleFilled /></el-icon>
          <template #title>质量问题</template>
        </el-menu-item>
        <el-menu-item index="/changes">
          <el-icon><Refresh /></el-icon>
          <template #title>变更管理</template>
        </el-menu-item>
        <!-- 审批管理（带红点） -->
        <el-menu-item index="/approvals">
          <el-icon><DocumentChecked /></el-icon>
          <template #title>
            <span style="display: flex; align-items: center; gap: 6px;">
              审批管理
              <el-badge v-if="pendingCount > 0" :value="pendingCount" :max="99" class="approval-badge" />
            </span>
          </template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="layout-header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse" :size="20">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="route.meta.title">{{ route.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-dropdown trigger="click">
            <span class="user-info">
              <el-avatar :size="28" icon="UserFilled" />
              <span class="username">{{ user?.username || '用户' }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import api from '../api'

const route = useRoute()
const router = useRouter()
const isCollapse = ref(false)
const user = ref<{ username: string; role?: string } | null>(null)
const pendingCount = ref(0)

async function fetchPendingCount() {
  try {
    const res = await api.get('/dashboard/summary')
    const count = res.data?.pending_approvals ?? 0
    pendingCount.value = count
    return count
  } catch {
    return 0
  }
}

onMounted(async () => {
  try {
    const res = await api.get('/auth/me')
    user.value = res.data
    
    // 获取待审批数
    const count = await fetchPendingCount()
    
    // 如果有待审批且角色是管理员/研发总监，弹出通知
    if (count > 0 && (user.value?.role === 'admin' || user.value?.role === 'rd_director')) {
      ElNotification({
        title: '待审批提醒',
        message: `您有 ${count} 条待审批请求，请及时处理`,
        type: 'warning',
        duration: 8000,
      })
    }
  } catch {
    handleLogout()
  }
  
  // 监听审批状态变化（从审批页面发出的自定义事件）
  window.addEventListener('approval-updated', () => {
    fetchPendingCount()
  })
})

function handleLogout() {
  localStorage.removeItem('token')
  ElMessage.info('已退出')
  router.push('/login')
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}
.layout-aside {
  background: #001529;
  transition: width 0.3s;
  overflow: hidden;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  cursor: pointer;
  font-weight: bold;
  font-size: 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 16px;
  height: 60px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.collapse-btn {
  cursor: pointer;
}
.header-right {
  display: flex;
  align-items: center;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.layout-main {
  background: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}
.approval-badge :deep(.el-badge__content) {
  background-color: #f56c6c;
  border: none;
  font-size: 11px;
  height: 16px;
  line-height: 16px;
  padding: 0 5px;
}
</style>
