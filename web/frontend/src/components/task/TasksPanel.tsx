import { StatusBadge } from '@/components/shared/StatusBadge';
import type { TaskItem } from '@/api/types';

interface Props {
  tasks: TaskItem[];
  className?: string;
}

export function TasksPanel({ tasks, className }: Props) {
  const sorted = [...tasks].sort((a, b) => {
    const order = { running: 0, pending: 1, failed: 2, done: 3 };
    return (order[a.status as keyof typeof order] ?? 4) - (order[b.status as keyof typeof order] ?? 4);
  });

  return (
    <div className={`glass-panel ${className ?? ''}`}>
      <div className="p-4 border-b border-slate-700/50">
        <h3 className="text-sm font-medium text-slate-300">
          Tasks <span className="text-slate-500 font-normal">({tasks.length})</span>
        </h3>
      </div>
      <div className="max-h-[400px] overflow-y-auto">
        {sorted.length === 0 ? (
          <p className="p-4 text-sm text-slate-500 text-center">No tasks yet</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-slate-900/90 backdrop-blur">
              <tr className="text-left text-xs text-slate-500 uppercase tracking-wider">
                <th className="px-4 py-2 font-medium">Task</th>
                <th className="px-4 py-2 font-medium">Attack Class</th>
                <th className="px-4 py-2 font-medium">Target Files</th>
                <th className="px-4 py-2 font-medium">Priority</th>
                <th className="px-4 py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {sorted.map((task) => (
                <tr key={task.task_id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="px-4 py-2.5">
                    <span className="font-mono text-xs text-slate-400">{task.task_id.slice(0, 12)}...</span>
                  </td>
                  <td className="px-4 py-2.5 text-slate-300">{task.attack_class}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex flex-wrap gap-1">
                      {task.target_files.slice(0, 3).map((f) => (
                        <span key={f} className="badge bg-slate-800 text-slate-400">
                          {f}
                        </span>
                      ))}
                      {task.target_files.length > 3 && (
                        <span className="text-xs text-slate-600">
                          +{task.target_files.length - 3}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-slate-400">{task.priority}</td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={task.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
