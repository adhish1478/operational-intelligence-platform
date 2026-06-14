import React from 'react';
import type { Severity, SourceSystem } from '../../types';
import {
    Clock,
    MessageSquare,
    ExternalLink,
    GitBranch,
    Mail,
    MessageCircle,
    Briefcase
} from 'lucide-react';
import { clsx } from 'clsx';

interface IssueCardProps {
    id: string;
    title: string;
    description: string;
    severity: Severity;
    sources: SourceSystem[];
    detectedAt: string;
    suggestedAction: string;
}

const severityConfig = {
    low: { color: 'text-slate-400', bg: 'bg-slate-400/10', border: 'border-slate-400/20' },
    medium: { color: 'text-warning', bg: 'bg-warning/10', border: 'border-warning/20' },
    high: { color: 'text-critical', bg: 'bg-critical/10', border: 'border-critical/20' },
    critical: { color: 'text-critical', bg: 'bg-critical/20', border: 'border-critical/40', glow: 'glow-critical' },
};

const sourceIcons = {
    slack: MessageCircle,
    jira: Briefcase,
    gmail: Mail,
    github: GitBranch,
};

export const IssueCard: React.FC<IssueCardProps> = ({
    title,
    description,
    severity,
    sources,
    detectedAt,
    suggestedAction
}) => {
    const config = severityConfig[severity];

    return (
        <div className="glass p-5 rounded-2xl border-white/5 space-y-4 group transition-all duration-300 hover:scale-[1.01] hover:border-white/10 glass-hover">
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                    <div className={clsx("w-2 h-2 rounded-full", config.color, severity === 'critical' && 'animate-pulse bg-current')} />
                    <span className={clsx("text-[10px] font-bold uppercase tracking-widest", config.color)}>
                        {severity}
                    </span>
                </div>
                <div className="flex items-center gap-1.5">
                    {sources.map(Source => {
                        const Icon = sourceIcons[Source];
                        return <Icon key={Source} className="w-3.5 h-3.5 text-slate-500" />;
                    })}
                </div>
            </div>

            <div className="space-y-1">
                <h4 className="text-white font-semibold group-hover:text-primary transition-colors cursor-pointer flex items-center gap-2">
                    {title}
                    <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                </h4>
                <p className="text-sm text-slate-400 line-clamp-2 leading-relaxed">
                    {description}
                </p>
            </div>

            <div className="pt-2 flex items-center justify-between border-t border-white/5">
                <div className="flex items-center gap-3 text-xs text-slate-500">
                    <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        <span>{detectedAt}</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <MessageSquare className="w-3 h-3" />
                        <span>4 comments</span>
                    </div>
                </div>

                <div className="flex -space-x-2">
                    {[1, 2].map(i => (
                        <div key={i} className="w-6 h-6 rounded-full border-2 border-[#020617] bg-slate-800 flex items-center justify-center text-[8px] font-bold">
                            {i === 1 ? 'JD' : 'ML'}
                        </div>
                    ))}
                </div>
            </div>

            <div className="mt-2 p-3 bg-white/5 rounded-xl border border-white/5 group-hover:border-primary/20 transition-colors">
                <div className="text-[10px] text-slate-500 uppercase font-bold tracking-wider mb-1">Suggested Action</div>
                <div className="text-xs text-slate-300 font-medium">{suggestedAction}</div>
            </div>
        </div>
    );
};
