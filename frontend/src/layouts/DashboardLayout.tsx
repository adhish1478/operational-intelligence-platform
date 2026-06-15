import React from 'react';
import { Sidebar } from './Sidebar.tsx';
import { Header } from './Header.tsx';
import { CommandPalette } from '../components/CommandPalette.tsx';

interface LayoutProps {
    children: React.ReactNode;
}

export const DashboardLayout: React.FC<LayoutProps> = ({ children }) => {
    return (
        <div className="flex min-h-screen bg-background">
            <Sidebar />
            <div className="flex-1 flex flex-col min-w-0">
                <Header />
                <main className="flex-1 overflow-y-auto px-6 py-6">
                    {children}
                </main>
            </div>
            {/* Mounted globally for keyboard shortcuts */}
            <CommandPalette />
        </div>
    );
};
