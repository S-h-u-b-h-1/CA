import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import { User, Building2, Save, CreditCard, Shield, Check } from "lucide-react";

interface SettingsPanelProps {
  currentUser: any;
  onRefreshUser: () => void;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  currentUser,
  onRefreshUser
}) => {
  const [org, setOrg] = useState<any | null>(null);
  
  // Org Form State
  const [orgName, setOrgName] = useState("");
  const [firmType, setFirmType] = useState("");
  const [gstin, setGstin] = useState("");
  const [pan, setPan] = useState("");
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");

  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadOrgProfile();
  }, []);

  const loadOrgProfile = async () => {
    try {
      const data = await api.getOrgProfile();
      setOrg(data);
      setOrgName(data.organization_name);
      setFirmType(data.firm_type);
      setGstin(data.GSTIN || "");
      setPan(data.PAN || "");
      setAddress(data.address || "");
      setPhone(data.phone || "");
    } catch (err) {
      console.error(err);
    }
  };

  const handleSaveOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);
    try {
      await api.updateOrgProfile({
        organization_name: orgName,
        firm_type: firmType,
        GSTIN: gstin || null,
        PAN: pan || null,
        address: address || null,
        phone: phone || null
      });
      setSuccess(true);
      loadOrgProfile();
    } catch (err: any) {
      setError(err.message || "Failed to update profile");
    } finally {
      setLoading(false);
    }
  };

  const isOrgAdmin = currentUser && ["SUPER_ADMIN", "FIRM_ADMIN"].includes(currentUser.role);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Settings & Profile</h1>
        <p className="text-sm text-slate-500 mt-1">Manage your Chartered Accountancy firm subscription, profile fields, and team rules.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* User Card */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 card-shadow h-fit space-y-4">
          <div className="flex items-center space-x-3 pb-3 border-b border-slate-100">
            <div className="p-2 bg-slate-100 rounded-full">
              <User className="h-6 w-6 text-slate-700" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-sm">
                {currentUser?.first_name} {currentUser?.last_name}
              </h3>
              <p className="text-xs text-slate-500">{currentUser?.email}</p>
            </div>
          </div>

          <div className="space-y-3 text-xs text-slate-600">
            <div className="flex justify-between">
              <span className="font-semibold">Security Role:</span>
              <span className="px-2 py-0.5 bg-blue-50 text-blue-900 rounded font-bold">{currentUser?.role}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-semibold">Account Status:</span>
              <span className="text-emerald-600 font-semibold">Active</span>
            </div>
          </div>
        </div>

        {/* Organization Card */}
        {org && (
          <div className="bg-white border border-slate-200 rounded-lg p-5 card-shadow lg:col-span-2 space-y-4">
            <div className="flex items-center space-x-2 pb-2 border-b border-slate-100">
              <Building2 className="h-5 w-5 text-blue-900" />
              <h3 className="font-bold text-slate-900">CA Firm Settings</h3>
            </div>

            {success && (
              <div className="bg-emerald-50 border border-emerald-100 p-3 rounded text-xs text-emerald-700 flex items-center space-x-1.5">
                <Check className="h-4 w-4" />
                <span>Firm settings updated successfully!</span>
              </div>
            )}

            {error && (
              <div className="bg-red-50 p-3 rounded text-xs text-red-700">
                {error}
              </div>
            )}

            <form onSubmit={handleSaveOrg} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700">Firm Name</label>
                  <input
                    type="text"
                    required
                    disabled={!isOrgAdmin}
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm disabled:bg-slate-50"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">Firm Type</label>
                  <select
                    disabled={!isOrgAdmin}
                    value={firmType}
                    onChange={(e) => setFirmType(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm disabled:bg-slate-50"
                  >
                    <option value="Proprietorship">Proprietorship</option>
                    <option value="Partnership">Partnership</option>
                    <option value="LLP">LLP</option>
                    <option value="Company">Company</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">GSTIN</label>
                  <input
                    type="text"
                    disabled={!isOrgAdmin}
                    value={gstin}
                    onChange={(e) => setGstin(e.target.value.toUpperCase())}
                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm disabled:bg-slate-50"
                    placeholder="27AAAAA1111A1Z1"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">PAN</label>
                  <input
                    type="text"
                    disabled={!isOrgAdmin}
                    value={pan}
                    onChange={(e) => setPan(e.target.value.toUpperCase())}
                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm disabled:bg-slate-50"
                    placeholder="AAAAA1111A"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-xs font-semibold text-slate-700">Registered Office Address</label>
                  <textarea
                    rows={2}
                    disabled={!isOrgAdmin}
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm disabled:bg-slate-50"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">Contact Phone</label>
                  <input
                    type="text"
                    disabled={!isOrgAdmin}
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm disabled:bg-slate-50"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">Subscription Tier</label>
                  <div className="mt-1 flex items-center space-x-2 py-2 px-3 bg-slate-50 border border-slate-200 rounded text-xs font-bold text-slate-700">
                    <CreditCard className="h-4 w-4 text-blue-900" />
                    <span>{org.subscription_plan} Plan</span>
                  </div>
                </div>
              </div>

              {isOrgAdmin && (
                <div className="flex justify-end pt-4 border-t border-slate-100">
                  <button
                    type="submit"
                    disabled={loading}
                    className="py-2 px-4 bg-slate-900 hover:bg-slate-800 text-white rounded-md text-sm font-semibold flex items-center space-x-1.5 transition-colors"
                  >
                    <Save className="h-4 w-4" />
                    <span>{loading ? "Saving..." : "Save Settings"}</span>
                  </button>
                </div>
              )}
            </form>
          </div>
        )}

      </div>
    </div>
  );
};
