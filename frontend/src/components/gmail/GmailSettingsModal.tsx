import React, { useState, useEffect } from 'react';
import { X, Settings2, Check } from 'lucide-react';
import { SenderSelector } from './SenderSelector';
import { KeywordEditor } from './KeywordEditor';
import { SubjectRuleEditor } from './SubjectRuleEditor';
import { PreviewPanel } from './PreviewPanel';
import { api } from '../../lib/api';

interface GmailSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  integrationId: string;
  existingConfig: any;
  onSaveSuccess: () => void;
}

export const GmailSettingsModal: React.FC<GmailSettingsModalProps> = ({
  isOpen,
  onClose,
  integrationId,
  existingConfig,
  onSaveSuccess
}) => {
  const [allowedSenders, setAllowedSenders] = useState<string[]>([]);
  const [requiredKeywords, setRequiredKeywords] = useState<string[]>([]);
  const [subjectContains, setSubjectContains] = useState<string[]>([]);
  const [subjectStartsWith, setSubjectStartsWith] = useState<string[]>([]);
  
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset draft state with existing integration configuration whenever modal opens or existingConfig updates
  useEffect(() => {
    if (isOpen && existingConfig) {
      setAllowedSenders(existingConfig.allowed_senders || []);
      setRequiredKeywords(existingConfig.required_keywords || []);
      setSubjectContains(existingConfig.subject_contains || []);
      setSubjectStartsWith(existingConfig.subject_starts_with || []);
    }
  }, [isOpen, existingConfig]);

  if (!isOpen) return null;

  const candidateConfig = {
    allowed_senders: allowedSenders,
    required_keywords: requiredKeywords,
    subject_contains: subjectContains,
    subject_starts_with: subjectStartsWith
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const updatedConfig = {
        ...(existingConfig || {}),
        ...candidateConfig
      };

      await api.patch(`/integrations/${integrationId}`, {
        config: updatedConfig
      });

      onSaveSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to save Gmail signal configuration.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
      <div className="bg-surface border border-outline-variant rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-outline-variant bg-surface-low flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-primary/10 text-primary">
              <Settings2 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-headline-sm font-bold text-on-surface">Gmail Signal Filtering Configuration</h3>
              <p className="text-[11px] text-on-surface-variant">Configure rules to classify incoming emails as operational signals vs noise.</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-outline hover:text-on-surface hover:bg-surface-high transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && (
            <div className="p-3 rounded bg-error-container/40 border border-error/20 text-error text-[12px] font-mono">
              {error}
            </div>
          )}

          {/* Section 1: Allowed Senders */}
          <SenderSelector
            allowedSenders={allowedSenders}
            onChange={setAllowedSenders}
          />

          <hr className="border-outline-variant/60" />

          {/* Section 2: Keyword Rules */}
          <KeywordEditor
            requiredKeywords={requiredKeywords}
            onChange={setRequiredKeywords}
          />

          <hr className="border-outline-variant/60" />

          {/* Section 3: Subject Rules */}
          <SubjectRuleEditor
            subjectContains={subjectContains}
            subjectStartsWith={subjectStartsWith}
            onChangeContains={setSubjectContains}
            onChangeStartsWith={setSubjectStartsWith}
          />

          <hr className="border-outline-variant/60" />

          {/* Live Preview Panel */}
          <PreviewPanel candidateConfig={candidateConfig} />
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-outline-variant bg-surface-low flex items-center justify-between shrink-0">
          <span className="text-[11px] text-outline font-mono">
            {allowedSenders.length + requiredKeywords.length + subjectContains.length + subjectStartsWith.length} rules active
          </span>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 rounded text-body-sm font-semibold text-on-surface-variant hover:bg-surface-high transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-1.5 bg-primary hover:bg-slate-800 text-white rounded text-body-sm font-bold transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              {saving ? (
                <span>Saving...</span>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  <span>Save Configuration</span>
                </>
              )}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
