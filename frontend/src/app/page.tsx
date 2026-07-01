"use client";

import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import { AuthPanel } from "../components/AuthPanel";
import { DashboardOverview } from "../components/DashboardOverview";
import { ClientWorkspace } from "../components/ClientWorkspace";
import { DocumentIntelligence } from "../components/DocumentIntelligence";
import { AISearch } from "../components/AISearch";
import { ComplianceRegistry } from "../components/ComplianceRegistry";
import { AKKCIntegration } from "../components/AKKCIntegration";
import { SettingsPanel } from "../components/SettingsPanel";
import DataPipelineDashboard from "../components/DataPipelineDashboard";
import GovernmentKnowledgeCenter from "../components/GovernmentKnowledgeCenter";
import { KnowledgeGraphDashboard } from "../components/KnowledgeGraphDashboard";


import { 
  Building2, Users, FileText, Search, Database, RefreshCcw, 
  Settings, LogOut, Loader2, PanelLeftClose, PanelLeft, Sparkles, Bell, Cpu, ShieldCheck, GitFork, BookOpen
} from "lucide-react";
import { ResearchWorkspace } from "../components/ResearchWorkspace";

export default function Home() {
  const [user, setUser] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("dashboard"); // dashboard, clients, documents, search, compliance, integrations, settings
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Global State Stores
  const [clients, setClients] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [complianceSources, setComplianceSources] = useState<any[]>([]);
  const [sysConfig, setSysConfig] = useState<any | null>(null);
  
  // Navigation helper for detail modals inside universal search
  const [deepOpenClient, setDeepOpenClient] = useState<any | null>(null);
  const [deepOpenDoc, setDeepOpenDoc] = useState<any | null>(null);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = api.getToken();
    if (token) {
      try {
        const u = await api.getMe();
        setUser(u);
        loadWorkspaceData();
        loadSystemConfig();
      } catch (err) {
        api.clearToken();
        setUser(null);
      }
    }
    setLoading(false);
  };

  const loadSystemConfig = async () => {
    try {
      const config = await api.getSystemConfig();
      setSysConfig(config);
    } catch (err) {
      console.error("Failed to load system config:", err);
    }
  };

  const loadWorkspaceData = async () => {
    try {
      const [c, d, s] = await Promise.all([
        api.listClients(),
        api.listDocuments(),
        api.listComplianceSources(),
      ]);
      setClients(c);
      setDocuments(d);
      setComplianceSources(s);
    } catch (err) {
      console.error("Error loading workspace details:", err);
    }
  };

  const handleAuthSuccess = (u: any) => {
    setUser(u);
    loadWorkspaceData();
    loadSystemConfig();
  };

  const handleLogout = () => {
    api.clearToken();
    setUser(null);
    setActiveTab("dashboard");
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center space-y-2">
        <Loader2 className="h-8 w-8 text-blue-900 animate-spin" />
        <span className="text-sm text-slate-500 font-semibold">Loading CA Intelligence Workspace...</span>
      </div>
    );
  }

  if (!user) {
    return <AuthPanel onAuthSuccess={handleAuthSuccess} />;
  }

  // Statistics calculation
  const totalClients = clients.length;
  const totalDocuments = documents.length;
  const pendingProcessing = documents.filter(d => d.processing_status === "PENDING" || d.processing_status === "PROCESSING").length;
  const connectedSources = complianceSources.filter(s => s.status === "ACTIVE").length;
  // Check if AKKC connection is stored in db
  const akkcConnected = true; // Simulated boolean or read from integration status

  const sidebarLinks = [
    { id: "dashboard", label: "Dashboard", icon: Building2 },
    { id: "clients", label: "Clients Workspace", icon: Users },
    { id: "research", label: "Research Workspace", icon: BookOpen },
    { id: "documents", label: "Documents", icon: FileText },
    { id: "search", label: "AI Search", icon: Search },
    { id: "graph", label: "Knowledge Graph", icon: GitFork },
    { id: "datapipeline", label: "Data Ingestion", icon: Cpu },
    { id: "govknowledge", label: "Gov Ingestion", icon: ShieldCheck },
    { id: "compliance", label: "Compliance Sources", icon: Database },
    { id: "integrations", label: "Integrations", icon: RefreshCcw },
    { id: "settings", label: "Settings", icon: Settings },
  ];

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar Navigation */}
      <aside className={`bg-white border-r border-slate-200 transition-all duration-300 flex flex-col ${
        sidebarOpen ? "w-64" : "w-16"
      }`}>
        {/* Brand */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-slate-200">
          {sidebarOpen ? (
            <div className="flex items-center space-x-2">
              <span className="font-extrabold text-slate-900 text-lg tracking-tight">CA Intelligence</span>
              <span className="text-[9px] bg-blue-50 text-blue-900 px-1.5 py-0.5 rounded-full font-bold">MVP</span>
            </div>
          ) : (
            <Sparkles className="h-5 w-5 text-blue-900 mx-auto" />
          )}
          <button 
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-600 transition-colors"
          >
            {sidebarOpen ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeft className="h-4 w-4" />}
          </button>
        </div>

        {/* Links */}
        <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
          {sidebarLinks.map((link) => {
            const Icon = link.icon;
            const isActive = activeTab === link.id;
            return (
              <button
                key={link.id}
                onClick={() => {
                  setActiveTab(link.id);
                  setDeepOpenClient(null);
                  setDeepOpenDoc(null);
                }}
                className={`w-full flex items-center py-2 px-3 rounded-md text-sm font-semibold transition-all ${
                  isActive 
                    ? "bg-slate-100 text-blue-900 border-l-4 border-blue-900 rounded-l-none" 
                    : "text-slate-600 hover:bg-slate-50 hover:text-blue-900"
                }`}
                title={link.label}
              >
                <Icon className={`h-4.5 w-4.5 shrink-0 ${isActive ? "text-blue-900" : "text-slate-400"} ${sidebarOpen ? "mr-3" : "mx-auto"}`} />
                {sidebarOpen && <span>{link.label}</span>}
              </button>
            );
          })}
        </nav>

        {/* Logout Footer */}
        <div className="p-2 border-t border-slate-200">
          <button
            onClick={handleLogout}
            className="w-full flex items-center py-2 px-3 rounded-md text-sm font-semibold text-red-600 hover:bg-red-50 transition-colors"
            title="Log Out"
          >
            <LogOut className={`h-4.5 w-4.5 shrink-0 text-red-500 ${sidebarOpen ? "mr-3" : "mx-auto"}`} />
            {sidebarOpen && <span>Log Out</span>}
          </button>
        </div>
      </aside>

      {/* Main Workspace Frame */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold text-slate-500">Firm Workspace:</span>
            <span className="text-sm font-bold text-slate-800 uppercase tracking-wider">{user?.email?.split('@')[0]} Office</span>
          </div>
          
          <div className="flex items-center space-x-4">
            {sysConfig && (sysConfig.llm_provider === "mock" || sysConfig.ocr_provider === "mock" || sysConfig.embedding_provider === "mock") && (
              <span className="flex items-center gap-1.5 px-3 py-1 bg-amber-50 border border-amber-200 text-amber-800 rounded-lg text-xs font-semibold select-none shadow-sm">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
                ⚠️ Sandbox Simulation Mode Active
              </span>
            )}
            <button className="p-1.5 hover:bg-slate-50 border border-slate-200 rounded-full text-slate-400 hover:text-slate-600 relative">
              <Bell className="h-4 w-4" />
              {pendingProcessing > 0 && (
                <span className="absolute top-0 right-0 h-2 w-2 bg-amber-500 rounded-full" />
              )}
            </button>
            <div className="h-8 w-px bg-slate-200" />
            <div className="flex items-center space-x-2 text-sm">
              <span className="font-semibold text-slate-700">{user?.first_name} {user?.last_name}</span>
              <span className="text-[10px] bg-slate-100 text-slate-600 font-bold px-2 py-0.5 rounded-full uppercase">
                {user?.role?.replace('_', ' ')}
              </span>
            </div>
          </div>
        </header>

        {/* Content View */}
        <main className="flex-grow p-6 overflow-y-auto max-w-7xl w-full mx-auto">
          {activeTab === "dashboard" && (
            <DashboardOverview 
              stats={{ totalClients, totalDocuments, pendingProcessing, connectedSources, akkcConnected }} 
              recentDocuments={documents}
              recentClients={clients}
              onNavigate={(tab) => setActiveTab(tab)}
            />
          )}

          {activeTab === "clients" && (
            <ClientWorkspace clients={clients} onRefresh={loadWorkspaceData} />
          )}

          {activeTab === "documents" && (
            <DocumentIntelligence documents={documents} clients={clients} onRefresh={loadWorkspaceData} />
          )}

          {activeTab === "research" && (
            <ResearchWorkspace />
          )}

          {activeTab === "search" && (
            <AISearch 
              onOpenClient={(c) => {
                setActiveTab("clients");
                // Deep link select client logic is handled in the child workspace
              }}
              onOpenDocument={(d) => {
                setActiveTab("documents");
              }}
            />
          )}

          {activeTab === "compliance" && (
            <ComplianceRegistry sources={complianceSources} currentUser={user} onRefresh={loadWorkspaceData} />
          )}

          {activeTab === "graph" && (
            <KnowledgeGraphDashboard />
          )}

          {activeTab === "datapipeline" && (
            <DataPipelineDashboard />
          )}

          {activeTab === "govknowledge" && (
            <GovernmentKnowledgeCenter />
          )}

          {activeTab === "integrations" && (
            <AKKCIntegration onRefreshClients={loadWorkspaceData} onRefreshDocs={loadWorkspaceData} />
          )}

          {activeTab === "settings" && (
            <SettingsPanel currentUser={user} onRefreshUser={checkAuth} />
          )}
        </main>
      </div>
    </div>
  );
}
