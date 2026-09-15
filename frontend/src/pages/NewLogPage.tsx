import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../api/client';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { useToast } from '../components/ui/Toast';

export function NewLogPage() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [internshipId, setInternshipId] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    title: '',
    raw_content: '',
    start_time: '',
    end_time: '',
    technologies: '',
    tags: '',
    topics: ''
  });

  useEffect(() => {
    const fetchInternship = async () => {
      try {
        const res = await client.get('/api/v1/internships/active');
        if (res.data?.success && res.data.data) {
          setInternshipId(res.data.data.id);
        }
      } catch (e) {
        console.error(e);
      }
    };
    fetchInternship();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!internshipId) {
      addToast('error', 'Aktif staj bulunamadı');
      return;
    }
    
    setLoading(true);
    try {
      const payload = {
        internship_id: internshipId,
        title: formData.title,
        raw_content: formData.raw_content,
        start_time: new Date(formData.start_time).toISOString(),
        end_time: new Date(formData.end_time).toISOString(),
        technologies: formData.technologies.split(',').map(t => t.trim()).filter(Boolean),
        tags: formData.tags.split(',').map(t => t.trim()).filter(Boolean),
        topics: formData.topics.split(',').map(t => t.trim()).filter(Boolean)
      };
      
      const res = await client.post('/api/v1/logs', payload);
      if (res.data?.success) {
        addToast('success', 'Günlük başarıyla oluşturuldu');
        navigate(`/logs/${res.data.data.id}`);
      }
    } catch (error) {
      addToast('error', 'Günlük oluşturulurken hata oluştu');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-6">
      <h1 className="text-2xl font-bold text-text-primary mb-6">Yeni Günlük Kayıt</h1>
      
      <div className="bg-bg-card rounded-lg shadow-sm border border-border p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          <Input
            label="Başlık"
            value={formData.title}
            onChange={(e) => setFormData({...formData, title: e.target.value})}
            required
          />
          
          <div className="space-y-1">
            <label className="block text-sm font-medium text-text-primary">İçerik</label>
            <textarea
              className="w-full min-h-[150px] p-3 rounded-md border border-border bg-bg-primary text-text-primary focus:border-border-focus focus:ring-1 focus:ring-border-focus outline-none transition-colors"
              value={formData.raw_content}
              onChange={(e) => setFormData({...formData, raw_content: e.target.value})}
              required
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              type="datetime-local"
              label="Başlangıç Zamanı"
              value={formData.start_time}
              onChange={(e) => setFormData({...formData, start_time: e.target.value})}
              required
            />
            <Input
              type="datetime-local"
              label="Bitiş Zamanı"
              value={formData.end_time}
              onChange={(e) => setFormData({...formData, end_time: e.target.value})}
              required
            />
          </div>

          <Input
            label="Teknolojiler (Virgülle ayırın)"
            value={formData.technologies}
            onChange={(e) => setFormData({...formData, technologies: e.target.value})}
          />
          
          <Input
            label="Etiketler (Virgülle ayırın)"
            value={formData.tags}
            onChange={(e) => setFormData({...formData, tags: e.target.value})}
          />
          
          <Input
            label="Konular (Virgülle ayırın)"
            value={formData.topics}
            onChange={(e) => setFormData({...formData, topics: e.target.value})}
          />

          <div className="flex justify-end pt-4">
            <Button type="submit" loading={loading}>
              Kaydet
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
