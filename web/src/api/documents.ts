import { api, APIResponse, apiClient } from './client';

export interface DocumentResponse {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  mime_type: string;
  file_extension: string;
  size_bytes: number;
  client_id?: string;
  case_id?: string;
  matter_id?: string;
  folder_id?: string;
  uploaded_by: string;
  current_version: number;
  status: string;
  is_confidential: boolean;
  requires_signature: boolean;
  signed_at?: string;
  ai_category?: string;
  ai_tags?: string[];
  tags?: string[];
  watermark_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: DocumentResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface DocumentExportRequest {
  document_ids: string[];
  packet_title?: string;
}

export interface DocumentExportResponse {
  snapshot_id: string;
  packet_hash: string;
  audit_id: string;
  evidence_hash: string;
  document_count: number;
  packet_json: string;
}

export interface DocumentUploadParams {
  name: string;
  description?: string;
  case_id?: string;
  client_id?: string;
  folder_id?: string;
  is_confidential?: boolean;
  tags?: string[];
}

export const documentsApi = {
  /** List documents with optional filtering. */
  list: (params?: { case_id?: string; page?: number; page_size?: number }) =>
    api.get<APIResponse<DocumentListResponse>>('/documents', params).then((r) => r.data),

  /** Get a single document by ID. */
  get: (id: string) => api.get<APIResponse<DocumentResponse>>(`/documents/${id}`).then((r) => r.data),

  /** Upload a new document with metadata. */
  upload: (file: File, params: DocumentUploadParams) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', params.name);
    if (params.description) formData.append('description', params.description);
    if (params.case_id) formData.append('case_id', params.case_id);
    if (params.client_id) formData.append('client_id', params.client_id);
    if (params.folder_id) formData.append('folder_id', params.folder_id);
    if (params.is_confidential !== undefined) formData.append('is_confidential', String(params.is_confidential));
    if (params.tags) formData.append('tags', JSON.stringify(params.tags));
    return api.upload<APIResponse<DocumentResponse>>('/documents/upload', formData).then((r) => r.data);
  },

  /** Export selected case documents as a verified evidence packet. */
  exportPacket: (caseId: string, payload: DocumentExportRequest) =>
    api
      .post<APIResponse<DocumentExportResponse>>(`/documents/cases/${caseId}/export-packet`, payload)
      .then((r) => r.data),

  /** Download a document by ID. */
  download: (id: string) => apiClient.get(`/documents/${id}/download`, { responseType: 'blob' }),
};
