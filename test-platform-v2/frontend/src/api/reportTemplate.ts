import api from './client'

export interface TemplateSection {
  key: string
  label: string
  enabled: boolean
  order: number
}

export interface ReportTemplate {
  id: number
  project_id: number
  name: string
  description: string
  sections: TemplateSection[]
  is_default: boolean
  created_at: string | null
  updated_at: string | null
}

export async function fetchTemplates(): Promise<{ total: number; items: ReportTemplate[] }> {
  return api.get('/report-templates') as unknown as Promise<{ total: number; items: ReportTemplate[] }>
}

export async function createTemplate(body: {
  name: string
  description?: string
  sections?: TemplateSection[]
  is_default?: boolean
}): Promise<ReportTemplate> {
  return api.post('/report-templates', body) as unknown as Promise<ReportTemplate>
}

export async function updateTemplate(id: number, body: {
  name?: string
  description?: string
  sections?: TemplateSection[]
  is_default?: boolean
}): Promise<ReportTemplate> {
  return api.put(`/report-templates/${id}`, body) as unknown as Promise<ReportTemplate>
}

export async function deleteTemplate(id: number): Promise<void> {
  return api.delete(`/report-templates/${id}`)
}
