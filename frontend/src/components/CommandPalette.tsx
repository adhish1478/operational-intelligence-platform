import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, ShieldAlert, Users, FolderKanban, Terminal, SquareChevronRight } from 'lucide-react';
import { useUIStore } from '../store/uiStore';

interface SearchItem {
  id: string;
  title: string;
  category: 'investigations' | 'entities' | 'actions';
  subtitle?: string;
  route: string;
  icon: React.ComponentType<{ className?: string }>;
}

const initialItems: SearchItem[] = [
  {
    id: '1',
    title: 'TechCorp Escalation: Customer Churn Risk',
    category: 'investigations',
    subtitle: 'Critical - Slack Alert',
    route: '/investigations/1e084d237ac94e8ab3b6b900ea4afa8f',
    icon: ShieldAlert,
  },
  {
    id: '2',
    title: 'Authentication Microservice Outage',
    category: 'investigations',
    subtitle: 'High - GitHub Alert',
    route: '/investigations/launch_delay',
    icon: ShieldAlert,
  },
  {
    id: '3',
    title: 'TechCorp Customer Account Profile',
    category: 'entities',
    subtitle: 'Customer Entity',
    route: '/entities/customer/techcorp',
    icon: Users,
  },
  {
    id: '4',
    title: 'Core Platform Engineering Team',
    category: 'entities',
    subtitle: 'Team Entity',
    route: '/entities/team/core-platform',
    icon: Users,
  },
  {
    id: '5',
    title: 'Authentication Gateway Service',
    category: 'entities',
    subtitle: 'Service Entity',
    route: '/entities/service/auth-gateway',
    icon: FolderKanban,
  },
  {
    id: '6',
    title: 'Go to Investigations Queue',
    category: 'actions',
    subtitle: 'Navigation',
    route: '/investigations',
    icon: SquareChevronRight,
  },
  {
    id: '7',
    title: 'Go to Integrations Setup',
    category: 'actions',
    subtitle: 'Navigation',
    route: '/integrations',
    icon: SquareChevronRight,
  },
];

export const CommandPalette: React.FC = () => {
  const isOpen = useUIStore((state) => state.isCommandPaletteOpen);
  const close = useUIStore((state) => state.closeCommandPalette);
  const toggle = useUIStore((state) => state.toggleCommandPalette);
  
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  // Global hotkeys (CMD+K or CTRL+K to toggle, ESC to close)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        toggle();
      } else if (e.key === 'Escape' && isOpen) {
        e.preventDefault();
        close();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, toggle, close]);

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
      const timer = setTimeout(() => {
        setQuery('');
        setSelectedIndex(0);
        inputRef.current?.focus();
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  // Handle clicking outside to close
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(e.target as Node)) {
        close();
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, close]);

  if (!isOpen) return null;

  // Filter items
  const filteredItems = initialItems.filter(item =>
    item.title.toLowerCase().includes(query.toLowerCase()) ||
    item.category.toLowerCase().includes(query.toLowerCase()) ||
    (item.subtitle && item.subtitle.toLowerCase().includes(query.toLowerCase()))
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % filteredItems.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filteredItems.length) % filteredItems.length);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredItems[selectedIndex]) {
        navigate(filteredItems[selectedIndex].route);
        close();
      }
    }
  };

  const cn = (...inputs: string[]) => inputs.filter(Boolean).join(' ');

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/20 backdrop-blur-xs flex items-start justify-center pt-[15vh]">
      <div 
        ref={modalRef}
        className="w-full max-w-xl bg-surface border border-outline-variant rounded-lg shadow-xl overflow-hidden flex flex-col max-h-[60vh]"
        onKeyDown={handleKeyDown}
      >
        {/* Search Input */}
        <div className="flex items-center gap-2.5 px-4 py-3 border-b border-outline-variant bg-surface-low">
          <Search className="w-5 h-5 text-outline shrink-0" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Type a command, search investigations, or find entities..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            className="flex-1 bg-transparent border-0 outline-none text-body-md text-on-surface placeholder-outline focus:ring-0"
          />
          <kbd className="text-[10px] bg-surface-container border border-outline-variant px-1.5 py-0.5 rounded text-on-surface-variant font-mono">ESC</kbd>
        </div>

        {/* Results List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {filteredItems.length === 0 ? (
            <div className="py-8 text-center text-body-sm text-on-surface-variant italic">
              No results found for "{query}"
            </div>
          ) : (
            <>
              {/* Group items by category */}
              {['investigations', 'entities', 'actions'].map((cat) => {
                const categoryItems = filteredItems.filter(i => i.category === cat);
                if (categoryItems.length === 0) return null;
                
                return (
                  <div key={cat} className="space-y-0.5">
                    <div className="px-3 py-1.5 text-[10px] font-bold text-outline uppercase tracking-wider">
                      {cat}
                    </div>
                    {categoryItems.map((item) => {
                      // Find actual index in filteredItems array
                      const itemIdx = filteredItems.findIndex(i => i.id === item.id);
                      const isSelected = itemIdx === selectedIndex;
                      const Icon = item.icon;

                      return (
                        <button
                          key={item.id}
                          onClick={() => {
                            navigate(item.route);
                            close();
                          }}
                          onMouseEnter={() => setSelectedIndex(itemIdx)}
                          className={cn(
                            "w-full flex items-center gap-3 px-3 py-2 rounded text-left transition-colors",
                            isSelected 
                              ? "bg-surface-container text-on-surface" 
                              : "text-on-surface-variant hover:bg-surface-low hover:text-on-surface"
                          )}
                        >
                          <Icon className={cn("w-4.5 h-4.5 shrink-0", isSelected ? "text-primary" : "text-outline")} />
                          <div className="flex-1 min-w-0">
                            <div className="text-body-sm font-medium truncate">{item.title}</div>
                            {item.subtitle && (
                              <div className="text-[10px] text-on-surface-variant truncate">{item.subtitle}</div>
                            )}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                );
              })}
            </>
          )}
        </div>

        {/* Instructions Footer */}
        <div className="px-4 py-2 border-t border-outline-variant bg-surface-low flex items-center gap-4 text-[10px] text-on-surface-variant font-medium">
          <span className="flex items-center gap-1"><Terminal className="w-3.5 h-3.5" /> Navigation hotkeys:</span>
          <span><kbd className="bg-surface border border-outline-variant px-1 rounded font-mono">↑↓</kbd> Select</span>
          <span><kbd className="bg-surface border border-outline-variant px-1 rounded font-mono">Enter</kbd> Open</span>
        </div>
      </div>
    </div>
  );
};
