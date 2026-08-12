import React, { useState, useEffect } from 'react';
import { Shield, CreditCard, Building2, User, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { api } from '../lib/api';

const PRESET_ROLES = [
  'Platform Engineer',
  'Site Reliability Engineer (SRE)',
  'DevOps Lead',
  'Security Engineer / SecOps',
  'Full Stack Developer',
  'Engineering Manager',
  'Other (Custom)'
];

export const Settings: React.FC = () => {
  const { user, token, activeOrgId, setAuth } = useAuthStore();

  const [activeTab, setActiveTab] = useState<'profile' | 'workspace' | 'security' | 'billing'>('profile');

  // Derive initial values from active logged in user
  const initialFullName = user?.first_name 
    ? `${user.first_name} ${user.last_name || ''}`.trim() 
    : '';
  
  const activeOrg = user?.organizations?.find(o => o.id === activeOrgId) || user?.organizations?.[0];
  const initialRole = activeOrg?.role || 'Platform Engineer';

  const [fullName, setFullName] = useState(initialFullName);
  const [email, setEmail] = useState(user?.email || '');
  
  const isPreset = PRESET_ROLES.includes(initialRole);
  const [selectedRole, setSelectedRole] = useState(isPreset ? initialRole : 'Other (Custom)');
  const [customRole, setCustomRole] = useState(isPreset ? '' : initialRole);

  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Sync state if user changes in store
  useEffect(() => {
    if (user) {
      setFullName(user.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : '');
      setEmail(user.email || '');
      const role = activeOrg?.role || 'Platform Engineer';
      if (PRESET_ROLES.includes(role)) {
        setSelectedRole(role);
        setCustomRole('');
      } else {
        setSelectedRole('Other (Custom)');
        setCustomRole(role);
      }
    }
  }, [user?.id, user?.email, activeOrg?.role]);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSuccessMsg(null);
    setErrorMsg(null);

    const effectiveRole = selectedRole === 'Other (Custom)' ? customRole.trim() : selectedRole;

    try {
      const updatedUser = await api.patch('/auth/me', {
        full_name: fullName,
        email: email,
        role: effectiveRole || 'Platform Engineer'
      });

      if (token && updatedUser) {
        setAuth(token, updatedUser, activeOrgId || updatedUser.organizations?.[0]?.id || '');
      }

      setSuccessMsg('Profile updated successfully!');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to update profile.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant pb-4">
        <div>
          <h1 className="text-headline-lg text-on-surface">Settings</h1>
          <p className="text-body-md text-on-surface-variant">
            Manage your workspace configuration, security roles, and user profile preferences.
          </p>
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        
        {/* Navigation Tabs (Left / 1 Column) */}
        <div className="md:col-span-1 space-y-1">
          {[
            { id: 'profile', label: 'Profile', icon: User },
            { id: 'workspace', label: 'Workspace', icon: Building2 },
            { id: 'security', label: 'Security & SSO', icon: Shield },
            { id: 'billing', label: 'Billing', icon: CreditCard },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded text-left text-body-sm font-semibold transition-colors ${
                  isActive
                    ? 'bg-surface-container text-on-surface'
                    : 'text-on-surface-variant hover:bg-surface-low hover:text-on-surface'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Content Pane (Right / 3 Columns) */}
        <div className="md:col-span-3 space-y-5">
          {activeTab === 'profile' && (
            <form onSubmit={handleSaveProfile} className="bg-surface border border-outline-variant rounded-lg p-5 space-y-4">
              <h3 className="text-headline-sm text-on-surface font-semibold pb-2 border-b border-outline-variant/60">
                Profile Management
              </h3>

              {successMsg && (
                <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded flex items-center gap-2 font-medium">
                  <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
                  <span>{successMsg}</span>
                </div>
              )}

              {errorMsg && (
                <div className="p-3 bg-red-50 border border-red-200 text-red-800 text-xs rounded flex items-center gap-2 font-medium">
                  <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
                  <span>{errorMsg}</span>
                </div>
              )}

              {/* Inputs grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider block">Full Name</label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Enter your full name"
                    required
                    className="w-full bg-surface-low border border-outline-variant rounded px-3 py-2 text-body-sm text-on-surface focus:outline-none focus:border-outline"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider block">Email Address</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@company.com"
                    required
                    className="w-full bg-surface-low border border-outline-variant rounded px-3 py-2 text-body-sm text-on-surface focus:outline-none focus:border-outline"
                  />
                </div>
              </div>

              {/* Role & Scope Dropdown + Custom Role Input */}
              <div className="space-y-2">
                <label className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider block">Role & Scope</label>
                <select
                  value={selectedRole}
                  onChange={(e) => setSelectedRole(e.target.value)}
                  className="w-full bg-surface-low border border-outline-variant rounded px-3 py-2 text-body-sm text-on-surface focus:outline-none focus:border-outline"
                >
                  {PRESET_ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>

                {selectedRole === 'Other (Custom)' && (
                  <input
                    type="text"
                    value={customRole}
                    onChange={(e) => setCustomRole(e.target.value)}
                    placeholder="Specify your custom role (e.g., Cloud Architect / SecOps)"
                    required
                    className="w-full bg-surface-low border border-outline-variant rounded px-3 py-2 text-body-sm text-on-surface focus:outline-none focus:border-outline transition-all"
                  />
                )}
              </div>

              <div className="pt-2 flex justify-end">
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 bg-primary hover:bg-slate-800 text-white text-body-sm font-semibold rounded transition-colors flex items-center gap-2 disabled:opacity-50"
                >
                  {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                  <span>{saving ? 'Saving Profile...' : 'Save Profile Configuration'}</span>
                </button>
              </div>
            </form>
          )}

          {activeTab !== 'profile' && (
            <div className="bg-surface border border-outline-variant rounded-lg p-6 text-center text-on-surface-variant text-body-sm font-mono">
              {activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} settings managed by organization administrator.
            </div>
          )}
        </div>

      </div>

    </div>
  );
};
