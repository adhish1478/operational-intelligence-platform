import React, { useState } from 'react';
import { Plus, X, UserCheck, Sparkles } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';

interface SenderSelectorProps {
  allowedSenders: string[];
  onChange: (senders: string[]) => void;
}

export const SenderSelector: React.FC<SenderSelectorProps> = ({ allowedSenders, onChange }) => {
  const [inputVal, setInputVal] = useState('');

  // Fetch recently seen Gmail senders from MongoDB evidence via backend
  const { data: suggestionsData } = useQuery({
    queryKey: ['gmail-sender-suggestions'],
    queryFn: () => api.get('/integrations/gmail/senders-suggestions')
  });

  const suggestions: string[] = suggestionsData?.suggestions || [];

  const handleAddSender = (senderToAdd: string) => {
    const trimmed = senderToAdd.trim();
    if (!trimmed) return;
    if (!allowedSenders.some(s => s.toLowerCase() === trimmed.toLowerCase())) {
      onChange([...allowedSenders, trimmed]);
    }
    setInputVal('');
  };

  const handleRemoveSender = (indexToRemove: number) => {
    onChange(allowedSenders.filter((_, idx) => idx !== indexToRemove));
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-[13px] font-bold text-on-surface flex items-center gap-1.5">
            <UserCheck className="w-4 h-4 text-primary" />
            <span>Section 1 — Allowed Senders</span>
          </h4>
          <p className="text-[11px] text-on-surface-variant leading-relaxed mt-0.5">
            Choose which email senders or domain patterns are treated as operational sources.
          </p>
        </div>
      </div>

      {/* Selected Senders Chips */}
      <div className="flex flex-wrap items-center gap-1.5 min-h-[36px] p-2 bg-surface-low border border-outline-variant/80 rounded-lg">
        {allowedSenders.length === 0 ? (
          <span className="text-[11px] text-outline italic px-1">No allowed senders selected. All incoming emails will be filtered.</span>
        ) : (
          allowedSenders.map((sender, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-primary/10 border border-primary/20 text-primary"
            >
              <span>{sender}</span>
              <button
                type="button"
                onClick={() => handleRemoveSender(idx)}
                className="hover:text-error transition-colors ml-0.5"
                title="Remove sender"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))
        )}
      </div>

      {/* Manual Addition Field */}
      <div className="flex items-center gap-2">
        <input
          type="text"
          placeholder="Add sender or domain (e.g. alerts@datadog.com or company.com)"
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              handleAddSender(inputVal);
            }
          }}
          className="flex-1 text-[11px] font-mono rounded border border-outline-variant bg-surface p-2 text-on-surface focus:outline-none focus:ring-1 focus:ring-primary placeholder:text-outline-variant"
        />
        <button
          type="button"
          onClick={() => handleAddSender(inputVal)}
          disabled={!inputVal.trim()}
          className="px-3 py-2 bg-primary hover:bg-slate-800 text-white rounded text-[11px] font-bold transition-colors disabled:opacity-50 flex items-center gap-1 shrink-0"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Add</span>
        </button>
      </div>

      {/* Suggestions Section */}
      {suggestions.length > 0 && (
        <div className="pt-1">
          <span className="text-[10px] uppercase font-bold text-outline tracking-wider flex items-center gap-1 mb-1.5">
            <Sparkles className="w-3 h-3 text-amber-500" />
            <span>Suggestions (from recently seen emails)</span>
          </span>
          <div className="flex flex-wrap items-center gap-1.5">
            {suggestions
              .filter(s => !allowedSenders.some(existing => existing.toLowerCase() === s.toLowerCase()))
              .slice(0, 6)
              .map((sug, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleAddSender(sug)}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-surface border border-outline-variant hover:border-primary text-on-surface-variant hover:text-primary transition-colors group"
                >
                  <Plus className="w-3 h-3 text-primary group-hover:scale-110 transition-transform" />
                  <span className="truncate max-w-[180px]">{sug}</span>
                </button>
              ))}
          </div>
        </div>
      )}
    </div>
  );
};
