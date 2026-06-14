import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Download, Shield, FileCode, Link as LinkIcon } from 'lucide-react';
import { getReport } from '@/api/client';
import { SeverityBadge } from '@/components/shared/SeverityBadge';
import { CodeBlock } from '@/components/shared/CodeBlock';
import { EmptyState } from '@/components/shared/EmptyState';
import { Spinner } from '@/components/shared/Spinner';
import type { ReportData, ReportFinding } from '@/api/types';

export function ReportPage() {
  const { runId } = useParams<{ runId: string }>();
  const { data: report, isLoading, error } = useQuery<ReportData>({
    queryKey: ['report', runId],
    queryFn: () => getReport(runId!, 'json') as Promise<ReportData>,
    enabled: !!runId,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner className="h-8 w-8 text-blue-400" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <EmptyState
        icon={<Shield className="h-10 w-10" />}
        title="Report not available"
        description="The run may not be complete yet, or no report was generated."
      >
        <Link to={`/runs/${runId}`} className="btn btn-secondary mt-4">
          <ArrowLeft className="h-4 w-4" />
          Back to Run
        </Link>
      </EmptyState>
    );
  }

  const handleDownload = (format: 'json' | 'md') => {
    if (!runId) return;
    window.open(`/api/runs/${runId}/report?format=${format}`, '_blank');
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Link to={`/runs/${runId}`} className="btn btn-ghost p-1">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-xl font-semibold text-slate-100">
              Vulnerability Report — <span className="font-mono text-blue-400">{report.run_id}</span>
            </h1>
            <p className="text-sm text-slate-500">Target: {report.target.repo_path}</p>
          </div>
        </div>

        <div className="flex gap-2">
          <button className="btn btn-secondary" onClick={() => handleDownload('md')}>
            <Download className="h-4 w-4" />
            Markdown
          </button>
          <button className="btn btn-secondary" onClick={() => handleDownload('json')}>
            <Download className="h-4 w-4" />
            JSON
          </button>
        </div>
      </div>

      {/* Summary */}
      <div className="glass-panel p-4 mb-6">
        <h2 className="text-sm font-semibold text-slate-200 mb-3">Summary</h2>
        <div className="flex items-center gap-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-slate-100">{report.summary.total}</div>
            <div className="text-xs text-slate-500">Total Findings</div>
          </div>
          {Object.entries(report.summary.by_severity).map(([sev, count]) => (
            <div key={sev} className="text-center">
              <div className="text-lg font-semibold text-slate-200">{count}</div>
              <SeverityBadge severity={sev} />
            </div>
          ))}
        </div>
      </div>

      {/* Findings */}
      {report.findings.length === 0 ? (
        <div className="glass-panel p-8 text-center text-slate-500">
          <Shield className="h-10 w-10 mx-auto mb-3 text-green-500" />
          <p className="text-lg font-medium text-slate-300">No vulnerabilities found</p>
          <p className="text-sm">The audit completed without finding any reachable security issues.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {report.findings.map((finding, i) => (
            <ReportFindingCard key={finding.finding_id || i} finding={finding} />
          ))}
        </div>
      )}
    </div>
  );
}

function ReportFindingCard({ finding }: { finding: ReportFinding }) {
  return (
    <div className="glass-panel p-5">
      <div className="flex items-start gap-3 mb-3">
        <SeverityBadge severity={finding.severity} className="mt-0.5" />
        <div className="flex-1">
          <h3 className="text-base font-medium text-slate-100">{finding.title}</h3>
          <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
            <span className="flex items-center gap-1">
              <FileCode className="h-3 w-3" />
              {finding.file}:{finding.line_start}-{finding.line_end}
            </span>
            <span>{finding.vuln_class}</span>
            {finding.cwe && <span>{finding.cwe}</span>}
          </div>
        </div>
      </div>

      <p className="text-sm text-slate-300 mb-4">{finding.description}</p>

      <div className="mb-4">
        <h4 className="text-xs font-medium text-slate-500 mb-1 uppercase tracking-wider">Evidence</h4>
        <CodeBlock code={finding.evidence} maxLines={20} />
      </div>

      {finding.trace?.entry_points && finding.trace.entry_points.length > 0 && (
        <div className="mb-3">
          <h4 className="text-xs font-medium text-slate-500 mb-1 uppercase tracking-wider">Entry Points</h4>
          <div className="space-y-1">
            {finding.trace.entry_points.map((ep, i) => (
              <div key={i} className="flex items-center gap-1.5 text-xs text-slate-400">
                <LinkIcon className="h-3 w-3 text-blue-400" />
                {ep.kind} at {ep.location}
              </div>
            ))}
          </div>
        </div>
      )}

      {finding.trace?.call_chain && finding.trace.call_chain.length > 0 && (
        <div className="mb-3">
          <h4 className="text-xs font-medium text-slate-500 mb-1 uppercase tracking-wider">Call Chain</h4>
          <div className="space-y-0.5 font-mono text-xs text-slate-400">
            {finding.trace.call_chain.map((frame, i) => (
              <div key={i} className="ml-4">
                {frame.file}:{frame.line} — {frame.function}()
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
        <h4 className="text-xs font-medium text-blue-400 mb-1 uppercase tracking-wider">Recommendation</h4>
        <p className="text-sm text-blue-300">{finding.recommendation}</p>
      </div>

      {finding.variants && finding.variants.length > 0 && (
        <div className="mt-3 text-xs text-slate-500">
          <span className="font-medium">Variants: </span>
          {finding.variants.join(', ')}
        </div>
      )}
    </div>
  );
}
