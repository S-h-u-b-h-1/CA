import React, { useState, useEffect, useRef } from "react";
import { api } from "../lib/api";
import { Bell, Archive, Check, Loader2 } from "lucide-react";

const SOURCE_STYLES: Record<string, string> = {
  TAX: "bg-purple-50 text-purple-700",
  COMPLIANCE: "bg-blue-50 text-blue-700",
  DOCUMENTS: "bg-slate-100 text-slate-600",
  RESEARCH: "bg-emerald-50 text-emerald-700",
};

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export const NotificationCenter: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    refreshUnreadCount();
    const interval = setInterval(refreshUnreadCount, 60000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const refreshUnreadCount = async () => {
    try {
      const res = await api.getUnreadNotificationCount();
      setUnreadCount(res.unread_count || 0);
    } catch {
      // silent — notification count is non-critical
    }
  };

  const togglePanel = async () => {
    const next = !open;
    setOpen(next);
    if (next) {
      setLoading(true);
      try {
        const rows = await api.listNotifications();
        setNotifications(rows);
      } finally {
        setLoading(false);
      }
    }
  };

  const markRead = async (id: string) => {
    await api.updateNotificationStatus(id, "READ");
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, status: "READ" } : n)));
    refreshUnreadCount();
  };

  const archive = async (id: string) => {
    await api.updateNotificationStatus(id, "ARCHIVED");
    setNotifications((prev) => prev.filter((n) => n.id !== id));
    refreshUnreadCount();
  };

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={togglePanel}
        className="p-1.5 hover:bg-slate-50 border border-slate-200 rounded-full text-slate-400 hover:text-slate-600 relative"
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 flex items-center justify-center rounded-full bg-red-500 text-white text-[9px] font-bold">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-96 bg-white border border-slate-200 rounded-xl shadow-lg z-50 max-h-[28rem] overflow-y-auto">
          <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
            <h4 className="text-sm font-bold text-slate-800">Notifications</h4>
            <span className="text-[10px] font-bold text-slate-400 uppercase">{unreadCount} unread</span>
          </div>
          {loading ? (
            <div className="p-8 flex justify-center">
              <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
            </div>
          ) : notifications.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-400">No notifications.</div>
          ) : (
            <div className="divide-y divide-slate-100">
              {notifications.map((n) => (
                <div key={n.id} className={`px-4 py-3 ${n.status === "UNREAD" ? "bg-blue-50/40" : ""}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5 mb-1">
                        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${SOURCE_STYLES[n.source] || "bg-slate-100 text-slate-600"}`}>{n.source}</span>
                        {n.client_name && <span className="text-[10px] text-slate-400">{n.client_name}</span>}
                      </div>
                      <p className="text-xs font-semibold text-slate-800">{n.title}</p>
                      <p className="text-[10px] text-slate-400 mt-0.5">{timeAgo(n.created_at)}</p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      {n.status === "UNREAD" && (
                        <button onClick={() => markRead(n.id)} title="Mark as read" className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-blue-900">
                          <Check className="h-3.5 w-3.5" />
                        </button>
                      )}
                      <button onClick={() => archive(n.id)} title="Archive" className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-700">
                        <Archive className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
