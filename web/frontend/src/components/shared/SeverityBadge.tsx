import { cn, severityColor } from '@/lib/utils';

interface Props {
  severity: string;
  className?: string;
}

export function SeverityBadge({ severity, className }: Props) {
  return (
    <span className={cn('badge border', severityColor(severity), className)}>
      {severity}
    </span>
  );
}
