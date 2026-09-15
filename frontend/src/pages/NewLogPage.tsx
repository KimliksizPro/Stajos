import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Building2, AlertCircle } from 'lucide-react';
import client from '../api/client';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { TagInput } from '../components/forms/TagInput';
import { useToast } from '../components/ui/Toast';

export function NewLogPage() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [checkingInternship, setCheckingInternship] = useState(true);
  const [internshipId, setInternshipId] = useState<string | null>(null);

  const [date, setDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [title, setTitle] = useState('');
  const [rawContent, setRawContent] = useState('');
  const [startTime, setStartTime] = useState('09:00');
  const [endTime, setEndTime] = useState('17:00');
  const [technologies, setTechnologies] = useState<string[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [topics, setTopics] = useState<string[]>([]);

  useEffect(() => {
    const fetchInternship = async () => {
      try {
        const res = await client.get('/api/v1/internships/active');
        if (res.data?.success && res.data.data) {
          setInternshipId(res.data.data.id);
        }
      } catch (e) {
        setInternshipId(null);
      } finally {
        setCheckingInternship(false);
      }
    };
    fetchInternship();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!internshipId) {
      addToast('error', 'Aktif bir staj bulunamadı. Lütfen önce staj kaydı oluşturun.');
      return;
    }

    if (!title.trim() || !rawContent.trim()) {
      addToast('error', 'Başlık ve içerik alanları zorunludur.');
      return;
    }

    setLoading(true);
    try {
      const payload: Record<string, any> = {
        internship_id: internshipId,
        title: title.trim(),
        raw_content: rawContent.trim(),
        date: date || undefined,
        start_time: startTime || undefined,
        end_time: endTime || undefined,
        technologies: technologies.length > 0 ? technologies : undefined,
        tags: tags.length > 0 ? tags : undefined,
        topics: topics.length > 0 ? topics : undefined,
      };

      const res = await client.post('/api/v1/logs', payload);
      if (res.data?.success) {
        addToast('success', 'Günlük başarıyla kaydedildi!');
        navigate(`/logs/${res.data.data.id}`);
      }
    } catch (error: any) {
      const msg = error?.response?.data?.errors?.[0] || 'Günlük oluşturulurken bir hata oluştu.';
      addToast('error', msg);
    } finally {
      setLoading(false);
    }
  };

  if (checkingInternship) {
    return (
      <div className="flex justify-center items-center py-16">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-accent border-t-transparent" />
      </div>
    );
  }

  if (!internshipId) {
    return (
      <div className="max-w-xl mx-auto py-12 text-center">
        <div className="bg-bg-card rounded-xl border border-border p-8 shadow-sm">
          <div className="mx-auto w-12 h-12 bg-warning-light text-warning rounded-full flex items-center justify-center mb-4">
            <AlertCircle size={26} />
          </div>
          <h2 className="text-xl font-bold text-text-primary mb-2">Aktif Staj Bulunamadı</h2>
          <p className="text-sm text-text-secondary mb-6">
            Günlük kaydı ekleyebilmek için önce bir staj kaydı oluşturmanız gerekmektedir.
          </p>
          <Button onClick={() => navigate('/')} className="gap-2">
            <Building2 size={18} />
            Dashboard'a Git ve Staj Oluştur
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto py-6">
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => navigate(-1)}
          className="p-2 hover:bg-bg-card rounded-lg text-text-secondary hover:text-text-primary transition-colors cursor-pointer"
        >
          <ArrowLeft size={20} />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Yeni Günlük Kayıt</h1>
          <p className="text-xs text-text-secondary mt-0.5">Bugün yaptıklarınızı, öğrendiklerinizi ve kullandığınız teknolojileri not edin</p>
        </div>
      </div>

      <div className="bg-bg-card rounded-xl shadow-sm border border-border p-6 sm:p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="Başlık *"
                placeholder="Örn: Docker Konteyner Kurulumu ve API Geliştirme"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
            </div>
            <div>
              <Input
                type="date"
                label="Tarih"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="block text-sm font-medium text-text-primary">
              Günlük Notlar / İçerik *
            </label>
            <textarea
              className="w-full min-h-[160px] p-3 rounded-md border border-border bg-bg-primary text-text-primary focus:border-border-focus focus:ring-1 focus:ring-border-focus outline-none transition-colors text-sm"
              placeholder="Bugün ne yaptınız, hangi problemleri çözdünüz, neler öğrendiniz? Detaylı yazabilirsiniz..."
              value={rawContent}
              onChange={(e) => setRawContent(e.target.value)}
              required
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              type="time"
              label="Başlangıç Saati"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
            />
            <Input
              type="time"
              label="Bitiş Saati"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
            />
          </div>

          <div className="space-y-4 pt-2 border-t border-border">
            <TagInput
              label="Kullanılan Teknolojiler"
              placeholder="Örn: React, Docker, Python (Enter veya virgülle ekleyin)"
              tags={technologies}
              onChange={setTechnologies}
            />

            <TagInput
              label="Öğrenilen Konular"
              placeholder="Örn: State Management, REST API, Async (Enter ile ekleyin)"
              tags={topics}
              onChange={setTopics}
            />

            <TagInput
              label="Etiketler"
              placeholder="Örn: frontend, bugfix, toplantı"
              tags={tags}
              onChange={setTags}
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-border">
            <Button
              type="button"
              variant="secondary"
              onClick={() => navigate(-1)}
              disabled={loading}
            >
              İptal
            </Button>
            <Button type="submit" loading={loading}>
              Kaydet ve AI ile İncele
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
