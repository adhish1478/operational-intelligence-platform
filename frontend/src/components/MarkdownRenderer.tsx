import React from 'react';
import ReactMarkdown from 'react-markdown';
import { ExternalLink } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className = '' }) => {
  if (!content) return null;

  return (
    <div className={`markdown-body ${className}`}>
      <ReactMarkdown
        components={{
          h1: ({ children }) => (
            <h1 className="text-lg font-bold text-slate-900 border-b border-slate-200 pb-1.5 mt-4 mb-2 flex items-center gap-2">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-base font-bold text-slate-900 mt-4 mb-2 flex items-center gap-2">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-sm font-bold text-indigo-950 uppercase tracking-wider mt-4 mb-1.5 flex items-center gap-2 border-l-2 border-indigo-500 pl-2 bg-indigo-50/40 py-1 rounded-r">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mt-3 mb-1">
              {children}
            </h4>
          ),
          p: ({ children }) => (
            <p className="text-sm text-slate-700 leading-relaxed mb-3 font-sans">
              {children}
            </p>
          ),
          ul: ({ children }) => (
            <ul className="list-disc list-inside space-y-1.5 mb-3 text-sm text-slate-700 pl-1">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside space-y-1.5 mb-3 text-sm text-slate-700 pl-1">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="text-sm text-slate-700 leading-normal inline-block w-full">
              <span className="inline">{children}</span>
            </li>
          ),
          code: ({ children, className: codeClassName, ...props }) => {
            return (
              <code
                className="font-mono text-xs text-indigo-900 bg-indigo-50/80 px-1.5 py-0.5 rounded border border-indigo-100 font-semibold"
                {...props}
              >
                {children}
              </code>
            );
          },
          pre: ({ children }) => (
            <pre className="bg-slate-900 text-slate-100 p-3.5 rounded-lg overflow-x-auto font-mono text-xs leading-relaxed my-3 border border-slate-800 shadow-inner">
              {children}
            </pre>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-indigo-500 bg-indigo-50/50 p-3 my-3 rounded-r text-sm text-indigo-950 italic">
              {children}
            </blockquote>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-slate-900">{children}</strong>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              className="text-indigo-600 hover:text-indigo-800 underline font-medium inline-flex items-center gap-0.5"
            >
              <span>{children}</span>
              <ExternalLink className="w-3 h-3 inline shrink-0" />
            </a>
          ),
          hr: () => <hr className="my-4 border-slate-200" />
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
