interface Props {
  code: string;
  maxLines?: number;
  className?: string;
}

export function CodeBlock({ code, maxLines = 30, className }: Props) {
  const lines = code.split('\n');
  const truncated = lines.length > maxLines;
  const display = truncated ? lines.slice(0, maxLines).join('\n') : code;

  return (
    <div className={`relative ${className ?? ''}`}>
      <pre className="bg-slate-950 border border-slate-700 rounded-lg p-4 overflow-x-auto text-sm font-mono text-slate-300 leading-relaxed m-0">
        <code>{display}</code>
      </pre>
      {truncated && (
        <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-slate-950 to-transparent flex items-end justify-center pb-2">
          <span className="text-xs text-slate-400">
            ... {lines.length - maxLines} more lines
          </span>
        </div>
      )}
    </div>
  );
}
