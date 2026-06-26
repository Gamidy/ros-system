/* ===== PMWorkspace 接口定义 ===== */

export interface PlanningItem {
  id: number
  name: string
  year: string
  description: string
  doc_ref: string
  project_count: number
  projects?: ProjectSummary[]
}

export interface ProjectSummary {
  id: number
  name: string
  status: string
  approval_status?: string
}

export interface ProjectItem {
  id: number
  name: string
  status: string
  project_class: string
  progress: number
  budget?: number
  market_policy?: string
  scene?: string
  linked_product?: string
  target_end_date?: string
  background_basis?: string
  product_type?: string
  target_market?: string
  refrigerant?: string
  main_capacity?: string
  capacity_range?: string
  voltage_freq?: string
  series_name?: string
  energy_rating?: string
  ip_ownership?: string
  project_duration?: string
  dev_category?: string
  project_origin?: string
  start_date?: string
  required_date?: string
  sample_qty?: number
  annual_planning_ref?: string
  annual_planning_id?: number | null
  market_demand_overview?: string
  competitor_analysis?: string
  customer_special_req?: string
  climate_zone?: string
  is_draft?: boolean
  has_outsourcing?: boolean
  customer_name?: string
  cert_requirements?: string
  energy_efficiency_req?: string
  target_price?: string
  customer_requirements?: string
  other_requirements?: string
  program_id?: number | null
  leader_id?: number | null
  overall_goal?: string
  background_basis_raw?: string
  tech_goal?: string
  cost_goal?: string
  sales_goal?: string
  cert_goal?: string
  schedule_goal?: string
  patent_goal?: string
  other_goals?: string
  deliverables?: string
  fob_price?: number
  bom_cost_target?: number
  annual_sales_forecast?: number
  product_lifecycle?: string
  dev_cost_items?: string
  mold_costs?: string
  prototype_costs_detail?: string
  test_costs?: string
  labor_costs?: string
  cert_costs?: string
  core_performance?: string
  safety_compliance?: string
  material_components?: string
  accessory_config?: string
  feature_config?: string
  team_members?: string
  approval_status?: string
  created_at?: string
  updated_at?: string
}

export interface WorkspaceStats {
  annual_plan_count: number
  total_projects: number
  total_budget: number
  completion_rate: number
  overdue_rate: number
  running_count: number
  overdue_count: number
  completed_count: number
}

export interface RoadmapData {
  roadmap_items: any[]
}
