import React, { useState } from "react";
import { api } from "../lib/api";
import { Building2, KeyRound, Mail, Phone, MapPin, User, FileText } from "lucide-react";

interface AuthPanelProps {
  onAuthSuccess: (user: any) => void;
}

export const AuthPanel: React.FC<AuthPanelProps> = ({ onAuthSuccess }) => {
  const [isRegister, setIsRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Login Form State
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // Register Form State
  const [orgName, setOrgName] = useState("");
  const [firmType, setFirmType] = useState("Partnership");
  const [gstin, setGstin] = useState("");
  const [pan, setPan] = useState("");
  const [address, setAddress] = useState("");
  const [orgEmail, setOrgEmail] = useState("");
  const [orgPhone, setOrgPhone] = useState("");
  const [adminFirstName, setAdminFirstName] = useState("");
  const [adminLastName, setAdminLastName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [adminPassword, setAdminPassword] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await api.login({ email: loginEmail, password: loginPassword });
      onAuthSuccess(data.user);
    } catch (err: any) {
      setError(err.message || "Invalid credentials. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload = {
        organization_name: orgName,
        firm_type: firmType,
        GSTIN: gstin || null,
        PAN: pan || null,
        address: address || null,
        contact_email: orgEmail,
        phone: orgPhone || null,
        admin_first_name: adminFirstName,
        admin_last_name: adminLastName,
        admin_email: adminEmail,
        admin_password: adminPassword,
      };
      const data = await api.register(payload);
      onAuthSuccess(data.user);
    } catch (err: any) {
      setError(err.message || "Registration failed. Please verify fields.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">
          CA Intelligence
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          AI Operating System for Indian Chartered Accountants
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-xl">
        <div className="bg-white py-8 px-4 shadow-sm sm:rounded-lg sm:px-10 border border-slate-200">
          <div className="flex justify-center space-x-4 mb-6 border-b border-slate-200 pb-4">
            <button
              onClick={() => { setIsRegister(false); setError(null); }}
              className={`pb-2 px-4 text-sm font-semibold transition-all ${
                !isRegister
                  ? "border-b-2 border-blue-900 text-blue-900"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => { setIsRegister(true); setError(null); }}
              className={`pb-2 px-4 text-sm font-semibold transition-all ${
                isRegister
                  ? "border-b-2 border-blue-900 text-blue-900"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              Register Firm
            </button>
          </div>

          {error && (
            <div className="mb-4 bg-red-50 border-l-4 border-red-500 p-4 text-sm text-red-700">
              {error}
            </div>
          )}

          {!isRegister ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                  Email Address
                </label>
                <div className="mt-1 relative rounded-md shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Mail className="h-4 w-4 text-slate-400" />
                  </div>
                  <input
                    type="email"
                    required
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    className="block w-full pl-10 pr-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 focus:border-blue-900 text-sm"
                    placeholder="partner@firm.com"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                  Password
                </label>
                <div className="mt-1 relative rounded-md shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <KeyRound className="h-4 w-4 text-slate-400" />
                  </div>
                  <input
                    type="password"
                    required
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    className="block w-full pl-10 pr-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 focus:border-blue-900 text-sm"
                    placeholder="••••••••"
                  />
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-semibold text-white bg-slate-900 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-900 disabled:opacity-50 transition-colors"
                >
                  {loading ? "Signing in..." : "Sign In"}
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="space-y-6">
              <div className="border-b border-slate-100 pb-3">
                <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
                  Firm Details
                </h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    Firm / Organization Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm"
                    placeholder="Singhania & Co."
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    Firm Type *
                  </label>
                  <select
                    value={firmType}
                    onChange={(e) => setFirmType(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm"
                  >
                    <option value="Proprietorship">Proprietorship</option>
                    <option value="Partnership">Partnership</option>
                    <option value="LLP">LLP</option>
                    <option value="Company">Company</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    GSTIN
                  </label>
                  <input
                    type="text"
                    value={gstin}
                    onChange={(e) => setGstin(e.target.value.toUpperCase())}
                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm"
                    placeholder="27AAAAA1111A1Z1"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    PAN
                  </label>
                  <input
                    type="text"
                    value={pan}
                    onChange={(e) => setPan(e.target.value.toUpperCase())}
                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm"
                    placeholder="AAAAA1111A"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-xs font-semibold text-slate-700">
                    Registered Address
                  </label>
                  <textarea
                    rows={2}
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm"
                    placeholder="101, Connaught Place, New Delhi"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    Firm Contact Email *
                  </label>
                  <input
                    type="email"
                    required
                    value={orgEmail}
                    onChange={(e) => setOrgEmail(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm"
                    placeholder="contact@singhaniaca.in"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    Firm Contact Phone
                  </label>
                  <input
                    type="text"
                    value={orgPhone}
                    onChange={(e) => setOrgPhone(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm"
                    placeholder="+91 11-450000"
                  />
                </div>
              </div>

              <div className="border-b border-slate-100 pb-3 pt-2">
                <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
                  Admin User Details (Firm Admin Role)
                </h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    First Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={adminFirstName}
                    onChange={(e) => setAdminFirstName(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm"
                    placeholder="Rajesh"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    Last Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={adminLastName}
                    onChange={(e) => setAdminLastName(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm"
                    placeholder="Singhania"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    Admin Personal Email *
                  </label>
                  <input
                    type="email"
                    required
                    value={adminEmail}
                    onChange={(e) => setAdminEmail(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm"
                    placeholder="rajesh@singhaniaca.in"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    Admin Password *
                  </label>
                  <input
                    type="password"
                    required
                    value={adminPassword}
                    onChange={(e) => setAdminPassword(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-900 text-sm"
                    placeholder="••••••••"
                  />
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-semibold text-white bg-slate-900 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-900 disabled:opacity-50 transition-colors"
                >
                  {loading ? "Registering..." : "Register Firm & Sign In"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
