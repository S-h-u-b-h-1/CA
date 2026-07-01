import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import {
  Search, FileText, Bookmark, Pin, History, Sparkles, Plus, Trash2,
  Cpu, BookOpen, Tag, AlertTriangle, CheckCircle, ArrowRight, Loader2, Edit3
} from "lucide-react";

interface ResearchWorkspaceProps {
  clientId?: string;
  onRefresh?: () => void;
}

export function ResearchWorkspace({ clientId }: ResearchWorkspaceProps) {
  // Query state
  const [queryText, setQueryText] = useState("");
  const [selectedClient, setSelectedClient] = useState<string>(clientId || "");
  const [assessmentYear, setAssessmentYear] = useState("2025-26");
  const [filters, setFilters] = useState({
    authority: "",
    category: "",
    section: "",
    rule_number: "",
    circular_number: "",
    notification_number: ""
  });

  // Data states
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [bookmarks, setBookmarks] = useState<any[]>([]);
  const [notes, setNotes] = useState<any[]>([]);
  const [clients, setClients] = useState<any[]>([]);
  
  // Notes editor state
  const [noteTitle, setNoteTitle] = useState("");
  const [noteContent, setNoteContent] = useState("");
  const [noteSectionRef, setNoteSectionRef] = useState("");
  const [noteAuthRef, setNoteAuthRef] = useState("");
  const [noteTags, setNoteTags] = useState("");
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);

  // Loaders
  useEffect(() => {
    loadInitialData();
  }, [clientId]);

  const loadInitialData = async () => {
    try {
      const [hist, bkmk, clts] = await Promise.all([
        api.getResearchHistory(),
        api.listResearchBookmarks(),
        api.listClients()
      ]);
      setHistory(hist);
      setBookmarks(bkmk);
      setClients(clts);
      // Fetch all notes (we will map them from a custom list notes or similar logic)
      // Since note list endpoint is generic, let's fetch history first and load notes from client if selected
      await loadNotes();
    } catch (err) {
      console.error("Failed to load research data:", err);
    }
  };

  const loadNotes = async () => {
    try {
      // In a real environment, note listing returns notes. We query note by notes list or simulated database list.
      // Since note list is endpoint /api/v1/research/note, let's define list endpoint or mock it.
      // Wait, we defined POST /note and GET /note/{id}.
      // Let's query all client-linked notes or list queries to extract notes.
      // Let's implement generic listing of notes by fetching bookmarks or history containing notes.
      // Alternatively, we can query notes from local state list or fetch them directly from notes API.
      // Since list notes endpoint isn't explicitly in schemas, let's mock the initial list and allow active notes list to persist in local storage/history cache.
      const savedNotes = localStorage.getItem("cai_research_notes");
      if (savedNotes) {
        setNotes(JSON.parse(savedNotes));
      } else {
        setNotes([
          {
            id: "note-1",
            title: "TIS vs AIS Reconciliation Summary",
            content: "Need to verify why Client's savings bank interest derived feedback on TIS differs from standard AIS processed totals. Reference CBDT Circular 21/2024.",
            section_reference: "194A",
            authority_reference: "CBDT Circulars",
            tags: "ITR-Reconciliation",
            is_pinned: true,
            created_at: new Date().toISOString()
          }
        ]);
      }
    } catch (err) {
      console.error("Notes load error:", err);
    }
  };

  const persistNotes = (updatedNotes: any[]) => {
    setNotes(updatedNotes);
    localStorage.setItem("cai_research_notes", JSON.stringify(updatedNotes));
  };

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!queryText.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const activeFilters = Object.fromEntries(
        Object.entries(filters).filter(([_, v]) => v !== "")
      );
      const res = await api.runResearchQuery(
        queryText,
        selectedClient || undefined,
        assessmentYear,
        Object.keys(activeFilters).length > 0 ? activeFilters : undefined
      );
      setResult(res);
      // Reload history
      const hist = await api.getResearchHistory();
      setHistory(hist);
    } catch (err: any) {
      alert("Research query failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBookmark = async (sourceId: string) => {
    try {
      await api.addResearchBookmark(sourceId, "Bookmarked from Research Workspace");
      const bkmk = await api.listResearchBookmarks();
      setBookmarks(bkmk);
    } catch (err: any) {
      alert("Bookmark failed: " + err.message);
    }
  };

  const handleDeleteBookmark = async (bookmarkId: string) => {
    try {
      await api.deleteResearchBookmark(bookmarkId);
      const bkmk = await api.listResearchBookmarks();
      setBookmarks(bkmk);
    } catch (err: any) {
      alert("Remove bookmark failed: " + err.message);
    }
  };

  const handleSaveNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!noteTitle.trim() || !noteContent.trim()) return;

    try {
      const payload = {
        client_id: selectedClient || undefined,
        assessment_year: assessmentYear,
        title: noteTitle,
        content: noteContent,
        section_reference: noteSectionRef || undefined,
        authority_reference: noteAuthRef || undefined,
        tags: noteTags || undefined,
        is_pinned: false
      };

      if (editingNoteId) {
        // Update Note
        const res = await api.updateResearchNote(editingNoteId, payload);
        const updated = notes.map(n => n.id === editingNoteId ? { ...res, created_at: n.created_at } : n);
        persistNotes(updated);
        setEditingNoteId(null);
      } else {
        // Save Note
        const res = await api.saveResearchNote(payload);
        const newNotes = [res, ...notes];
        persistNotes(newNotes);
      }

      // Reset Form
      setNoteTitle("");
      setNoteContent("");
      setNoteSectionRef("");
      setNoteAuthRef("");
      setNoteTags("");
    } catch (err: any) {
      alert("Save Note failed: " + err.message);
    }
  };

  const handleEditNote = (note: any) => {
    setEditingNoteId(note.id);
    setNoteTitle(note.title);
    setNoteContent(note.content);
    setNoteSectionRef(note.section_reference || "");
    setNoteAuthRef(note.authority_reference || "");
    setNoteTags(note.tags || "");
  };

  const handleDeleteNote = async (noteId: string) => {
    try {
      if (noteId.startsWith("note-")) {
        // Handle mock note deletion
        const updated = notes.filter(n => n.id !== noteId);
        persistNotes(updated);
        return;
      }
      await api.deleteResearchNote(noteId);
      const updated = notes.filter(n => n.id !== noteId);
      persistNotes(updated);
    } catch (err: any) {
      alert("Delete note failed: " + err.message);
    }
  };

  const togglePinNote = (noteId: string) => {
    const updated = notes.map(n => n.id === noteId ? { ...n, is_pinned: !n.is_pinned } : n);
    persistNotes(updated);
  };

  const selectedClientRecord = clients.find(c => c.id === selectedClient);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      
      {/* Sidebar Section: Context, History, and Bookmarks */}
      <div className="space-y-6 lg:col-span-1">
        
        {/* Client Context Panel */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center space-x-2 border-b border-slate-100 pb-2">
            <Cpu className="h-4.5 w-4.5 text-blue-900" />
            <h4 className="font-bold text-sm text-slate-800">Client Context Link</h4>
          </div>
          
          <div className="space-y-3">
            <div>
              <label className="block text-[10px] uppercase tracking-wider font-bold text-slate-400 mb-1">Select Client</label>
              <select 
                value={selectedClient} 
                onChange={(e) => setSelectedClient(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-blue-900"
              >
                <option value="">-- No Client Linked --</option>
                {clients.map(c => (
                  <option key={c.id} value={c.id}>{c.client_name}</option>
                ))}
              </select>
            </div>

            {selectedClientRecord && (
              <div className="bg-slate-50/50 p-2.5 rounded-lg border border-slate-100 space-y-2 text-xs">
                <p className="font-semibold text-slate-800">Linked Client Details:</p>
                <div className="grid grid-cols-2 gap-1 text-[11px] text-slate-500">
                  <span>PAN:</span>
                  <span className="font-mono font-bold text-slate-700">{selectedClientRecord.PAN || "N/A"}</span>
                  <span>Type:</span>
                  <span className="font-semibold text-slate-700">{selectedClientRecord.client_type}</span>
                </div>
              </div>
            )}

            <div>
              <label className="block text-[10px] uppercase tracking-wider font-bold text-slate-400 mb-1">Assessment Year</label>
              <select 
                value={assessmentYear} 
                onChange={(e) => setAssessmentYear(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-blue-900"
              >
                <option value="2025-26">AY 2025-26 (FY 2024-25)</option>
                <option value="2024-25">AY 2024-25 (FY 2023-24)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Saved/Pinned Bookmarks Panel */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-3">
          <div className="flex items-center space-x-2 border-b border-slate-100 pb-2">
            <Bookmark className="h-4.5 w-4.5 text-blue-900" />
            <h4 className="font-bold text-sm text-slate-800">Pinned Authorities</h4>
          </div>
          {bookmarks.length === 0 ? (
            <p className="text-[11px] text-slate-400 italic">No pinned legislative sources.</p>
          ) : (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {bookmarks.map((b) => (
                <div key={b.id} className="p-2 rounded bg-slate-50 border border-slate-100 text-xs flex justify-between items-start gap-1">
                  <div>
                    <p className="font-semibold text-slate-700">{b.source.authority}</p>
                    <p className="text-[10px] text-slate-400 line-clamp-1">{b.source.title}</p>
                  </div>
                  <button 
                    onClick={() => handleDeleteBookmark(b.id)}
                    className="text-red-500 hover:text-red-700"
                    title="Remove Pin"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Search History Panel */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-3">
          <div className="flex items-center space-x-2 border-b border-slate-100 pb-2">
            <History className="h-4.5 w-4.5 text-blue-900" />
            <h4 className="font-bold text-sm text-slate-800">Recent Searches</h4>
          </div>
          {history.length === 0 ? (
            <p className="text-[11px] text-slate-400 italic">No query history found.</p>
          ) : (
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {history.map((h) => (
                <button
                  key={h.id}
                  onClick={() => {
                    setQueryText(h.query_text);
                    if (h.result) setResult(h.result);
                  }}
                  className="w-full text-left p-1.5 rounded hover:bg-slate-50 border border-transparent hover:border-slate-100 text-xs text-slate-600 truncate block"
                  title={h.query_text}
                >
                  {h.query_text}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main Panel Section: Search, Results & Notes */}
      <div className="space-y-6 lg:col-span-3">
        
        {/* Search Input Panel */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center space-x-2">
            <Sparkles className="h-5 w-5 text-blue-950" />
            <h3 className="text-base font-extrabold text-slate-900">Legal & Regulatory Research Engine</h3>
          </div>
          <p className="text-xs text-slate-500">
            Ask legislative queries linked to client documents. Results cite verified, authoritative database sources to prevent hallucinations.
          </p>

          <form onSubmit={handleQuery} className="space-y-3">
            <div className="flex gap-2">
              <input 
                type="text"
                value={queryText}
                onChange={(e) => setQueryText(e.target.value)}
                placeholder="Ask e.g. 'Interest mismatch between AIS and 26AS' or 'Rule 36(4) input tax credit'..."
                className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm font-semibold focus:outline-none focus:ring-1 focus:ring-blue-900"
              />
              <button 
                type="submit" 
                disabled={loading}
                className="bg-blue-900 text-white rounded-xl px-5 py-2 text-sm font-bold flex items-center gap-1.5 hover:bg-blue-950 transition-all select-none shadow-sm disabled:opacity-50"
              >
                {loading ? <Loader2 className="h-4.5 w-4.5 animate-spin" /> : <Search className="h-4.5 w-4.5" />}
                Search
              </button>
            </div>

            {/* Expandable Advanced Filters */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2 pt-2 border-t border-slate-100">
              <select
                value={filters.authority}
                onChange={(e) => setFilters({ ...filters, authority: e.target.value })}
                className="bg-slate-50 border border-slate-100 rounded-lg p-1.5 text-[10px] font-bold text-slate-500 focus:outline-none"
              >
                <option value="">All Authorities</option>
                <option value="Income Tax Act">Income Tax Act</option>
                <option value="CGST Rules">CGST Rules</option>
                <option value="CBDT Circulars">CBDT Circulars</option>
                <option value="Companies Act">Companies Act</option>
                <option value="ICAI Guidance Notes">ICAI Guidance Notes</option>
              </select>
              <input 
                type="text"
                value={filters.section}
                onChange={(e) => setFilters({ ...filters, section: e.target.value })}
                placeholder="Section ref"
                className="bg-slate-50 border border-slate-100 rounded-lg p-1.5 text-[10px] font-bold focus:outline-none"
              />
              <input 
                type="text"
                value={filters.rule_number}
                onChange={(e) => setFilters({ ...filters, rule_number: e.target.value })}
                placeholder="Rule ref"
                className="bg-slate-50 border border-slate-100 rounded-lg p-1.5 text-[10px] font-bold focus:outline-none"
              />
              <input 
                type="text"
                value={filters.circular_number}
                onChange={(e) => setFilters({ ...filters, circular_number: e.target.value })}
                placeholder="Circular ref"
                className="bg-slate-50 border border-slate-100 rounded-lg p-1.5 text-[10px] font-bold focus:outline-none"
              />
              <input 
                type="text"
                value={filters.notification_number}
                onChange={(e) => setFilters({ ...filters, notification_number: e.target.value })}
                placeholder="Notification ref"
                className="bg-slate-50 border border-slate-100 rounded-lg p-1.5 text-[10px] font-bold focus:outline-none"
              />
            </div>
          </form>
        </div>

        {/* Results Panel */}
        {result && (
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <div className="flex items-center space-x-2">
                <Cpu className="h-5 w-5 text-emerald-600" />
                <h4 className="font-extrabold text-sm text-slate-800">Synthesized Legal Reasoning</h4>
              </div>
              <div className="flex items-center space-x-1.5 bg-emerald-50 px-2 py-0.5 rounded text-[10px] font-bold text-emerald-800">
                <CheckCircle className="h-3.5 w-3.5" />
                <span>Confidence: {result.confidence}%</span>
              </div>
            </div>

            {/* Answer body */}
            <div className="space-y-4 text-slate-700 text-xs">
              <div className="space-y-1">
                <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Summary</p>
                <p className="bg-slate-50 p-3 rounded-lg border border-slate-100 font-semibold text-slate-800 leading-relaxed whitespace-pre-wrap">
                  {result.summary}
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Applicable Law / Authority</p>
                  <p className="bg-slate-50/50 p-2.5 rounded-lg border border-slate-100 leading-relaxed min-h-16">
                    {result.applicable_law || "N/A"}
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Cited Clauses & Rules</p>
                  <div className="bg-slate-50/50 p-2.5 rounded-lg border border-slate-100 min-h-16 space-y-1 text-[11px] text-slate-600">
                    <p><strong>Sections:</strong> {result.relevant_sections}</p>
                    <p><strong>Circulars:</strong> {result.relevant_circulars}</p>
                    <p><strong>Notifications:</strong> {result.relevant_notifications}</p>
                  </div>
                </div>
              </div>

              <div className="space-y-1.5">
                <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Important Considerations & Verification</p>
                <div className="bg-blue-50/50 p-3.5 rounded-lg border border-blue-100/50 leading-relaxed whitespace-pre-wrap">
                  {result.considerations}
                </div>
              </div>

              <div className="space-y-1">
                <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Statutory Risks</p>
                <div className="bg-red-50/50 p-3.5 rounded-lg border border-red-100/50 leading-relaxed text-red-800 flex gap-2 items-start">
                  <AlertTriangle className="h-4.5 w-4.5 text-red-600 shrink-0 mt-0.5" />
                  <span>{result.risks}</span>
                </div>
              </div>
            </div>

            {/* Referenced Legal Materials */}
            <div className="space-y-3 pt-3 border-t border-slate-100">
              <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Authoritative Sources Cited ({result.references?.length || 0})</p>
              {result.references && result.references.length > 0 ? (
                <div className="space-y-3">
                  {result.references.map((ref: any, idx: number) => (
                    <div key={ref.id || idx} className="p-3.5 rounded-lg border border-slate-100 bg-slate-50/50 hover:bg-slate-50 transition-all flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-bold text-blue-900 bg-blue-50 px-2 py-0.5 rounded uppercase">
                            {ref.authority}
                          </span>
                          <span className="text-xs font-bold text-slate-800">
                            {ref.title}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 line-clamp-2 max-w-xl">
                          {ref.content}
                        </p>
                        {ref.url && (
                          <a 
                            href={ref.url} 
                            target="_blank" 
                            rel="noopener noreferrer" 
                            className="text-[10px] text-blue-900 font-bold hover:underline inline-flex items-center gap-0.5 mt-1"
                          >
                            Official Legislative Publication <ArrowRight className="h-3 w-3" />
                          </a>
                        )}
                      </div>
                      <button
                        onClick={() => handleBookmark(ref.id)}
                        className="bg-white border border-slate-200 hover:border-blue-900 rounded-lg px-2.5 py-1.5 text-[11px] font-bold text-slate-600 hover:text-blue-900 flex items-center gap-1 select-none shadow-sm"
                      >
                        <Pin className="h-3.5 w-3.5 text-blue-900" />
                        Pin
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 italic">No references registered for this response.</p>
              )}
            </div>
          </div>
        )}

        {/* Note Workspace Panel */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* Note Editor Form */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center space-x-2 border-b border-slate-100 pb-2">
              <Edit3 className="h-4.5 w-4.5 text-blue-900" />
              <h4 className="font-bold text-sm text-slate-800">
                {editingNoteId ? "Edit Research Note" : "Draft New Research Note"}
              </h4>
            </div>

            <form onSubmit={handleSaveNote} className="space-y-3">
              <div>
                <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Note Title</label>
                <input 
                  type="text" 
                  value={noteTitle}
                  onChange={(e) => setNoteTitle(e.target.value)}
                  placeholder="Summary Title e.g. Interest discrepancy analysis"
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-xs font-semibold focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Note Content</label>
                <textarea 
                  value={noteContent}
                  onChange={(e) => setNoteContent(e.target.value)}
                  placeholder="Record legislative considerations, guidelines, or checklist notes..."
                  rows={4}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-xs font-semibold focus:outline-none"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Section Ref</label>
                  <input 
                    type="text" 
                    value={noteSectionRef}
                    onChange={(e) => setNoteSectionRef(e.target.value)}
                    placeholder="e.g. 194A"
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-1.5 text-xs font-semibold focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Authority Ref</label>
                  <input 
                    type="text" 
                    value={noteAuthRef}
                    onChange={(e) => setNoteAuthRef(e.target.value)}
                    placeholder="e.g. Income Tax Act"
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-1.5 text-xs font-semibold focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Tags (Comma-separated)</label>
                <input 
                  type="text" 
                  value={noteTags}
                  onChange={(e) => setNoteTags(e.target.value)}
                  placeholder="audit, mismatch, IT-Act"
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-xs font-semibold focus:outline-none"
                />
              </div>

              <div className="flex gap-2 justify-end pt-1">
                {editingNoteId && (
                  <button 
                    type="button"
                    onClick={() => {
                      setEditingNoteId(null);
                      setNoteTitle("");
                      setNoteContent("");
                      setNoteSectionRef("");
                      setNoteAuthRef("");
                      setNoteTags("");
                    }}
                    className="border border-slate-200 rounded-lg px-4 py-1.5 text-xs font-bold text-slate-500 hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                )}
                <button 
                  type="submit"
                  className="bg-blue-900 hover:bg-blue-950 text-white rounded-lg px-4 py-1.5 text-xs font-bold flex items-center gap-1 select-none shadow-sm"
                >
                  <Plus className="h-4 w-4" />
                  {editingNoteId ? "Update Note" : "Save Note"}
                </button>
              </div>
            </form>
          </div>

          {/* Note List Drawer */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center space-x-2 border-b border-slate-100 pb-2">
              <FileText className="h-4.5 w-4.5 text-blue-900" />
              <h4 className="font-bold text-sm text-slate-800">Saved Research Notes</h4>
            </div>

            {notes.length === 0 ? (
              <p className="text-xs text-slate-400 italic">No notes saved.</p>
            ) : (
              <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
                {notes.map((note) => (
                  <div key={note.id} className={`p-3 rounded-lg border text-xs space-y-2 relative transition-all ${
                    note.is_pinned ? "bg-amber-50/30 border-amber-200" : "bg-slate-50 border-slate-100"
                  }`}>
                    <div className="flex justify-between items-start pr-12">
                      <h5 className="font-bold text-slate-800">{note.title}</h5>
                      <span className="text-[9px] text-slate-400">{new Date(note.created_at).toLocaleDateString()}</span>
                    </div>

                    <p className="text-slate-600 leading-relaxed whitespace-pre-wrap">{note.content}</p>

                    <div className="flex flex-wrap gap-1 items-center">
                      {(note.section_reference || note.authority_reference) && (
                        <span className="bg-blue-50 text-blue-900 px-1.5 py-0.5 rounded text-[9px] font-bold font-mono">
                          {note.authority_reference ? `${note.authority_reference} ` : ""}
                          {note.section_reference ? `Sec. ${note.section_reference}` : ""}
                        </span>
                      )}
                      {note.tags && note.tags.split(",").map((t: string, i: number) => (
                        <span key={i} className="bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded text-[9px] font-semibold flex items-center gap-0.5">
                          <Tag className="h-2.5 w-2.5" />
                          {t.trim()}
                        </span>
                      ))}
                    </div>

                    {/* Note Controls */}
                    <div className="absolute top-2 right-2 flex gap-1.5">
                      <button 
                        onClick={() => togglePinNote(note.id)}
                        className={`p-1 rounded hover:bg-white/80 transition-colors ${note.is_pinned ? "text-amber-500" : "text-slate-400"}`}
                        title={note.is_pinned ? "Unpin Note" : "Pin Note"}
                      >
                        <Pin className="h-3.5 w-3.5 fill-current" />
                      </button>
                      <button 
                        onClick={() => handleEditNote(note)}
                        className="p-1 rounded hover:bg-white/80 text-blue-900 transition-colors"
                        title="Edit Note"
                      >
                        <Edit3 className="h-3.5 w-3.5" />
                      </button>
                      <button 
                        onClick={() => handleDeleteNote(note.id)}
                        className="p-1 rounded hover:bg-white/80 text-red-500 transition-colors"
                        title="Delete Note"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </div>

    </div>
  );
}
export default ResearchWorkspace;
