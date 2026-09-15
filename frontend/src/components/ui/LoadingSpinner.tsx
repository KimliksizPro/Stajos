import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = 'md', className = '' }) => {
  const sizes = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  };

  return (
    <Loader2 className={`animate-spin text-accent ${sizes[size]} ${className}`} />
  );
};

export const FullPageLoader: React.FC = () => {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-bg-primary/80 z-50">
      <LoadingSpinner size="lg" />
    </div>
  );
};
