export interface ReferencedDocument {
  id: string;
  name: string;
  clean_name: string;
  summary: string;
  type: string;
  reference_count: number;
  created_datetime: string | null;
}

export interface TopReferencedDocumentsResponse {
  documents: ReferencedDocument[];
  total: number;
}
