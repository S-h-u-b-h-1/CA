import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import {
  Plus, User, Mail, Phone, Briefcase, FileText, Settings, BookOpen, AlertCircle,
  ArrowLeft, Sparkles, ShieldCheck, CheckCircle2, AlertTriangle, Clock, Play,
  Download, RefreshCcw, Search, Trash2, Calendar, ClipboardList, CheckSquare,
  Tag, Pin, MessageSquare, Paperclip, ChevronRight, Activity, SearchIcon
} from "lucide-react";
import { TaxIntelligence } from "./TaxIntelligence";
import { ITRPreparation } from "./ITRPreparation";
import { TISView } from "./TISView";
import { ResearchWorkspace } from "./ResearchWorkspace";
import { ClientComplianceProfile } from "./ClientComplianceProfile";

interface ClientWorkspaceProps {
  clients: any[];
  onRefresh: () => void;
}

export const ClientWorkspace: React.FC<ClientWorkspaceProps> = ({ clients, onRefresh }) => {
  const [selectedClient, setSelectedClient] = useState<any | null>(null);
  
  // Workspace unified data
  const [workspaceData, setWorkspaceData] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Tab states
  const [activeSubTab, setActiveSubTab] = useState("overview"); 
  const [activeDocumentDetail, setActiveDocumentDetail] = useState<{ id: string, category: string } | null>(null);
  
  // Create client form state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [clientName, setClientName] = useState("");
  const [clientType, setClientType] = useState("Company");
  const [pan, setPan] = useState("");
  const [gstin, setGstin] = useState("");
  const [cinLlpIn, setCinLlpIn] = useState("");
  const [tan, setTan] = useState("");
  const [address, setAddress] = useState("");
  const [contactPerson, setContactPerson] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [industry, setIndustry] = useState("");
  const [assignedManager, setAssignedManager] = useState("");
  const [assignedPartner, setAssignedPartner] = useState("");

  // Quick tasks & quick notes input
  const [quickTaskText, setQuickTaskText] = useState("");
  const [quickNoteTitle, setQuickNoteTitle] = useState("");
  const [quickNoteContent, setQuickNoteContent] = useState("");
  const [quickNoteTags, setQuickNoteTags] = useState("");

  // Global search state
  const [workspaceSearchQuery, setWorkspaceSearchQuery] = useState("");

  // Loader for Workspace data
  useEffect(() => {
    if (selectedClient) {
      loadWorkspaceData(selectedClient.id);
    }
  }, [selectedClient]);

  const loadWorkspaceData = async (clientId: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getClient360Workspace(clientId);
      setWorkspaceData(data);
    } catch (err: any) {
      setError(err.message || "Failed to load workspace data");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateClient = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.createClient({
        client_name: clientName,
        client_type: clientType,
        PAN: pan || undefined,
        GSTIN: gstin || undefined,
        CIN_LLPIN: cinLlpIn || undefined,
        TAN: tan || undefined,
        registered_address: address || undefined,
        contact_person: contactPerson || undefined,
        contact_email: contactEmail || undefined,
        contact_phone: contactPhone || undefined,
        industry: industry || undefined
      });
      
      // Reset form
      setClientName("");
      setPan("");
      setGstin("");
      setCinLlpIn("");
      setTan("");
      setAddress("");
      setContactPerson("");
      setContactEmail("");
      setContactPhone("");
      setIndustry("");
      
      setShowCreateModal(false);
      onRefresh();
    } catch (err: any) {
      setError(err.message || "Failed to create client");
    } finally {
      setLoading(false);
    }
  };

  // Task Handlers
  const handleAddTask = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!quickTaskText.trim() || !selectedClient) return;

    try {
      await api.createClientTask(selectedClient.id, {
        task_name: quickTaskText,
        status: "PENDING"
      });
      setQuickTaskText("");
      loadWorkspaceData(selectedClient.id);
    } catch (err: any) {
      alert("Failed to add task: " + err.message);
    }
  };

  const handleToggleTaskStatus = async (task: any) => {
    if (!selectedClient) return;
    const newStatus = task.status === "COMPLETED" ? "PENDING" : "COMPLETED";
    try {
      await api.updateClientTask(selectedClient.id, task.id, {
        task_name: task.task_name,
        status: newStatus
      });
      loadWorkspaceData(selectedClient.id);
    } catch (err: any) {
      alert("Failed to update task: " + err.message);
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    if (!selectedClient) return;
    try {
      await api.deleteClientTask(selectedClient.id, taskId);
      loadWorkspaceData(selectedClient.id);
    } catch (err: any) {
      alert("Failed to delete task: " + err.message);
    }
  };

  // Note Handlers
  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickNoteTitle.trim() || !quickNoteContent.trim() || !selectedClient) return;

    try {
      await api.createClientNote(selectedClient.id, {
        title: quickNoteTitle,
        content: quickNoteContent,
        tags: quickNoteTags || undefined
      });
      setQuickNoteTitle("");
      setQuickNoteContent("");
      setQuickNoteTags("");
      loadWorkspaceData(selectedClient.id);
    } catch (err: any) {
      alert("Failed to create note: " + err.message);
    }
  };

  const handleDeleteNote = async (noteId: string) => {
    if (!selectedClient) return;
    try {
      await api.deleteClientNote(selectedClient.id, noteId);
      loadWorkspaceData(selectedClient.id);
    } catch (err: any) {
      alert("Failed to delete note: " + err.message);
    }
  };

  // Dynamic filter for global search within workspace
  const getFilteredDocuments = () => {
    if (!workspaceData) return [];
    if (!workspaceSearchQuery.trim()) return workspaceData.documents;
    return workspaceData.documents.filter((d: any) => 
      d.name.toLowerCase().includes(workspaceSearchQuery.toLowerCase()) ||
      d.category.toLowerCase().includes(workspaceSearchQuery.toLowerCase())
    );
  };

  const getFilteredTasks = () => {
    if (!workspaceData) return [];
    if (!workspaceSearchQuery.trim()) return workspaceData.tasks;
    return workspaceData.tasks.filter((t: any) => 
      t.task_name.toLowerCase().includes(workspaceSearchQuery.toLowerCase()) ||
      (t.description && t.description.toLowerCase().includes(workspaceSearchQuery.toLowerCase()))
    );
  };

  const getFilteredNotes = () => {
    if (!workspaceData) return [];
    if (!workspaceSearchQuery.trim()) return workspaceData.notes;
    return workspaceData.notes.filter((n: any) => 
      n.title.toLowerCase().includes(workspaceSearchQuery.toLowerCase()) ||
      n.content.toLowerCase().includes(workspaceSearchQuery.toLowerCase()) ||
      (n.tags && n.tags.toLowerCase().includes(workspaceSearchQuery.toLowerCase()))
    );
  };

  // Color mappings for health status
  const getHealthColor = (score: string) => {
    switch (score) {
      case "Excellent": return "bg-emerald-50 text-emerald-800 border-emerald-200";
      case "Good": return "bg-blue-50 text-blue-800 border-blue-200";
      case "Needs Attention": return "bg-amber-50 text-amber-800 border-amber-200";
      case "Critical": return "bg-red-50 text-red-800 border-red-200";
      default: return "bg-slate-50 text-slate-800 border-slate-200";
    }
  };

  const getHealthRingColor = (score: string) => {
    switch (score) {
      case "Excellent": return "stroke-emerald-500";
      case "Good": return "stroke-blue-500";
      case "Needs Attention": return "stroke-amber-500";
      case "Critical": return "stroke-red-500";
      default: return "stroke-slate-300";
    }
  };

  return (
    <div className="space-y-6">
      
      {/* 1. Client List View (Initial Screen) */}
      {!selectedClient ? (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-extrabold text-slate-900">Clients Registry</h2>
              <p className="text-xs text-slate-500">Select or create a client to load the unified 360° workspace.</p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="bg-blue-900 text-white rounded-lg px-4 py-2 text-xs font-bold flex items-center gap-1 hover:bg-blue-950 transition-colors shadow-sm select-none"
            >
              <Plus className="h-4 w-4" />
              New Client
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {clients.map((c) => (
              <div 
                key={c.id} 
                className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:border-blue-900/50 hover:shadow transition-all duration-200 flex flex-col justify-between"
              >
                <div className="space-y-3">
                  <div className="flex justify-between items-start">
                    <h3 className="font-extrabold text-sm text-slate-800 line-clamp-1">{c.client_name}</h3>
                    <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-bold uppercase tracking-wider shrink-0">
                      {c.client_type}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-x-2 gap-y-1.5 text-[11px] text-slate-500">
                    <span>PAN:</span>
                    <span className="font-mono font-bold text-slate-700">{c.PAN || "N/A"}</span>
                    <span>GSTIN:</span>
                    <span className="font-mono font-bold text-slate-700">{c.GSTIN || "N/A"}</span>
                    <span>Industry:</span>
                    <span className="font-semibold text-slate-700">{c.industry || "N/A"}</span>
                  </div>
                </div>

                <div className="border-t border-slate-100 pt-3 mt-4 flex justify-between items-center">
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                    c.status === "ACTIVE" ? "bg-emerald-50 text-emerald-800" : "bg-slate-100 text-slate-600"
                  }`}>
                    {c.status}
                  </span>
                  <button
                    onClick={() => setSelectedClient(c)}
                    className="text-blue-900 hover:text-blue-950 font-bold text-xs flex items-center gap-0.5"
                  >
                    Open Workspace
                    <ChevronRight className="h-4.5 w-4.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        
        /* 2. Client Detailed 360° Workspace View (Split Layout) */
        <div className="space-y-6">
          
          {/* Header Bar */}
          <div className="flex justify-between items-center border-b border-slate-200 pb-4">
            <div className="flex items-center space-x-3">
              <button 
                onClick={() => { setSelectedClient(null); setWorkspaceData(null); setActiveDocumentDetail(null); }}
                className="p-1.5 border border-slate-200 bg-white rounded-lg hover:bg-slate-50 transition-colors"
                title="Back to Registry"
              >
                <ArrowLeft className="h-4 w-4 text-slate-600" />
              </button>
              <div>
                <div className="flex items-center space-x-2">
                  <h1 className="text-xl font-black text-slate-900">{selectedClient.client_name}</h1>
                  <span className="text-[10px] bg-blue-50 text-blue-800 px-2 py-0.5 rounded font-bold uppercase">
                    {selectedClient.client_type}
                  </span>
                </div>
                <p className="text-xs text-slate-400">PAN: <span className="font-mono">{selectedClient.PAN || "N/A"}</span> | GSTIN: <span className="font-mono">{selectedClient.GSTIN || "N/A"}</span></p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase">Assessment Year:</span>
              <span className="bg-slate-100 text-slate-700 px-2.5 py-1 rounded-lg text-xs font-bold">AY 2025-26</span>
            </div>
          </div>

          {loading && !workspaceData ? (
            <div className="flex flex-col items-center justify-center py-20 space-y-2">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-900"></div>
              <p className="text-xs text-slate-500 font-semibold">Aggregating workspace data...</p>
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-lg flex items-center space-x-2 text-xs">
              <AlertCircle className="h-5 w-5 text-red-600" />
              <span>{error}</span>
            </div>
          ) : workspaceData ? (
            
            /* Main Split Layout Grid */
            <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
              
              {/* ======================================================== */}
              {/* LEFT COLUMN: Client Overview & Health Score */}
              {/* ======================================================== */}
              <div className="xl:col-span-1 space-y-6">
                
                {/* Health Score Widget */}
                <div className={`p-5 rounded-xl border shadow-sm flex flex-col items-center text-center space-y-3 ${getHealthColor(workspaceData.overview.health_score)}`}>
                  <p className="text-[10px] uppercase font-bold tracking-wider opacity-70">Client Health Status</p>
                  
                  {/* Gauge indicator */}
                  <div className="relative h-20 w-20">
                    <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                      <path
                        className="stroke-slate-200/50"
                        strokeWidth="3.5"
                        fill="none"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                      <path
                        className={getHealthRingColor(workspaceData.overview.health_score)}
                        strokeWidth="3.5"
                        strokeDasharray={`${workspaceData.overview.health_score_value}, 100`}
                        strokeLinecap="round"
                        fill="none"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-base font-black">{workspaceData.overview.health_score_value}%</span>
                    </div>
                  </div>

                  <div>
                    <h4 className="font-extrabold text-sm">{workspaceData.overview.health_score}</h4>
                    <p className="text-[10px] mt-1 leading-relaxed opacity-80">
                      {workspaceData.overview.health_score === "Excellent" && "All documents uploaded, verification complete, zero mismatches."}
                      {workspaceData.overview.health_score === "Good" && "Documents present. Reconcile remaining action items."}
                      {workspaceData.overview.health_score === "Needs Attention" && "Pending warning checklists or missing document types."}
                      {workspaceData.overview.health_score === "Critical" && "Multiple high value mismatches. Prompt action required."}
                    </p>
                  </div>
                </div>

                {/* Summary Card */}
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
                  <div className="flex items-center space-x-2 border-b border-slate-100 pb-2">
                    <ClipboardList className="h-4.5 w-4.5 text-blue-900" />
                    <h4 className="font-bold text-sm text-slate-800">Client Info Card</h4>
                  </div>

                  <div className="space-y-3.5 text-xs">
                    <div className="grid grid-cols-2 gap-1">
                      <span className="text-slate-400">PAN:</span>
                      <span className="font-mono font-bold text-slate-700">{workspaceData.overview.PAN || "N/A"}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-1">
                      <span className="text-slate-400">GSTIN:</span>
                      <span className="font-mono font-bold text-slate-700">{workspaceData.overview.GSTIN || "N/A"}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-1">
                      <span className="text-slate-400">Status:</span>
                      <span className="font-bold text-slate-700">{workspaceData.overview.status}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-1">
                      <span className="text-slate-400">Financial Year:</span>
                      <span className="font-bold text-slate-700">{workspaceData.overview.financial_year}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-1">
                      <span className="text-slate-400">Assigned Manager:</span>
                      <span className="font-bold text-slate-700">{workspaceData.overview.assigned_manager}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-1">
                      <span className="text-slate-400">Assigned Partner:</span>
                      <span className="font-bold text-slate-700">{workspaceData.overview.assigned_partner}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-1">
                      <span className="text-slate-400">Registered on:</span>
                      <span className="text-slate-500 font-semibold">
                        {new Date(workspaceData.overview.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-1">
                      <span className="text-slate-400">Last Activity:</span>
                      <span className="text-slate-500 font-semibold">
                        {new Date(workspaceData.overview.last_activity).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* ======================================================== */}
              {/* CENTER COLUMN: Tabs & Main Inner Workspace */}
              {/* ======================================================== */}
              <div className="xl:col-span-2 space-y-6">
                
                {/* Horizontal Navigation Tabs */}
                <div className="flex border-b border-slate-200 overflow-x-auto space-x-6 text-xs no-scrollbar select-none">
                  {[
                    { id: "overview", label: "Dashboard Overview", icon: Activity },
                    { id: "documents", label: "Document Center", icon: FileText },
                    { id: "compliance", label: "Compliance Profile", icon: ShieldCheck },
                    { id: "tax_intelligence", label: "Tax Intelligence", icon: Sparkles },
                    { id: "itr_preparation", label: "ITR Preparation", icon: ShieldCheck },
                    { id: "research", label: "Research Workspace", icon: BookOpen },
                    { id: "tasks", label: "Checklists & Tasks", icon: ClipboardList },
                    { id: "timeline", label: "Timeline", icon: Clock },
                    { id: "search", label: "Global Search", icon: Search }
                  ].map((tab) => {
                    const Icon = tab.icon;
                    return (
                      <button
                        key={tab.id}
                        onClick={() => { setActiveSubTab(tab.id); setActiveDocumentDetail(null); }}
                        className={`pb-3 flex items-center space-x-1.5 font-bold transition-all shrink-0 border-b-2 ${
                          activeSubTab === tab.id
                            ? "border-blue-900 text-blue-900"
                            : "border-transparent text-slate-500 hover:text-slate-700"
                        }`}
                      >
                        <Icon className="h-4 w-4" />
                        <span>{tab.label}</span>
                      </button>
                    );
                  })}
                </div>

                {/* Workspace tab views */}
                <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm min-h-96">
                  
                  {/* Dash Overview Tab */}
                  {activeSubTab === "overview" && (
                    <div className="space-y-6">
                      <div className="flex items-center space-x-2">
                        <Activity className="h-5 w-5 text-blue-950" />
                        <h3 className="font-extrabold text-base text-slate-800">Workspace Dashboard</h3>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <div className="p-4 bg-slate-50 rounded-lg border border-slate-100 space-y-1">
                          <p className="text-[10px] text-slate-400 uppercase font-bold">Documents Processed</p>
                          <p className="text-xl font-black text-slate-800">{workspaceData.documents.length}</p>
                        </div>
                        <div className="p-4 bg-slate-50 rounded-lg border border-slate-100 space-y-1">
                          <p className="text-[10px] text-slate-400 uppercase font-bold">Total Active Mismatches</p>
                          <p className="text-xl font-black text-amber-800">{workspaceData.tax_intelligence.mismatches.length}</p>
                        </div>
                        <div className="p-4 bg-slate-50 rounded-lg border border-slate-100 space-y-1">
                          <p className="text-[10px] text-slate-400 uppercase font-bold">Readiness Score</p>
                          <p className="text-xl font-black text-blue-900">{workspaceData.itr_preparation.readiness_score}%</p>
                        </div>
                        <div className="p-4 bg-slate-50 rounded-lg border border-slate-100 space-y-1">
                          <p className="text-[10px] text-slate-400 uppercase font-bold">Pending Tasks</p>
                          <p className="text-xl font-black text-slate-800">
                            {workspaceData.tasks.filter((t: any) => t.status !== "COMPLETED").length}
                          </p>
                        </div>
                      </div>

                      {/* Timeline Events Snippet */}
                      <div className="space-y-3">
                        <p className="text-xs font-bold text-slate-700">Recent Activities</p>
                        {workspaceData.timeline.length === 0 ? (
                          <p className="text-xs text-slate-400 italic">No timeline events logged.</p>
                        ) : (
                          <div className="space-y-3">
                            {workspaceData.timeline.slice(0, 3).map((evt: any) => (
                              <div key={evt.id} className="text-xs flex items-start gap-2.5">
                                <Clock className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
                                <div>
                                  <p className="font-bold text-slate-800">{evt.title}</p>
                                  <p className="text-slate-500 mt-0.5">{evt.description}</p>
                                  <span className="text-[10px] text-slate-400 block mt-0.5">{new Date(evt.created_at).toLocaleTimeString()}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Document Center Tab */}
                  {activeSubTab === "documents" && (
                    <div className="space-y-4">
                      {activeDocumentDetail && activeDocumentDetail.category === "TIS" ? (
                        <TISView 
                          documentId={activeDocumentDetail.id} 
                          onBack={() => setActiveDocumentDetail(null)} 
                        />
                      ) : (
                        <>
                          <div className="flex justify-between items-center">
                            <h3 className="font-extrabold text-sm text-slate-800">Document Registry</h3>
                          </div>
                          
                          {workspaceData.documents.length === 0 ? (
                            <p className="text-slate-500 text-xs italic">No documents uploaded. Go to standard documents upload engine.</p>
                          ) : (
                            <div className="space-y-3">
                              {workspaceData.documents.map((doc: any) => (
                                <div key={doc.id} className="p-3 bg-slate-50 border border-slate-100 rounded-lg flex justify-between items-center text-xs">
                                  <div className="space-y-1">
                                    {doc.category === "TIS" && doc.processing_status === "COMPLETED" ? (
                                      <button 
                                        onClick={() => setActiveDocumentDetail({ id: doc.id, category: doc.category })}
                                        className="text-blue-900 font-extrabold hover:underline text-left block"
                                      >
                                        📄 {doc.name}
                                      </button>
                                    ) : (
                                      <p className="font-bold text-slate-800">📄 {doc.name}</p>
                                    )}
                                    <div className="flex items-center gap-2 text-[10px] text-slate-400">
                                      <span>Cat: {doc.category}</span>
                                      <span>•</span>
                                      <span>Conf: {doc.confidence}%</span>
                                    </div>
                                  </div>
                                  
                                  <div className="flex items-center gap-2">
                                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                      doc.processing_status === "COMPLETED" ? "bg-emerald-50 text-emerald-800" : "bg-slate-100 text-slate-600"
                                    }`}>
                                      {doc.processing_status}
                                    </span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  )}

                  {/* Compliance Profile Tab */}
                  {activeSubTab === "compliance" && (
                    <ClientComplianceProfile clientId={selectedClient.id} />
                  )}

                  {/* Tax Intelligence Tab */}
                  {activeSubTab === "tax_intelligence" && (
                    <TaxIntelligence clientId={selectedClient.id} />
                  )}

                  {/* ITR Prep Tab */}
                  {activeSubTab === "itr_preparation" && (
                    <ITRPreparation clientId={selectedClient.id} />
                  )}

                  {/* Research Workspace Tab */}
                  {activeSubTab === "research" && (
                    <ResearchWorkspace clientId={selectedClient.id} />
                  )}

                  {/* Tasks Manager Tab */}
                  {activeSubTab === "tasks" && (
                    <div className="space-y-4">
                      <div className="flex items-center space-x-2 border-b border-slate-100 pb-2">
                        <ClipboardList className="h-4.5 w-4.5 text-blue-900" />
                        <h4 className="font-bold text-sm text-slate-800">Tasks Checklist ({workspaceData.tasks.length})</h4>
                      </div>

                      <form onSubmit={handleAddTask} className="flex gap-2">
                        <input
                          type="text"
                          value={quickTaskText}
                          onChange={(e) => setQuickTaskText(e.target.value)}
                          placeholder="Type checklist task name..."
                          className="flex-1 bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs font-semibold focus:outline-none"
                        />
                        <button type="submit" className="bg-blue-900 text-white rounded-lg px-4 text-xs font-bold hover:bg-blue-950">
                          Add
                        </button>
                      </form>

                      <div className="space-y-2">
                        {workspaceData.tasks.map((task: any) => (
                          <div key={task.id} className="flex justify-between items-center p-2.5 rounded bg-slate-50 border border-slate-100 text-xs">
                            <div className="flex items-center gap-2">
                              <input
                                type="checkbox"
                                checked={task.status === "COMPLETED"}
                                onChange={() => handleToggleTaskStatus(task)}
                                className="rounded text-blue-900 focus:ring-blue-900"
                              />
                              <span className={task.status === "COMPLETED" ? "line-through text-slate-400 font-semibold" : "font-bold text-slate-800"}>
                                {task.task_name}
                              </span>
                            </div>
                            <button onClick={() => handleDeleteTask(task.id)} className="text-red-500 hover:text-red-700">
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Timeline Tab */}
                  {activeSubTab === "timeline" && (
                    <div className="space-y-4">
                      <h4 className="font-bold text-sm text-slate-800">Chronological Event Timeline</h4>
                      {workspaceData.timeline.length === 0 ? (
                        <p className="text-xs text-slate-400 italic">No timeline logs.</p>
                      ) : (
                        <div className="space-y-4 relative border-l border-slate-200 pl-4 ml-2 mt-2">
                          {workspaceData.timeline.map((evt: any) => (
                            <div key={evt.id} className="relative text-xs">
                              <span className="absolute -left-[21px] top-0.5 bg-blue-900 rounded-full h-2 w-2"></span>
                              <p className="font-bold text-slate-800">{evt.title}</p>
                              {evt.description && <p className="text-slate-500 mt-0.5">{evt.description}</p>}
                              <span className="text-[10px] text-slate-400 block mt-0.5">{new Date(evt.created_at).toLocaleString()}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Global Workspace Search Tab */}
                  {activeSubTab === "search" && (
                    <div className="space-y-6">
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={workspaceSearchQuery}
                          onChange={(e) => setWorkspaceSearchQuery(e.target.value)}
                          placeholder="Search workspace documents, tasks, and notes..."
                          className="flex-1 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-semibold focus:outline-none"
                        />
                      </div>

                      <div className="space-y-4">
                        <div>
                          <p className="text-[10px] uppercase font-bold text-slate-400 mb-2">Matched Documents ({getFilteredDocuments().length})</p>
                          {getFilteredDocuments().map((d: any) => (
                            <div key={d.id} className="p-2 border border-slate-100 rounded mb-1 text-xs font-bold text-slate-800 bg-slate-50/50">
                              📄 {d.name} <span className="text-[10px] font-normal text-slate-400 ml-2">({d.category})</span>
                            </div>
                          ))}
                        </div>

                        <div>
                          <p className="text-[10px] uppercase font-bold text-slate-400 mb-2">Matched Checklist Tasks ({getFilteredTasks().length})</p>
                          {getFilteredTasks().map((t: any) => (
                            <div key={t.id} className="p-2 border border-slate-100 rounded mb-1 text-xs font-bold text-slate-800 bg-slate-50/50">
                              ☑️ {t.task_name} <span className="text-[10px] font-normal text-slate-400 ml-2">({t.status})</span>
                            </div>
                          ))}
                        </div>

                        <div>
                          <p className="text-[10px] uppercase font-bold text-slate-400 mb-2">Matched Notes ({getFilteredNotes().length})</p>
                          {getFilteredNotes().map((n: any) => (
                            <div key={n.id} className="p-2 border border-slate-100 rounded mb-1 text-xs font-bold text-slate-800 bg-slate-50/50">
                              📌 {n.title} - <span className="font-normal text-slate-500">{n.content}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                </div>
              </div>

              {/* ======================================================== */}
              {/* RIGHT COLUMN: Sidebar Notes, Tasks, and Alerts */}
              {/* ======================================================== */}
              <div className="xl:col-span-1 space-y-6">
                
                {/* Active Alerts Panel */}
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
                  <div className="flex items-center space-x-2 border-b border-slate-100 pb-2">
                    <AlertTriangle className="h-4.5 w-4.5 text-amber-500" />
                    <h4 className="font-bold text-sm text-slate-800">Critical Alerts</h4>
                  </div>
                  {workspaceData.tax_intelligence.mismatches.length === 0 && workspaceData.itr_preparation.warnings.length === 0 ? (
                    <p className="text-xs text-slate-400 italic">No warnings or mismatches found.</p>
                  ) : (
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {workspaceData.tax_intelligence.mismatches.map((m: any) => (
                        <div key={m.id} className="p-2 rounded bg-amber-50 border border-amber-200 text-[11px] text-amber-900 flex gap-2">
                          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                          <span>{m.description}</span>
                        </div>
                      ))}
                      {workspaceData.itr_preparation.warnings.map((w: any) => (
                        <div key={w.id} className="p-2 rounded bg-red-50 border border-red-200 text-[11px] text-red-900 flex gap-2">
                          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                          <span>{w.description}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Quick Task Drawer */}
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
                  <div className="flex items-center space-x-2 border-b border-slate-100 pb-2">
                    <CheckSquare className="h-4.5 w-4.5 text-blue-900" />
                    <h4 className="font-bold text-sm text-slate-800">Pending Actions</h4>
                  </div>
                  {workspaceData.tasks.filter((t: any) => t.status !== "COMPLETED").length === 0 ? (
                    <p className="text-[11px] text-slate-400 italic">All actions complete.</p>
                  ) : (
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {workspaceData.tasks.filter((t: any) => t.status !== "COMPLETED").map((task: any) => (
                        <div key={task.id} className="flex items-start gap-2 text-xs">
                          <input 
                            type="checkbox"
                            checked={false}
                            onChange={() => handleToggleTaskStatus(task)}
                            className="mt-0.5 rounded text-blue-900"
                          />
                          <span className="font-bold text-slate-700">{task.task_name}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Quick Notes Panel */}
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
                  <div className="flex items-center space-x-2 border-b border-slate-100 pb-2">
                    <MessageSquare className="h-4.5 w-4.5 text-blue-900" />
                    <h4 className="font-bold text-sm text-slate-800">Quick Workspace Notes</h4>
                  </div>

                  <form onSubmit={handleAddNote} className="space-y-2.5">
                    <input
                      type="text"
                      value={quickNoteTitle}
                      onChange={(e) => setQuickNoteTitle(e.target.value)}
                      placeholder="Note Title..."
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg p-1.5 text-xs font-semibold focus:outline-none"
                      required
                    />
                    <textarea
                      value={quickNoteContent}
                      onChange={(e) => setQuickNoteContent(e.target.value)}
                      placeholder="Draft note content..."
                      rows={3}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg p-1.5 text-xs font-semibold focus:outline-none"
                      required
                    />
                    <input
                      type="text"
                      value={quickNoteTags}
                      onChange={(e) => setQuickNoteTags(e.target.value)}
                      placeholder="comma-separated tags..."
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg p-1.5 text-xs font-semibold focus:outline-none"
                    />
                    <button type="submit" className="w-full bg-blue-900 text-white rounded-lg py-1.5 text-xs font-bold hover:bg-blue-950">
                      Save Workspace Note
                    </button>
                  </form>

                  {/* Notes List snippet */}
                  <div className="space-y-2 border-t border-slate-100 pt-3 max-h-48 overflow-y-auto">
                    {workspaceData.notes.map((note: any) => (
                      <div key={note.id} className="p-2 rounded bg-slate-50 border border-slate-100 text-xs space-y-1 relative group">
                        <div className="flex justify-between items-start pr-6">
                          <h5 className="font-extrabold text-slate-800">{note.title}</h5>
                          {note.is_pinned && <Pin className="h-3 w-3 text-amber-500 fill-current shrink-0" />}
                        </div>
                        <p className="text-slate-600 font-medium text-[11px] leading-relaxed line-clamp-2">{note.content}</p>
                        <button
                          onClick={() => handleDeleteNote(note.id)}
                          className="absolute right-2 top-2 text-red-500 hover:text-red-700 opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

              </div>

            </div>
          ) : null}
        </div>
      )}

      {/* Create Client Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-lg w-full p-6 space-y-4">
            <h3 className="text-base font-extrabold text-slate-900">Create Client Profile</h3>
            
            <form onSubmit={handleCreateClient} className="space-y-3.5 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Client Name</label>
                  <input
                    type="text"
                    value={clientName}
                    onChange={(e) => setClientName(e.target.value)}
                    placeholder="Suasion Finvest Pvt Ltd"
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold focus:outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Client Type</label>
                  <select
                    value={clientType}
                    onChange={(e) => setClientType(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold focus:outline-none"
                  >
                    <option value="Company">Company</option>
                    <option value="Individual">Individual</option>
                    <option value="Partnership">Partnership</option>
                    <option value="LLP">LLP</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">PAN</label>
                  <input
                    type="text"
                    value={pan}
                    onChange={(e) => setPan(e.target.value)}
                    placeholder="AADCS6785Q"
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">GSTIN</label>
                  <input
                    type="text"
                    value={gstin}
                    onChange={(e) => setGstin(e.target.value)}
                    placeholder="27AADCS6785Q1Z1"
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Registered Address</label>
                <textarea
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="Official office registry address details..."
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold focus:outline-none"
                  rows={2}
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="border border-slate-200 rounded-lg px-4 py-2 font-bold text-slate-500 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-blue-900 hover:bg-blue-950 text-white rounded-lg px-4 py-2 font-bold shadow-sm"
                >
                  Create Client
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
