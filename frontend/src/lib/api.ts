const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  private getHeaders(isMultipart = false): HeadersInit {
    const headers: Record<string, string> = {};
    if (!isMultipart) {
      headers["Content-Type"] = "application/json";
    }
    
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("cai_token");
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
    }
    return headers;
  }

  setToken(token: string) {
    if (typeof window !== "undefined") {
      localStorage.setItem("cai_token", token);
    }
  }

  getToken(): string | null {
    if (typeof window !== "undefined") {
      return localStorage.getItem("cai_token");
    }
    return null;
  }

  clearToken() {
    if (typeof window !== "undefined") {
      localStorage.removeItem("cai_token");
      localStorage.removeItem("cai_user");
    }
  }

  setUser(user: any) {
    if (typeof window !== "undefined") {
      localStorage.setItem("cai_user", JSON.stringify(user));
    }
  }

  getUser(): any | null {
    if (typeof window !== "undefined") {
      const user = localStorage.getItem("cai_user");
      return user ? JSON.parse(user) : null;
    }
    return null;
  }

  async request<T>(path: string, options: RequestInit = {}, isMultipart = false): Promise<T> {
    const baseUrl = API_BASE_URL.replace(/\/$/, "");
    const cleanPath = path.replace(/^\//, "");
    const url = `${baseUrl}/${cleanPath}`;
    const headers = {
      ...this.getHeaders(isMultipart),
      ...options.headers,
    };

    const config = {
      ...options,
      headers,
    };

    try {
      const response = await fetch(url, config);
      if (response.status === 204) {
        return null as unknown as T;
      }
      
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Request failed");
      }
      return data as T;
    } catch (error: any) {
      console.error(`API Error on ${path}:`, error);
      throw error;
    }
  }

  async getDocumentTIS(documentId: string): Promise<any> {
    return this.request<any>(`/api/v1/documents/${documentId}/tis`, { method: "GET" });
  }

  async getComplianceDashboard(): Promise<any> {
    return this.request<any>("/api/v1/compliance/dashboard", { method: "GET" });
  }

  async getClientCompliance(clientId: string): Promise<any> {
    return this.request<any>(`/api/v1/compliance/clients/${clientId}`, { method: "GET" });
  }

  async getComplianceCalendar(): Promise<any[]> {
    return this.request<any[]>("/api/v1/compliance/calendar", { method: "GET" });
  }

  async createComplianceProfile(profile: {
    client_id: string;
    compliance_type: string;
    registration_number?: string;
    frequency?: string;
    due_day?: number;
    assigned_manager?: string;
    assigned_partner?: string;
    risk_level?: string;
  }): Promise<any> {
    return this.request<any>("/api/v1/compliance/profile", {
      method: "POST",
      body: JSON.stringify(profile)
    });
  }

  async createComplianceTask(task: {
    client_id: string;
    profile_id: string;
    task_name: string;
    due_date: string;
    priority?: string;
    status?: string;
    assigned_user_id?: string;
    notes?: string;
  }): Promise<any> {
    return this.request<any>("/api/v1/compliance/task", {
      method: "POST",
      body: JSON.stringify(task)
    });
  }

  async updateComplianceTask(taskId: string, task: any): Promise<any> {
    return this.request<any>(`/api/v1/compliance/task/${taskId}`, {
      method: "PUT",
      body: JSON.stringify(task)
    });
  }

  async getComplianceAlerts(): Promise<any[]> {
    return this.request<any[]>("/api/v1/compliance/alerts", { method: "GET" });
  }

  async getClient360Workspace(clientId: string, assessmentYear?: string): Promise<any> {
    const params = new URLSearchParams();
    if (assessmentYear) params.append("assessment_year", assessmentYear);
    const queryString = params.toString() ? `?${params.toString()}` : "";
    return this.request<any>(`/api/v1/clients/${clientId}/workspace${queryString}`, { method: "GET" });
  }

  async createClientTask(clientId: string, task: {
    task_name: string;
    description?: string;
    status?: string;
    linked_to?: string;
    linked_id?: string;
    due_date?: string;
  }): Promise<any> {
    return this.request<any>(`/api/v1/clients/${clientId}/tasks`, {
      method: "POST",
      body: JSON.stringify(task)
    });
  }

  async updateClientTask(clientId: string, taskId: string, task: any): Promise<any> {
    return this.request<any>(`/api/v1/clients/${clientId}/tasks/${taskId}`, {
      method: "PUT",
      body: JSON.stringify(task)
    });
  }

  async deleteClientTask(clientId: string, taskId: string): Promise<any> {
    return this.request<any>(`/api/v1/clients/${clientId}/tasks/${taskId}`, { method: "DELETE" });
  }

  async createClientNote(clientId: string, note: {
    title: string;
    content: string;
    tags?: string;
    is_pinned?: boolean;
    attachments?: string[];
    mentions?: string[];
  }): Promise<any> {
    return this.request<any>(`/api/v1/clients/${clientId}/notes`, {
      method: "POST",
      body: JSON.stringify(note)
    });
  }

  async updateClientNote(clientId: string, noteId: string, note: any): Promise<any> {
    return this.request<any>(`/api/v1/clients/${clientId}/notes/${noteId}`, {
      method: "PUT",
      body: JSON.stringify(note)
    });
  }

  async deleteClientNote(clientId: string, noteId: string): Promise<any> {
    return this.request<any>(`/api/v1/clients/${clientId}/notes/${noteId}`, { method: "DELETE" });
  }

  async createClientTimelineEvent(clientId: string, event: {
    event_type: string;
    title: string;
    description?: string;
  }): Promise<any> {
    return this.request<any>(`/api/v1/clients/${clientId}/timeline`, {
      method: "POST",
      body: JSON.stringify(event)
    });
  }

  async runResearchQuery(queryText: string, clientId?: string, assessmentYear?: string, filters?: any): Promise<any> {
    return this.request<any>("/api/v1/research/query", {
      method: "POST",
      body: JSON.stringify({ query_text: queryText, client_id: clientId, assessment_year: assessmentYear, filters }),
    });
  }

  async getResearchHistory(): Promise<any[]> {
    return this.request<any[]>("/api/v1/research/history", { method: "GET" });
  }

  async getResearchSources(authority?: string, category?: string): Promise<any[]> {
    const params = new URLSearchParams();
    if (authority) params.append("authority", authority);
    if (category) params.append("category", category);
    const queryString = params.toString() ? `?${params.toString()}` : "";
    return this.request<any[]>(`/api/v1/research/sources${queryString}`, { method: "GET" });
  }

  async listResearchBookmarks(): Promise<any[]> {
    return this.request<any[]>("/api/v1/research/bookmarks", { method: "GET" });
  }

  async addResearchBookmark(sourceId: string, notes?: string): Promise<any> {
    return this.request<any>("/api/v1/research/bookmark", {
      method: "POST",
      body: JSON.stringify({ source_id: sourceId, notes }),
    });
  }

  async deleteResearchBookmark(bookmarkId: string): Promise<any> {
    return this.request<any>(`/api/v1/research/bookmark/${bookmarkId}`, { method: "DELETE" });
  }

  async saveResearchNote(note: {
    client_id?: string;
    assessment_year?: string;
    document_id?: string;
    title: string;
    content: string;
    section_reference?: string;
    authority_reference?: string;
    tags?: string;
    is_pinned?: boolean;
  }): Promise<any> {
    return this.request<any>("/api/v1/research/note", {
      method: "POST",
      body: JSON.stringify(note),
    });
  }

  async updateResearchNote(noteId: string, note: any): Promise<any> {
    return this.request<any>(`/api/v1/research/note/${noteId}`, {
      method: "PUT",
      body: JSON.stringify(note),
    });
  }

  async getResearchNote(noteId: string): Promise<any> {
    return this.request<any>(`/api/v1/research/note/${noteId}`, { method: "GET" });
  }

  async deleteResearchNote(noteId: string): Promise<any> {
    return this.request<any>(`/api/v1/research/note/${noteId}`, { method: "DELETE" });
  }

  // ==========================================
  // AUTHENTICATION
  // ==========================================
  async register(payload: any): Promise<any> {
    const data = await this.request<any>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    this.setToken(data.access_token);
    this.setUser(data.user);
    return data;
  }

  async login(payload: any): Promise<any> {
    const data = await this.request<any>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    this.setToken(data.access_token);
    this.setUser(data.user);
    return data;
  }

  async getMe(): Promise<any> {
    return this.request<any>("/api/v1/auth/me", { method: "GET" });
  }

  // ==========================================
  // ORGANIZATIONS
  // ==========================================
  async getOrgProfile(): Promise<any> {
    return this.request<any>("/api/v1/organizations/profile", { method: "GET" });
  }

  async updateOrgProfile(payload: any): Promise<any> {
    return this.request<any>("/api/v1/organizations/profile", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  }

  // ==========================================
  // CLIENTS
  // ==========================================
  async listClients(search?: string, status?: string, skip?: number, limit?: number): Promise<any[]> {
    let path = "/api/v1/clients";
    const params = new URLSearchParams();
    if (search) params.append("search", search);
    if (status) params.append("status_filter", status);
    if (skip !== undefined) params.append("skip", skip.toString());
    if (limit !== undefined) params.append("limit", limit.toString());
    const queryString = params.toString();
    if (queryString) path += `?${queryString}`;

    return this.request<any[]>(path, { method: "GET" });
  }

  async createClient(payload: any): Promise<any> {
    return this.request<any>("/api/v1/clients", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async getClient(id: string): Promise<any> {
    return this.request<any>(`/api/v1/clients/${id}`, { method: "GET" });
  }

  async updateClient(id: string, payload: any): Promise<any> {
    return this.request<any>(`/api/v1/clients/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  }

  async deleteClient(id: string): Promise<void> {
    return this.request<void>(`/api/v1/clients/${id}`, { method: "DELETE" });
  }

  // ==========================================
  // DOCUMENTS
  // ==========================================
  async uploadDocument(file: File, category: string, clientId?: string): Promise<any> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("category", category);
    if (clientId) {
      formData.append("client_id", clientId);
    }

    return this.request<any>("/api/v1/documents/upload", {
      method: "POST",
      body: formData,
    }, true);
  }

  async listDocuments(clientId?: string, category?: string, skip?: number, limit?: number): Promise<any[]> {
    let path = "/api/v1/documents";
    const params = new URLSearchParams();
    if (clientId) params.append("client_id", clientId);
    if (category) params.append("category", category);
    if (skip !== undefined) params.append("skip", skip.toString());
    if (limit !== undefined) params.append("limit", limit.toString());
    const queryString = params.toString();
    if (queryString) path += `?${queryString}`;

    return this.request<any[]>(path, { method: "GET" });
  }

  async getDocument(id: string): Promise<any> {
    return this.request<any>(`/api/v1/documents/${id}`, { method: "GET" });
  }

  async updateDocument(id: string, payload: any): Promise<any> {
    return this.request<any>(`/api/v1/documents/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  }

  async deleteDocument(id: string): Promise<void> {
    return this.request<void>(`/api/v1/documents/${id}`, { method: "DELETE" });
  }

  async getDocumentStructured(id: string): Promise<any> {
    return this.request<any>(`/api/v1/documents/${id}/structured`, { method: "GET" });
  }

  async getDocumentForm26AS(id: string): Promise<any> {
    return this.request<any>(`/api/v1/documents/${id}/form26as`, { method: "GET" });
  }

  async getDocumentAIS(id: string): Promise<any> {
    return this.request<any>(`/api/v1/documents/${id}/ais`, { method: "GET" });
  }

  async getDocumentSummary(id: string): Promise<any> {
    return this.request<any>(`/api/v1/documents/${id}/summary`, { method: "GET" });
  }

  async getClientTaxProfile(clientId: string, assessmentYear?: string): Promise<any> {
    const ayParam = assessmentYear ? `?assessment_year=${assessmentYear}` : "";
    return this.request<any>(`/api/v1/clients/${clientId}/tax-profile${ayParam}`, { method: "GET" });
  }

  async getClientTaxSummary(clientId: string, assessmentYear?: string): Promise<any> {
    const ayParam = assessmentYear ? `?assessment_year=${assessmentYear}` : "";
    return this.request<any>(`/api/v1/clients/${clientId}/tax-summary${ayParam}`, { method: "GET" });
  }

  async getClientTaxInsights(clientId: string, assessmentYear?: string): Promise<any> {
    const ayParam = assessmentYear ? `?assessment_year=${assessmentYear}` : "";
    return this.request<any>(`/api/v1/clients/${clientId}/tax-insights${ayParam}`, { method: "GET" });
  }

  async getClientITRProfile(clientId: string, assessmentYear?: string): Promise<any> {
    const ayParam = assessmentYear ? `?assessment_year=${assessmentYear}` : "";
    return this.request<any>(`/api/v1/clients/${clientId}/itr-profile${ayParam}`, { method: "GET" });
  }

  async getClientITRReadiness(clientId: string, assessmentYear?: string): Promise<any> {
    const ayParam = assessmentYear ? `?assessment_year=${assessmentYear}` : "";
    return this.request<any>(`/api/v1/clients/${clientId}/itr-readiness${ayParam}`, { method: "GET" });
  }

  async getClientITRActions(clientId: string, assessmentYear?: string): Promise<any> {
    const ayParam = assessmentYear ? `?assessment_year=${assessmentYear}` : "";
    return this.request<any>(`/api/v1/clients/${clientId}/itr-actions${ayParam}`, { method: "GET" });
  }

  async getClientITRVerification(clientId: string, assessmentYear?: string): Promise<any> {
    const ayParam = assessmentYear ? `?assessment_year=${assessmentYear}` : "";
    return this.request<any>(`/api/v1/clients/${clientId}/itr-verification${ayParam}`, { method: "GET" });
  }

  // ==========================================
  // COMPLIANCE SOURCES
  // ==========================================
  async listComplianceSources(skip?: number, limit?: number): Promise<any[]> {
    let path = "/api/v1/compliance/sources";
    const params = new URLSearchParams();
    if (skip !== undefined) params.append("skip", skip.toString());
    if (limit !== undefined) params.append("limit", limit.toString());
    const queryString = params.toString();
    if (queryString) path += `?${queryString}`;
    return this.request<any[]>(path, { method: "GET" });
  }

  async createComplianceSource(payload: any): Promise<any> {
    return this.request<any>("/api/v1/compliance/sources", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async updateComplianceSource(id: string, payload: any): Promise<any> {
    return this.request<any>(`/api/v1/compliance/sources/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  }

  async deleteComplianceSource(id: string): Promise<void> {
    return this.request<void>(`/api/v1/compliance/sources/${id}`, { method: "DELETE" });
  }

  // ==========================================
  // SEARCH
  // ==========================================
  async search(query: string): Promise<any> {
    return this.request<any>(`/api/v1/search?q=${encodeURIComponent(query)}`, { method: "GET" });
  }

  // ==========================================
  // INTEGRATIONS (AKKC)
  // ==========================================
  async connectAKKC(payload: any): Promise<any> {
    return this.request<any>("/api/v1/integrations/akkc/connect", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async getAKKCStatus(): Promise<any> {
    return this.request<any>("/api/v1/integrations/akkc/status", { method: "GET" });
  }

  async syncAKKC(entityType: string): Promise<any> {
    const pathMap: Record<string, string> = {
      CLIENTS: "/api/v1/integrations/akkc/sync/clients",
      TASKS: "/api/v1/integrations/akkc/sync/tasks",
      BILLS: "/api/v1/integrations/akkc/sync/bills",
    };
    return this.request<any>(pathMap[entityType], { method: "POST" });
  }

  // ==========================================
  // OBSERVABILITY & PIPELINES (PHASE 2)
  // ==========================================
  async getPipelineStats(): Promise<any> {
    return this.request<any>("/api/v1/observability/stats", { method: "GET" });
  }

  async getSystemConfig(): Promise<any> {
    return this.request<any>("/api/v1/observability/config", { method: "GET" });
  }

  async retryPipeline(pipelineId: string): Promise<any> {
    return this.request<any>(`/api/v1/observability/pipelines/${pipelineId}/retry`, { method: "POST" });
  }

  // ==========================================
  // COMPLIANCE CONNECTORS (PHASE 3)
  // ==========================================
  async listConnectors(): Promise<any> {
    return this.request<any>("/api/v1/compliance/connectors", { method: "GET" });
  }

  async syncConnector(sourceId: string): Promise<any> {
    return this.request<any>(`/api/v1/compliance/connectors/${sourceId}/sync`, { method: "POST" });
  }

  async pauseConnector(sourceId: string): Promise<any> {
    return this.request<any>(`/api/v1/compliance/connectors/${sourceId}/pause`, { method: "POST" });
  }

  async resumeConnector(sourceId: string): Promise<any> {
    return this.request<any>(`/api/v1/compliance/connectors/${sourceId}/resume`, { method: "POST" });
  }

  async getConnectorLogs(sourceId: string): Promise<any> {
    return this.request<any>(`/api/v1/compliance/connectors/${sourceId}/logs`, { method: "GET" });
  }

  async searchGovernmentDocuments(q = "", category = ""): Promise<any> {
    return this.request<any>(`/api/v1/compliance/connectors/documents?q=${encodeURIComponent(q)}&category=${encodeURIComponent(category)}`, { method: "GET" });
  }

  async getDocumentVersions(docId: string): Promise<any> {
    return this.request<any>(`/api/v1/compliance/connectors/documents/${docId}/versions`, { method: "GET" });
  }

  async archiveGovernmentDocument(docId: string): Promise<any> {
    return this.request<any>(`/api/v1/compliance/connectors/documents/${docId}`, { method: "DELETE" });
  }

  // ==========================================
  // CITATIONS (PHASE 4)
  // ==========================================
  async listCitations(sourceType?: string): Promise<any[]> {
    let path = "/api/v1/citations";
    if (sourceType) path += `?source_type=${encodeURIComponent(sourceType)}`;
    return this.request<any[]>(path, { method: "GET" });
  }

  async createCitation(payload: any): Promise<any> {
    return this.request<any>("/api/v1/citations", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async getCitationsByDocument(docId: string): Promise<any[]> {
    return this.request<any[]>(`/api/v1/citations/document/${docId}`, { method: "GET" });
  }

  async getCitationsByClient(clientId: string): Promise<any[]> {
    return this.request<any[]>(`/api/v1/citations/client/${clientId}`, { method: "GET" });
  }

  async getCitationsByGovUpdate(updateId: string): Promise<any[]> {
    return this.request<any[]>(`/api/v1/citations/government/${updateId}`, { method: "GET" });
  }

  async verifyCitation(citationId: string): Promise<any> {
    return this.request<any>("/api/v1/citations/verify", {
      method: "POST",
      body: JSON.stringify({ citation_id: citationId }),
    });
  }

  // ==========================================
  // KNOWLEDGE GRAPH & ENTITY RESOLUTION (PHASE 4)
  // ==========================================
  async listGraphNodes(nodeType?: string): Promise<any[]> {
    let path = "/api/v1/graph/nodes";
    if (nodeType) path += `?node_type=${encodeURIComponent(nodeType)}`;
    return this.request<any[]>(path, { method: "GET" });
  }

  async listGraphEdges(relationship?: string): Promise<any[]> {
    let path = "/api/v1/graph/edges";
    if (relationship) path += `?relationship=${encodeURIComponent(relationship)}`;
    return this.request<any[]>(path, { method: "GET" });
  }

  async getEntityDetails(entityId: string): Promise<any> {
    return this.request<any>(`/api/v1/graph/entity/${entityId}`, { method: "GET" });
  }

  async getClientGraph(clientId: string): Promise<any> {
    return this.request<any>(`/api/v1/graph/client/${clientId}`, { method: "GET" });
  }

  async getDocumentGraph(docId: string): Promise<any> {
    return this.request<any>(`/api/v1/graph/document/${docId}`, { method: "GET" });
  }

  async buildDocumentGraph(docId: string): Promise<any> {
    return this.request<any>(`/api/v1/graph/build/document/${docId}`, { method: "POST" });
  }

  async buildGovernmentGraph(updateId: string): Promise<any> {
    return this.request<any>(`/api/v1/graph/build/government/${updateId}`, { method: "POST" });
  }

  async mergeEntities(primaryId: string, secondaryId: string): Promise<any> {
    return this.request<any>("/api/v1/graph/entities/merge", {
      method: "POST",
      body: JSON.stringify({ primary_entity_id: primaryId, secondary_entity_id: secondaryId }),
    });
  }

  async createEntityAlias(payload: any): Promise<any> {
    return this.request<any>("/api/v1/graph/entities/alias", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }
}

export const api = new ApiClient();

