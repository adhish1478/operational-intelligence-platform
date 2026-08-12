import React, { useState } from 'react';
import { Bell, Search, ChevronRight } from 'lucide-react';
import { useLocation, Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useUIStore } from '../store/uiStore';
import { useAuthStore } from '../store/authStore';
import { api } from '../lib/api';
import { mapInvestigation } from '../lib/mappers';
import type { OperationalInvestigation } from '../types';

export const Header: React.FC = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const openCommandPalette = useUIStore((state) => state.openCommandPalette);
    const { user, activeOrgId } = useAuthStore();
    const [showNotifications, setShowNotifications] = useState(false);
    const [hasUnread, setHasUnread] = useState(true);

    // Find active organization details
    const activeOrg = user?.organizations?.find(o => o.id === activeOrgId) || user?.organizations?.[0];
    const orgName = activeOrg ? activeOrg.name : (user?.first_name ? `${user.first_name}'s Organization` : 'My Organization');

    // Fetch active investigations for real-time notifications
    const { data: rawInvs } = useQuery({
        queryKey: ['header-notifications'],
        queryFn: () => api.get('/investigations/'),
        refetchInterval: 10000
    });

    const investigations: OperationalInvestigation[] = (rawInvs || []).map(mapInvestigation);

    // Dynamic Notifications list generated from tenant investigations
    const notifications = investigations.slice(0, 5).map(inv => ({
        id: inv.id,
        title: `New ${inv.severity.toUpperCase()} Investigation`,
        subtitle: inv.title,
        time: inv.detectedAt ? new Date(inv.detectedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Just now',
        severity: inv.severity,
        invId: inv.id
    }));

    const handleBellClick = () => {
        setShowNotifications(!showNotifications);
        setHasUnread(false);
    };

    // Generate dynamic breadcrumbs from path
    const pathnames = location.pathname.split('/').filter((x) => x);
    const breadcrumbItems = pathnames.map((value, index) => {
        const to = `/${pathnames.slice(0, index + 1).join('/')}`;
        const isLast = index === pathnames.length - 1;
        const formattedName = value.charAt(0).toUpperCase() + value.slice(1).replace(/-/g, ' ');

        return {
            name: formattedName,
            to,
            isLast
        };
    });

    return (
        <header className="h-14 bg-surface border-b border-outline-variant px-6 flex items-center justify-between sticky top-0 z-40">
            {/* Contextual Breadcrumbs */}
            <div className="flex items-center gap-1.5 text-body-sm">
                <Link to="/dashboard" className="text-on-surface-variant hover:text-on-surface transition-colors font-semibold">
                    {orgName}
                </Link>
                {breadcrumbItems.length > 0 && <ChevronRight className="w-3.5 h-3.5 text-outline" />}
                {breadcrumbItems.map((item, index) => (
                    <React.Fragment key={item.to}>
                        {index > 0 && <ChevronRight className="w-3.5 h-3.5 text-outline" />}
                        {item.isLast ? (
                            <span className="font-semibold text-on-surface truncate max-w-[200px]">
                                {item.name === 'Dashboard' ? 'Attention Deck' : item.name}
                            </span>
                        ) : (
                            <Link to={item.to} className="text-on-surface-variant hover:text-on-surface transition-colors truncate max-w-[150px]">
                                {item.name === 'Dashboard' ? 'Attention Deck' : item.name}
                            </Link>
                        )}
                    </React.Fragment>
                ))}
            </div>

            {/* Middle Search Indicator */}
            <div className="flex-1 max-w-md mx-8">
                <button
                    onClick={openCommandPalette}
                    className="w-full flex items-center gap-2 px-3 py-1.5 rounded bg-surface-low border border-outline-variant text-on-surface-variant hover:bg-surface-high hover:text-on-surface transition-all text-left text-body-sm group"
                >
                    <Search className="w-4 h-4 text-outline" />
                    <span>Search workspace...</span>
                    <kbd className="ml-auto text-[10px] bg-surface-container border border-outline-variant px-1.5 py-0.5 rounded text-on-surface-variant font-mono">⌘K</kbd>
                </button>
            </div>

            {/* Action Group */}
            <div className="flex items-center gap-4 relative">
                {/* Bell Icon & Dropdown Notification Popover */}
                <div className="relative">
                    <button 
                        onClick={handleBellClick}
                        className="relative p-2 rounded hover:bg-surface-low text-on-surface-variant hover:text-on-surface transition-colors"
                        title="Notifications"
                    >
                        <Bell className="w-4.5 h-4.5 text-slate-700" />
                        {hasUnread && notifications.length > 0 && (
                            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-error rounded-full ring-2 ring-white" />
                        )}
                    </button>

                    {/* Notifications Dropdown Panel */}
                    {showNotifications && (
                        <div className="absolute right-0 mt-2 w-80 bg-white border border-slate-200 rounded-xl shadow-xl z-50 overflow-hidden animate-fadeIn">
                            <div className="px-4 py-3 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
                                <h4 className="text-xs font-bold text-slate-900 font-mono uppercase tracking-wider">Live Incident Alerts</h4>
                                <span className="text-[10px] font-mono font-bold bg-slate-200 text-slate-800 px-2 py-0.5 rounded-full">
                                    {notifications.length} active
                                </span>
                            </div>

                            <div className="max-h-72 overflow-y-auto divide-y divide-slate-100">
                                {notifications.length === 0 ? (
                                    <div className="p-6 text-center text-xs text-slate-500 font-mono">
                                        No active notifications.
                                    </div>
                                ) : (
                                    notifications.map((n) => (
                                        <div
                                            key={n.id}
                                            onClick={() => {
                                                setShowNotifications(false);
                                                navigate(`/investigations/${n.invId}?autoDiagnose=true`);
                                            }}
                                            className="p-3.5 hover:bg-slate-50 transition-colors cursor-pointer space-y-1"
                                        >
                                            <div className="flex items-center justify-between">
                                                <span className={`text-[10px] font-mono font-bold uppercase px-1.5 py-0.5 rounded ${
                                                    n.severity === 'critical' ? 'bg-red-100 text-red-700' :
                                                    n.severity === 'high' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'
                                                }`}>
                                                    {n.title}
                                                </span>
                                                <span className="text-[10px] text-slate-400 font-mono">{n.time}</span>
                                            </div>
                                            <p className="text-xs font-semibold text-slate-800 line-clamp-1">
                                                {n.subtitle}
                                            </p>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </header>
    );
};
