import { apiRequest, getAPIClient } from './client';

export interface Document {
  id: string;
  title: string;
  category: DocumentCategory;
  mimeType: string;
  size: number;
  createdAt: string;
  updatedAt: string;
  caseId?: string;
  tags: string[];
  isEncrypted: boolean;
  expiresAt?: string;
  downloadUrl?: string;
  thumbnailUrl?: string;
}

export type DocumentCategory =
  | 'legal'
  | 'financial'
  | 'identity'
  | 'medical'
  | 'real_estate'
  | 'tax'
  | 'contract'
  | 'court_filing'
  | 'other';

export interface UploadDocumentRequest {
  title: string;
  category: DocumentCategory;
  caseId?: string;
  tags?: string[];
}

export interface OCRResult {
  text: string;
  confidence: number;
  pages: number;
}

export const documentsAPI = {
  list: (params?: { category?: DocumentCategory; caseId?: string }) =>
    apiRequest<Document[]>('get', '/documents', undefined, { params }),

  get: (documentId: string) =>
    apiRequest<Document>('get', `/documents/${documentId}`),

  delete: (documentId: string) =>
    apiRequest<void>('delete', `/documents/${documentId}`),

  upload: async (
    fileUri: string,
    metadata: UploadDocumentRequest,
    onProgress?: (progress: number) => void,
  ): Promise<Document> => {
    const client = getAPIClient();
    const formData = new FormData();
    formData.append('file', {
      uri: fileUri,
      name: `document_${Date.now()}.pdf`,
      type: 'application/pdf',
    } as unknown as Blob);
    formData.append('metadata', JSON.stringify(metadata));

    const response = await client.post<Document>('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          onProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total));
        }
      },
    });
    return response.data;
  },

  runOCR: (documentId: string) =>
    apiRequest<OCRResult>('post', `/documents/${documentId}/ocr`),

  shareDocument: (documentId: string, recipientEmail: string, expiresInDays?: number) =>
    apiRequest<{ shareUrl: string; expiresAt: string }>('post', `/documents/${documentId}/share`, {
      recipientEmail,
      expiresInDays: expiresInDays ?? 7,
    }),

  updateTags: (documentId: string, tags: string[]) =>
    apiRequest<Document>('patch', `/documents/${documentId}`, { tags }),
};
