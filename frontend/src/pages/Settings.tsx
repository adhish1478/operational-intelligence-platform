import React from 'react';
import { Shield, CreditCard, Building2, User } from 'lucide-react';

export const Settings: React.FC = () => {
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
            { label: 'Profile', icon: User, active: true },
            { label: 'Workspace', icon: Building2, active: false },
            { label: 'Security & SSO', icon: Shield, active: false },
            { label: 'Billing', icon: CreditCard, active: false },
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.label}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded text-left text-body-sm font-semibold transition-colors ${
                  tab.active
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
          <div className="bg-surface border border-outline-variant rounded-lg p-5 space-y-4">
            <h3 className="text-headline-sm text-on-surface font-semibold pb-2 border-b border-outline-variant/60">
              Profile Management
            </h3>

            {/* Inputs grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider block">Full Name</label>
                <input
                  type="text"
                  defaultValue="Adhish Aravind"
                  className="w-full bg-surface-low border border-outline-variant rounded px-3 py-2 text-body-sm text-on-surface focus:outline-none focus:border-outline"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider block">Email Address</label>
                <input
                  type="email"
                  defaultValue="adhish@oip.com"
                  disabled
                  className="w-full bg-surface-low border border-outline-variant rounded px-3 py-2 text-body-sm text-on-surface-variant font-medium cursor-not-allowed"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider block">Role Scope</label>
              <input
                type="text"
                defaultValue="Lead SecOps / Admin"
                disabled
                className="w-full bg-surface-low border border-outline-variant rounded px-3 py-2 text-body-sm text-on-surface-variant font-medium cursor-not-allowed"
              />
            </div>

            <div className="pt-2 flex justify-end">
              <button className="px-4 py-2 bg-primary hover:bg-slate-800 text-white text-body-sm font-semibold rounded transition-colors">
                Save Profile Configuration
              </button>
            </div>
          </div>
        </div>

      </div>

    </div>
  );
};
