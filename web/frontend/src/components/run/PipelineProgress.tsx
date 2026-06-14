import { Check, Circle, Loader2, XCircle, AlertTriangle } from 'lucide-react';
import { STAGE_LABELS, STAGE_ORDER } from '@/lib/constants';

interface StageState {
  started: boolean;
  done: boolean;
  failed: boolean;
}

interface Props {
  stages: Record<string, StageState>;
}

// The canonical 9 stages in pipeline order
const ALL_STAGES = [
  'recon', 'merge', 'hunt', 'validate', 'gapfill',
  'dedupe', 'trace', 'feedback', 'report',
];

export function PipelineProgress({ stages }: Props) {
  return (
    <div className="glass-panel p-4">
      <h3 className="text-sm font-medium text-slate-300 mb-4">Pipeline Progress</h3>
      <div className="flex items-center gap-1 flex-wrap">
        {ALL_STAGES.map((stage, i) => {
          const state = stages[stage];
          return (
            <div key={stage} className="flex items-center gap-1">
              <StageNode
                label={STAGE_LABELS[stage] || stage}
                started={state?.started ?? false}
                done={state?.done ?? false}
                failed={state?.failed ?? false}
              />
              {i < ALL_STAGES.length - 1 && (
                <div
                  className={`w-4 h-px ${
                    (state?.done ?? false) ? 'bg-green-500/50' : 'bg-slate-700'
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StageNode({
  label,
  started,
  done,
  failed,
}: {
  label: string;
  started: boolean;
  done: boolean;
  failed: boolean;
}) {
  let Icon = Circle;
  let colorClass = 'text-slate-600';
  let bgClass = 'bg-slate-800/50';

  if (failed) {
    Icon = AlertTriangle;
    colorClass = 'text-red-400';
    bgClass = 'bg-red-500/10';
  } else if (done) {
    Icon = Check;
    colorClass = 'text-green-400';
    bgClass = 'bg-green-500/10';
  } else if (started) {
    Icon = Loader2;
    colorClass = 'text-blue-400 animate-spin';
    bgClass = 'bg-blue-500/10';
  }

  return (
    <div className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg ${bgClass} text-xs`}>
      <Icon className={`h-3.5 w-3.5 ${colorClass}`} />
      <span className={`font-medium ${failed ? 'text-red-300' : done ? 'text-green-300' : started ? 'text-blue-300' : 'text-slate-500'}`}>
        {label}
      </span>
    </div>
  );
}
