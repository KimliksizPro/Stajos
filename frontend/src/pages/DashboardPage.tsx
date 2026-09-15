import { useEffect, useState } from 'react';
import { Calendar, Clock, Code, Brain } from 'lucide-react';
import { StatCard } from '../components/dashboard/StatCard';
import { RecentLogs } from '../components/dashboard/RecentLogs';
import client from '../api/client';
import type { DailyLog } from '../types';

export function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<any>(null);
  const [recentLogs, setRecentLogs] = useState<DailyLog[]>([]);
  const [activeInternship, setActiveInternship] = useState<any>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const internshipRes = await client.get('/api/v1/internships/active');
        if (internshipRes.data?.success && internshipRes.data.data) {
          const internship = internshipRes.data.data;
          setActiveInternship(internship);
          
          const [statsRes, logsRes] = await Promise.all([
            client.get(`/api/v1/dashboard/stats?internship_id=${internship.id}`),
            client.get(`/api/v1/logs?internship_id=${internship.id}&per_page=5&sort=start_time&order=desc`)
          ]);

          if (statsRes.data?.success) setStats(statsRes.data.data);
          if (logsRes.data?.success) setRecentLogs(logsRes.data.data);
        }
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center h-full">Yükleniyor...</div>;
  }

  if (!activeInternship) {
    return (
      <div className="p-8 text-center bg-bg-card rounded-lg border border-border mt-8">
        <h2 className="text-xl font-semibold mb-2">Aktif Staj Bulunamadı</h2>
        <p className="text-text-secondary">Lütfen önce bir staj kaydı oluşturun.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-text-primary">Dashboard</h1>
      </div>

      <div className="bg-accent-light p-4 rounded-lg border border-accent/20 flex justify-between items-center">
        <div>
          <h2 className="font-semibold text-accent">{activeInternship.company_name}</h2>
          <p className="text-sm text-text-secondary mt-1">
            {new Date(activeInternship.start_date).toLocaleDateString('tr-TR')} - {new Date(activeInternship.end_date).toLocaleDateString('tr-TR')}
          </p>
        </div>
        <div className="px-3 py-1 bg-white rounded-full text-xs font-medium text-accent border border-accent/20">
          Aktif
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          icon={Calendar}
          label="Toplam Gün"
          value={stats?.total_days || 0}
        />
        <StatCard
          icon={Clock}
          label="Toplam Saat"
          value={stats?.total_hours || 0}
        />
        <StatCard
          icon={Code}
          label="Teknolojiler"
          value={stats?.technologies_count || 0}
        />
        <StatCard
          icon={Brain}
          label="AI Onay %"
          value={`${stats?.ai_acceptance_rate || 0}%`}
        />
      </div>

      <div className="mt-8">
        <h2 className="text-xl font-semibold text-text-primary mb-4">Son Günlükler</h2>
        <RecentLogs logs={recentLogs} />
      </div>
    </div>
  );
}
