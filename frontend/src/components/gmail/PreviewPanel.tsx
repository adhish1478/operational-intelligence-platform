import React from 'react';
import { CheckCircle2, Eye, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';

interface CandidateConfig {
  allowed_senders: string[];
  required_keywords: string[];
  subject_contains: string[];
  subject_starts_with: string[];
}

interface PreviewPanelProps {
  candidateConfig: CandidateConfig;
}

export const PreviewPanel: React.FC<PreviewPanelProps> = ({ candidateConfig }) => {
  // Query backend filter preview evaluation endpoint
  const { data: previewData, isLoading, isFetching } = useQuery({
    queryKey: ['gmail-preview-filter', candidateConfig],
    queryFn: () => api.post('/integrations/gmail/preview-filter', candidateConfig),
    staleTime: 300
  });

  const matchedCount = previewData?.matched_count ?? 0;
  const ignoredCount = previewData?.ignored_count ?? 0;
  const matchedSamples: string[] = previewData?.matched_samples || [];
  const ignoredSamples: string[] = previewData?.ignored_samples || [];

  return (
    <div className="bg-surface-low border border-outline-variant/80 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Eye className="w-4 h-4 text-primary" />
          <h4 className="text-[12px] font-bold text-on-surface uppercase tracking-wider">
            Live Preview Panel
          </h4>
          {isFetching && <Loader2 className="w-3 h-3 animate-spin text-primary ml-1" />}
        </div>

        {/* Counts Badges */}
        <div className="flex items-center gap-2 font-mono text-[11px]">
          <span className="px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-400 font-bold">
            Matched: {matchedCount}
          </span>
          <span className="px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-on-surface-variant font-bold">
            Ignored: {ignoredCount}
          </span>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 justify-center py-4 text-[11px] text-outline font-mono">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
          <span>Evaluating sample evidence against rules...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
          {/* Matched Samples */}
          <div className="space-y-1.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 block">
              Matched Samples ({matchedSamples.length})
            </span>
            {matchedSamples.length === 0 ? (
              <p className="text-[11px] text-outline italic">No sample emails matched current rules.</p>
            ) : (
              <ul className="space-y-1">
                {matchedSamples.map((sample, idx) => (
                  <li key={idx} className="flex items-center gap-1.5 text-[11px] text-on-surface truncate">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                    <span className="truncate">{sample}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Ignored Samples */}
          <div className="space-y-1.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-outline block">
              Ignored Samples ({ignoredSamples.length})
            </span>
            {ignoredSamples.length === 0 ? (
              <p className="text-[11px] text-outline italic">No sample emails ignored.</p>
            ) : (
              <ul className="space-y-1">
                {ignoredSamples.map((sample, idx) => (
                  <li key={idx} className="flex items-center gap-1.5 text-[11px] text-on-surface-variant truncate opacity-75">
                    <span className="w-1.5 h-1.5 rounded-full bg-outline-variant shrink-0 ml-1" />
                    <span className="truncate">{sample}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
