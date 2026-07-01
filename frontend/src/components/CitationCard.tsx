import React, { useState } from "react";
import { ShieldCheck, ShieldAlert, Shield, Loader2, ArrowRight } from "lucide-react";
import { api } from "../lib/api";

interface CitationCardProps {
  citation: {
    id: string;
    source_type: string;
    quote_text?: string;
    section_reference?: string;
    act_reference?: string;
    rule_reference?: string;
    text_reference: string;
    confidence_score: number;
  };
  onVerified?: (result: any) => void;
}

export const CitationCard: React.FC<CitationCardProps> = ({ citation, onVerified }) => {
  const [loading, setLoading] = useState(false);
  const [verification, setVerification] = useState<any>(null);

  const handleVerify = async () => {
    setLoading(true);
    try {
      const res = await api.verifyCitation(citation.id);
      setVerification(res);
      if (onVerified) onVerified(res);
    } catch (err) {
      console.error("Verification failed", err);
      setVerification({
        status: "FAILED",
        details: { message: "Internal server error connecting to verification engine." }
      });
    } finally {
      setLoading(false);
    }
  };

  const getSourceBadgeColor = (type: string) => {
    switch (type) {
      case "GOVERNMENT_UPDATE":
        return "bg-purple-100 text-purple-800 border-purple-200";
      case "CLIENT_DOCUMENT":
      default:
        return "bg-blue-100 text-blue-800 border-blue-200";
    }
  };

  const formatSourceType = (type: string) => {
    return type === "GOVERNMENT_UPDATE" ? "Gov Update" : "Client Document";
  };

  return (
    <div className="bg-white p-5 border border-slate-200 rounded-lg shadow-sm space-y-4 relative overflow-hidden transition-all duration-200 hover:shadow-md hover:border-slate-300">
      {/* Top row */}
      <div className="flex justify-between items-start gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 border rounded-full ${getSourceBadgeColor(citation.source_type)}`}>
              {formatSourceType(citation.source_type)}
            </span>
            {citation.confidence_score && (
              <span className="text-[10px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full border border-slate-200">
                Confidence: {Math.round(citation.confidence_score * 100)}%
              </span>
            )}
          </div>
          <h4 className="text-sm font-bold text-slate-900 mt-1">
            {citation.act_reference ? `${citation.act_reference}` : "Legal Citation"}
            {citation.section_reference && ` • Sec ${citation.section_reference}`}
            {citation.rule_reference && ` • Rule ${citation.rule_reference}`}
          </h4>
        </div>

        {/* Status Indicator */}
        <div className="shrink-0">
          {verification?.status === "VERIFIED" ? (
            <div className="flex items-center gap-1 text-emerald-600 bg-emerald-50 px-2 py-1 rounded-md border border-emerald-200 text-xs font-semibold">
              <ShieldCheck className="h-4 w-4" />
              <span>Verified</span>
            </div>
          ) : verification?.status === "PARTIALLY_VERIFIED" ? (
            <div className="flex items-center gap-1 text-amber-600 bg-amber-50 px-2 py-1 rounded-md border border-amber-200 text-xs font-semibold">
              <ShieldCheck className="h-4 w-4" />
              <span>Partial</span>
            </div>
          ) : verification?.status === "FAILED" ? (
            <div className="flex items-center gap-1 text-rose-600 bg-rose-50 px-2 py-1 rounded-md border border-rose-200 text-xs font-semibold">
              <ShieldAlert className="h-4 w-4" />
              <span>Failed</span>
            </div>
          ) : (
            <div className="flex items-center gap-1 text-slate-500 bg-slate-50 px-2 py-1 rounded-md border border-slate-200 text-xs">
              <Shield className="h-4 w-4" />
              <span>Unverified</span>
            </div>
          )}
        </div>
      </div>

      {/* Quote Block */}
      {citation.quote_text && (
        <div className="bg-slate-50 p-3 rounded border border-slate-100 text-xs text-slate-700 italic border-l-4 border-l-blue-900 leading-relaxed font-mono">
          "{citation.quote_text}"
        </div>
      )}

      {/* Reference Context text */}
      <p className="text-xs text-slate-500 leading-relaxed">
        <span className="font-semibold text-slate-700">Context:</span> {citation.text_reference}
      </p>

      {/* Verification Action / Verification logs */}
      <div className="pt-2 flex items-center justify-between gap-4 border-t border-slate-100">
        <div className="text-[11px] text-slate-400">
          {verification ? (
            <span className="text-slate-600 font-medium">
              {verification.details?.message || "Verification completed."}
            </span>
          ) : (
            <span>Fact-check this citation against the parsed source text.</span>
          )}
        </div>
        
        <button
          onClick={handleVerify}
          disabled={loading}
          className="shrink-0 flex items-center gap-1.5 text-xs font-bold text-blue-950 bg-blue-50 border border-blue-200 hover:bg-blue-100 px-3 py-1.5 rounded transition-all duration-150 disabled:opacity-50"
        >
          {loading ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              <span>Verifying...</span>
            </>
          ) : (
            <>
              <span>Verify Claim</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </>
          )}
        </button>
      </div>
    </div>
  );
};
