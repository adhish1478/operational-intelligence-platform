import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { api } from '../lib/api';
import {
  Building2,
  ArrowRight,
  ShieldAlert,
  Mail,
  Lock
} from 'lucide-react';


export const Onboarding: React.FC = () => {
  const navigate = useNavigate();
  const { user, token, setAuth } = useAuthStore();

  const [orgName, setOrgName] = useState('');
  const [orgSlug, setOrgSlug] = useState('');

  const [inviteCode, setInviteCode] = useState('');

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Auto-generate slug from name on change
  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setOrgName(value);
    // Convert to lowercase, remove non-alphanumeric, replace spaces with hyphens
    const generatedSlug = value
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-')
      .slice(0, 30);
    setOrgSlug(generatedSlug);
  };

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orgName || !orgSlug) {
      setError('Please provide a workspace name and slug.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // 1. Send create request to Backend
      const newOrg = await api.post('api/v1/organizations/', {
        name: orgName,
        slug: orgSlug
      });

      // 2. Fetch updated user profile containing organizations
      const updatedUser = await api.get('/api/v1/auth/me');

      // 3. Update auth store with active workspace organization
      if (token && updatedUser) {
        setAuth(token, updatedUser, newOrg.id);
      }

      // 4. Redirect to dashboard
      navigate('/dashboard');

    } catch (err: any) {
      setError(err.message || 'Failed to create organization. Workspace slug might already be taken.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F7F9FB] text-[#191C1E] flex flex-col items-center justify-center p-6 selection:bg-[#dae2fd] selection:text-[#131b2e]">
      {/* Header Logotype */}
      <div className="mb-8 text-center">
        <div className="font-mono text-xs tracking-[0.25em] text-[#515F74] flex items-center justify-center gap-2 uppercase font-bold mb-2">
          <span className="w-2 h-2 rounded-full bg-[#10B981]"></span>
          AGY SYSTEM ONBOARDING
        </div>
        <h1 className="text-3xl font-bold text-[#0F172A] tracking-tight">Configure Your Ops Command</h1>
      </div>

      <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-8 bg-white border border-[#C6C6CD] p-8 rounded-lg shadow-sm">
        {/* Left Side: Create Workspace */}
        <div className="flex flex-col justify-between pr-0 md:pr-8 border-r-0 md:border-r border-[#E2E8F0]">
          <div>
            <div className="flex items-center gap-2 mb-4 text-[#0F172A]">
              <Building2 className="w-5 h-5 shrink-0" />
              <h2 className="text-lg font-bold">Create a new Workspace</h2>
            </div>
            <p className="text-xs text-[#515F74] leading-relaxed mb-6">
              Establish a secure isolated tenant organization. You will be assigned as the **Organization Owner** and can invite team members later.
            </p>

            {error && (
              <div className="p-3 bg-red-50 text-red-700 text-xs rounded mb-4 flex items-start gap-2 border border-red-100">
                <ShieldAlert className="w-4.5 h-4.5 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleCreateWorkspace} className="space-y-4">
              <div>
                <label className="block font-mono text-[9px] text-[#515F74] mb-1 uppercase tracking-widest font-bold">Workspace Name</label>
                <input
                  type="text"
                  value={orgName}
                  onChange={handleNameChange}
                  className="w-full bg-[#F7F9FB] border border-[#C6C6CD] p-3 focus:border-[#0F172A] focus:outline-none text-xs rounded transition-all"
                  placeholder="e.g. Acme Ops"
                  required
                  disabled={loading}
                />
              </div>
              <div>
                <label className="block font-mono text-[9px] text-[#515F74] mb-1 uppercase tracking-widest font-bold">Workspace URL Slug</label>
                <div className="flex items-center bg-[#F7F9FB] border border-[#C6C6CD] rounded focus-within:border-[#0F172A] transition-all">
                  <span className="pl-3 pr-1 text-xs text-[#515F74] select-none font-mono">/org/</span>
                  <input
                    type="text"
                    value={orgSlug}
                    onChange={(e) => setOrgSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                    className="w-full bg-transparent p-3 focus:outline-none text-xs"
                    placeholder="acme-ops"
                    required
                    disabled={loading}
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={loading || !orgName}
                className="w-full py-3 bg-[#0F172A] text-white text-xs font-mono uppercase tracking-widest hover:bg-black active:bg-slate-900 transition-all rounded font-bold disabled:opacity-40 flex items-center justify-center gap-2 mt-6"
              >
                {loading ? 'Creating Workspace...' : 'Create Workspace'}
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>

        {/* Right Side: Have Invite / Enter Code */}
        <div className="flex flex-col justify-between pl-0 md:pl-8 pt-6 md:pt-0">
          <div>
            <div className="flex items-center gap-2 mb-4 text-[#515F74]">
              <Mail className="w-5 h-5 shrink-0" />
              <h2 className="text-lg font-bold">Join Existing Workspace</h2>
            </div>
            <p className="text-xs text-[#515F74] leading-relaxed mb-6">
              Received a secure invitation link or access token from your team administrator? Enter details below to link your account.
            </p>

            <div className="space-y-4 opacity-60 pointer-events-none">
              <div>
                <label className="block font-mono text-[9px] text-[#515F74] mb-1 uppercase tracking-widest font-bold">Invitation Code</label>
                <input
                  type="text"
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value)}
                  className="w-full bg-[#f2f4f6] border border-[#C6C6CD] p-3 text-xs rounded transition-all cursor-not-allowed"
                  placeholder="e.g. INV-9028-XY"
                  disabled
                />
              </div>
              <div className="p-3 bg-[#ECEEF0] text-[#515F74] text-xs rounded flex gap-2 border border-[#C6C6CD] mt-2">
                <Lock className="w-4 h-4 shrink-0 mt-0.5" />
                <span>Invite integration features are coming soon. The organization owner will be able to dispatch codes shortly.</span>
              </div>
              <button
                disabled
                className="w-full py-3 border border-[#C6C6CD] text-[#515F74] text-xs font-mono uppercase tracking-widest transition-all rounded font-bold cursor-not-allowed mt-4"
              >
                Join Workspace
              </button>
            </div>
          </div>

          {/* Logged in User Indicator Footer */}
          <div className="mt-8 pt-4 border-t border-[#E2E8F0] flex items-center justify-between text-[11px] text-[#515F74]">
            <span>Signed in as: <strong className="text-[#0F172A]">{user?.email}</strong></span>
            <button
              onClick={() => {
                useAuthStore.getState().logout();
                navigate('/');
              }}
              className="text-[#ba1a1a] hover:underline"
            >
              Sign Out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
