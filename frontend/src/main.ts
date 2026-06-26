import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles/claude-theme.css'  // Claude风格主题覆盖
import './styles/responsive.css'     // 响应式CSS变量 (兼容旧引用)
import './styles/responsive.scss'    // 响应式SCSS工具 (断点变量/混入/覆盖样式)
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'

const app = createApp(App)

// Register all element-plus icons
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

// ── 全局指令: v-click-feedback — 点击微缩放触感反馈 ──
app.directive('click-feedback', {
  mounted(el: HTMLElement) {
    el.style.cursor = 'pointer'
    el.style.willChange = 'transform'
    const scaleDown = () => {
      el.style.transition = 'transform 0.12s cubic-bezier(0.25, 0.46, 0.45, 0.94)'
      el.style.transform = 'scale(0.96)'
    }
    const scaleUp = () => {
      el.style.transform = 'scale(1)'
    }
    el.addEventListener('pointerdown', scaleDown)
    el.addEventListener('pointerup', scaleUp)
    el.addEventListener('pointerleave', scaleUp)
  },
  unmounted(el: HTMLElement) {
    // Remove inline styles on unmount (cleanup happens automatically via event removal)
    el.style.transform = ''
    el.style.transition = ''
    el.style.cursor = ''
    el.style.willChange = ''
  },
})

app.mount('#app')
