import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { Button } from './Button';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  className = '',
}) => {
  return (
    <div className={`flex flex-col items-center justify-center p-8 text-center bg-bg-card rounded-lg shadow-sm border border-border ${className}`}>
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent-light mb-4">
        <Icon className="h-8 w-8 text-accent" />
      </div>
      <h3 className="text-lg font-medium text-text-primary mb-2">{title}</h3>
      <p className="text-sm text-text-secondary max-w-sm mb-6">{description}</p>
      {actionLabel && onAction && (
        <Button onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
