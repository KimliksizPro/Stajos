import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Clock, Calendar } from 'lucide-react';
import client from '../api/client';
import type { DailyLog } from '../types';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { AiStatusBadge } from '../components/logs/AiStatusBadge';
import { useToast } from '../components/ui/Toast';

export function LogDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [log, setLog] = useState<DailyLog | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    const fetchLog = async () => {
      try {
        const res = await client.get(`/api/v1/logs/${id}`);
        if (res.data?.success) {
          setLog(res.data.data);
        }
      } catch (error) {
        addToast('error', 'Günlük yüklenirken hata oluştu');
      } finally {
        setLoading(false);
      }
    };
    fetchLog();
  }, [id]);

  const handleAction = async (action: 'accept-ai' | 'reject-ai') => {
    setActionLoading(true);
    try {
      const res = await client.put(`/api/v1/logs/${id}/${action}`);
      if (res.data?.success) {
        setLog(res.data.data);
        addToast('success', 'İşlem başarılı');
      }
    } catch (error) {
      addToast('error', 'İşlem sırasında hata oluştu');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return <div className="p-8 text-center">Yükleniyor...</div>;
  if (!log) return <div className="p-8 text-center text-error">Günlük bulunamadı</div>;

  const durationStr = () => {
    if (!log.start_time || !log.end_time) return '';
    const start = new Date(log.start_time);
    const end = new Date(log.end_time);
    const diffHours = (end.getTime() - start.getTime()) / (1000 * 60 * 60);
    return `${diffHours.toFixed(1)} saat`;
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center space-x-4 mb-6">
        <button 
          onClick={() => navigate('/logs')}
          className="p-2 hover:bg-bg-card rounded-full text-text-secondary hover:text-text-primary transition-colors"
        >
          <ArrowLeft size={20} />
        </button>
        <h1 className="text-2xl font-bold text-text-primary">Günlük Detayı</h1>
      </div>

      <div className="bg-bg-card rounded-lg shadow-sm border border-border p-6">
        <div className="flex flex-col md:flex-row md:justify-between md:items-start gap-4 mb-6">
          <div>
            <div className="flex items-center space-x-3 mb-2">
              <Badge variant="default">Gün {log.day_number}</Badge>
              <AiStatusBadge status={log.ai_status} />
            </div>
            <h2 className="text-xl font-bold text-text-primary">{log.title}</h2>
          </div>
          
          <div className="flex flex-col gap-2 text-sm text-text-secondary">
            <div className="flex items-center">
              <Calendar size={16} className="mr-2" />
              {new Date(log.start_time).toLocaleDateString('tr-TR')}
            </div>
            <div className="flex items-center">
              <Clock size={16} className="mr-2" />
              {durationStr()}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <section>
            <h3 className="text-lg font-semibold text-text-primary mb-3">İçerik</h3>
            <div className="bg-bg-primary p-4 rounded-md border border-border whitespace-pre-wrap text-text-secondary">
              {log.raw_content}
            </div>
          </section>

          {log.ai_refined_content && (
            <section>
              <h3 className="text-lg font-semibold text-text-primary mb-3">AI Analizi</h3>
              <div className="bg-info-light p-4 rounded-md border border-info/20 whitespace-pre-wrap text-text-primary">
                {log.ai_refined_content}
              </div>
              
              {log.ai_status?.toUpperCase() === 'REFINED' && (
                <div className="flex gap-4 mt-4">
                  <Button 
                    variant="primary" 
                    onClick={() => handleAction('accept-ai')}
                    loading={actionLoading}
                  >
                    Kabul Et
                  </Button>
                  <Button variant="secondary" 
                    className="text-error border-error hover:bg-error-light"
                    onClick={() => handleAction('reject-ai')}
                    disabled={actionLoading}
                  >
                    Reddet
                  </Button>
                </div>
              )}
            </section>
          )}

          <section className="pt-4 border-t border-border flex flex-wrap gap-2">
            {log.technologies?.map(tech => (
              <Badge key={tech} variant="info">{tech}</Badge>
            ))}
            {log.tags?.map(tag => (
              <Badge key={tag} variant="default">{tag}</Badge>
            ))}
            {log.topics?.map(topic => (
              <Badge key={topic} variant="default">{topic}</Badge>
            ))}
          </section>
        </div>
      </div>
    </div>
  );
}
