import { cn, statusColor } from '@/lib/utils';

interface Props {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: Props) {
  return (
    <span className={cn('badge border', statusColor(status), className)}>
      {status}
    </span>
  );
}
