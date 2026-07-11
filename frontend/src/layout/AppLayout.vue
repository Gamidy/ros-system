<template>
  <el-container class="layout">
    <el-aside :width="collapsed ? '64px' : '200px'" class="aside">
      <div class="logo" @click="$router.push('/dashboard')">
        <span v-if="!collapsed">PLM 系统</span><span v-else>P</span>
      </div>
      <el-menu :default-active="$route.path" :collapse="collapsed" router background-color="#001529" text-color="#fff" active-text-color="#ffd04b">
        <el-menu-item index="/dashboard"><el-icon><HomeFilled /></el-icon><span>驾驶舱</span></el-menu-item>
        <el-menu-item index="/platforms"><el-icon><Platform /></el-icon><span>产品平台</span></el-menu-item>
        <el-menu-item index="/models"><el-icon><Goods /></el-icon><span>产品型号</span></el-menu-item>
        <el-menu-item index="/materials"><el-icon><Box /></el-icon><span>物料管理</span></el-menu-item>
        <el-menu-item index="/bom"><el-icon><Connection /></el-icon><span>BOM管理</span></el-menu-item>
        <el-menu-item index="/projects"><el-icon><Folder /></el-icon><span>项目管理</span></el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <el-button text @click="collapsed = !collapsed"><el-icon><Expand v-if="collapsed" /><Fold v-else /></el-icon></el-button>
        <el-breadcrumb separator="/"><el-breadcrumb-item to="/dashboard">首页</el-breadcrumb-item>
          <el-breadcrumb-item v-if="$route.meta.title">{{ $route.meta.title }}</el-breadcrumb-item>
        </el-breadcrumb>
        <div style="flex:1" />
        <span>{{ auth.user?.username }}</span>
        <el-button text @click="handleLogout">退出</el-button>
      </el-header>
      <el-main><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore()
const router = useRouter()
const collapsed = ref(false)
function handleLogout() { auth.logout(); router.push('/login') }
</script>

<style scoped>
.layout { height: 100vh; }
.aside { background: #001529; overflow: hidden; }
.logo { height: 50px; display: flex; align-items: center; justify-content: center; color: #fff; font-weight: bold; cursor: pointer; }
.header { display: flex; align-items: center; gap: 12px; background: #fff; border-bottom: 1px solid #eee; }
</style>
