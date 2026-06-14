import { useState } from 'react';
import { ChevronDown, ChevronRight, FileCode, Link, Shield } from 'lucide-react';
import { SeverityBadge } from '@/components/shared/SeverityBadge';
import { CodeBlock } from '@/components/shared/CodeBlock';
import type { FindingItem } from '@/api/types';

interface Props {
  findings: FindingItem[];
  className?: string;
}

export function FindingsPanel({ findings, className }: Props) {
  const [filter, setFilter] = useState<string>('all');

  const filtered =
    filter === 'all' ? findings : findings.filter((f) => f.validation_status === filter);

  return (
    <div className={`glass-panel ${className ?? ''}`}>
      <div className="p-4 border-b border-slate-700/50 flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-300">
          Findings <span className="text-slate-500 font-normal">({filtered.length})</span>
        </h3>
        <div className="flex gap-1">
          {[
            ['all', 'All'],
            ['confirmed', 'Confirmed'],
            ['rejected', 'Rejected'],
            [null, 'Unvalidated'],
          ].map(([val, label]) => (
            <button
              key={label}
              className={`text-xs px-2 py-1 rounded-md transition-colors ${
                filter === (val ?? null)
                  ? 'bg-blue-500/20 text-blue-400'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
              onClick={() => setFilter(val as string)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="max-h-[600px] overflow-y-auto divide-y divide-slate-800/50">
        {filtered.length === 0 ? (
          <p className="p-4 text-sm text-slate-500 text-center">No findings yet</p>
        ) : (
          filtered.map((f) => <FindingCard key={f.finding_id} finding={f} />)
        )}
      </div>
    </div>
  );
}

function FindingCard({ finding: f }: { finding: FindingItem }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="hover:bg-slate-800/30 transition-colors">
      <div
        className="p-4 flex items-start gap-3 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <button className="mt-0.5 text-slate-500">
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </button>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <SeverityBadge severity={f.severity} />
            <span className="text-sm font-medium text-slate-200">{f.vuln_class}</span>
            {f.is_canonical && (
              <Shield className="h-3.5 w-3.5 text-yellow-500" />
            )}
          </div>
          <p className="text-xs text-slate-500 line-clamp-2">{f.description}</p>
          <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
            <span className="flex items-center gap-1">
              <FileCode className="h-3 w-3" />
              {f.file}:{f.line_start}-{f.line_end}
            </span>
            {f.confidence != null && (
              <span>confidence: {(f.confidence * 100).toFixed(0)}%</span>
            )}
            {f.validation_status && (
              <span className={`badge ${
                f.validation_status === 'confirmed'
                  ? 'bg-green-500/20 text-green-400'
                  : f.validation_status === 'rejected'
                  ? 'bg-red-500/20 text-red-400'
                  : 'bg-yellow-500/20 text-yellow-400'
              }`}>
                {f.validation_status}
              </span>
            )}
          </div>
        </div>
      </div>

      {expanded && (
        <div className="px-12 pb-4 space-y-3">
          <p className="text-sm text-slate-300">{f.description}</p>

          <div>
            <h4 className="text-xs font-medium text-slate-500 mb-1 uppercase tracking-wider">
              Evidence
            </h4>
            <CodeBlock code={f.evidence} maxLines={20} />
          </div>

          {f.trace && (
            <div>
              <h4 className="text-xs font-medium text-slate-500 mb-1 uppercase tracking-wider">
                Trace
              </h4>
              <div className="text-xs text-slate-400 space-y-1">
                {f.trace.reachable ? (
                  <>
                    <div className="flex items-center gap-1 text-green-400">
                      <Link className="h-3 w-3" />
                      Reachable (confidence: {((f.trace.confidence ?? 0) * 100).toFixed(0)}%)
                    </div>
                    {f.trace.entry_points && f.trace.entry_points.length > 0 && (
                      <div className="mt-1">
                        <span className="text-slate-500">Entry points: </span>
                        {f.trace.entry_points.map((ep, i) => (
                          <span key={i} className="mr-2">
                            {ep.kind} @ {ep.location}
                          </span>
                        ))}
                      </div>
                    )}
                    {f.trace.call_chain && f.trace.call_chain.length > 0 && (
                      <div className="mt-1 space-y-0.5">
                        <span className="text-slate-500">Call chain:</span>
                        {f.trace.call_chain.map((frame, i) => (
                          <div key={i} className="ml-4 font-mono text-[11px]">
                            {frame.file}:{frame.line} — {frame.function}()
                          </div>
                        ))}
                      </div>
                    )}
                    <p className="text-slate-500 mt-1 text-[11px]">{f.trace.rationale}</p>
                  </>
                ) : (
                  <div className="flex items-center gap-1 text-red-400">
                    Not reachable
                    <span className="text-slate-500 ml-2">— {f.trace.rationale}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
