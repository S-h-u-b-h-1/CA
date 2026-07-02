import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import { Brain, RefreshCcw, Loader2, CheckCircle2, Newspaper } from "lucide-react";
import { SuggestionCard, SEVERITY_ORDER } from "./IntelligenceDashboard";

interface ClientIntelligencePanelProps {
  clientId: string;
}

export const ClientIntelligencePanel: React.FC<ClientIntelligencePanelProps> = ({ clientId }) => {
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clientId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const rows = await api.getClientSuggestions(clientId);
      setSuggestions(rows);
    } catch {
      setSuggestions([]);
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerate = async () => {
    setRegenerating(true);
    try {
      await api.regenerateIntelligence(clientId);
      await loadData();
    } finally {
      setRegenerating(false);
    }
  };

  const handleTransition = async (suggestionId: string, newStatus: string, reason?: string) => {
    await api.updateSuggestionStatus(suggestionId, newStatus, reason);
    await loadData();
  };

  const active = suggestions.filter((s) => s.status === "NEW" || s.status === "ACKNOWLEDGED" || s.status === "IN_PROGRESS");
  const authorityUpdateSuggestions = active.filter((s) => s.rule_key === "RESEARCH_AUTHORITY_UPDATE_MATCH");
  const otherByCategory: Record<string, any[]> = {};
  active.filter((s) => s.rule_key !== "RESEARCH_AUTHORITY_UPDATE_MATCH").forEach((s) => {
    otherByCategory[s.category] = otherByCategory[s.category] || [];
    otherByCategory[s.category].push(s);
  });

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16 space-y-2">
        <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        <p className="text-xs text-slate-500 font-semibold">Loading intelligence...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="h-5 w-5 text-blue-900" />
          <h3 className="font-extrabold text-base text-slate-800">Intelligence Suggestions</h3>
          <span className="text-xs font-bold text-slate-400">({active.length} active)</span>
        </div>
        <button
          onClick={handleRegenerate}
          disabled={regenerating}
          className="flex items-center gap-1.5 bg-blue-900 hover:bg-blue-800 text-white px-3 py-1.5 rounded-lg text-xs font-bold disabled:opacity-50"
        >
          {regenerating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCcw className="h-3.5 w-3.5" />}
          Regenerate
        </button>
      </div>

      {active.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 space-y-2 bg-slate-50 rounded-xl border border-slate-100">
          <CheckCircle2 className="h-6 w-6 text-emerald-500" />
          <p className="text-xs text-slate-500 font-semibold">Nothing needs attention for this client right now.</p>
        </div>
      ) : (
        <div className="space-y-5">
          {authorityUpdateSuggestions.length > 0 && (
            <div>
              <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5">
                <Newspaper className="h-3.5 w-3.5" /> Authority Updates Relevant to This Client
              </h4>
              <div className="space-y-2">
                {authorityUpdateSuggestions.map((s) => (
                  <SuggestionCard key={s.id} suggestion={s} expanded={expandedId === s.id} onToggle={() => setExpandedId(expandedId === s.id ? null : s.id)} onTransition={handleTransition} />
                ))}
              </div>
            </div>
          )}

          {Object.keys(otherByCategory).map((category) => (
            <div key={category}>
              <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-500 mb-2">{category} ({otherByCategory[category].length})</h4>
              <div className="space-y-2">
                {otherByCategory[category]
                  .sort((a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity))
                  .map((s) => (
                    <SuggestionCard key={s.id} suggestion={s} expanded={expandedId === s.id} onToggle={() => setExpandedId(expandedId === s.id ? null : s.id)} onTransition={handleTransition} />
                  ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
