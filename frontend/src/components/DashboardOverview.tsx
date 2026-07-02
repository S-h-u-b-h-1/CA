import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import {
  Users, FileText, Clock, AlertTriangle, ShieldAlert, Newspaper, Brain,
  ArrowRight, Loader2, CheckCircle2,
} from "lucide-react";

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

const SEVERITY_BADGE: Record<string, string> = {
  CRITICAL: "bg-red-50 text-red-700 border-red-200",
  HIGH: "bg-amber-50 text-amber-700 border-amber-200",
  MEDIUM: "bg-blue-50 text-blue-700 border-blue-200",
  LOW: "bg-slate-50 text-slate-600 border-slate-200",
};

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  stats,
  recentDocuments,
  recentClients,
  onNavigate,
}) => {
  const [complianceDash, setComplianceDash] = useState<any | null>(null);
  const [intelDash, setIntelDash] = useState<any | null>(null);
  const [calendarTasks, setCalendarTasks] = useState<any[]>([]);
  const [authorityUpdates, setAuthorityUpdates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [c, i, cal, updates] = await Promise.all([
          api.getComplianceDashboard().catch(() => null),
          api.getIntelligenceDashboard({ status_filter: "" }).catch(() => null),
          api.getComplianceCalendar().catch(() => []),
          api.searchGovernmentDocuments().catch(() => []),
        ]);
        if (cancelled) return;
        setComplianceDash(c);
        setIntelDash(i);
        setCalendarTasks(cal || []);
        setAuthorityUpdates(Array.isArray(updates) ? updates : []);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const todayStr = new Date().toDateString();
  const dueToday = calendarTasks.filter((t) => t.status !== "COMPLETED" && new Date(t.due_date).toDateString() === todayStr);
  const overdueTasks = calendarTasks.filter((t) => t.status !== "COMPLETED" && new Date(t.due_date) < new Date());

  const suggestions: any[] = intelDash?.suggestions || [];
  const highRiskSuggestions = suggestions.filter((s) => s.rule_key === "COMPLIANCE_HIGH_RISK_CLIENT");
  const priorityItems = suggestions
    .filter((s) => s.severity === "CRITICAL" || s.severity === "HIGH")
    .sort((a, b) => new Date(b.generated_at).getTime() - new Date(a.generated_at).getTime())
    .slice(0, 6);

  const recentSuggestions = [...suggestions]
    .sort((a, b) => new Date(b.generated_at).getTime() - new Date(a.generated_at).getTime())
    .slice(0, 5);

  const recentUpdates = [...authorityUpdates]
    .sort((a, b) => new Date(b.issue_date || 0).getTime() - new Date(a.issue_date || 0).getTime())
    .slice(0, 5);

  const recentDocs = [...recentDocuments]
    .sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime())
    .slice(0, 5);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Dashboard</h1>
        <p className="text-sm text-slate-500 mt-1">
          What needs your attention today — pulled live from Compliance, Intelligence, and Authority Updates.
        </p>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <div onClick={() => onNavigate("clients")} className="bg-white p-5 border border-slate-200 rounded-lg cursor-pointer card-hover card-shadow flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Clients</span>
            <Users className="h-5 w-5 text-blue-900" />
          </div>
          <span className="text-2xl font-black text-slate-900 mt-4">{stats.totalClients}</span>
        </div>

        <div onClick={() => onNavigate("compliance")} className="bg-white p-5 border border-slate-200 rounded-lg cursor-pointer card-hover card-shadow flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Due Today</span>
            <Clock className="h-5 w-5 text-amber-600" />
          </div>
          <span className="text-2xl font-black text-amber-600 mt-4">{complianceDash?.due_today ?? "—"}</span>
        </div>

        <div onClick={() => onNavigate("compliance")} className="bg-white p-5 border border-slate-200 rounded-lg cursor-pointer card-hover card-shadow flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Overdue Filings</span>
            <AlertTriangle className="h-5 w-5 text-red-600" />
          </div>
          <span className="text-2xl font-black text-red-600 mt-4">{complianceDash?.total_returns_overdue ?? "—"}</span>
        </div>

        <div onClick={() => onNavigate("intelligence")} className="bg-white p-5 border border-slate-200 rounded-lg cursor-pointer card-hover card-shadow flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Open Suggestions</span>
            <Brain className="h-5 w-5 text-blue-900" />
          </div>
          <span className="text-2xl font-black text-slate-900 mt-4">{intelDash?.total_open ?? "—"}</span>
        </div>

        <div onClick={() => onNavigate("documents")} className="bg-white p-5 border border-slate-200 rounded-lg cursor-pointer card-hover card-shadow flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Documents</span>
            <FileText className="h-5 w-5 text-slate-700" />
          </div>
          <span className="text-2xl font-black text-slate-900 mt-4">{stats.totalDocuments}</span>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-16 space-y-2">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
          <p className="text-xs text-slate-500 font-semibold">Loading workspace...</p>
        </div>
      ) : (
        <>
          {/* Today's Priorities */}
          <div className="bg-white border border-slate-200 rounded-lg card-shadow">
            <div className="px-5 py-4 border-b border-slate-100 flex justify-between items-center">
              <h3 className="font-bold text-slate-900 flex items-center gap-2"><ShieldAlert className="h-4 w-4 text-red-600" /> Today's Priorities</h3>
              <button onClick={() => onNavigate("intelligence")} className="text-xs font-semibold text-blue-900 hover:underline flex items-center gap-1">
                View All <ArrowRight className="h-3 w-3" />
              </button>
            </div>
            <div className="divide-y divide-slate-100">
              {priorityItems.length === 0 && overdueTasks.length === 0 && dueToday.length === 0 ? (
                <div className="p-8 text-center text-sm text-slate-500 flex flex-col items-center gap-2">
                  <CheckCircle2 className="h-6 w-6 text-emerald-500" />
                  Nothing urgent right now.
                </div>
              ) : (
                <>
                  {overdueTasks.slice(0, 3).map((t) => (
                    <div key={t.id} className="px-5 py-3 flex items-center justify-between text-sm">
                      <span className="text-slate-700">Overdue: {t.task_name}</span>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-50 text-red-700 border border-red-200">OVERDUE</span>
                    </div>
                  ))}
                  {priorityItems.map((s) => (
                    <div key={s.id} className="px-5 py-3 flex items-center justify-between text-sm">
                      <span className="text-slate-700">{s.title}</span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${SEVERITY_BADGE[s.severity]}`}>{s.severity}</span>
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* High-Risk Clients */}
            <div className="bg-white border border-slate-200 rounded-lg card-shadow">
              <div className="px-5 py-4 border-b border-slate-100 flex justify-between items-center">
                <h3 className="font-bold text-slate-900">High-Risk Clients</h3>
                <button onClick={() => onNavigate("intelligence")} className="text-xs font-semibold text-blue-900 hover:underline">View All</button>
              </div>
              <div className="divide-y divide-slate-100">
                {highRiskSuggestions.length === 0 ? (
                  <div className="p-8 text-center text-sm text-slate-500">No high-risk clients flagged right now.</div>
                ) : (
                  highRiskSuggestions.slice(0, 5).map((s) => (
                    <div key={s.id} className="px-5 py-3 text-sm">
                      <p className="font-semibold text-slate-800">{s.client_name}</p>
                      <p className="text-xs text-slate-500">{s.title}</p>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Recent Authority Updates */}
            <div className="bg-white border border-slate-200 rounded-lg card-shadow">
              <div className="px-5 py-4 border-b border-slate-100 flex justify-between items-center">
                <h3 className="font-bold text-slate-900 flex items-center gap-2"><Newspaper className="h-4 w-4 text-slate-500" /> Recent Authority Updates</h3>
                <button onClick={() => onNavigate("govknowledge")} className="text-xs font-semibold text-blue-900 hover:underline">View All</button>
              </div>
              <div className="divide-y divide-slate-100">
                {recentUpdates.length === 0 ? (
                  <div className="p-8 text-center text-sm text-slate-500">No authority updates ingested yet.</div>
                ) : (
                  recentUpdates.map((u) => (
                    <div key={u.id} className="px-5 py-3 text-sm">
                      <p className="font-semibold text-slate-800 truncate">{u.title}</p>
                      <p className="text-xs text-slate-500">{u.issuing_authority} · {u.issue_date ? new Date(u.issue_date).toLocaleDateString() : "—"}</p>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Recent Intelligence Suggestions */}
            <div className="bg-white border border-slate-200 rounded-lg card-shadow">
              <div className="px-5 py-4 border-b border-slate-100 flex justify-between items-center">
                <h3 className="font-bold text-slate-900 flex items-center gap-2"><Brain className="h-4 w-4 text-blue-900" /> Recent Intelligence Suggestions</h3>
                <button onClick={() => onNavigate("intelligence")} className="text-xs font-semibold text-blue-900 hover:underline">View All</button>
              </div>
              <div className="divide-y divide-slate-100">
                {recentSuggestions.length === 0 ? (
                  <div className="p-8 text-center text-sm text-slate-500">No suggestions generated yet.</div>
                ) : (
                  recentSuggestions.map((s) => (
                    <div key={s.id} className="px-5 py-3 flex items-center justify-between text-sm">
                      <div className="min-w-0">
                        <p className="font-semibold text-slate-800 truncate">{s.title}</p>
                        <p className="text-xs text-slate-500">{s.client_name}</p>
                      </div>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border shrink-0 ml-2 ${SEVERITY_BADGE[s.severity]}`}>{s.severity}</span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Recently Uploaded Documents */}
            <div className="bg-white border border-slate-200 rounded-lg card-shadow">
              <div className="px-5 py-4 border-b border-slate-100 flex justify-between items-center">
                <h3 className="font-bold text-slate-900">Recently Uploaded Documents</h3>
                <button onClick={() => onNavigate("documents")} className="text-xs font-semibold text-blue-900 hover:underline">View All</button>
              </div>
              <div className="divide-y divide-slate-100">
                {recentDocs.length === 0 ? (
                  <div className="p-8 text-center text-sm text-slate-500">No documents uploaded yet.</div>
                ) : (
                  recentDocs.map((doc) => (
                    <div key={doc.id} className="px-5 py-3 flex items-center justify-between text-sm">
                      <span className="font-medium text-slate-800 truncate max-w-[220px]">{doc.name}</span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        doc.processing_status === "COMPLETED" ? "bg-emerald-50 text-emerald-700"
                        : doc.processing_status === "PROCESSING" ? "bg-blue-50 text-blue-700"
                        : "bg-amber-50 text-amber-700"
                      }`}>{doc.processing_status}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Recent Clients */}
          <div className="bg-white border border-slate-200 rounded-lg card-shadow">
            <div className="px-5 py-4 border-b border-slate-100 flex justify-between items-center">
              <h3 className="font-bold text-slate-900">Recent Clients</h3>
              <button onClick={() => onNavigate("clients")} className="text-xs font-semibold text-blue-900 hover:underline">View All</button>
            </div>
            <div className="p-0 overflow-x-auto">
              {recentClients.length === 0 ? (
                <div className="p-8 text-center text-sm text-slate-500">No clients added yet.</div>
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
        </>
      )}
    </div>
  );
};
