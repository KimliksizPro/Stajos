import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../api/client';
import type { DailyLog } from '../types';
import { LogCard } from '../components/logs/LogCard';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';

export function LogListPage() {
  const navigate = useNavigate();
  const [logs, setLogs] = useState<DailyLog[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Filters & Pagination
  const [search, setSearch] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [sortOrder, setSortOrder] = useState('desc');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const activeInternshipRes = await client.get('/api/v1/internships/active');
      if (activeInternshipRes.data?.success && activeInternshipRes.data.data) {
        const internshipId = activeInternshipRes.data.data.id;
        
        let url = `/api/v1/logs?internship_id=${internshipId}&page=${page}&per_page=10&sort=start_time&order=${sortOrder}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (startDate) url += `&start_date=${startDate}`;
        if (endDate) url += `&end_date=${endDate}`;
        
        const res = await client.get(url);
        if (res.data?.success) {
          setLogs(res.data.data);
          if (res.data.meta) {
            setTotalPages(Math.ceil(res.data.meta.total / res.data.meta.per_page));
          }
        }
      }
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [page, sortOrder, search, startDate, endDate]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="text-2xl font-bold text-text-primary">Günlükler</h1>
        <Button onClick={() => navigate('/logs/new')}>Yeni Kayıt</Button>
      </div>

      <div className="bg-bg-card p-4 rounded-lg shadow-sm border border-border flex flex-wrap gap-4 items-end">
        <div className="flex-1 min-w-[200px]">
          <Input
            label="Ara"
            placeholder="Başlık veya içerikte ara..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            
          />
        </div>
        <div className="w-full sm:w-auto">
          <Input
            type="date"
            label="Başlangıç Tarihi"
            value={startDate}
            onChange={(e) => { setStartDate(e.target.value); setPage(1); }}
          />
        </div>
        <div className="w-full sm:w-auto">
          <Input
            type="date"
            label="Bitiş Tarihi"
            value={endDate}
            onChange={(e) => { setEndDate(e.target.value); setPage(1); }}
          />
        </div>
        <div className="w-full sm:w-auto space-y-1">
          <label className="block text-sm font-medium text-text-primary">Sıralama</label>
          <select 
            className="w-full px-3 py-2 rounded-md border border-border bg-bg-primary text-text-primary outline-none focus:border-border-focus"
            value={sortOrder}
            onChange={(e) => { setSortOrder(e.target.value); setPage(1); }}
          >
            <option value="desc">Tarih (Yeni → Eski)</option>
            <option value="asc">Tarih (Eski → Yeni)</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-8 text-text-secondary">Yükleniyor...</div>
      ) : logs.length === 0 ? (
        <div className="text-center py-12 bg-bg-card rounded-lg border border-border">
          <p className="text-text-muted">Kayıt bulunamadı.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {logs.map(log => <LogCard key={log.id} log={log} />)}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex justify-center items-center space-x-4 mt-6">
          <Button variant="secondary" 
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            Önceki
          </Button>
          <span className="text-sm text-text-secondary">
            Sayfa {page} / {totalPages}
          </span>
          <Button variant="secondary" 
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
          >
            Sonraki
          </Button>
        </div>
      )}
    </div>
  );
}
