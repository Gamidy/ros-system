// 外协管理 API 层
import api from './index'

export function listOutsourcePartners(params: Record<string, any>) { return api.get('/outsource/partners', { params }) }
export function getOutsourcePartner(id: number) { return api.get(`/outsource/partners/${id}`) }
export function createOutsourcePartner(data: Record<string, any>) { return api.post('/outsource/partners', data) }
export function updateOutsourcePartner(id: number, data: Record<string, any>) { return api.put(`/outsource/partners/${id}`, data) }
export function deleteOutsourcePartner(id: number) { return api.delete(`/outsource/partners/${id}`) }

export function listOutsourceOrders(params: Record<string, any>) { return api.get('/outsource/orders', { params }) }
export function getOutsourceOrder(id: number) { return api.get(`/outsource/orders/${id}`) }
export function createOutsourceOrder(data: Record<string, any>) { return api.post('/outsource/orders', data) }
export function updateOutsourceOrder(id: number, data: Record<string, any>) { return api.put(`/outsource/orders/${id}`, data) }
export function deleteOutsourceOrder(id: number) { return api.delete(`/outsource/orders/${id}`) }

export function listOutsourceQualityRecords(params: Record<string, any>) { return api.get('/outsource/quality-records', { params }) }
export function createOutsourceQualityRecord(data: Record<string, any>) { return api.post('/outsource/quality-records', data) }
export function updateOutsourceQualityRecord(id: number, data: Record<string, any>) { return api.put(`/outsource/quality-records/${id}`, data) }
export function deleteOutsourceQualityRecord(id: number) { return api.delete(`/outsource/quality-records/${id}`) }
