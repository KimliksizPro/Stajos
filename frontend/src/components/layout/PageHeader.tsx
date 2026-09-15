import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { Button } from '../ui/Button';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actionLabel?: string;
  onAction?: () => void;
  actionIcon?: LucideIcon;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  actionLabel,
  onAction,
  actionIcon: ActionIcon,
}) => {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold text-text-primary">{title}</h1>
        {subtitle && <p className="text-text-secondary mt-1">{subtitle}</p>}
      </div>
      {actionLabel && onAction && (
        <Button onClick={onAction}>
          {ActionIcon && <ActionIcon className="h-4 w-4 mr-2" />}
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
