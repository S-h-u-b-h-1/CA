import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import {
  Calendar as CalendarIcon, ClipboardList, CheckCircle2, AlertTriangle,
  Clock, ShieldAlert, Plus, Check, Search, Trash2, ArrowRight, UserCheck,
  Building, RefreshCcw, LayoutGrid, ListFilter, Database
} from "lucide-react";
import { ComplianceRegistry } from "./ComplianceRegistry";

interface ComplianceWorkspaceProps {
  clients: any[];
  complianceSources?: any[];
  currentUser?: any;
  onRefreshSources?: () => void;
}

export const ComplianceWorkspace: React.FC<ComplianceWorkspaceProps> = ({
  clients,
  complianceSources = [],
  currentUser,
  onRefreshSources = () => {},
}) => {
  const [dashboard, setDashboard] = useState<any | null>(null);
  const [calendarEvents, setCalendarEvents] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [complianceTypes, setComplianceTypes] = useState<any[]>([]);

  // Modal / Form state for new profile
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [selectedClientId, setSelectedClientId] = useState("");
  const [complianceType, setComplianceType] = useState("GST");
  const [regNumber, setRegNumber] = useState("");
  const [frequency, setFrequency] = useState("MONTHLY");
  const [dueDay, setDueDay] = useState(20);
  const [riskLevel, setRiskLevel] = useState("LOW");
  const [assignedManager, setAssignedManager] = useState("");
  const [assignedPartner, setAssignedPartner] = useState("");

  const selectedTypeRule = complianceTypes.find((t) => t.key === complianceType || t.label === complianceType);

  // Tab state inside compliance
  const [complianceTab, setComplianceTab] = useState("overview"); // overview, calendar, kanban, table, alerts

  // Search/Filter state
  const [filterQuery, setFilterQuery] = useState("");

  useEffect(() => {
    loadComplianceData();
    api.getComplianceTypes().then(setComplianceTypes).catch(() => setComplianceTypes([]));
  }, []);

  // When the CA picks a compliance type, prefill frequency/due day from the
  // real registry default (where a safe one exists) - still fully editable,
  // this is just a starting point, not an invented value silently applied.
  const handleComplianceTypeChange = (typeKey: string) => {
    setComplianceType(typeKey);
    const rule = complianceTypes.find((t) => t.key === typeKey);
    if (rule?.default_frequency) setFrequency(rule.default_frequency);
    if (rule?.default_due_day) setDueDay(rule.default_due_day);
  };

  const loadComplianceData = async () => {
    setLoading(true);
    setError(null);
    try {
      const dbData = await api.getComplianceDashboard();
      setDashboard(dbData);

      const calData = await api.getComplianceCalendar();
      setCalendarEvents(calData);

      const alertList = await api.getComplianceAlerts();
      setAlerts(alertList);
    } catch (err: any) {
      setError(err.message || "Failed to load compliance data");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClientId) {
      alert("Please select a client.");
      return;
    }
    try {
      await api.createComplianceProfile({
        client_id: selectedClientId,
        compliance_type: complianceType,
        registration_number: regNumber,
        frequency,
        due_day: dueDay,
        assigned_manager: assignedManager || undefined,
        assigned_partner: assignedPartner || undefined,
        risk_level: riskLevel
      });
      setShowProfileModal(false);
      
      // Reset form
      setRegNumber("");
      setDueDay(20);
      setAssignedManager("");
      setAssignedPartner("");

      loadComplianceData();
    } catch (err: any) {
      alert("Failed to create compliance profile: " + err.message);
    }
  };

  const handleUpdateTaskStatus = async (task: any, newStatus: string) => {
    try {
      await api.updateComplianceTask(task.id, {
        client_id: task.client_id,
        profile_id: task.profile_id,
        task_name: task.task_name,
        due_date: task.due_date,
        status: newStatus,
        priority: task.priority,
        assigned_user_id: task.assigned_user_id,
        notes: task.notes
      });
      loadComplianceData();
    } catch (err: any) {
      alert("Failed to update status: " + err.message);
    }
  };

  // Filters tasks based on search bar
  const getFilteredTasks = (taskList: any[]) => {
    if (!filterQuery.trim()) return taskList;
    return taskList.filter((t) => 
      t.task_name.toLowerCase().includes(filterQuery.toLowerCase())
    );
  };

  const getHealthColor = (score: string) => {
    switch (score) {
      case "Excellent": return "bg-emerald-50 text-emerald-800 border-emerald-200";
      case "Good": return "bg-blue-50 text-blue-800 border-blue-200";
      case "Needs Attention": return "bg-amber-50 text-amber-800 border-amber-200";
      case "Critical": return "bg-red-50 text-red-800 border-red-200";
      default: return "bg-slate-50 text-slate-800 border-slate-200";
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-extrabold text-slate-900">Compliance Intelligence Engine</h2>
          <p className="text-xs text-slate-500">Firm-wide statutory calendar trackers, alerts, and rolling schedules.</p>
        </div>

        <button
          onClick={() => setShowProfileModal(true)}
          className="bg-blue-900 text-white rounded-lg px-4 py-2 text-xs font-bold flex items-center gap-1.5 hover:bg-blue-950 transition-colors shadow-sm select-none"
        >
          <Plus className="h-4 w-4" />
          Setup Compliance Profile
        </button>
      </div>

      {loading && !dashboard ? (
        <div className="flex flex-col items-center justify-center py-20 space-y-2">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-900"></div>
          <p className="text-xs text-slate-500 font-semibold">Consolidating compliance reports...</p>
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-lg flex items-center space-x-2 text-xs">
          <ShieldAlert className="h-5 w-5 text-red-600" />
          <span>{error}</span>
        </div>
      ) : dashboard ? (
        <div className="space-y-6">
          
          {/* 1. Statistics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            
            <div className={`p-4 rounded-xl border shadow-sm flex flex-col justify-between ${getHealthColor(dashboard.health_score)}`}>
              <p className="text-[10px] uppercase font-bold tracking-wider opacity-70">Compliance Health</p>
              <div className="flex justify-between items-baseline mt-2">
                <span className="text-2xl font-black">{dashboard.health_score_value}%</span>
                <span className="text-xs font-bold">{dashboard.health_score}</span>
              </div>
            </div>

            <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
              <p className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">On-Time Filing Rate</p>
              <div className="flex justify-between items-baseline mt-2">
                <span className="text-2xl font-black text-slate-800">{dashboard.on_time_filing_percentage}%</span>
                <span className="text-xs font-bold text-emerald-600">Avg Target</span>
              </div>
            </div>

            <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
              <p className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Pending Returns</p>
              <div className="flex justify-between items-baseline mt-2">
                <span className="text-2xl font-black text-slate-800">{dashboard.total_returns_pending}</span>
                <span className="text-xs font-bold text-blue-900">Active Pipeline</span>
              </div>
            </div>

            <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
              <p className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Overdue Returns</p>
              <div className="flex justify-between items-baseline mt-2">
                <span className="text-2xl font-black text-red-600">{dashboard.total_returns_overdue}</span>
                <span className="text-xs font-bold text-red-600">Immediate Action</span>
              </div>
            </div>

            <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
              <p className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Due Today</p>
              <div className="flex justify-between items-baseline mt-2">
                <span className="text-2xl font-black text-amber-600">{dashboard.due_today}</span>
                <span className="text-xs font-bold text-amber-600">Filing Window</span>
              </div>
            </div>

            <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
              <p className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Due This Week</p>
              <div className="flex justify-between items-baseline mt-2">
                <span className="text-2xl font-black text-blue-900">{dashboard.due_this_week}</span>
                <span className="text-xs font-bold text-blue-900">Upcoming</span>
              </div>
            </div>

            <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
              <p className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Due This Month</p>
              <div className="flex justify-between items-baseline mt-2">
                <span className="text-2xl font-black text-slate-800">{dashboard.due_this_month}</span>
                <span className="text-xs font-bold text-slate-500">Planning Horizon</span>
              </div>
            </div>

          </div>

          {/* 2. Search and Navigation Tabs */}
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center border-b border-slate-200 gap-3">
            <div className="flex space-x-6 text-xs select-none overflow-x-auto pb-1 no-scrollbar">
              {[
                { id: "overview", label: "Overview & Agenda", icon: LayoutGrid },
                { id: "calendar", label: "Filing Calendar", icon: CalendarIcon },
                { id: "kanban", label: "Kanban Board", icon: ClipboardList },
                { id: "alerts", label: "Compliance Alerts", icon: ShieldAlert },
                { id: "sources", label: "Data Sources", icon: Database }
              ].map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setComplianceTab(tab.id)}
                    className={`pb-3 flex items-center space-x-1.5 font-bold border-b-2 transition-all shrink-0 ${
                      complianceTab === tab.id
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

            <div className="relative w-full sm:w-64 pb-2">
              <input
                type="text"
                value={filterQuery}
                onChange={(e) => setFilterQuery(e.target.value)}
                placeholder="Search compliance tasks..."
                className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs font-semibold focus:outline-none"
              />
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
            </div>
          </div>

          {/* 3. Tab contents */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm min-h-96">
            
            {/* Overview / Agenda Tab */}
            {complianceTab === "overview" && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Upcoming Agenda (Left & Center) */}
                <div className="lg:col-span-2 space-y-4">
                  <h3 className="font-extrabold text-sm text-slate-800 flex items-center gap-1.5">
                    <CalendarIcon className="h-4.5 w-4.5 text-slate-700" />
                    Upcoming Deadline Agenda ({getFilteredTasks(dashboard.upcoming_deadlines).length})
                  </h3>

                  {getFilteredTasks(dashboard.upcoming_deadlines).length === 0 ? (
                    <p className="text-xs text-slate-400 italic">No upcoming deadlines.</p>
                  ) : (
                    <div className="space-y-2">
                      {getFilteredTasks(dashboard.upcoming_deadlines).map((task: any) => (
                        <div key={task.id} className="p-3.5 rounded-lg bg-slate-50 border border-slate-100 flex justify-between items-center text-xs">
                          <div className="space-y-1">
                            <p className="font-bold text-slate-800">{task.task_name}</p>
                            <div className="flex items-center gap-2 text-[10px] text-slate-400">
                              <span>Due: {new Date(task.due_date).toLocaleDateString()}</span>
                              <span>•</span>
                              <span className="uppercase font-semibold">{task.priority} Priority</span>
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleUpdateTaskStatus(task, "COMPLETED")}
                              className="bg-emerald-50 text-emerald-700 hover:bg-emerald-100 px-3 py-1.5 rounded-lg font-bold border border-emerald-200"
                            >
                              Complete Filing
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Alerts Pane (Right) */}
                <div className="lg:col-span-1 space-y-4 border-t lg:border-t-0 lg:border-l border-slate-100 lg:pl-6">
                  <h3 className="font-extrabold text-sm text-slate-800 flex items-center gap-1.5">
                    <ShieldAlert className="h-4.5 w-4.5 text-red-500" />
                    Active Alerts ({alerts.length})
                  </h3>

                  {alerts.length === 0 ? (
                    <p className="text-xs text-slate-400 italic">No warnings.</p>
                  ) : (
                    <div className="space-y-2">
                      {alerts.map((al: any) => (
                        <div key={al.id} className={`p-3 rounded-lg border text-xs flex gap-2 ${
                          al.alert_type === "OVERDUE" ? "bg-red-50 border-red-200 text-red-900" : "bg-amber-50 border-amber-200 text-amber-900"
                        }`}>
                          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                          <span>{al.message}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

              </div>
            )}

            {/* Calendar Tab */}
            {complianceTab === "calendar" && (
              <div className="space-y-4">
                <h3 className="font-extrabold text-sm text-slate-800">Deadlines Calendar View</h3>
                
                <div className="grid grid-cols-7 gap-2 border-b border-slate-100 pb-2 text-center text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                  <span>Sun</span>
                  <span>Mon</span>
                  <span>Tue</span>
                  <span>Wed</span>
                  <span>Thu</span>
                  <span>Fri</span>
                  <span>Sat</span>
                </div>

                {/* Agenda list under calendar */}
                <div className="space-y-3 mt-4">
                  <p className="text-xs font-bold text-slate-600">Chronological Deadlines List</p>
                  {calendarEvents.map((evt) => (
                    <div key={evt.id} className="p-3 bg-slate-50 border border-slate-100 rounded-lg flex items-center justify-between text-xs">
                      <div className="flex items-center gap-3">
                        <span className="h-2 w-2 rounded-full bg-blue-900"></span>
                        <div>
                          <p className="font-bold text-slate-800">{evt.task_name}</p>
                          <span className="text-[10px] text-slate-400">Due: {new Date(evt.due_date).toLocaleDateString()}</span>
                        </div>
                      </div>
                      
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        evt.status === "COMPLETED" ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"
                      }`}>
                        {evt.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Kanban Board Tab */}
            {complianceTab === "kanban" && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                {/* PENDING COLUMN */}
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 space-y-3">
                  <div className="flex justify-between items-center border-b border-slate-200 pb-2">
                    <span className="text-xs font-extrabold text-slate-700 uppercase tracking-wider">Pending</span>
                    <span className="bg-slate-200 text-slate-700 text-[10px] font-bold px-2 py-0.5 rounded">
                      {calendarEvents.filter(t => t.status === "PENDING").length}
                    </span>
                  </div>

                  <div className="space-y-2 overflow-y-auto max-h-96">
                    {calendarEvents.filter(t => t.status === "PENDING").map((task) => (
                      <div key={task.id} className="p-3 bg-white border border-slate-200 rounded-lg shadow-sm space-y-2">
                        <p className="text-xs font-bold text-slate-800">{task.task_name}</p>
                        <p className="text-[10px] text-slate-400">Due: {new Date(task.due_date).toLocaleDateString()}</p>
                        <button
                          onClick={() => handleUpdateTaskStatus(task, "COMPLETED")}
                          className="w-full text-center bg-blue-900 text-white rounded py-1 text-[10px] font-bold hover:bg-blue-950"
                        >
                          Complete Filing
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                {/* IN PROGRESS COLUMN */}
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 space-y-3">
                  <div className="flex justify-between items-center border-b border-slate-200 pb-2">
                    <span className="text-xs font-extrabold text-slate-700 uppercase tracking-wider">In Progress</span>
                    <span className="bg-blue-100 text-blue-800 text-[10px] font-bold px-2 py-0.5 rounded">
                      {calendarEvents.filter(t => t.status === "IN_PROGRESS").length}
                    </span>
                  </div>

                  <div className="space-y-2 overflow-y-auto max-h-96">
                    {calendarEvents.filter(t => t.status === "IN_PROGRESS").map((task) => (
                      <div key={task.id} className="p-3 bg-white border border-slate-200 rounded-lg shadow-sm space-y-2">
                        <p className="text-xs font-bold text-slate-800">{task.task_name}</p>
                        <p className="text-[10px] text-slate-400">Due: {new Date(task.due_date).toLocaleDateString()}</p>
                        <button
                          onClick={() => handleUpdateTaskStatus(task, "COMPLETED")}
                          className="w-full text-center bg-blue-900 text-white rounded py-1 text-[10px] font-bold hover:bg-blue-950"
                        >
                          Complete Filing
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                {/* COMPLETED COLUMN */}
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 space-y-3">
                  <div className="flex justify-between items-center border-b border-slate-200 pb-2">
                    <span className="text-xs font-extrabold text-slate-700 uppercase tracking-wider">Completed</span>
                    <span className="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2 py-0.5 rounded">
                      {calendarEvents.filter(t => t.status === "COMPLETED").length}
                    </span>
                  </div>

                  <div className="space-y-2 overflow-y-auto max-h-96">
                    {calendarEvents.filter(t => t.status === "COMPLETED").map((task) => (
                      <div key={task.id} className="p-3 bg-white border border-slate-200 rounded-lg shadow-sm space-y-1">
                        <p className="text-xs font-bold text-slate-800">{task.task_name}</p>
                        <p className="text-[10px] text-emerald-600 font-semibold flex items-center gap-0.5">
                          <CheckCircle2 className="h-3 w-3" /> Done
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            )}

            {/* Compliance Alerts Feed Tab */}
            {complianceTab === "alerts" && (
              <div className="space-y-4">
                <h3 className="font-extrabold text-sm text-slate-800">Compliance Warnings Panel</h3>
                
                {alerts.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No alerts.</p>
                ) : (
                  <div className="space-y-3">
                    {alerts.map((al) => (
                      <div key={al.id} className={`p-4 rounded-lg border text-xs flex justify-between items-center ${
                        al.alert_type === "OVERDUE" ? "bg-red-50 border-red-200 text-red-900" : "bg-amber-50 border-amber-200 text-amber-900"
                      }`}>
                        <div className="flex gap-2.5">
                          <AlertTriangle className="h-4.5 w-4.5 shrink-0 mt-0.5" />
                          <div>
                            <p className="font-bold">{al.message}</p>
                            <span className="text-[10px] opacity-75">{new Date(al.created_at).toLocaleString()}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Data Sources Tab */}
            {complianceTab === "sources" && (
              <ComplianceRegistry
                sources={complianceSources}
                currentUser={currentUser}
                onRefresh={onRefreshSources}
              />
            )}

          </div>

        </div>
      ) : null}

      {/* Setup Compliance Profile Modal */}
      {showProfileModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-lg w-full p-6 space-y-4">
            <h3 className="text-base font-extrabold text-slate-900">Setup statutory Compliance Profile</h3>
            
            <form onSubmit={handleCreateProfile} className="space-y-3.5 text-xs">
              
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Select Client</label>
                  <select
                    value={selectedClientId}
                    onChange={(e) => setSelectedClientId(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold focus:outline-none"
                    required
                  >
                    <option value="">-- Choose Client --</option>
                    {clients.map((c) => (
                      <option key={c.id} value={c.id}>{c.client_name}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Compliance Type</label>
                  <select
                    value={complianceType}
                    onChange={(e) => handleComplianceTypeChange(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold focus:outline-none"
                  >
                    {complianceTypes.length > 0 ? (
                      complianceTypes.map((t) => (
                        <option key={t.key} value={t.key}>{t.label}</option>
                      ))
                    ) : (
                      <>
                        <option value="GST">GST</option>
                        <option value="Income Tax">Income Tax</option>
                        <option value="TDS">TDS</option>
                        <option value="TCS">TCS</option>
                        <option value="MCA/ROC">MCA/ROC</option>
                        <option value="PF">PF</option>
                        <option value="ESI">ESI</option>
                        <option value="Professional Tax">Professional Tax</option>
                      </>
                    )}
                  </select>
                </div>
              </div>

              {selectedTypeRule && !selectedTypeRule.is_nationally_uniform && (
                <div className="bg-amber-50 border border-amber-200 text-amber-900 rounded-lg p-3 text-[11px] leading-relaxed flex gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-amber-600" />
                  <span>
                    <strong>No safe default for this type.</strong> {selectedTypeRule.limitations}
                  </span>
                </div>
              )}
              {selectedTypeRule && selectedTypeRule.is_nationally_uniform && (
                <div className="bg-slate-50 border border-slate-200 text-slate-600 rounded-lg p-3 text-[11px] leading-relaxed">
                  {selectedTypeRule.summary} {selectedTypeRule.limitations}
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Registration/GSTIN</label>
                  <input
                    type="text"
                    value={regNumber}
                    onChange={(e) => setRegNumber(e.target.value)}
                    placeholder="27AADCS6785Q1Z1"
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold focus:outline-none"
                  />
                </div>
                
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Filing Frequency</label>
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
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Standard Due Day of Month</label>
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
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Risk Classification</label>
                  <select
                    value={riskLevel}
                    onChange={(e) => setRiskLevel(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-semibold focus:outline-none"
                  >
                    <option value="LOW">Low Risk</option>
                    <option value="MEDIUM">Medium Risk</option>
                    <option value="HIGH">High Risk</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowProfileModal(false)}
                  className="border border-slate-200 rounded-lg px-4 py-2 font-bold text-slate-500 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-blue-900 hover:bg-blue-950 text-white rounded-lg px-4 py-2 font-bold shadow-sm"
                >
                  Setup Profile
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
