import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import {
  ShieldCheck, Plus, CheckCircle2, AlertTriangle, Clock, RefreshCcw, Pencil
} from "lucide-react";

interface ClientComplianceProfileProps {
  clientId: string;
}

const getHealthColor = (score: string) => {
  switch (score) {
    case "Excellent": return "bg-emerald-50 text-emerald-800 border-emerald-200";
    case "Good": return "bg-blue-50 text-blue-800 border-blue-200";
    case "Needs Attention": return "bg-amber-50 text-amber-800 border-amber-200";
    case "Critical": return "bg-red-50 text-red-800 border-red-200";
    default: return "bg-slate-50 text-slate-800 border-slate-200";
  }
};

export const ClientComplianceProfile: React.FC<ClientComplianceProfileProps> = ({ clientId }) => {
  const [data, setData] = useState<any | null>(null);
  const [complianceTypes, setComplianceTypes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showModal, setShowModal] = useState(false);
  const [editingProfile, setEditingProfile] = useState<any | null>(null);
  const [complianceType, setComplianceType] = useState("GST");
  const [regNumber, setRegNumber] = useState("");
  const [frequency, setFrequency] = useState("MONTHLY");
  const [dueDay, setDueDay] = useState(20);
  const [riskLevel, setRiskLevel] = useState("LOW");

  const selectedTypeRule = complianceTypes.find((t) => t.key === complianceType);

  useEffect(() => {
    loadData();
    api.getComplianceTypes().then(setComplianceTypes).catch(() => setComplianceTypes([]));
  }, [clientId]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getClientCompliance(clientId);
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load compliance profile");
    } finally {
      setLoading(false);
    }
  };

  const handleTypeChange = (typeKey: string) => {
    setComplianceType(typeKey);
    const rule = complianceTypes.find((t) => t.key === typeKey);
    if (rule?.default_frequency) setFrequency(rule.default_frequency);
    if (rule?.default_due_day) setDueDay(rule.default_due_day);
  };

  const openCreateModal = () => {
    setEditingProfile(null);
    setComplianceType("GST");
    setRegNumber("");
    setFrequency("MONTHLY");
    setDueDay(20);
    setRiskLevel("LOW");
    setShowModal(true);
  };

  const openEditModal = (profile: any) => {
    setEditingProfile(profile);
    setComplianceType(profile.compliance_type);
    setRegNumber(profile.registration_number || "");
    setFrequency(profile.frequency);
    setDueDay(profile.due_day);
    setRiskLevel(profile.risk_level);
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingProfile) {
        await api.updateComplianceProfile(editingProfile.id, {
          compliance_type: complianceType,
          registration_number: regNumber,
          frequency,
          due_day: dueDay,
          risk_level: riskLevel,
        });
      } else {
        await api.createComplianceProfile({
          client_id: clientId,
          compliance_type: complianceType,
          registration_number: regNumber,
          frequency,
          due_day: dueDay,
          risk_level: riskLevel,
        });
      }
      setShowModal(false);
      loadData();
    } catch (err: any) {
      alert(`Failed to save compliance profile: ${err.message}`);
    }
  };

  const handleCompleteTask = async (task: any) => {
    try {
      await api.updateComplianceTask(task.id, {
        client_id: task.client_id,
        profile_id: task.profile_id,
        task_name: task.task_name,
        due_date: task.due_date,
        status: "COMPLETED",
        priority: task.priority,
        notes: task.notes,
      });
      loadData();
    } catch (err: any) {
      alert(`Failed to complete task: ${err.message}`);
    }
  };

  if (loading && !data) {
    return (
      <div className="flex flex-col items-center justify-center py-16 space-y-2">
        <RefreshCcw className="h-6 w-6 animate-spin text-slate-400" />
        <p className="text-xs text-slate-500 font-semibold">Loading compliance profile...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-lg text-xs">
        {error}
      </div>
    );
  }

  if (!data) return null;

  const pendingTasks = (data.tasks || []).filter((t: any) => t.status !== "COMPLETED");
  const now = new Date();

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div className={`px-4 py-2 rounded-lg border text-xs font-bold ${getHealthColor(data.health_score)}`}>
          Compliance Health: {data.health_score} ({data.health_score_value}%)
        </div>
        <button
          onClick={openCreateModal}
          className="bg-blue-900 hover:bg-blue-950 text-white rounded-lg px-3 py-1.5 text-xs font-bold flex items-center gap-1.5"
        >
          <Plus className="h-3.5 w-3.5" /> Add Compliance Type
        </button>
      </div>

      <div>
        <h4 className="text-xs font-extrabold text-slate-700 uppercase tracking-wider mb-2">Registered Compliance Types</h4>
        {(data.profiles || []).length === 0 ? (
          <p className="text-xs text-slate-400 italic">No compliance types configured for this client yet.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {data.profiles.map((p: any) => (
              <div key={p.id} className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1.5">
                <div className="flex justify-between items-start">
                  <span className="font-extrabold text-slate-800">{p.compliance_type}</span>
                  <button onClick={() => openEditModal(p)} className="text-slate-400 hover:text-blue-900" title="Edit">
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                </div>
                <div className="text-slate-500">{p.frequency} • Due day {p.due_day}</div>
                {p.registration_number && <div className="text-slate-400 font-mono text-[10px]">{p.registration_number}</div>}
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <h4 className="text-xs font-extrabold text-slate-700 uppercase tracking-wider mb-2">
          Pending & Upcoming Tasks ({pendingTasks.length})
        </h4>
        {pendingTasks.length === 0 ? (
          <p className="text-xs text-slate-400 italic">No pending compliance tasks.</p>
        ) : (
          <div className="space-y-2">
            {pendingTasks.map((t: any) => {
              const isOverdue = new Date(t.due_date) < now;
              return (
                <div key={t.id} className={`p-3 rounded-lg border flex justify-between items-center text-xs ${isOverdue ? "bg-red-50 border-red-200" : "bg-white border-slate-200"}`}>
                  <div className="space-y-0.5">
                    <p className="font-bold text-slate-800">{t.task_name}</p>
                    <div className="flex items-center gap-2 text-[10px] text-slate-400">
                      {isOverdue && <AlertTriangle className="h-3 w-3 text-red-500" />}
                      <span className={isOverdue ? "text-red-600 font-bold" : ""}>
                        Due: {new Date(t.due_date).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleCompleteTask(t)}
                    className="bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 rounded px-2.5 py-1 font-bold"
                  >
                    Complete
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div>
        <h4 className="text-xs font-extrabold text-slate-700 uppercase tracking-wider mb-2">Filing History</h4>
        {(data.history || []).length === 0 ? (
          <p className="text-xs text-slate-400 italic">No filings recorded yet.</p>
        ) : (
          <div className="space-y-2">
            {data.history.slice(0, 10).map((h: any) => (
              <div key={h.id} className="p-2.5 bg-slate-50 border border-slate-100 rounded-lg flex justify-between items-center text-xs">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                  <span>{new Date(h.filing_date).toLocaleDateString()}</span>
                  {h.acknowledgement_number && <span className="text-slate-400 font-mono text-[10px]">{h.acknowledgement_number}</span>}
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${h.status === "ON_TIME" ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"}`}>
                  {h.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-lg w-full p-6 space-y-4">
            <h3 className="text-base font-extrabold text-slate-900">
              {editingProfile ? "Edit Compliance Profile" : "Add Compliance Type"}
            </h3>
            <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Compliance Type</label>
                <select
                  value={complianceType}
                  onChange={(e) => handleTypeChange(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold focus:outline-none"
                  disabled={!!editingProfile}
                >
                  {complianceTypes.length > 0 ? (
                    complianceTypes.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)
                  ) : (
                    <option value="GST">GST</option>
                  )}
                </select>
              </div>

              {selectedTypeRule && !selectedTypeRule.is_nationally_uniform && (
                <div className="bg-amber-50 border border-amber-200 text-amber-900 rounded-lg p-3 text-[11px] leading-relaxed flex gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-amber-600" />
                  <span><strong>No safe default for this type.</strong> {selectedTypeRule.limitations}</span>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Registration/GSTIN</label>
                  <input
                    type="text"
                    value={regNumber}
                    onChange={(e) => setRegNumber(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Frequency</label>
                  <select
                    value={frequency}
                    onChange={(e) => setFrequency(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold focus:outline-none"
                  >
                    <option value="MONTHLY">Monthly</option>
                    <option value="QUARTERLY">Quarterly</option>
                    <option value="ANNUALLY">Annually</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Due Day of Month</label>
                  <input
                    type="number"
                    value={dueDay}
                    onChange={(e) => setDueDay(Number(e.target.value))}
                    min={1}
                    max={31}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold focus:outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Risk Level</label>
                  <select
                    value={riskLevel}
                    onChange={(e) => setRiskLevel(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold focus:outline-none"
                  >
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowModal(false)} className="border border-slate-200 rounded-lg px-4 py-2 font-bold text-slate-500 hover:bg-slate-50">
                  Cancel
                </button>
                <button type="submit" className="bg-blue-900 hover:bg-blue-950 text-white rounded-lg px-4 py-2 font-bold shadow-sm">
                  {editingProfile ? "Save Changes" : "Add"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
