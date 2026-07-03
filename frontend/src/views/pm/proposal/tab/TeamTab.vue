<template>
  <div class="team-tab">
    <el-form :model="{}" label-width="100px" size="small">
      <el-form-item label="项目类型">
        <el-select v-model="projectType" placeholder="选择项目类型以加载团队模板" style="width:280px" @change="onProjectTypeChange">
          <el-option v-for="t in ['全新开发','改型','引用','派生']" :key="t" :label="t" :value="t" />
        </el-select>
        <el-button size="small" style="margin-left:8px" @click="loadTeamRoleTemplate(projectType)" :disabled="!projectType">加载模板</el-button>
        <el-button size="small" @click="loadDefaultTeamTemplate" :disabled="loadingTemplate">默认模板</el-button>
      </el-form-item>
    </el-form>

    <el-card shadow="never" class="summary-card" v-if="teamTable.length > 0">
      <div class="summary-title">👥 团队摘要</div>
      <div class="summary-stats">
        <el-tag type="info" size="small">总人数 {{ summary.total }}</el-tag>
        <el-tag type="success" size="small">已分配 {{ summary.assigned }}</el-tag>
        <el-tag type="warning" size="small">未分配 {{ summary.unassigned }}</el-tag>
      </div>
      <div class="summary-roles" v-if="summary.roleStats.length > 0">
        <el-tag v-for="rs in summary.roleStats" :key="rs.role" size="small" effect="plain" :type="rs.assigned > 0 ? 'success' : 'info'" style="margin:2px">
          {{ rs.role }}: {{ rs.assigned }}/{{ rs.total }}
        </el-tag>
      </div>
    </el-card>

    <el-table :data="teamTable" style="width:100%" size="small" max-height="480" v-if="teamTable.length > 0" border>
      <el-table-column label="序号" width="50" prop="seq" />
      <el-table-column label="项目角色" width="130">
        <template #default="{ row, $index }">
          <el-select v-model="row.role_name" filterable allow-create size="small" style="width:120px" @change="() => onRoleChange(row, $index)">
            <el-option v-for="r in roles" :key="r.value" :label="r.label" :value="r.value" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="系统岗位" width="150">
        <template #default="{ row }">
          <el-select v-model="row.sysPosition" filterable clearable size="small" style="width:140px" placeholder="选择/输入">
            <el-option v-for="sp in sysPositions(row.role)" :key="sp" :label="sp" :value="sp" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="人数" width="60">
        <template #default="{ row, $index }">
          <el-input-number v-model="row.headcount" :min="1" :max="10" size="small" controls-position="right" style="width:60px" @change="(v: number) => onHeadcountChange(row, v, $index)" />
        </template>
      </el-table-column>
      <el-table-column label="人员选择" min-width="250">
        <template #default="{ row, $index }">
          <template v-if="row.headcount <= 1">
            <el-select v-model="row.user_id" filterable clearable size="small" style="width:240px" placeholder="选择人员" @change="(v:number|null) => onUserChange(row, v, $index)">
              <el-option v-for="u in userOpts" :key="u.id" :label="u.label" :value="u.id" :disabled="isAssigned(u.id, $index)">
                <span>{{ u.label }}</span>
                <el-tag v-if="u.wl && u.wl.c > 0" :type="u.wl.r >= 80 ? 'danger' : u.wl.r >= 50 ? 'warning' : 'info'" size="small" style="margin-left:6px;float:right">{{ u.wl.c }}项 {{ u.wl.r }}%</el-tag>
              </el-option>
            </el-select>
          </template>
          <div v-else>
            <div v-for="sl in row.slots" :key="sl.slot_id" style="display:flex;align-items:center;gap:4px;margin-bottom:2px">
              <span style="font-size:11px;color:#909399;min-width:18px">#{{ sl.slot_id }}</span>
              <el-select v-model="sl.user_id" filterable clearable size="small" style="width:200px" placeholder="选择人员" @change="(v:number|null) => onSlotChange(row, sl, v, $index)">
                <el-option v-for="u in userOpts" :key="u.id" :label="u.label" :value="u.id" :disabled="isAssignedInRow(row, u.id, sl.slot_id)">
                  <span>{{ u.label }}</span>
                  <el-tag v-if="u.wl && u.wl.c > 0" :type="u.wl.r >= 80 ? 'danger' : u.wl.r >= 50 ? 'warning' : 'info'" size="small" style="margin-left:6px;float:right">{{ u.wl.c }}项 {{ u.wl.r }}%</el-tag>
                </el-option>
              </el-select>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="部门" width="120">
        <template #default="{ row }">
          <template v-if="row.headcount <= 1">{{ row.department }}</template>
          <div v-else><div v-for="sl in row.slots" :key="sl.slot_id" style="font-size:12px;color:#606266">{{ sl.department }}</div></div>
        </template>
      </el-table-column>
      <el-table-column label="核心职责" min-width="180">
        <template #default="{ row }">
          <el-input v-model="row.responsibility" type="textarea" :rows="1" size="small" placeholder="核心职责" @input="emitUpdate" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="70" fixed="right">
        <template #default="{ $index }">
          <el-button type="danger" size="small" link @click="removeRow($index)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="team-actions" v-if="teamTable.length > 0">
      <el-button size="small" type="primary" plain @click="addRow">+ 添加角色</el-button>
    </div>
    <el-empty v-else description="请选择项目类型并加载团队模板" :image-size="80" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../../../api'

interface Slot { slot_id: number; user_id: number | null; full_name: string; department: string }
interface Row {
  role_name: string; sysPosition: string; headcount: number; slots: Slot[]
  user_id: number | null; full_name: string; department: string
  responsibility: string; superior_id: number | null; seq: number
  _deptManual: boolean; _deptFailed: boolean
}
interface TmplItem { role_name: string; headcount: number; responsibility_default: string; seq: number }
interface RoleOpt { label: string; value: string; sys_role: string }
interface WlInfo { user_id: number; username: string; full_name: string; role: string; project_count: number; load_rate: number }
interface UserItem { id: number; username: string; full_name: string; department: string }
interface UOpt { id: number; label: string; department: string; wl: { c: number; r: number } | null }
interface TeamFormData {
  team_members: string
  dev_category?: string
  project_type?: string
}

const props = defineProps<{ data: TeamFormData; projectType?: string }>()
const emit = defineEmits<{ update: [p: Partial<TeamFormData>]; 'leader-change': [id: number | null] }>()

const projectType = ref(props.projectType || '')
const teamTable = reactive<Row[]>([])
const allUsers = ref<UserItem[]>([])
const workloads = ref<WlInfo[]>([])
const roleMappings = ref<Record<string, string[]>>({})
const roles = ref<RoleOpt[]>([])
const loadingTemplate = ref(false)

const userOpts = computed<UOpt[]>(() => {
  const wm = new Map<number, { c: number; r: number }>()
  workloads.value.forEach(w => wm.set(w.user_id, { c: w.project_count, r: w.load_rate }))
  return allUsers.value.map((u: UserItem) => ({
    id: u.id,
    label: `${u.full_name || u.username}${u.department ? ` (${u.department})` : ''}`,
    department: u.department || '',
    wl: wm.get(u.id) || null,
  }))
})

const defaultSysPositions: Record<string, string[]> = {
  '项目经理': ['项目经理','高级项目经理'],
  '结构工程师': ['主任结构工程师','高级结构工程师','结构工程师'],
  '系统工程师': ['主任系统工程师','高级系统工程师','系统工程师'],
  '电控工程师': ['主任电控工程师','高级电控工程师','电控工程师'],
  '电气工程师': ['主任电气工程师','高级电气工程师','电气工程师'],
  '工艺工程师': ['主任工艺工程师','高级工艺工程师','工艺工程师'],
  '采购工程师': ['采购工程师','高级采购工程师'],
  '质量工程师': ['质量工程师','高级质量工程师'],
  'IQC工程师': ['IQC工程师','高级IQC工程师'],
  '测试工程师': ['测试工程师','高级测试工程师'],
  '认证工程师': ['认证工程师','高级认证工程师'],
}

function sysPositions(role: string): string[] {
  return roleMappings.value[role] || defaultSysPositions[role] || [role]
}

function mkSlot(id: number): Slot { return { slot_id: id, user_id: null, full_name: '', department: '' } }
function mkRow(roleName: string, hc: number, resp: string, seq: number): Row {
  const slots: Slot[] = []
  for (let i = 1; i <= hc; i++) slots.push(mkSlot(i))
  return { role_name: roleName, sysPosition: '', headcount: hc, slots, user_id: null, full_name: '', department: '', responsibility: resp, superior_id: null, seq, _deptManual: false, _deptFailed: false }
}

function isAssigned(uid: number, skip: number): boolean {
  return teamTable.some((r, i) => i !== skip && (r.headcount <= 1 ? r.user_id === uid : r.slots.some(s => s.user_id === uid)))
}
function isAssignedInRow(r: Row, uid: number, skipSid: number): boolean {
  return r.slots.some(s => s.slot_id !== skipSid && s.user_id === uid)
}
function syncFromRow(r: Row): void {
  if (r.headcount <= 1 && r.slots.length > 0) { r.user_id = r.slots[0].user_id; r.full_name = r.slots[0].full_name; r.department = r.slots[0].department }
}
function syncToRow(r: Row): void {
  if (r.headcount <= 1 && r.slots.length > 0) { r.slots[0].user_id = r.user_id; r.slots[0].full_name = r.full_name; r.slots[0].department = r.department }
}

const summary = computed(() => {
  let t = 0, a = 0
  const rs = new Map<string, { t: number; a: number }>()
  teamTable.forEach(r => {
    const hc = r.headcount || 1; t += hc
    const ra = hc <= 1 ? (r.user_id != null ? 1 : 0) : r.slots.filter(s => s.user_id != null).length
    a += ra
    const e = rs.get(r.role_name) || { t: 0, a: 0 }; e.t += hc; e.a += ra; rs.set(r.role_name, e)
  })
  return { total: t, assigned: a, unassigned: t - a, roleStats: Array.from(rs.entries()).map(([role, v]) => ({ role, total: v.t, assigned: v.a })) }
})

async function autoDept(uid: number): Promise<string> {
  const u = allUsers.value.find((x: UserItem) => x.id === uid)
  if (u?.department) return u.department
  try { const r = await api.get('/admin/users', { params: { id: uid } }); const arr = r.data?.users || r.data || []; return (Array.isArray(arr) ? arr.find((x: any) => x.id === uid) : arr)?.department || '' }
  catch (e: unknown) { return '' }
}

function syncLeader() {
  const lr = teamTable.find(r => r.role_name === '项目经理' || r.role_name === '项目负责人')
  if (!lr) { emit('leader-change', null); return }
  emit('leader-change', lr.headcount <= 1 ? lr.user_id : (lr.slots[0]?.user_id ?? null))
}

function emitUpdate() { emit('update', { team_members: JSON.stringify(serialize()) }) }

function serialize() {
  return teamTable.map(t => ({
    role_name: t.role_name, sysPosition: t.sysPosition, headcount: t.headcount || 1,
    user_id: t.headcount <= 1 ? t.user_id : null, full_name: t.full_name || '', department: t.department || '',
    responsibility: t.responsibility || '', superior_id: t.superior_id, seq: t.seq || 0,
    slots: t.slots.map(s => ({ slot_id: s.slot_id, user_id: s.user_id, full_name: s.full_name || '', department: s.department || '' })),
  }))
}

function restore(json: string) {
  if (!json) return
  try {
    const arr = JSON.parse(json)
    if (!Array.isArray(arr) || arr.length === 0) return
    teamTable.length = 0
    arr.forEach((item: any) => {
      const r = mkRow(item.role_name || '', item.headcount || 1, item.responsibility || '', item.seq || teamTable.length + 1)
      r.sysPosition = item.sysPosition || ''; r.superior_id = item.superior_id ?? null
      if (item.headcount <= 1 || !item.slots) {
        r.user_id = item.user_id ?? null; r.full_name = item.full_name || ''; r.department = item.department || ''
        if (r.slots[0]) { r.slots[0].user_id = item.user_id ?? null; r.slots[0].full_name = item.full_name || ''; r.slots[0].department = item.department || '' }
      }
      if (item.slots) item.slots.forEach((s: any, si: number) => { if (r.slots[si]) { r.slots[si].user_id = s.user_id ?? null; r.slots[si].full_name = s.full_name || ''; r.slots[si].department = s.department || '' } })
      teamTable.push(r)
    })
  } catch (e: unknown) { /* ignore */ }
}

function onRoleChange(row: Row, _i: number) {
  const sp = sysPositions(row.role_name)
  if (sp.length > 0 && !sp.includes(row.sysPosition)) row.sysPosition = sp[0]
  emitUpdate()
}
function onHeadcountChange(row: Row, n: number, _i: number) {
  const old = row.slots.length
  if (n > old) { for (let i = old + 1; i <= n; i++) row.slots.push(mkSlot(i)) }
  else if (n < old) row.slots.splice(n)
  syncFromRow(row); emitUpdate()
}
async function onUserChange(row: Row, uid: number | null, _i: number) {
  if (uid != null) {
    const u = allUsers.value.find((x: UserItem) => x.id === uid)
    if (u) { row.full_name = u.full_name || u.username; if (!row._deptManual) { row.department = u.department || ''; if (!row.department) { row.department = await autoDept(uid); row._deptFailed = !row.department } } }
  } else { row.full_name = ''; if (!row._deptManual) row.department = '' }
  syncToRow(row); syncLeader(); emitUpdate()
}
async function onSlotChange(row: Row, sl: Slot, uid: number | null, _i: number) {
  if (uid != null) {
    const u = allUsers.value.find((x: UserItem) => x.id === uid)
    if (u) { sl.full_name = u.full_name || u.username; sl.department = u.department || await autoDept(uid) }
  } else { sl.full_name = ''; sl.department = '' }
  syncFromRow(row); syncLeader(); emitUpdate()
}
function addRow() {
  const ns = teamTable.length > 0 ? Math.max(...teamTable.map(r => r.seq || 0)) + 1 : teamTable.length + 1
  teamTable.push(mkRow('', 1, '', ns))
}
function removeRow(i: number) { teamTable.splice(i, 1); syncLeader(); emitUpdate() }

function applyItems(items: TmplItem[]) {
  teamTable.length = 0
  items.sort((a, b) => (a.seq || 0) - (b.seq || 0)).forEach(item => teamTable.push(mkRow(item.role_name, item.headcount || 1, item.responsibility_default || '', item.seq || 0)))
  emitUpdate(); syncLeader()
}

function loadDefaultTeamTemplate() {
  applyItems([
    { role_name: '项目经理', headcount: 1, responsibility_default: '全面负责项目管理', seq: 1 },
    { role_name: '系统工程师', headcount: 2, responsibility_default: '系统方案设计与性能匹配', seq: 2 },
    { role_name: '结构工程师', headcount: 3, responsibility_default: '结构设计与外观设计', seq: 3 },
    { role_name: '电控工程师', headcount: 2, responsibility_default: '硬件电路与软件控制', seq: 4 },
    { role_name: '电气工程师', headcount: 2, responsibility_default: '电气系统与线束设计', seq: 5 },
    { role_name: '工艺工程师', headcount: 1, responsibility_default: '生产工艺规划', seq: 6 },
    { role_name: 'IQC工程师', headcount: 1, responsibility_default: '来料质量控制', seq: 7 },
    { role_name: '采购工程师', headcount: 1, responsibility_default: '零部件采购', seq: 8 },
    { role_name: '项目管理员', headcount: 1, responsibility_default: '项目文档及进度跟踪', seq: 9 },
  ])
}

async function loadTeamRoleTemplate(t: string) {
  if (!t) return
  loadingTemplate.value = true
  try {
    const res = await api.get('/pm/team-role-template', { params: { project_type: t } })
    const items: TmplItem[] = res.data?.items || res.data || []
    if (items.length > 0) { applyItems(items) }
    else { ElMessage.info(`「${t}」暂无预设模板，已加载默认模板`); loadDefaultTeamTemplate() }
  } catch (e: unknown) { ElMessage.warning('模板API不可用，使用默认模板'); if (teamTable.length === 0) loadDefaultTeamTemplate() }
  finally { loadingTemplate.value = false }
}

function onProjectTypeChange(t: string) { emit('update', { dev_category: t }) }

async function fetchRoles() {
  try { const r = await api.get('/kb/team-roles'); roles.value = r.data || [] }
  catch (e: unknown) {
    roles.value = [
      { label: '项目经理', value: '项目经理', sys_role: '' },
      { label: '系统工程师', value: '系统工程师', sys_role: '' },
      { label: '结构工程师', value: '结构工程师', sys_role: '' },
      { label: '电控工程师', value: '电控工程师', sys_role: '' },
      { label: '电气工程师', value: '电气工程师', sys_role: '' },
      { label: '工艺工程师', value: '工艺工程师', sys_role: '' },
      { label: '采购工程师', value: '采购工程师', sys_role: '' },
      { label: '质量工程师', value: '质量工程师', sys_role: '' },
      { label: 'IQC工程师', value: 'IQC工程师', sys_role: '' },
      { label: '项目管理员', value: '项目管理员', sys_role: '' },
      { label: '测试工程师', value: '测试工程师', sys_role: '' },
      { label: '认证工程师', value: '认证工程师', sys_role: '' },
    ]
  }
}
async function fetchUsers() {
  try { const r = await api.get('/kb/team'); allUsers.value = r.data || [] }
  catch (e: unknown) {
    try { const r = await api.get('/admin/users'); allUsers.value = r.data?.users || r.data || [] }
    catch (e: unknown) { /* non-critical */ }
  }
}
async function fetchMappings() {
  try {
    const r = await api.get('/pm/role-mappings')
    const raw: any[] = r.data?.items || r.data || []
    const g = new Map<string, Set<string>>()
    raw.forEach(item => {
      const pr = item.project_role; const sr = item.system_role || item.sys_role
      if (pr && sr) { if (!g.has(pr)) g.set(pr, new Set()); g.get(pr)!.add(sr) }
    })
    const map: Record<string, string[]> = {}
    g.forEach((v, k) => { map[k] = [...v] })
    roleMappings.value = map
  } catch (e: unknown) { /* non-critical */ }
}
async function fetchWorkloads() {
  try { const r = await api.get('/pm/user-workloads'); workloads.value = r.data?.users || r.data?.items || [] }
  catch (e: unknown) { /* non-critical */ }
}

watch(() => props.data?.team_members, (val) => { if (val && teamTable.length === 0) restore(val) }, { immediate: true })

onMounted(async () => {
  await Promise.all([fetchRoles(), fetchUsers(), fetchMappings(), fetchWorkloads()])
  if (props.data?.team_members) restore(props.data.team_members)
  if (projectType.value && teamTable.length === 0) await loadTeamRoleTemplate(projectType.value)
  else if (teamTable.length === 0) loadDefaultTeamTemplate()
})
</script>

<style scoped>
.team-tab { padding: 8px 0; }
.summary-card { margin-bottom: 16px; border-left: 3px solid #409eff; }
.summary-title { font-size: 14px; font-weight: 600; color: #303133; margin-bottom: 8px; }
.summary-stats { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.summary-roles { display: flex; gap: 4px; flex-wrap: wrap; }
.team-actions { margin-top: 12px; display: flex; justify-content: center; }
</style>
