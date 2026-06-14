import { formatCost } from '@/lib/utils';

interface Props {
  usd: number;
  className?: string;
}

export function CostDisplay({ usd, className }: Props) {
  return (
    <span className={`font-mono text-sm tabular-nums ${className ?? ''}`}>
      {formatCost(usd)}
    </span>
  );
}
