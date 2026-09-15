import { useNavigate } from 'react-router-dom';
import type { DailyLog } from '../../types';
import { Badge } from '../ui/Badge';

interface RecentLogsProps {
  logs: DailyLog[];
}

export function RecentLogs({ logs }: RecentLogsProps) {
  const navigate = useNavigate();

  if (!logs || logs.length === 0) {
    return <div className="text-text-muted py-4">Henüz kayıt bulunmuyor.</div>;
  }

  return (
    <div className="space-y-4">
      {logs.map((log) => (
        <div
          key={log.id}
          onClick={() => navigate(`/logs/${log.id}`)}
          className="flex flex-col sm:flex-row justify-between p-4 bg-bg-card border border-border rounded-lg shadow-sm hover:border-border-focus cursor-pointer transition-colors"
        >
          <div>
            <h4 className="text-text-primary font-medium">{log.title}</h4>
            <p className="text-sm text-text-secondary mt-1">
              {new Date(log.date || log.start_time).toLocaleDateString('tr-TR')}
            </p>
          </div>
          <div className="flex flex-wrap gap-2 mt-2 sm:mt-0 items-center">
            {log.technologies?.slice(0, 3).map((tech) => (
              <Badge key={tech} variant="default">{tech}</Badge>
            ))}
            {log.technologies && log.technologies.length > 3 && (
              <Badge variant="default">+{log.technologies.length - 3}</Badge>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
