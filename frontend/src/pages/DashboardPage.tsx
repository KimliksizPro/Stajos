import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Calendar, Clock, Code, Brain, Building2, PlusCircle, ArrowRight } from 'lucide-react';
import { StatCard } from '../components/dashboard/StatCard';
import { RecentLogs } from '../components/dashboard/RecentLogs';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { useToast } from '../components/ui/Toast';
import client from '../api/client';
import type { DailyLog, Internship } from '../types';

export function DashboardPage() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<any>(null);
  const [recentLogs, setRecentLogs] = useState<DailyLog[]>([]);
  const [activeInternship, setActiveInternship] = useState<Internship | null>(null);

  // Staj oluşturma formu state
  const [creatingInternship, setCreatingInternship] = useState(false);
  const [internshipForm, setInternshipForm] = useState({
    company_name: '',
    start_date: new Date().toISOString().split('T')[0],
    end_date: '',
    total_expected_days: '20',
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const internshipRes = await client.get('/api/v1/internships/active');
      if (internshipRes.data?.success && internshipRes.data.data) {
        const internship = internshipRes.data.data;
        setActiveInternship(internship);

        const [statsRes, logsRes] = await Promise.all([
          client.get(`/api/v1/dashboard/stats?internship_id=${internship.id}`),
          client.get(`/api/v1/logs?internship_id=${internship.id}&per_page=5&sort=start_time&order=desc`),
        ]);

        if (statsRes.data?.success) setStats(statsRes.data.data);
        if (logsRes.data?.success) setRecentLogs(logsRes.data.data);
      } else {
        setActiveInternship(null);
      }
    } catch (error: any) {
      if (error?.response?.status === 404) {
        setActiveInternship(null);
      } else {
        console.error('Dashboard verisi çekilirken hata:', error);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateInternship = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!internshipForm.company_name.trim()) {
      addToast('error', 'Şirket adı zorunludur.');
      return;
    }
    if (!internshipForm.start_date || !internshipForm.end_date) {
      addToast('error', 'Başlangıç ve bitiş tarihleri zorunludur.');
      return;
    }
    if (new Date(internshipForm.start_date) > new Date(internshipForm.end_date)) {
      addToast('error', 'Başlangıç tarihi bitiş tarihinden sonra olamaz.');
      return;
    }

    setCreatingInternship(true);
    try {
      const res = await client.post('/api/v1/internships', {
        company_name: internshipForm.company_name.trim(),
        start_date: internshipForm.start_date,
        end_date: internshipForm.end_date,
        total_expected_days: parseInt(internshipForm.total_expected_days, 10) || 20,
      });

      if (res.data?.success) {
        addToast('success', 'Staj kaydınız başarıyla oluşturuldu!');
        setActiveInternship(res.data.data);
        fetchData();
      }
    } catch (error: any) {
      const msg = error?.response?.data?.errors?.[0] || 'Staj oluşturulurken bir hata oluştu.';
      addToast('error', msg);
    } finally {
      setCreatingInternship(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-accent border-t-transparent" />
        <p className="text-sm text-text-secondary">Yükleniyor...</p>
      </div>
    );
  }

  // Aktif staj yoksa oluşturma formunu göster
  if (!activeInternship) {
    return (
      <div className="max-w-2xl mx-auto py-8">
        <div className="bg-bg-card rounded-xl shadow-md border border-border p-6 sm:p-8">
          <div className="flex items-center gap-4 mb-6 pb-6 border-b border-border">
            <div className="p-3 bg-accent-light text-accent rounded-xl">
              <Building2 size={32} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-text-primary">Stajınızı Başlatın</h2>
              <p className="text-sm text-text-secondary mt-1">
                Günlük kayıtlarınızı tutmak ve öğrenme sürecinizi takip etmek için staj bilgilerinizi girin.
              </p>
            </div>
          </div>

          <form onSubmit={handleCreateInternship} className="space-y-5">
            <Input
              label="Şirket / Kurum Adı"
              placeholder="Örn: Trendyol, Aselsan, Google..."
              value={internshipForm.company_name}
              onChange={(e) => setInternshipForm({ ...internshipForm, company_name: e.target.value })}
              required
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                type="date"
                label="Başlangıç Tarihi"
                value={internshipForm.start_date}
                onChange={(e) => setInternshipForm({ ...internshipForm, start_date: e.target.value })}
                required
              />
              <Input
                type="date"
                label="Bitiş Tarihi"
                value={internshipForm.end_date}
                onChange={(e) => setInternshipForm({ ...internshipForm, end_date: e.target.value })}
                required
              />
            </div>

            <Input
              type="number"
              label="Toplam Beklenen İş Günü"
              placeholder="20"
              min={1}
              value={internshipForm.total_expected_days}
              onChange={(e) => setInternshipForm({ ...internshipForm, total_expected_days: e.target.value })}
              required
            />

            <div className="pt-3">
              <Button type="submit" className="w-full" loading={creatingInternship}>
                Stajı Başlat
              </Button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  // Aktif staj varsa Dashboard görünümü
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Dashboard</h1>
          <p className="text-sm text-text-secondary mt-0.5">Staj sürecinizin genel durumu ve özet istatistikler</p>
        </div>
        <Button onClick={() => navigate('/logs/new')} className="gap-2">
          <PlusCircle size={18} />
          Yeni Günlük Yaz
        </Button>
      </div>

      <div className="bg-bg-card p-5 rounded-xl border border-border shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-accent-light text-accent rounded-lg">
            <Building2 size={22} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-semibold text-text-primary text-lg">{activeInternship.company_name}</h2>
              <span className="px-2.5 py-0.5 bg-success-light text-success rounded-full text-xs font-semibold">
                Aktif
              </span>
            </div>
            <p className="text-xs text-text-secondary mt-1">
              {new Date(activeInternship.start_date).toLocaleDateString('tr-TR')} —{' '}
              {new Date(activeInternship.end_date).toLocaleDateString('tr-TR')} ({activeInternship.total_expected_days} İş Günü)
            </p>
          </div>
        </div>
        <Button variant="secondary" size="sm" onClick={() => navigate('/logs')} className="gap-1 text-xs">
          Tüm Günlükleri Gör
          <ArrowRight size={14} />
        </Button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={Calendar}
          label="Tamamlanan Gün"
          value={stats?.total_days || 0}
          trend={`${activeInternship.total_expected_days} gün hedeflenen`}
        />
        <StatCard
          icon={Clock}
          label="Toplam Süre"
          value={`${stats?.total_hours || 0} sa`}
        />
        <StatCard
          icon={Code}
          label="Kullanılan Teknoloji"
          value={stats?.technologies_count || 0}
        />
        <StatCard
          icon={Brain}
          label="AI Kabul Oranı"
          value={`%${stats?.ai_acceptance_rate ?? 0}`}
        />
      </div>

      <div className="mt-8">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-text-primary">Son Günlükler</h2>
          {recentLogs.length > 0 && (
            <button
              onClick={() => navigate('/logs')}
              className="text-xs font-medium text-accent hover:text-accent-hover cursor-pointer"
            >
              Hepsini Görüntüle →
            </button>
          )}
        </div>
        <RecentLogs logs={recentLogs} />
      </div>
    </div>
  );
}
