<template>
  <div class="team-section">
    <!-- 项目类型选择（与Tab1 dev_category同步） -->
    <div class="team-toolbar">
      <el-form-item label="项目类型" label-width="80px" size="small" style="margin-bottom:0">
        <el-select :model-value="projectForm.dev_category || ''" placeholder="选择项目类型加载角色模板" clearable @change="onProjectTypeChange" style="width:180px">
          <el-option label="全新开发" value="全新开发" />
          <el-option label="派生" value="派生" />
          <el-option label="降本优化" value="降本优化" />
        </el-select>
      </el-form-item>
      <el-button type="primary" size="small" @click="addTeamRow">添加成员</el-button>
      <span class="team-hint">选择项目类型自动加载预设角色模板</span>
    </div>

    <!-- 团队摘要面板 -->
    <div class="team-summary" v-if="teamTable.length > 0">
      <el-tag size="small" type="info">总角色: {{ teamSummary.totalRoles }}</el-tag>
      <el-tag size="small" type="info">总人数: {{ teamSummary.totalSlots }}</el-tag>
      <el-tag size="small" :type="teamSummary.unfilled === 0 ? 'success' : 'warning'">已分配: {{ teamSummary.filled }}</el-tag>
      <el-tag size="small" :type="teamSummary.unfilled > 0 ? 'danger' : 'success'">未分配: {{ teamSummary.unfilled }}</el-tag>
      <span class="team-summary-roles">
        <span v-for="sr in teamSummary.roleSummaries" :key="sr.role" class="summary-role-item">
          {{ sr.role }} {{ sr.headcount }}
          <span v-if="sr.filled === sr.headcount">✅</span>
          <span v-else>⚠{{ sr.filled }}/{{ sr.headcount }}</span>
        </span>
      </span>
    </div>

    <el-table :data="teamTable" border size="small" class="section-table" row-key="seq">
      <!-- 序号 -->
      <el-table-column label="序号" width="55" align="center">
        <template #default="{ $index }">{{ $index + 1 }}</template>
      </el-table-column>
      <!-- 角色 -->
      <el-table-column width="140">
        <template #header>
          角色
          <el-tooltip content="选择项目类型后自动加载预设角色模板，可自行调整人数和分配人员。14种标准角色覆盖研发全流程" placement="top">
            <el-icon style="margin-left:4px;cursor:help;color:#909399;font-size:13px"><QuestionFilled /></el-icon>
          </el-tooltip>
        </template>
        <template #default="{ row, $index }">
          <el-select v-model="row.role" size="small" placeholder="选择角色" @change="onTeamRoleChange($index)" style="width:100%">
            <el-option v-for="r in teamRoles" :key="r.value" :label="r.label" :value="r.value" />
          </el-select>
        </template>
      </el-table-column>
      <!-- 人数 -->
      <el-table-column label="人数" width="65" align="center">
        <template #default="{ row, $index }">
          <el-input-number v-model="row.headcount" :min="1" :max="10" size="small" controls-position="right" @change="onHeadcountChange($index)" style="width:60px" />
        </template>
      </el-table-column>
      <!-- 姓名（支持槽位展开） -->
      <el-table-column label="姓名" min-width="200">
        <template #default="{ row, $index }">
          <!-- headcount=1: 直接显示 -->
          <template v-if="row.headcount <= 1">
            <el-select v-model="row.user_id" size="small" placeholder="选择人员" filterable @change="onTeamUserChange($index, 0)" style="width:100%">
              <el-option
                v-for="u in getUsersByRole(row.role)"
                :key="u.id"
                :label="getUserOptionLabel(u)"
                :value="u.id"
              >
                <div class="user-option">
                  <span>{{ u.full_name || u.username }}</span>
                  <span v-if="getWorkloadBadge(u.id)" class="workload-badge" :style="{color: getWorkloadBadge(u.id)?.color}">
                    {{ getWorkloadBadge(u.id)?.text }}
                  </span>
                </div>
              </el-option>
            </el-select>
          </template>
          <!-- headcount>1: 弹出槽位编辑 -->
          <template v-else>
            <el-popover placement="bottom" :width="320" trigger="click">
              <template #reference>
                <el-tag
                  :type="getSlotFillStatus(row) === 'full' ? 'success' : getSlotFillStatus(row) === 'partial' ? 'warning' : 'info'"
                  style="cursor:pointer"
                >
                  {{ getSlotSummary(row) }}
                </el-tag>
              </template>
              <div class="slot-editor">
                <div v-for="(slot, si) in row.slots" :key="slot.slot_id" class="slot-row">
                  <span class="slot-label">槽{{ slot.slot_id }}</span>
                  <el-select v-model="slot.user_id" size="small" placeholder="选择人员" filterable @change="onSlotUserChange($index, si)" style="width:180px">
                    <el-option
                      v-for="u in getUsersByRole(row.role)"
                      :key="u.id"
                      :label="getUserOptionLabel(u)"
                      :value="u.id"
                    >
                      <div class="user-option">
                        <span>{{ u.full_name || u.username }}</span>
                        <span v-if="getWorkloadBadge(u.id)" class="workload-badge" :style="{color: getWorkloadBadge(u.id)?.color}">
                          {{ getWorkloadBadge(u.id)?.text }}
                        </span>
                      </div>
                    </el-option>
                  </el-select>
                  <span v-if="slot.department" class="slot-dept">{{ slot.department }}</span>
                </div>
              </div>
            </el-popover>
          </template>
        </template>
      </el-table-column>
      <!-- 部门 -->
      <el-table-column label="部门" width="120">
        <template #default="{ row }">
          <el-tooltip
            v-if="row._departmentFailed && !row.department"
            content="该用户未设置部门信息，请手动填写"
            placement="top"
            :disabled="!row._departmentFailed"
          >
            <el-input v-model="row.department" size="small" :disabled="!row._departmentFailed && !row._departmentManual" placeholder="自动填充" />
          </el-tooltip>
          <el-input v-else v-model="row.department" size="small" :disabled="!row._departmentManual" placeholder="自动填充" />
        </template>
      </el-table-column>
      <!-- 上级（汇报关系） -->
      <el-table-column label="上级" width="140">
        <template #default="{ row, $index }">
          <el-select v-model="row.superior_id" size="small" placeholder="选择上级" clearable filterable style="width:100%">
            <el-option
              v-for="s in getSuperiorOptions($index)"
              :key="s.id"
              :label="s.label"
              :value="s.id"
            />
          </el-select>
        </template>
      </el-table-column>
      <!-- 核心职责 -->
      <el-table-column label="核心职责" min-width="180">
        <template #default="{ row }">
          <el-input v-model="row.responsibility" size="small" placeholder="核心职责描述（可从模板自动填充）" />
        </template>
      </el-table-column>
      <!-- 操作 -->
      <el-table-column label="操作" width="70">
        <template #default="{ $index }">
          <el-button link type="danger" size="small" @click="removeTeamRow($index)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface TeamSlot {
  slot_id: number
  user_id: number | null
  full_name: string
  department: string
}
interface TeamMemberRow {
  role: string
  headcount: number
  slots: TeamSlot[]
  user_id: number | null
  full_name: string
  department: string
  responsibility: string
  superior_id: number | null
  seq: number
  _departmentManual?: boolean
  _departmentFailed?: boolean
}
interface TeamRole { label: string; value: string; sys_role: string }
interface UserInfo { id: number; username: string; full_name: string; department: string; position: string; role: string; job_title?: string }
interface RoleMapping { project_role: string; sys_roles: string[] }
interface UserWorkload { user_id: number; project_count: number; workload_pct: number }

const props = defineProps<{
  tabStatus: Record<string, { valid: boolean }>
  teamTable: TeamMemberRow[]
  projectForm: Record<string, any>
  teamRoles: TeamRole[]
  allTeamUsers: UserInfo[]
  roleMappings: RoleMapping[]
  userWorkloads: UserWorkload[]
}>()

const emit = defineEmits<{
  'project-type-change': [val: string]
}>()

// 团队摘要
const teamSummary = computed(() => {
  const totalRoles = props.teamTable.length
  let totalSlots = 0
  let filled = 0
  const roleSummaries: { role: string; headcount: number; filled: number }[] = []

  for (const row of props.teamTable) {
    const hc = row.headcount || 1
    totalSlots += hc
    let rowFilled = 0
    if (hc <= 1) {
      if (row.user_id != null) rowFilled = 1
    } else {
      rowFilled = row.slots.filter(s => s.user_id != null).length
    }
    filled += rowFilled
    roleSummaries.push({ role: row.role, headcount: hc, filled: rowFilled })
  }
  return {
    totalRoles,
    totalSlots,
    filled,
    unfilled: totalSlots - filled,
    roleSummaries,
  }
})

// Helper functions
function getWorkloadInfo(userId: number): UserWorkload | undefined {
  return props.userWorkloads.find(w => w.user_id === userId)
}

function getUsersByRole(role: string): UserInfo[] {
  if (!role) return props.allTeamUsers
  const mapping = props.roleMappings.find(m => m.project_role === role)
  if (mapping && mapping.sys_roles.length > 0) {
    return props.allTeamUsers.filter(u => {
      const userRole = u.role || ''
      const userTitle = u.job_title || ''
      return mapping.sys_roles.some(sr =>
        userRole === sr || userTitle.includes(sr) || userRole.includes(sr)
      )
    })
  }
  const roleMap: Record<string, string> = {}
  props.teamRoles.forEach(r => { roleMap[r.value] = r.sys_role })
  const sysRole = roleMap[role]
  if (!sysRole) return props.allTeamUsers
  return props.allTeamUsers.filter(u => u.role === sysRole)
}

function getUserOptionLabel(u: UserInfo): string {
  const wl = getWorkloadInfo(u.id)
  if (wl) {
    return `${u.full_name || u.username} · ${wl.project_count}个项目 · 负载${wl.workload_pct}%`
  }
  return u.full_name || u.username
}

function getWorkloadBadge(userId: number): { text: string; color: string } | null {
  const wl = getWorkloadInfo(userId)
  if (!wl) return null
  const pct = wl.workload_pct
  let color = '#67c23a'
  if (pct >= 80) color = '#f56c6c'
  else if (pct >= 50) color = '#e6a23c'
  return { text: `负载${pct}%`, color }
}

function getSlotFillStatus(row: TeamMemberRow): 'full' | 'partial' | 'empty' {
  if (row.headcount <= 1) {
    return row.user_id != null ? 'full' : 'empty'
  }
  const filled = row.slots.filter(s => s.user_id != null).length
  if (filled === row.headcount) return 'full'
  if (filled > 0) return 'partial'
  return 'empty'
}

function getSlotSummary(row: TeamMemberRow): string {
  if (row.headcount <= 1) {
    return row.full_name || '未分配'
  }
  const filled = row.slots.filter(s => s.user_id != null).length
  const names = row.slots.filter(s => s.full_name).map(s => s.full_name).join(', ')
  return names || `${filled}/${row.headcount} 已分配`
}

function getSuperiorOptions(excludeIndex: number): { id: number; label: string }[] {
  const options: { id: number; label: string }[] = []
  const excludeIds = new Set<number>()

  const row = props.teamTable[excludeIndex]
  if (row) {
    if (row.headcount <= 1) {
      if (row.user_id != null) excludeIds.add(row.user_id)
    } else {
      row.slots.forEach(s => { if (s.user_id != null) excludeIds.add(s.user_id) })
    }
  }

  for (const tr of props.teamTable) {
    if (tr.headcount <= 1) {
      if (tr.user_id != null && !excludeIds.has(tr.user_id)) {
        options.push({ id: tr.user_id, label: `${tr.role}: ${tr.full_name || '未命名'}` })
      }
    } else {
      tr.slots.forEach(s => {
        if (s.user_id != null && !excludeIds.has(s.user_id)) {
          options.push({ id: s.user_id, label: `${tr.role}: ${s.full_name || '未命名'}` })
        }
      })
    }
  }
  return options
}

function createEmptySlot(slotId: number): TeamSlot {
  return { slot_id: slotId, user_id: null, full_name: '', department: '' }
}

function createTeamRow(role: string, headcount: number, responsibility: string, seq: number): TeamMemberRow {
  const slots: TeamSlot[] = []
  for (let i = 1; i <= headcount; i++) {
    slots.push(createEmptySlot(i))
  }
  return {
    role,
    headcount,
    slots,
    user_id: headcount === 1 ? null : null,
    full_name: '',
    department: '',
    responsibility,
    superior_id: null,
    seq,
    _departmentManual: false,
    _departmentFailed: false,
  }
}

// Event handlers
function onProjectTypeChange(projectType: string) {
  props.projectForm.dev_category = projectType
  emit('project-type-change', projectType)
}

function addTeamRow() {
  const seq = props.teamTable.length > 0 ? Math.max(...props.teamTable.map(r => r.seq || 0)) + 1 : 1
  props.teamTable.push(createTeamRow('', 1, '', seq))
}

function removeTeamRow(index: number) {
  props.teamTable.splice(index, 1)
}

function onTeamRoleChange(index: number) {
  const row = props.teamTable[index]
  if (!row) return
  row.user_id = null
  row.full_name = ''
  row.department = ''
  row._departmentManual = false
  row._departmentFailed = false
  row.slots.forEach(s => { s.user_id = null; s.full_name = ''; s.department = '' })
}

function onHeadcountChange(index: number) {
  const row = props.teamTable[index]
  if (!row) return
  const newHc = row.headcount || 1
  while (row.slots.length < newHc) {
    row.slots.push(createEmptySlot(row.slots.length + 1))
  }
  while (row.slots.length > newHc) {
    row.slots.pop()
  }
  if (newHc === 1 && row.slots.length > 0) {
    row.user_id = row.slots[0].user_id
    row.full_name = row.slots[0].full_name
    row.department = row.slots[0].department
  } else {
    row.user_id = null
    row.full_name = ''
  }
}

function onTeamUserChange(index: number, _slotIndex: number = 0) {
  const row = props.teamTable[index]
  if (!row) return
  if (row.headcount <= 1) {
    const user = props.allTeamUsers.find(u => u.id === row.user_id)
    if (user) {
      row.full_name = user.full_name || user.username
      if (user.department) {
        row.department = user.department
        row._departmentFailed = false
        row._departmentManual = false
      } else {
        row.department = ''
        row._departmentFailed = true
        row._departmentManual = true
      }
    }
  }
}

function onSlotUserChange(rowIndex: number, slotIndex: number) {
  const row = props.teamTable[rowIndex]
  if (!row || !row.slots[slotIndex]) return
  const slot = row.slots[slotIndex]
  const user = props.allTeamUsers.find(u => u.id === slot.user_id)
  if (user) {
    slot.full_name = user.full_name || user.username
    slot.department = user.department || ''
  }
  if (row.headcount === 1 && row.slots.length > 0) {
    row.user_id = row.slots[0].user_id
    row.full_name = row.slots[0].full_name
    row.department = row.slots[0].department
  }
  if (row.headcount > 1) {
    const depts = row.slots.filter(s => s.department).map(s => s.department)
    row.department = [...new Set(depts)].join('/')
    row._departmentFailed = depts.length < row.slots.length
  }
}
</script>
