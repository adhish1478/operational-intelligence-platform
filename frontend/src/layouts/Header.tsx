import React from 'react';
import { Bell, Search, Plus, ChevronRight } from 'lucide-react';
import { useLocation, Link } from 'react-router-dom';
import { useUIStore } from '../store/uiStore';
import { useAuthStore } from '../store/authStore';

export const Header: React.FC = () => {
    const location = useLocation();
    const openCommandPalette = useUIStore((state) => state.openCommandPalette);
    const { user, activeOrgId } = useAuthStore();

    // Find active organization details
    const activeOrg = user?.organizations?.find(o => o.id === activeOrgId);
    const orgName = activeOrg ? activeOrg.name : 'Global Ops';

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
                <Link to="/dashboard" className="text-on-surface-variant hover:text-on-surface transition-colors">
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
            <div className="flex items-center gap-4">
                <button className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-primary hover:bg-slate-800 text-white text-body-sm font-semibold transition-colors">
                    <Plus className="w-4 h-4" />
                    <span>New Investigation</span>
                </button>

                <div className="w-px h-5 bg-outline-variant" />

                <button className="relative p-1.5 rounded hover:bg-surface-low text-on-surface-variant hover:text-on-surface transition-colors">
                    <Bell className="w-4.5 h-4.5" />
                    <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-error rounded-full" />
                </button>
            </div>
        </header>
    );
};
