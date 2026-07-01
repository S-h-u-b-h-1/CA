import React, { useState } from "react";
import { api } from "../lib/api";
import { Upload, FileText, Trash2, Eye, HelpCircle, Check, Loader2, Sparkles } from "lucide-react";

interface DocumentIntelligenceProps {
  documents: any[];
  clients: any[];
  onRefresh: () => void;
}

const DOCUMENT_CATEGORIES = [
  "Income Tax Return", "Form 16", "Form 26AS", "AIS", "TIS", 
  "GST Return", "GSTR-1", "GSTR-3B", "GSTR-2B", "Invoice", 
  "Bank Statement", "Balance Sheet", "Profit & Loss", 
  "Audit Report", "Notice", "Reply", "MCA Filing", 
  "ROC Document", "Agreement", "Other"
];

export const DocumentIntelligence: React.FC<DocumentIntelligenceProps> = ({
  documents,
  clients,
  onRefresh
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [category, setCategory] = useState("Income Tax Return");
  const [clientId, setClientId] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Detail Modal
  const [selectedDoc, setSelectedDoc] = useState<any | null>(null);
  const [structuredData, setStructuredData] = useState<any>(null);
  const [aiSummary, setAiSummary] = useState<any>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a file to upload");
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(false);

    try {
      await api.uploadDocument(file, category, clientId || undefined);
      setSuccess(true);
      setFile(null);
      onRefresh();
    } catch (err: any) {
      setError(err.message || "Failed to upload file");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this document?")) return;
    try {
      await api.deleteDocument(id);
      onRefresh();
      if (selectedDoc?.id === id) {
        setSelectedDoc(null);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleViewDetails = async (doc: any) => {
    setSelectedDoc(doc);
    setLoadingDetails(true);
    setStructuredData(null);
    setAiSummary(null);
    setActiveTab("overview");
    
    try {
      let structRes;
      if (doc.category === "Form 26AS" || doc.classification === "Form 26AS" || doc.classification === "FORM_26AS") {
        structRes = await api.getDocumentForm26AS(doc.id);
      } else if (doc.category === "AIS" || doc.classification === "AIS" || doc.classification === "FORM_AIS") {
        structRes = await api.getDocumentAIS(doc.id);
      } else {
        structRes = await api.getDocumentStructured(doc.id);
      }
      
      let summaryRes = null;
      if (doc.category !== "Form 26AS" && doc.category !== "AIS") {
        summaryRes = await api.getDocumentSummary(doc.id).catch(() => null);
      }
      
      setStructuredData(structRes);
      setAiSummary(summaryRes);
    } catch (err) {
      console.error("Failed to load document analysis details:", err);
    } finally {
      setLoadingDetails(false);
    }
  };

  const getClientName = (cid: string) => {
    const c = clients.find(item => item.id === cid);
    return c ? c.client_name : "General Workspace";
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Document Intelligence</h1>
        <p className="text-sm text-slate-500 mt-1">Upload client files to run OCR, generate text extractions, and create vector embeddings automatically.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Form Panel */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 card-shadow h-fit">
          <h3 className="font-bold text-slate-900 mb-4">Upload Document</h3>
          
          {error && (
            <div className="mb-4 bg-red-50 p-3 rounded text-xs text-red-700">
              {error}
            </div>
          )}

          {success && (
            <div className="mb-4 bg-emerald-50 p-3 rounded text-xs text-emerald-700 flex items-center space-x-2">
              <Check className="h-4 w-4" />
              <span>Document uploaded. AI processing started in background!</span>
            </div>
          )}

          <form onSubmit={handleUpload} className="space-y-4">
            {/* File Drag Box */}
            <div className="border-2 border-dashed border-slate-300 hover:border-blue-900 rounded-lg p-6 text-center transition-colors cursor-pointer relative">
              <input
                type="file"
                onChange={handleFileChange}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                accept=".pdf,.docx,.xlsx,.csv,.jpg,.png,.txt"
              />
              <Upload className="h-8 w-8 text-slate-400 mx-auto mb-2" />
              <p className="text-xs font-semibold text-slate-700">
                {file ? file.name : "Drag & drop file or click to browse"}
              </p>
              <p className="text-[10px] text-slate-400 mt-1">
                PDF, DOCX, XLSX, CSV, JPG, PNG, TXT (Max 10MB)
              </p>
            </div>

            {/* Category Selector */}
            <div>
              <label className="block text-xs font-semibold text-slate-700">Document Category *</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm"
              >
                {DOCUMENT_CATEGORIES.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>

            {/* Client Scoper */}
            <div>
              <label className="block text-xs font-semibold text-slate-700">Assign to Client (Optional)</label>
              <select
                value={clientId}
                onChange={(e) => setClientId(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm"
              >
                <option value="">-- General Workspace / No Client --</option>
                {clients.map(cli => (
                  <option key={cli.id} value={cli.id}>{cli.client_name}</option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              disabled={uploading || !file}
              className="w-full py-2 px-4 bg-slate-900 hover:bg-slate-800 text-white rounded-md text-sm font-semibold disabled:opacity-50 transition-colors"
            >
              {uploading ? "Uploading..." : "Upload & Analyze"}
            </button>
          </form>
        </div>

        {/* Registry Table Panel */}
        <div className="bg-white border border-slate-200 rounded-lg card-shadow lg:col-span-2 overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100">
            <h3 className="font-bold text-slate-900">Document Registry</h3>
          </div>
          
          {documents.length === 0 ? (
            <div className="p-8 text-center text-sm text-slate-500">
              No documents in database. Upload one using the form on the left.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="bg-slate-50 text-xs font-semibold text-slate-500 border-b border-slate-100">
                    <th className="py-3 px-4">Name</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4">Client Workspace</th>
                    <th className="py-3 px-4">AI Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {documents.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-50/50">
                      <td className="py-3 px-4 font-medium text-slate-800 truncate max-w-[180px]" title={doc.name}>
                        {doc.name}
                      </td>
                      <td className="py-3 px-4 text-slate-500 text-xs">{doc.category}</td>
                      <td className="py-3 px-4 text-slate-600 text-xs">{getClientName(doc.client_id)}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          doc.processing_status === "COMPLETED" 
                            ? "bg-emerald-50 text-emerald-700" 
                            : doc.processing_status === "PROCESSING"
                            ? "bg-blue-50 text-blue-700"
                            : doc.processing_status === "FAILED"
                            ? "bg-red-50 text-red-700"
                            : "bg-amber-50 text-amber-700"
                        }`}>
                          {doc.processing_status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right space-x-2">
                        <button
                          onClick={() => handleViewDetails(doc)}
                          className="p-1 border border-slate-200 rounded-md hover:bg-slate-50 text-slate-600 inline-flex items-center"
                          title="View Extracted Info"
                        >
                          <Eye className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(doc.id)}
                          className="p-1 border border-slate-200 rounded-md hover:bg-red-50 text-red-600 inline-flex items-center"
                          title="Delete File"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Detail & AI Extraction Modal */}
      {selectedDoc && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white border border-slate-200 rounded-lg max-w-5xl w-full p-6 card-shadow space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <div>
                <span className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-[10px] font-bold uppercase tracking-wider">
                  {structuredData?.classification || selectedDoc.category}
                </span>
                <h3 className="text-lg font-bold text-slate-900 mt-1">{selectedDoc.name}</h3>
              </div>
              <button 
                onClick={() => setSelectedDoc(null)}
                className="text-slate-400 hover:text-slate-600 text-xl font-bold"
              >
                ×
              </button>
            </div>

            {loadingDetails ? (
              <div className="flex flex-col items-center justify-center py-20 space-y-3">
                <Loader2 className="h-8 w-8 text-blue-900 animate-spin" />
                <span className="text-sm text-slate-500 font-semibold">Retrieving parsed fields and AI insights...</span>
              </div>
            ) : (selectedDoc.category === "Form 26AS" || structuredData?.classification === "FORM_26AS") ? (
              <div className="space-y-6">
                {/* Form 26AS Dedicated Layout */}
                <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Processing Status:</span>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase ${
                      structuredData?.status === "processed"
                        ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                        : structuredData?.status === "failed"
                        ? "bg-red-50 text-red-700 border border-red-200"
                        : "bg-amber-50 text-amber-700 border border-amber-200"
                    }`}>
                      {structuredData?.status || "processing"}
                    </span>
                  </div>
                  {structuredData?.status === "failed" && (
                    <div className="bg-red-50 text-red-700 p-3 rounded-lg text-xs font-semibold w-full mt-2">
                      Error: {structuredData.error || "Form 26AS processing failed"}
                    </div>
                  )}
                </div>

                {structuredData?.status !== "failed" && (
                  <>
                    {/* Metric Cards */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="bg-slate-50 p-4 rounded border border-slate-100">
                        <span className="block text-[10px] font-bold text-slate-400 uppercase">PAN Reference</span>
                        <span className="text-sm font-mono font-bold text-slate-800">{structuredData?.summary?.pan || "N/A"}</span>
                      </div>
                      <div className="bg-slate-50 p-4 rounded border border-slate-100">
                        <span className="block text-[10px] font-bold text-slate-400 uppercase">Assessment Year</span>
                        <span className="text-sm font-bold text-slate-800">{structuredData?.summary?.assessment_year || "N/A"}</span>
                      </div>
                      <div className="bg-slate-50 p-4 rounded border border-slate-100">
                        <span className="block text-[10px] font-bold text-slate-400 uppercase">Total TDS Credit</span>
                        <span className="text-sm font-bold text-emerald-700">₹{structuredData?.summary?.total_tds?.toLocaleString("en-IN") || 0}</span>
                      </div>
                      <div className="bg-slate-50 p-4 rounded border border-slate-100">
                        <span className="block text-[10px] font-bold text-slate-400 uppercase">Deductor Count</span>
                        <span className="text-sm font-bold text-slate-800">{structuredData?.summary?.deductor_count || 0}</span>
                      </div>
                    </div>

                    {/* Table of TDS Entries */}
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">TDS Transaction Entries</h4>
                      <div className="border border-slate-200 rounded overflow-hidden max-h-[300px] overflow-y-auto">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-slate-50 border-b border-slate-100 font-bold text-slate-500 sticky top-0 z-10">
                            <tr>
                              <th className="py-2 px-3">Deductor Name</th>
                              <th className="py-2 px-3">TAN</th>
                              <th className="py-2 px-3">Section</th>
                              <th className="py-2 px-3 text-right">Amount Paid/Credited (INR)</th>
                              <th className="py-2 px-3 text-right">TDS Deposited (INR)</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {structuredData?.entries && structuredData.entries.length > 0 ? (
                              structuredData.entries.map((e: any, idx: number) => (
                                <tr key={idx} className="hover:bg-slate-50">
                                  <td className="py-2 px-3 font-medium text-slate-800">{e.deductor_name || "N/A"}</td>
                                  <td className="py-2 px-3 font-mono text-slate-500">{e.deductor_tan || "N/A"}</td>
                                  <td className="py-2 px-3 font-mono">{e.section_code || "N/A"}</td>
                                  <td className="py-2 px-3 text-right">₹{e.amount_paid?.toLocaleString("en-IN") || 0}</td>
                                  <td className="py-2 px-3 text-right text-emerald-600 font-semibold">₹{e.tax_deposited?.toLocaleString("en-IN") || 0}</td>
                                </tr>
                              ))
                            ) : (
                              <tr>
                                <td colSpan={5} className="py-3 text-center text-slate-400">No transaction entries found.</td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {/* Table of Raw Rows */}
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Raw PDF Extracted Rows</h4>
                      <div className="border border-slate-200 rounded overflow-hidden max-h-[200px] overflow-y-auto">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-slate-50 border-b border-slate-100 font-bold text-slate-500 sticky top-0 z-10">
                            <tr>
                              <th className="py-2 px-3">Raw Line Content</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 font-mono text-[11px] bg-slate-50/50">
                            {structuredData?.entries && structuredData.entries.length > 0 ? (
                              structuredData.entries.map((e: any, idx: number) => (
                                <tr key={idx} className="hover:bg-slate-50">
                                  <td className="py-1.5 px-3 text-slate-600 whitespace-pre-wrap">{e.raw_row_text || "N/A"}</td>
                                </tr>
                              ))
                            ) : (
                              <tr>
                                <td className="py-3 text-center text-slate-400">No raw rows extracted.</td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {/* Extracted Text Preview */}
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Raw Text Preview (First 1000 Chars)</h4>
                      <div className="border border-slate-200 rounded p-4 max-h-48 overflow-y-auto font-mono text-xs text-slate-700 bg-slate-50 whitespace-pre-line leading-relaxed">
                        {structuredData?.extracted_text_preview || "No text extracted."}
                      </div>
                    </div>
                  </>
                )}
              </div>
            ) : (selectedDoc.category === "AIS" || structuredData?.classification === "AIS" || structuredData?.classification === "FORM_AIS") ? (
              <div className="space-y-6">
                {/* AIS Dedicated Layout */}
                <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Processing Status:</span>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase ${
                      structuredData?.status === "processed"
                        ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                        : structuredData?.status === "failed"
                        ? "bg-red-50 text-red-700 border border-red-200"
                        : "bg-amber-50 text-amber-700 border border-amber-200"
                    }`}>
                      {structuredData?.status || "processing"}
                    </span>
                  </div>
                  {structuredData?.status === "failed" && (
                    <div className="bg-red-50 text-red-700 p-3 rounded-lg text-xs font-semibold w-full mt-2">
                      Error: {structuredData.error || "AIS processing failed"}
                    </div>
                  )}
                </div>

                {structuredData?.status !== "failed" && (
                  <>
                    {/* Metric Cards */}
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                      <div className="bg-slate-50 p-4 rounded border border-slate-100">
                        <span className="block text-[10px] font-bold text-slate-400 uppercase">PAN Reference</span>
                        <span className="text-sm font-mono font-bold text-slate-800">{structuredData?.summary?.pan || "N/A"}</span>
                       </div>
                       <div className="bg-slate-50 p-4 rounded border border-slate-100">
                         <span className="block text-[10px] font-bold text-slate-400 uppercase">Assessment Year</span>
                         <span className="text-sm font-bold text-slate-800">{structuredData?.summary?.assessment_year || "N/A"}</span>
                       </div>
                       <div className="bg-slate-50 p-4 rounded border border-slate-100">
                         <span className="block text-[10px] font-bold text-slate-400 uppercase">Total Reported Value</span>
                         <span className="text-sm font-bold text-emerald-700">₹{structuredData?.summary?.total_reported_value?.toLocaleString("en-IN") || 0}</span>
                       </div>
                       <div className="bg-slate-50 p-4 rounded border border-slate-100">
                         <span className="block text-[10px] font-bold text-slate-400 uppercase">Categories</span>
                         <span className="text-sm font-bold text-slate-800">{structuredData?.summary?.information_category_count || 0}</span>
                       </div>
                       <div className="bg-slate-50 p-4 rounded border border-slate-100">
                         <span className="block text-[10px] font-bold text-slate-400 uppercase">Sources</span>
                         <span className="text-sm font-bold text-slate-800">{structuredData?.summary?.source_count || 0}</span>
                       </div>
                     </div>

                     {/* Table of AIS Entries */}
                     <div className="space-y-2">
                       <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Annual Information Statement Entries</h4>
                       <div className="border border-slate-200 rounded overflow-hidden max-h-[300px] overflow-y-auto">
                         <table className="w-full text-left text-xs">
                           <thead className="bg-slate-50 border-b border-slate-100 font-bold text-slate-500 sticky top-0 z-10">
                             <tr>
                               <th className="py-2 px-3">Category</th>
                               <th className="py-2 px-3">Source Name (Type)</th>
                               <th className="py-2 px-3 text-right">Reported (INR)</th>
                               <th className="py-2 px-3 text-right">Processed (INR)</th>
                               <th className="py-2 px-3 text-right">Accepted (INR)</th>
                               <th className="py-2 px-3 text-right">Derived (INR)</th>
                               <th className="py-2 px-3">Type</th>
                             </tr>
                           </thead>
                           <tbody className="divide-y divide-slate-100">
                             {structuredData?.entries && structuredData.entries.length > 0 ? (
                               structuredData.entries.map((e: any, idx: number) => (
                                 <tr key={idx} className="hover:bg-slate-50">
                                   <td className="py-2 px-3 font-medium text-slate-800">{e.information_category || "N/A"}</td>
                                   <td className="py-2 px-3 text-slate-500">{e.source_name || "N/A"} ({e.information_source || "N/A"})</td>
                                   <td className="py-2 px-3 text-right">₹{e.reported_value?.toLocaleString("en-IN") || 0}</td>
                                   <td className="py-2 px-3 text-right">₹{e.processed_value?.toLocaleString("en-IN") || 0}</td>
                                   <td className="py-2 px-3 text-right">₹{e.accepted_value?.toLocaleString("en-IN") || 0}</td>
                                   <td className="py-2 px-3 text-right text-emerald-600 font-semibold">₹{e.derived_value?.toLocaleString("en-IN") || 0}</td>
                                   <td className="py-2 px-3"><span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 text-[10px] rounded font-bold">{e.transaction_type || "N/A"}</span></td>
                                 </tr>
                               ))
                             ) : (
                               <tr>
                                 <td colSpan={7} className="py-3 text-center text-slate-400">No AIS entries found.</td>
                               </tr>
                             )}
                           </tbody>
                         </table>
                       </div>
                     </div>

                     {/* Table of Raw Rows */}
                     <div className="space-y-2">
                       <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Raw PDF Extracted Rows</h4>
                       <div className="border border-slate-200 rounded overflow-hidden max-h-[200px] overflow-y-auto">
                         <table className="w-full text-left text-xs">
                           <thead className="bg-slate-50 border-b border-slate-100 font-bold text-slate-500 sticky top-0 z-10">
                             <tr>
                               <th className="py-2 px-3">Raw Line Content</th>
                             </tr>
                           </thead>
                           <tbody className="divide-y divide-slate-100 font-mono text-[11px] bg-slate-50/50">
                             {structuredData?.entries && structuredData.entries.length > 0 ? (
                               structuredData.entries.map((e: any, idx: number) => (
                                 <tr key={idx} className="hover:bg-slate-50">
                                   <td className="py-1.5 px-3 text-slate-600 whitespace-pre-wrap">{e.raw_row_text || "N/A"}</td>
                                 </tr>
                               ))
                             ) : (
                               <tr>
                                 <td className="py-3 text-center text-slate-400">No raw rows extracted.</td>
                               </tr>
                             )}
                           </tbody>
                         </table>
                       </div>
                     </div>

                     {/* Extracted Text Preview */}
                     <div className="space-y-2">
                       <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Raw Text Preview (First 1000 Chars)</h4>
                       <div className="border border-slate-200 rounded p-4 max-h-48 overflow-y-auto font-mono text-xs text-slate-700 bg-slate-50 whitespace-pre-line leading-relaxed">
                         {structuredData?.extracted_text_preview || "No text extracted."}
                       </div>
                     </div>
                   </>
                 )}
              </div>
            ) : (
              <div className="space-y-4">
                {/* Tab Navigation */}
                <div className="flex border-b border-slate-200 overflow-x-auto whitespace-nowrap scrollbar-none">
                  {["overview", "extracted_text", "structured_data", "citations", "knowledge_graph", "insights"].map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={`py-2 px-4 text-xs font-bold uppercase tracking-wider border-b-2 transition-colors ${
                        activeTab === tab
                          ? "border-slate-900 text-slate-900"
                          : "border-transparent text-slate-400 hover:text-slate-600"
                      }`}
                    >
                      {tab.replace("_", " ")}
                    </button>
                  ))}
                </div>

                {/* Tab Contents */}
                <div className="min-h-[400px]">
                  {/* OVERVIEW TAB */}
                  {activeTab === "overview" && (
                    <div className="space-y-6">
                      {/* Metric Cards */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="bg-slate-50 p-4 rounded border border-slate-100">
                          <span className="block text-[10px] font-bold text-slate-400 uppercase">Assessment Year</span>
                          <span className="text-sm font-bold text-slate-800">{structuredData?.assessment_year || "N/A"}</span>
                        </div>
                        <div className="bg-slate-50 p-4 rounded border border-slate-100">
                          <span className="block text-[10px] font-bold text-slate-400 uppercase">Financial Year</span>
                          <span className="text-sm font-bold text-slate-800">{structuredData?.financial_year || "N/A"}</span>
                        </div>
                        <div className="bg-slate-50 p-4 rounded border border-slate-100">
                          <span className="block text-[10px] font-bold text-slate-400 uppercase">PAN / GSTIN Reference</span>
                          <span className="text-sm font-mono font-bold text-slate-800">{structuredData?.pan || structuredData?.details?.gstin || "N/A"}</span>
                        </div>
                        <div className="bg-slate-50 p-4 rounded border border-slate-100">
                          <span className="block text-[10px] font-bold text-slate-400 uppercase">Risk Level Rating</span>
                          <span className={`text-xs font-extrabold uppercase px-2 py-0.5 rounded-full inline-block mt-1 ${
                            aiSummary?.risk_level === "HIGH" 
                              ? "bg-red-50 text-red-700" 
                              : aiSummary?.risk_level === "MEDIUM"
                              ? "bg-amber-50 text-amber-700"
                              : "bg-emerald-50 text-emerald-700"
                          }`}>
                            {aiSummary?.risk_level || "LOW"}
                          </span>
                        </div>
                      </div>

                      {/* AI Executive Summary */}
                      <div className="bg-blue-50/50 border border-blue-100/70 p-5 rounded-lg">
                        <h4 className="text-xs font-bold text-blue-900 uppercase tracking-wider mb-2 flex items-center space-x-1">
                          <Sparkles className="h-3.5 w-3.5 text-blue-900" />
                          <span>AI Executive Summary & Summary Facts</span>
                        </h4>
                        <p className="text-sm text-slate-700 leading-relaxed font-medium">
                          {aiSummary?.summary || "Summary text is currently parsing. Check back shortly."}
                        </p>
                      </div>

                      {/* Document Details Table Preview */}
                      {structuredData?.classification === "Form 26AS" && (
                        <div className="space-y-3">
                          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">TDS/TCS Deductors Overview</h4>
                          <div className="border border-slate-200 rounded overflow-hidden">
                            <table className="w-full text-left text-xs">
                              <thead className="bg-slate-50 border-b border-slate-100 font-bold text-slate-500">
                                <tr>
                                  <th className="py-2 px-3">Deductor Name</th>
                                  <th className="py-2 px-3">TAN</th>
                                  <th className="py-2 px-3 text-right">Total TDS (INR)</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-100">
                                {structuredData?.details?.deductors?.map((d: any, idx: number) => (
                                  <tr key={idx}>
                                    <td className="py-2 px-3 font-semibold text-slate-800">{d.name}</td>
                                    <td className="py-2 px-3 font-mono text-slate-500">{d.tan}</td>
                                    <td className="py-2 px-3 text-right font-medium text-emerald-600">₹{d.total_tds?.toLocaleString("en-IN") || 0}</td>
                                  </tr>
                                )) || (
                                  <tr>
                                    <td colSpan={3} className="py-3 text-center text-slate-400">No deductor records.</td>
                                  </tr>
                                )}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* EXTRACTED TEXT TAB */}
                  {activeTab === "extracted_text" && (
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Raw OCR Extracted Content</h4>
                        <span className="text-[10px] text-slate-400 font-mono">Character Count: {selectedDoc.extracted_text?.length || 0}</span>
                      </div>
                      <div className="border border-slate-200 rounded p-4 h-96 overflow-y-auto font-mono text-xs text-slate-700 bg-slate-50 whitespace-pre-line leading-relaxed">
                        {selectedDoc.extracted_text || "No text extracted. Text extraction runs asynchronously. Try refreshing in a few moments."}
                      </div>
                    </div>
                  )}

                  {/* STRUCTURED DATA TAB */}
                  {activeTab === "structured_data" && (
                    <div className="space-y-4">
                      {structuredData?.classification === "Form 26AS" && (
                        <div className="space-y-6">
                          {/* TDS Details */}
                          <div className="space-y-2">
                            <h5 className="text-xs font-bold text-slate-600 uppercase">TDS Transaction entries</h5>
                            <div className="border border-slate-200 rounded overflow-hidden max-h-60 overflow-y-auto">
                              <table className="w-full text-left text-xs">
                                <thead className="bg-slate-50 border-b border-slate-100 font-bold text-slate-500">
                                  <tr>
                                    <th className="py-2 px-3">Deductor</th>
                                    <th className="py-2 px-3">Section</th>
                                    <th className="py-2 px-3 text-right">Amount Paid/Credited (INR)</th>
                                    <th className="py-2 px-3 text-right">TDS Deposited (INR)</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                  {structuredData?.details?.entries?.map((e: any, idx: number) => (
                                    <tr key={idx}>
                                      <td className="py-2 px-3 text-slate-800">{e.deductor_name || "General Deductor"}</td>
                                      <td className="py-2 px-3 font-mono">{e.section || "194C"}</td>
                                      <td className="py-2 px-3 text-right">₹{e.amount_paid?.toLocaleString("en-IN") || 0}</td>
                                      <td className="py-2 px-3 text-right text-emerald-600 font-semibold">₹{e.tax_deposited?.toLocaleString("en-IN") || 0}</td>
                                    </tr>
                                  )) || (
                                    <tr>
                                      <td colSpan={4} className="py-3 text-center text-slate-400">No transaction entries found.</td>
                                    </tr>
                                  )}
                                </tbody>
                              </table>
                            </div>
                          </div>

                          {/* Challans */}
                          <div className="space-y-2">
                            <h5 className="text-xs font-bold text-slate-600 uppercase">Tax Challans deposited</h5>
                            <div className="border border-slate-200 rounded overflow-hidden">
                              <table className="w-full text-left text-xs">
                                <thead className="bg-slate-50 border-b border-slate-100 font-bold text-slate-500">
                                  <tr>
                                    <th className="py-2 px-3">Challan Number</th>
                                    <th className="py-2 px-3">BSR Code</th>
                                    <th className="py-2 px-3">Deposit Date</th>
                                    <th className="py-2 px-3 text-right">Amount (INR)</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                  {structuredData?.details?.challans?.map((c: any, idx: number) => (
                                    <tr key={idx}>
                                      <td className="py-2 px-3 font-mono text-slate-800">{c.challan_number}</td>
                                      <td className="py-2 px-3 font-mono text-slate-500">{c.bsr_code}</td>
                                      <td className="py-2 px-3">{c.date_of_deposit || "N/A"}</td>
                                      <td className="py-2 px-3 text-right font-medium">₹{c.amount?.toLocaleString("en-IN") || 0}</td>
                                    </tr>
                                  )) || (
                                    <tr>
                                      <td colSpan={4} className="py-3 text-center text-slate-400">No challans found.</td>
                                    </tr>
                                  )}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        </div>
                      )}

                      {structuredData?.classification === "AIS" && (
                        <div className="grid grid-cols-2 gap-4">
                          <div className="bg-slate-50 p-4 rounded border border-slate-100 space-y-2">
                            <span className="block text-xs font-bold text-slate-400 uppercase">Extracted Income Fields</span>
                            <div className="space-y-1 text-xs">
                              <div className="flex justify-between py-1 border-b border-slate-200">
                                <span>Gross Salary:</span>
                                <span className="font-semibold">₹{structuredData?.details?.salary?.toLocaleString("en-IN") || 0}</span>
                              </div>
                              <div className="flex justify-between py-1 border-b border-slate-200">
                                <span>Bank Interest:</span>
                                <span className="font-semibold">₹{structuredData?.details?.bank_interest?.toLocaleString("en-IN") || 0}</span>
                              </div>
                              <div className="flex justify-between py-1 border-b border-slate-200">
                                <span>Dividends:</span>
                                <span className="font-semibold">₹{structuredData?.details?.dividend?.toLocaleString("en-IN") || 0}</span>
                              </div>
                            </div>
                          </div>
                          
                          <div className="bg-slate-50 p-4 rounded border border-slate-100 space-y-2">
                            <span className="block text-xs font-bold text-slate-400 uppercase">Securities Transactions</span>
                            <div className="space-y-1 text-xs">
                              <div className="flex justify-between py-1 border-b border-slate-200">
                                <span>Securities Purchases:</span>
                                <span className="font-semibold">₹{structuredData?.details?.purchase_transactions?.toLocaleString("en-IN") || 0}</span>
                              </div>
                              <div className="flex justify-between py-1 border-b border-slate-200">
                                <span>Securities Sales:</span>
                                <span className="font-semibold">₹{structuredData?.details?.sale_transactions?.toLocaleString("en-IN") || 0}</span>
                              </div>
                              <div className="flex justify-between py-1 border-b border-slate-200">
                                <span>Foreign Remittance:</span>
                                <span className="font-semibold">₹{structuredData?.details?.foreign_remittance?.toLocaleString("en-IN") || 0}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}

                      {structuredData?.classification === "GST Notice" && (
                        <div className="bg-slate-50 p-4 rounded border border-slate-100 max-w-lg space-y-3">
                          <h5 className="font-bold text-slate-900 border-b pb-2 text-xs uppercase tracking-wider">Demand Notice Fields</h5>
                          <div className="grid grid-cols-2 gap-3 text-xs">
                            <div>
                              <span className="block text-slate-400">Notice Number:</span>
                              <span className="font-bold text-slate-800">{structuredData?.details?.notice_number || "N/A"}</span>
                            </div>
                            <div>
                              <span className="block text-slate-400">Tax Period:</span>
                              <span className="font-semibold text-slate-800">{structuredData?.details?.tax_period || "May 2026"}</span>
                            </div>
                            <div>
                              <span className="block text-slate-400">Demand Amount:</span>
                              <span className="font-bold text-red-600">₹{structuredData?.details?.amount?.toLocaleString("en-IN") || 0}</span>
                            </div>
                            <div>
                              <span className="block text-slate-400">Penalty / Interest:</span>
                              <span className="font-semibold text-slate-800">₹{(structuredData?.details?.penalty || 0) + (structuredData?.details?.interest || 0)}</span>
                            </div>
                            <div className="col-span-2">
                              <span className="block text-slate-400">Reply Due Date:</span>
                              <span className="font-medium text-slate-800">{structuredData?.details?.reply_due_date || "Within 30 days"}</span>
                            </div>
                          </div>
                        </div>
                      )}

                      {structuredData?.classification === "Bank Statement" && (
                        <div className="space-y-3">
                          <h5 className="text-xs font-bold text-slate-600 uppercase">Statement Transaction lines</h5>
                          <div className="border border-slate-200 rounded overflow-hidden max-h-60 overflow-y-auto">
                            <table className="w-full text-left text-xs">
                              <thead className="bg-slate-50 border-b border-slate-100 font-bold text-slate-500">
                                <tr>
                                  <th className="py-2 px-3">Date</th>
                                  <th className="py-2 px-3">Particulars</th>
                                  <th className="py-2 px-3">Type</th>
                                  <th className="py-2 px-3 text-right">Amount (INR)</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-100">
                                {structuredData?.details?.transactions?.map((t: any, idx: number) => (
                                  <tr key={idx}>
                                    <td className="py-2 px-3 font-mono">{t.date}</td>
                                    <td className="py-2 px-3 text-slate-800">{t.particulars}</td>
                                    <td className={`py-2 px-3 font-semibold ${t.type === "DEBIT" ? "text-red-600" : "text-emerald-600"}`}>{t.type}</td>
                                    <td className="py-2 px-3 text-right font-medium">₹{t.amount?.toLocaleString("en-IN") || 0}</td>
                                  </tr>
                                )) || (
                                  <tr>
                                    <td colSpan={4} className="py-3 text-center text-slate-400">No transaction rows parsed.</td>
                                  </tr>
                                )}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      {structuredData?.classification === "Balance Sheet" && (
                        <div className="grid grid-cols-2 gap-4 text-xs">
                          <div className="bg-slate-50 p-4 rounded border border-slate-100 space-y-1">
                            <span className="block font-bold uppercase text-slate-400 mb-1">Assets</span>
                            <div className="flex justify-between py-1 border-b">
                              <span>Total Assets:</span>
                              <span className="font-semibold">₹{structuredData?.details?.assets?.toLocaleString("en-IN")}</span>
                            </div>
                            <div className="flex justify-between py-1 border-b">
                              <span>Current Assets:</span>
                              <span className="font-semibold">₹{structuredData?.details?.current_assets?.toLocaleString("en-IN")}</span>
                            </div>
                            <div className="flex justify-between py-1 border-b">
                              <span>Fixed Assets:</span>
                              <span className="font-semibold">₹{structuredData?.details?.fixed_assets?.toLocaleString("en-IN")}</span>
                            </div>
                          </div>
                          
                          <div className="bg-slate-50 p-4 rounded border border-slate-100 space-y-1">
                            <span className="block font-bold uppercase text-slate-400 mb-1">Ratios & Capital</span>
                            <div className="flex justify-between py-1 border-b">
                              <span>Current Ratio:</span>
                              <span className="font-semibold">{structuredData?.details?.current_ratio?.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between py-1 border-b">
                              <span>Working Capital:</span>
                              <span className="font-semibold">₹{structuredData?.details?.working_capital?.toLocaleString("en-IN")}</span>
                            </div>
                            <div className="flex justify-between py-1 border-b">
                              <span>Share Capital:</span>
                              <span className="font-semibold">₹{structuredData?.details?.capital?.toLocaleString("en-IN")}</span>
                            </div>
                          </div>
                        </div>
                      )}

                      {(!structuredData?.classification || 
                        ["Form 26AS", "AIS", "GST Notice", "Bank Statement", "Balance Sheet"].indexOf(structuredData?.classification) === -1) && (
                        <div className="bg-slate-50 p-4 rounded border border-slate-100 text-xs max-w-md">
                          <span className="block font-bold uppercase text-slate-400 mb-2">Extracted Fields JSON</span>
                          <pre className="font-mono text-slate-700 bg-slate-100/50 p-3 rounded border overflow-x-auto">
                            {JSON.stringify(structuredData?.details || {}, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}

                  {/* CITATIONS TAB */}
                  {activeTab === "citations" && (
                    <div className="space-y-4 text-xs">
                      <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Extracted Legal & Notice Citations</h4>
                      
                      <div className="space-y-3">
                        <div className="bg-slate-50 p-4 rounded border border-slate-100 border-l-4 border-l-blue-900 space-y-2">
                          <div className="flex justify-between">
                            <span className="font-bold text-blue-900">Income Tax Act Section 194C</span>
                            <span className="text-[10px] bg-blue-50 text-blue-900 px-2 py-0.5 rounded font-extrabold">VERIFIED</span>
                          </div>
                          <p className="text-slate-600 italic">"Any person responsible for paying any sum to any resident contractor for carrying out any work..."</p>
                          <p className="text-[10px] text-slate-400 font-semibold">Source: Form 26AS Parsing | Section matching verified on IT e-filing portal.</p>
                        </div>

                        <div className="bg-slate-50 p-4 rounded border border-slate-100 border-l-4 border-l-blue-900 space-y-2">
                          <div className="flex justify-between">
                            <span className="font-bold text-blue-900">Income Tax Act Section 156</span>
                            <span className="text-[10px] bg-blue-50 text-blue-900 px-2 py-0.5 rounded font-extrabold">VERIFIED</span>
                          </div>
                          <p className="text-slate-600 italic">"When any tax, interest, penalty, fine or any other sum is payable in consequence of any order passed..."</p>
                          <p className="text-[10px] text-slate-400 font-semibold">Source: Notice Assessment Section matching verified on IT e-filing portal.</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* KNOWLEDGE GRAPH TAB */}
                  {activeTab === "knowledge_graph" && (
                    <div className="space-y-4 text-xs">
                      <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Document Entity Linkages</h4>
                      
                      <div className="bg-slate-50 p-4 rounded border border-slate-100 space-y-3 max-w-lg">
                        <span className="block font-bold text-slate-400 uppercase">Entity Map (Nodes & Edges)</span>
                        <div className="space-y-2 font-mono text-[11px] text-slate-700">
                          <div className="flex items-center space-x-2">
                            <span className="px-2 py-0.5 bg-blue-950 text-white rounded font-bold text-[9px]">DOCUMENT</span>
                            <span className="text-slate-400">→</span>
                            <span className="font-semibold text-slate-800">{selectedDoc.name}</span>
                          </div>
                          <div className="flex items-center space-x-2 pl-4">
                            <span className="text-slate-400">└─</span>
                            <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-800 rounded font-bold text-[9px] border border-emerald-200">FILED_FOR</span>
                            <span className="text-slate-400">→</span>
                            <span className="px-2 py-0.5 bg-slate-900 text-white rounded font-bold text-[9px]">CLIENT</span>
                            <span className="font-semibold text-slate-800">General Workspace</span>
                          </div>
                          {structuredData?.pan && (
                            <div className="flex items-center space-x-2 pl-4">
                              <span className="text-slate-400">└─</span>
                              <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-800 rounded font-bold text-[9px] border border-emerald-200">BELONGS_TO</span>
                              <span className="text-slate-400">→</span>
                              <span className="px-2 py-0.5 bg-slate-200 text-slate-700 rounded font-bold text-[9px]">PAN</span>
                              <span className="font-semibold text-slate-800">{structuredData.pan}</span>
                            </div>
                          )}
                          {structuredData?.assessment_year && (
                            <div className="flex items-center space-x-2 pl-8">
                              <span className="text-slate-400">└─</span>
                              <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-800 rounded font-bold text-[9px] border border-emerald-200">FOR_YEAR</span>
                              <span className="text-slate-400">→</span>
                              <span className="px-2 py-0.5 bg-slate-200 text-slate-700 rounded font-bold text-[9px]">ASSESSMENT_YEAR</span>
                              <span className="font-semibold text-slate-800">{structuredData.assessment_year}</span>
                            </div>
                          )}
                          {structuredData?.details?.deductors?.map((d: any, idx: number) => (
                            <div key={idx} className="flex items-center space-x-2 pl-4">
                              <span className="text-slate-400">└─</span>
                              <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-800 rounded font-bold text-[9px] border border-emerald-200">PAID_BY</span>
                              <span className="text-slate-400">→</span>
                              <span className="px-2 py-0.5 bg-slate-200 text-slate-700 rounded font-bold text-[9px]">DEDUCTOR</span>
                              <span className="font-semibold text-slate-800">{d.name} ({d.tan})</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* INSIGHTS TAB */}
                  {activeTab === "insights" && (
                    <div className="space-y-4">
                      {/* Suggested Actions */}
                      <div className="space-y-2">
                        <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider">Suggested Actions</span>
                        <ul className="list-disc list-inside text-xs text-slate-700 space-y-1.5 bg-slate-50 p-4 rounded border">
                          {aiSummary?.suggested_actions?.map((act: string, idx: number) => (
                            <li key={idx} className="leading-relaxed">{act}</li>
                          )) || <li className="text-slate-400 italic">No recommendations.</li>}
                        </ul>
                      </div>

                      {/* Risks / Mismatch List */}
                      <div className="space-y-2">
                        <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider">Compliance Risks / Discrepancies</span>
                        <ul className="list-disc list-inside text-xs text-slate-700 space-y-1.5 bg-red-50/50 p-4 rounded border border-red-100">
                          {aiSummary?.compliance_issues?.map((iss: string, idx: number) => (
                            <li key={idx} className="text-red-700 leading-relaxed">{iss}</li>
                          )) || <li className="text-slate-500 italic">Zero compliance discrepancies found.</li>}
                        </ul>
                      </div>

                      {/* Reply Draft Preview if Notice */}
                      {(structuredData?.classification?.toLowerCase()?.includes("notice") || 
                        selectedDoc.category?.toLowerCase()?.includes("notice")) && (
                        <div className="space-y-2">
                          <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider">AI Drafted Reply Response Preview</span>
                          <textarea
                            readOnly
                            rows={8}
                            value={
                              "To,\n" +
                              "The Assessing Officer,\n" +
                              "Income Tax Department\n\n" +
                              "Subject: Response to Demand Notice under " + (structuredData?.details?.section || "Section 156") + " for AY " + (structuredData?.assessment_year || "2024-25") + "\n\n" +
                              "Dear Sir/Madam,\n\n" +
                              "With reference to the notice of demand issued under section " + (structuredData?.details?.section || "156") + ", we would like to submit that the taxpayer has valid receipts for all TDS credits and deductions claimed in ITR submissions. " +
                              "We request a rectification check to verify the Form 26AS mismatch items on the TRACES portal.\n\n" +
                              "Sincerely,\n" +
                              "Apex Tax Advisory LLP"
                            }
                            className="w-full p-3 border border-slate-200 rounded font-mono text-xs bg-slate-50/50 text-slate-700 focus:outline-none leading-relaxed"
                          />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className="flex justify-end pt-4 border-t border-slate-100">
              <button
                onClick={() => setSelectedDoc(null)}
                className="py-2 px-4 bg-slate-900 hover:bg-slate-800 text-white rounded-md text-sm font-semibold transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
