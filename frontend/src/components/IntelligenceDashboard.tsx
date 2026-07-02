import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import {
  Brain, AlertTriangle, AlertCircle, Info, CheckCircle2, RefreshCcw,
  ChevronDown, ChevronUp, XCircle, PlayCircle, ThumbsUp, FileText, Loader2,
} from "lucide-react";

interface IntelligenceDashboardProps {
  clients: any[];
}

export const SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

export const SEVERITY_STYLES: Record<string, { bg: string; text: string; border: string; icon: any }> = {
  CRITICAL: { bg: "bg-red-50", text: "text-red-700", border: "border-red-200", icon: AlertTriangle },
  HIGH: { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200", icon: AlertCircle },
  MEDIUM: { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200", icon: Info },
  LOW: { bg: "bg-slate-50", text: "text-slate-600", border: "border-slate-200", icon: Info },
};

const CONFIDENCE_STYLES: Record<string, string> = {
  HIGH: "bg-emerald-50 text-emerald-700 border-emerald-200",
  MEDIUM: "bg-slate-100 text-slate-600 border-slate-200",
  LOW: "bg-slate-50 text-slate-400 border-slate-200",
};

const NEXT_STATUS: Record<string, { label: string; icon: any }> = {
  NEW: { label: "Acknowledge", icon: ThumbsUp },
  ACKNOWLEDGED: { label: "Start Work", icon: PlayCircle },
  IN_PROGRESS: { label: "Mark Resolved", icon: CheckCircle2 },
};

const TRANSITION_TARGET: Record<string, string> = {
  NEW: "ACKNOWLEDGED",
  ACKNOWLEDGED: "IN_PROGRESS",
  IN_PROGRESS: "RESOLVED",
};

export const IntelligenceDashboard: React.FC<IntelligenceDashboardProps> = ({ clients }) => {
  const [dashboard, setDashboard] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const [filterClient, setFilterClient] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [filterSeverity, setFilterSeverity] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  useEffect(() => {
    loadDashboard();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterClient, filterCategory, filterSeverity, filterStatus]);

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getIntelligenceDashboard({
        client_id: filterClient || undefined,
        category: filterCategory || undefined,
        severity: filterSeverity || undefined,
        status_filter: filterStatus || undefined,
      });
      setDashboard(data);
    } catch (err: any) {
      setError(err.message || "Failed to load intelligence dashboard");
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerate = async () => {
    setRegenerating(true);
    try {
      await api.regenerateIntelligenceForOrganization();
      await loadDashboard();
    } catch (err: any) {
      setError(err.message || "Failed to regenerate suggestions");
    } finally {
      setRegenerating(false);
    }
  };

  const handleTransition = async (suggestionId: string, newStatus: string, reason?: string) => {
    try {
      await api.updateSuggestionStatus(suggestionId, newStatus, reason);
      await loadDashboard();
    } catch (err: any) {
      setError(err.message || "Failed to update suggestion");
    }
  };

  const grouped: Record<string, any[]> = { CRITICAL: [], HIGH: [], MEDIUM: [], LOW: [] };
  (dashboard?.suggestions || []).forEach((s: any) => {
    if (grouped[s.severity]) grouped[s.severity].push(s);
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-slate-900 flex items-center gap-2">
            <Brain className="h-6 w-6 text-blue-900" />
            Intelligence Dashboard
          </h1>
          <p className="text-sm text-slate-500 mt-1">What requires your attention today — every suggestion is evidence-backed and traceable to a real record.</p>
        </div>
        <button
          onClick={handleRegenerate}
          disabled={regenerating}
          className="flex items-center gap-2 bg-blue-900 hover:bg-blue-800 text-white px-4 py-2 rounded-lg text-sm font-bold disabled:opacity-50"
        >
          {regenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCcw className="h-4 w-4" />}
          Regenerate
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
      )}

      {/* Severity stat strip */}
      <div className="grid grid-cols-4 gap-4">
        {SEVERITY_ORDER.map((sev) => {
          const style = SEVERITY_STYLES[sev];
          const Icon = style.icon;
          const count = dashboard ? dashboard[`${sev.toLowerCase()}_count`] : 0;
          return (
            <div key={sev} className={`p-4 rounded-xl border ${style.border} ${style.bg}`}>
              <div className="flex items-center justify-between">
                <p className={`text-[10px] uppercase font-bold tracking-wider ${style.text}`}>{sev}</p>
                <Icon className={`h-4 w-4 ${style.text}`} />
              </div>
              <span className={`text-2xl font-black ${style.text}`}>{count ?? 0}</span>
            </div>
          );
        })}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 bg-white p-3 rounded-xl border border-slate-200">
        <select value={filterClient} onChange={(e) => setFilterClient(e.target.value)} className="text-xs font-semibold border border-slate-200 rounded-lg px-3 py-2 text-slate-700">
          <option value="">All Clients</option>
          {clients.map((c) => (
            <option key={c.id} value={c.id}>{c.client_name}</option>
          ))}
        </select>
        <select value={filterCategory} onChange={(e) => setFilterCategory(e.target.value)} className="text-xs font-semibold border border-slate-200 rounded-lg px-3 py-2 text-slate-700">
          <option value="">All Categories</option>
          <option value="TAX">Tax</option>
          <option value="COMPLIANCE">Compliance</option>
          <option value="DOCUMENTS">Documents</option>
          <option value="RESEARCH">Research</option>
        </select>
        <select value={filterSeverity} onChange={(e) => setFilterSeverity(e.target.value)} className="text-xs font-semibold border border-slate-200 rounded-lg px-3 py-2 text-slate-700">
          <option value="">All Severities</option>
          {SEVERITY_ORDER.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="text-xs font-semibold border border-slate-200 rounded-lg px-3 py-2 text-slate-700">
          <option value="">Active (New / Acknowledged / In Progress)</option>
          <option value="NEW">New</option>
          <option value="ACKNOWLEDGED">Acknowledged</option>
          <option value="IN_PROGRESS">In Progress</option>
          <option value="RESOLVED">Resolved</option>
          <option value="DISMISSED">Dismissed</option>
        </select>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-16 space-y-2">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
          <p className="text-xs text-slate-500 font-semibold">Loading suggestions...</p>
        </div>
      ) : (dashboard?.suggestions || []).length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 space-y-2 bg-white rounded-xl border border-slate-200">
          <CheckCircle2 className="h-8 w-8 text-emerald-500" />
          <p className="text-sm font-bold text-slate-700">Nothing needs attention right now.</p>
          <p className="text-xs text-slate-400">Click Regenerate after new documents, tasks, or filings are added.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {SEVERITY_ORDER.filter((sev) => grouped[sev].length > 0).map((sev) => (
            <div key={sev}>
              <h3 className={`text-xs font-extrabold uppercase tracking-wider mb-2 ${SEVERITY_STYLES[sev].text}`}>
                {sev} ({grouped[sev].length})
              </h3>
              <div className="space-y-2">
                {grouped[sev].map((s: any) => (
                  <SuggestionCard
                    key={s.id}
                    suggestion={s}
                    expanded={expandedId === s.id}
                    onToggle={() => setExpandedId(expandedId === s.id ? null : s.id)}
                    onTransition={handleTransition}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export const SuggestionCard: React.FC<{
  suggestion: any;
  expanded: boolean;
  onToggle: () => void;
  onTransition: (id: string, status: string, reason?: string) => void;
}> = ({ suggestion, expanded, onToggle, onTransition }) => {
  const style = SEVERITY_STYLES[suggestion.severity] || SEVERITY_STYLES.LOW;
  const nextAction = NEXT_STATUS[suggestion.status];
  const nextStatusValue = TRANSITION_TARGET[suggestion.status];

  return (
    <div className={`bg-white rounded-xl border ${style.border} overflow-hidden`}>
      <button onClick={onToggle} className="w-full flex items-start justify-between p-4 text-left hover:bg-slate-50">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-bold text-slate-800">{suggestion.title}</span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${CONFIDENCE_STYLES[suggestion.confidence]}`}>
              {suggestion.confidence} CONFIDENCE
            </span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">{suggestion.category}</span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">{suggestion.status.replace("_", " ")}</span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {suggestion.client_name} · generated {new Date(suggestion.generated_at).toLocaleDateString()}
          </p>
        </div>
        {expanded ? <ChevronUp className="h-4 w-4 text-slate-400 shrink-0" /> : <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" />}
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-slate-100 pt-3 space-y-3">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Why this was generated</p>
            <p className="text-sm text-slate-700">{suggestion.explanation}</p>
          </div>

          {suggestion.recommendation && (
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Recommendation</p>
              <p className="text-sm text-slate-700">{suggestion.recommendation}</p>
            </div>
          )}

          {suggestion.confidence_reason && (
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Confidence basis</p>
              <p className="text-xs text-slate-500">{suggestion.confidence_reason}</p>
            </div>
          )}

          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Evidence ({suggestion.evidence.length})</p>
            <div className="space-y-1.5">
              {suggestion.evidence.map((e: any) => (
                <div key={e.id} className="flex items-start gap-2 text-xs bg-slate-50 border border-slate-100 rounded-lg p-2">
                  <FileText className="h-3.5 w-3.5 text-slate-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold text-slate-600">{e.evidence_type.replace(/_/g, " ")}: </span>
                    <span className="text-slate-600">{e.summary}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2 pt-2">
            {nextAction && nextStatusValue && (
              <button
                onClick={() => onTransition(suggestion.id, nextStatusValue)}
                className="flex items-center gap-1.5 bg-blue-900 hover:bg-blue-800 text-white text-xs font-bold px-3 py-1.5 rounded-lg"
              >
                <nextAction.icon className="h-3.5 w-3.5" />
                {nextAction.label}
              </button>
            )}
            {(suggestion.status === "NEW" || suggestion.status === "ACKNOWLEDGED" || suggestion.status === "IN_PROGRESS") && (
              <button
                onClick={() => onTransition(suggestion.id, "DISMISSED", "Dismissed from Intelligence Dashboard")}
                className="flex items-center gap-1.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 text-xs font-bold px-3 py-1.5 rounded-lg"
              >
                <XCircle className="h-3.5 w-3.5" />
                Dismiss
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
