<template>
  <div class="cal-tab">
    <div class="cal-header">
      <el-button size="small" @click="prevMonth">‹ 上月</el-button>
      <span class="cal-title">{{ year }}年{{ month + 1 }}月</span>
      <el-button size="small" @click="nextMonth">下月 ›</el-button>
      <el-button size="small" @click="today" class="today-btn">今天</el-button>
      <span class="task-summary">
        <span class="sm-dot todo" />待办 {{ stats.todo }}
        <span class="sm-dot progress" />进行中 {{ stats.in_progress }}
        <span class="sm-dot done" />完成 {{ stats.done }}
      </span>
    </div>

    <div class="cal-grid">
      <div class="cal-weekday" v-for="wd in weekdays" :key="wd">{{ wd }}</div>
      <div
        v-for="day in calendarDays" :key="day.dateStr"
        class="cal-day"
        :class="{
          'is-today': day.isToday,
          'is-other-month': !day.isCurrentMonth,
          'is-weekend': day.isWeekend,
        }"
      >
        <div class="day-num">{{ day.day }}</div>
        <div class="day-tasks">
          <div
            v-for="t in day.tasks" :key="t.id"
            class="day-task"
            :class="'dt-' + t.status"
            :title="t.title"
          >
            {{ t.title }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const props = defineProps<{ pid: number }>()

const todayDate = new Date()
const year = ref(todayDate.getFullYear())
const month = ref(todayDate.getMonth())
const tasks = ref<any[]>([])

const weekdays = ['一', '二', '三', '四', '五', '六', '日']

const stats = computed(() => ({
  todo: tasks.value.filter(t => t.status === 'todo').length,
  in_progress: tasks.value.filter(t => t.status === 'in_progress').length,
  done: tasks.value.filter(t => t.status === 'done').length,
}))

const calendarDays = computed(() => {
  const firstDay = new Date(year.value, month.value, 1)
  const lastDay = new Date(year.value, month.value + 1, 0)
  // Monday-based week
  let startDow = firstDay.getDay() - 1
  if (startDow < 0) startDow = 6

  const days: any[] = []

  // Previous month padding
  for (let i = startDow - 1; i >= 0; i--) {
    const d = new Date(year.value, month.value, -i)
    days.push(createDay(d, false))
  }

  // Current month
  for (let d = 1; d <= lastDay.getDate(); d++) {
    const dt = new Date(year.value, month.value, d)
    days.push(createDay(dt, true))
  }

  // Next month padding to fill last week
  const remaining = 7 - (days.length % 7)
  if (remaining < 7) {
    for (let i = 1; i <= remaining; i++) {
      const d = new Date(year.value, month.value + 1, i)
      days.push(createDay(d, false))
    }
  }

  return days
})

function createDay(d: Date, isCurrentMonth: boolean) {
  const dateStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  const dayTasks = tasks.value.filter(t => {
    const match = t.due_date === dateStr || t.planned_date === dateStr
    return match
  })
  return {
    dateStr,
    day: d.getDate(),
    isToday: dateStr === `${todayDate.getFullYear()}-${String(todayDate.getMonth() + 1).padStart(2, '0')}-${String(todayDate.getDate()).padStart(2, '0')}`,
    isCurrentMonth,
    isWeekend: d.getDay() === 0 || d.getDay() === 6,
    tasks: dayTasks,
  }
}

function prevMonth() {
  if (month.value === 0) { year.value--; month.value = 11 }
  else month.value--
}

function nextMonth() {
  if (month.value === 11) { year.value++; month.value = 0 }
  else month.value++
}

function today() {
  year.value = todayDate.getFullYear()
  month.value = todayDate.getMonth()
}

async function fetchTasks() {
  try {
    const res = await api.get(`/projects/${props.pid}/tasks`)
    tasks.value = (res.data || []).filter((t: any) => t.planned_date || t.due_date)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载失败')
  }
}

onMounted(fetchTasks)
</script>

<style scoped>
.cal-tab { width: 100%; }
.cal-header {
  display: flex; align-items: center; gap: 8px; margin-bottom: 12px;
  flex-wrap: wrap;
}
.cal-title { font-size: 16px; font-weight: 700; color: #303133; min-width: 120px; text-align: center; }
.today-btn { margin-left: 4px; }
.task-summary { margin-left: auto; font-size: 11px; color: #909399; display: flex; align-items: center; gap: 8px; }
.sm-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; }
.sm-dot.todo { background: #909399; }
.sm-dot.progress { background: #409eff; }
.sm-dot.done { background: #67c23a; }

.cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
  background: #ebeef5;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  overflow: hidden;
}
.cal-weekday {
  background: #f5f7fa;
  padding: 8px;
  text-align: center;
  font-size: 12px;
  font-weight: 600;
  color: #606266;
}
.cal-day {
  background: #fff;
  min-height: 80px;
  padding: 4px;
  transition: background 0.1s;
}
.cal-day:hover { background: #fafafa; }
.cal-day.is-today { background: #e6f7ff; }
.cal-day.is-other-month { background: #fafafa; }
.cal-day.is-other-month .day-num { color: #c0c4cc; }
.cal-day.is-weekend .day-num { color: #f56c6c; }
.cal-day.is-today .day-num { color: #409eff; font-weight: 700; }

.day-num { font-size: 12px; color: #303133; margin-bottom: 4px; }
.day-tasks { display: flex; flex-direction: column; gap: 2px; }
.day-task {
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: default;
}
.dt-todo { background: #f0f0f0; color: #606266; }
.dt-in_progress { background: #d9ecff; color: #1d6bb7; }
.dt-done { background: #e1f3d8; color: #529b2e; text-decoration: line-through; }
.dt-blocked { background: #fde2e2; color: #cd3636; }
</style>
