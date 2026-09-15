import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  icon: LucideIcon;
  value: string | number;
  label: string;
  trend?: string;
}

export function StatCard({ icon: Icon, value, label, trend }: StatCardProps) {
  return (
    <div className="bg-bg-card shadow-sm rounded-lg p-6 border border-border">
      <div className="flex items-center space-x-4">
        <div className="p-3 bg-accent-light rounded-full text-accent">
          <Icon size={24} />
        </div>
        <div>
          <p className="text-sm font-medium text-text-secondary">{label}</p>
          <h3 className="text-2xl font-semibold text-text-primary mt-1">{value}</h3>
          {trend && <p className="text-xs text-text-muted mt-1">{trend}</p>}
        </div>
      </div>
    </div>
  );
}
