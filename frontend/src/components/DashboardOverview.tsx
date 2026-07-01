import React from "react";
import { Users, FileText, Database, Radio, RefreshCcw, CheckCircle, Clock } from "lucide-react";

interface DashboardOverviewProps {
  stats: {
    totalClients: number;
    totalDocuments: number;
    pendingProcessing: number;
    connectedSources: number;
    akkcConnected: boolean;
  };
  recentDocuments: any[];
  recentClients: any[];
  onNavigate: (tab: string) => void;
}

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  stats,
  recentDocuments,
  recentClients,
  onNavigate
}) => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          Dashboard Overview
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Welcome to CA Intelligence. Here is the operational summary of your firm's AI OS workspace.
        </p>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Total Clients Card */}
        <div 
          onClick={() => onNavigate("clients")}
          className="bg-white p-5 border border-slate-200 rounded-lg cursor-pointer card-hover card-shadow flex flex-col justify-between"
        >
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Clients</span>
            <Users className="h-5 w-5 text-blue-900" />
          </div>
          <div className="mt-4">
            <span className="text-2xl font-black text-slate-900">{stats.totalClients}</span>
          </div>
        </div>

        {/* Documents Card */}
        <div 
          onClick={() => onNavigate("documents")}
          className="bg-white p-5 border border-slate-200 rounded-lg cursor-pointer card-hover card-shadow flex flex-col justify-between"
        >
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Documents</span>
            <FileText className="h-5 w-5 text-slate-700" />
          </div>
          <div className="mt-4">
            <span className="text-2xl font-black text-slate-900">{stats.totalDocuments}</span>
          </div>
        </div>

        {/* Pending OCR Processing Card */}
        <div 
          onClick={() => onNavigate("documents")}
          className="bg-white p-5 border border-slate-200 rounded-lg cursor-pointer card-hover card-shadow flex flex-col justify-between"
        >
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Pending AI</span>
            <Clock className="h-5 w-5 text-amber-600" />
          </div>
          <div className="mt-4">
            <span className="text-2xl font-black text-amber-600">{stats.pendingProcessing}</span>
          </div>
        </div>

        {/* Compliance Sources Card */}
        <div 
          onClick={() => onNavigate("compliance")}
          className="bg-white p-5 border border-slate-200 rounded-lg cursor-pointer card-hover card-shadow flex flex-col justify-between"
        >
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Sources Active</span>
            <Database className="h-5 w-5 text-emerald-600" />
          </div>
          <div className="mt-4">
            <span className="text-2xl font-black text-slate-900">{stats.connectedSources}</span>
          </div>
        </div>

        {/* AKKC Status Card */}
        <div 
          onClick={() => onNavigate("integrations")}
          className="bg-white p-5 border border-slate-200 rounded-lg cursor-pointer card-hover card-shadow flex flex-col justify-between"
        >
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">AKKC Sync</span>
            <RefreshCcw className={`h-5 w-5 ${stats.akkcConnected ? 'text-blue-900' : 'text-slate-400'}`} />
          </div>
          <div className="mt-4 flex items-center space-x-2">
            <span className={`text-sm font-bold ${stats.akkcConnected ? 'text-blue-900' : 'text-slate-500'}`}>
              {stats.akkcConnected ? "Connected" : "Disconnected"}
            </span>
          </div>
        </div>
      </div>

      {/* Recents Lists Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Documents Card */}
        <div className="bg-white border border-slate-200 rounded-lg card-shadow">
          <div className="px-5 py-4 border-b border-slate-100 flex justify-between items-center">
            <h3 className="font-bold text-slate-900">Recent Documents</h3>
            <button 
              onClick={() => onNavigate("documents")}
              className="text-xs font-semibold text-blue-900 hover:underline"
            >
              View All
            </button>
          </div>
          <div className="p-0 overflow-x-auto">
            {recentDocuments.length === 0 ? (
              <div className="p-8 text-center text-sm text-slate-500">
                No documents uploaded yet.
              </div>
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="bg-slate-50 text-xs font-semibold text-slate-500 border-b border-slate-100">
                    <th className="py-2 px-4">Document Name</th>
                    <th className="py-2 px-4">Category</th>
                    <th className="py-2 px-4">AI Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {recentDocuments.slice(0, 5).map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-50/50">
                      <td className="py-3 px-4 font-medium text-slate-800 truncate max-w-[200px]">{doc.name}</td>
                      <td className="py-3 px-4 text-slate-500 text-xs">{doc.category}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          doc.processing_status === "COMPLETED" 
                            ? "bg-emerald-50 text-emerald-700" 
                            : doc.processing_status === "PROCESSING"
                            ? "bg-blue-50 text-blue-700"
                            : "bg-amber-50 text-amber-700"
                        }`}>
                          {doc.processing_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Recent Clients Card */}
        <div className="bg-white border border-slate-200 rounded-lg card-shadow">
          <div className="px-5 py-4 border-b border-slate-100 flex justify-between items-center">
            <h3 className="font-bold text-slate-900">Recent Clients</h3>
            <button 
              onClick={() => onNavigate("clients")}
              className="text-xs font-semibold text-blue-900 hover:underline"
            >
              View All
            </button>
          </div>
          <div className="p-0 overflow-x-auto">
            {recentClients.length === 0 ? (
              <div className="p-8 text-center text-sm text-slate-500">
                No clients added yet.
              </div>
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="bg-slate-50 text-xs font-semibold text-slate-500 border-b border-slate-100">
                    <th className="py-2 px-4">Client Name</th>
                    <th className="py-2 px-4">Entity Type</th>
                    <th className="py-2 px-4">PAN</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {recentClients.slice(0, 5).map((cli) => (
                    <tr key={cli.id} className="hover:bg-slate-50/50">
                      <td className="py-3 px-4 font-medium text-slate-800">{cli.client_name}</td>
                      <td className="py-3 px-4 text-slate-500 text-xs">{cli.client_type}</td>
                      <td className="py-3 px-4 text-slate-600 font-mono text-xs">{cli.PAN || "N/A"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
