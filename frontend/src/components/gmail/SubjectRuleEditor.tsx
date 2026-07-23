import React, { useState } from 'react';
import { Plus, X, Type } from 'lucide-react';

interface SubjectRuleEditorProps {
  subjectContains: string[];
  subjectStartsWith: string[];
  onChangeContains: (items: string[]) => void;
  onChangeStartsWith: (items: string[]) => void;
}

export const SubjectRuleEditor: React.FC<SubjectRuleEditorProps> = ({
  subjectContains,
  subjectStartsWith,
  onChangeContains,
  onChangeStartsWith
}) => {
  const [containsVal, setContainsVal] = useState('');
  const [startsWithVal, setStartsWithVal] = useState('');

  const handleAddContains = (val: string) => {
    const trimmed = val.trim();
    if (!trimmed) return;
    if (!subjectContains.some(c => c.toLowerCase() === trimmed.toLowerCase())) {
      onChangeContains([...subjectContains, trimmed]);
    }
    setContainsVal('');
  };

  const handleAddStartsWith = (val: string) => {
    const trimmed = val.trim();
    if (!trimmed) return;
    if (!subjectStartsWith.some(s => s.toLowerCase() === trimmed.toLowerCase())) {
      onChangeStartsWith([...subjectStartsWith, trimmed]);
    }
    setStartsWithVal('');
  };

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-[13px] font-bold text-on-surface flex items-center gap-1.5">
          <Type className="w-4 h-4 text-primary" />
          <span>Section 3 — Subject Rules</span>
        </h4>
        <p className="text-[11px] text-on-surface-variant leading-relaxed mt-0.5">
          Optional subject matching rules. Emails matching these subject criteria will pass classification.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Subject Contains */}
        <div className="space-y-2">
          <label className="text-[11px] font-bold text-on-surface uppercase tracking-wider block">
            Subject Contains
          </label>
          <div className="flex flex-wrap items-center gap-1.5 min-h-[36px] p-2 bg-surface-low border border-outline-variant/80 rounded-lg">
            {subjectContains.length === 0 ? (
              <span className="text-[10px] text-outline italic">e.g. deployment, latency, critical</span>
            ) : (
              subjectContains.map((item, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono bg-blue-500/10 border border-blue-500/30 text-blue-700 dark:text-blue-400"
                >
                  <span>{item}</span>
                  <button
                    type="button"
                    onClick={() => onChangeContains(subjectContains.filter((_, i) => i !== idx))}
                    className="hover:text-error transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))
            )}
          </div>

          <div className="flex items-center gap-1.5">
            <input
              type="text"
              placeholder="e.g. latency"
              value={containsVal}
              onChange={(e) => setContainsVal(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddContains(containsVal);
                }
              }}
              className="flex-1 text-[11px] font-mono rounded border border-outline-variant bg-surface p-1.5 text-on-surface focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <button
              type="button"
              onClick={() => handleAddContains(containsVal)}
              disabled={!containsVal.trim()}
              className="px-2.5 py-1.5 bg-primary text-white rounded text-[10px] font-bold disabled:opacity-50"
            >
              <Plus className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Subject Starts With */}
        <div className="space-y-2">
          <label className="text-[11px] font-bold text-on-surface uppercase tracking-wider block">
            Subject Starts With
          </label>
          <div className="flex flex-wrap items-center gap-1.5 min-h-[36px] p-2 bg-surface-low border border-outline-variant/80 rounded-lg">
            {subjectStartsWith.length === 0 ? (
              <span className="text-[10px] text-outline italic">e.g. [ALERT], [SEV1], [P1]</span>
            ) : (
              subjectStartsWith.map((item, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono bg-purple-500/10 border border-purple-500/30 text-purple-700 dark:text-purple-400"
                >
                  <span>{item}</span>
                  <button
                    type="button"
                    onClick={() => onChangeStartsWith(subjectStartsWith.filter((_, i) => i !== idx))}
                    className="hover:text-error transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))
            )}
          </div>

          <div className="flex items-center gap-1.5">
            <input
              type="text"
              placeholder="e.g. [ALERT]"
              value={startsWithVal}
              onChange={(e) => setStartsWithVal(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddStartsWith(startsWithVal);
                }
              }}
              className="flex-1 text-[11px] font-mono rounded border border-outline-variant bg-surface p-1.5 text-on-surface focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <button
              type="button"
              onClick={() => handleAddStartsWith(startsWithVal)}
              disabled={!startsWithVal.trim()}
              className="px-2.5 py-1.5 bg-primary text-white rounded text-[10px] font-bold disabled:opacity-50"
            >
              <Plus className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
