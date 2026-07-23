import React, { useState } from 'react';
import { Plus, X, KeyRound, Layers } from 'lucide-react';

interface KeywordEditorProps {
  requiredKeywords: string[];
  onChange: (keywords: string[]) => void;
}

interface StarterTemplate {
  name: string;
  keywords: string[];
}

const STARTER_TEMPLATES: StarterTemplate[] = [
  { name: 'DevOps Alerts', keywords: ['alert', 'outage', 'error', 'spikes', 'failure'] },
  { name: 'Infrastructure', keywords: ['database', 'cluster', 'memory', 'latency', 'exhaustion'] },
  { name: 'Security', keywords: ['vulnerability', 'breach', 'unauthorized', 'leak', 'firewall'] },
  { name: 'CI/CD', keywords: ['build', 'pipeline', 'deploy', 'commit', 'test'] }
];

export const KeywordEditor: React.FC<KeywordEditorProps> = ({ requiredKeywords, onChange }) => {
  const [inputVal, setInputVal] = useState('');

  const handleAddKeyword = (wordToAdd: string) => {
    const trimmed = wordToAdd.trim().toLowerCase();
    if (!trimmed) return;
    if (!requiredKeywords.some(k => k.toLowerCase() === trimmed)) {
      onChange([...requiredKeywords, trimmed]);
    }
    setInputVal('');
  };

  const handleRemoveKeyword = (indexToRemove: number) => {
    onChange(requiredKeywords.filter((_, idx) => idx !== indexToRemove));
  };

  const handleApplyTemplate = (templateKeywords: string[]) => {
    const merged = new Set([...requiredKeywords, ...templateKeywords]);
    onChange(Array.from(merged));
  };

  return (
    <div className="space-y-3">
      <div>
        <h4 className="text-[13px] font-bold text-on-surface flex items-center gap-1.5">
          <KeyRound className="w-4 h-4 text-primary" />
          <span>Section 2 — Keyword Rules</span>
        </h4>
        <p className="text-[11px] text-on-surface-variant leading-relaxed mt-0.5">
          Define keywords indicating operational relevance. Messages containing any of these keywords will be classified as signals.
        </p>
      </div>

      {/* Starter Templates */}
      <div className="bg-surface-low border border-outline-variant/60 p-2.5 rounded-lg space-y-1.5">
        <span className="text-[10px] uppercase font-bold text-outline tracking-wider flex items-center gap-1">
          <Layers className="w-3 h-3 text-primary" />
          <span>Starter Templates (Click to populate)</span>
        </span>
        <div className="flex flex-wrap items-center gap-1.5">
          {STARTER_TEMPLATES.map((tmpl) => (
            <button
              key={tmpl.name}
              type="button"
              onClick={() => handleApplyTemplate(tmpl.keywords)}
              className="px-2.5 py-1 rounded bg-surface border border-outline-variant hover:border-primary text-[11px] font-semibold text-on-surface hover:text-primary transition-colors flex items-center gap-1"
            >
              <span>+ {tmpl.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Selected Keywords Chips */}
      <div className="flex flex-wrap items-center gap-1.5 min-h-[36px] p-2 bg-surface-low border border-outline-variant/80 rounded-lg">
        {requiredKeywords.length === 0 ? (
          <span className="text-[11px] text-outline italic px-1">No keywords defined. Select a template above or type a keyword below.</span>
        ) : (
          requiredKeywords.map((kw, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-400"
            >
              <span>{kw}</span>
              <button
                type="button"
                onClick={() => handleRemoveKeyword(idx)}
                className="hover:text-error transition-colors ml-0.5"
                title="Remove keyword"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))
        )}
      </div>

      {/* Manual Input */}
      <div className="flex items-center gap-2">
        <input
          type="text"
          placeholder="Add custom keyword (e.g. critical, incident, error)"
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              handleAddKeyword(inputVal);
            }
          }}
          className="flex-1 text-[11px] font-mono rounded border border-outline-variant bg-surface p-2 text-on-surface focus:outline-none focus:ring-1 focus:ring-primary placeholder:text-outline-variant"
        />
        <button
          type="button"
          onClick={() => handleAddKeyword(inputVal)}
          disabled={!inputVal.trim()}
          className="px-3 py-2 bg-primary hover:bg-slate-800 text-white rounded text-[11px] font-bold transition-colors disabled:opacity-50 flex items-center gap-1 shrink-0"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Add</span>
        </button>
      </div>
    </div>
  );
};
