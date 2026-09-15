import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { GraduationCap } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { useToast } from '../components/ui/Toast';

export function RegisterPage() {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();
  const { addToast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await register(email, password, fullName);
      addToast('success', 'Kayıt başarılı. Lütfen giriş yapın.');
      navigate('/login');
    } catch (error: any) {
      const msg = error?.response?.data?.errors?.[0] || 'Kayıt olurken bir hata oluştu.';
      addToast('error', msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg-primary flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center text-accent">
          <GraduationCap size={48} />
        </div>
        <h2 className="mt-6 text-center text-3xl font-extrabold text-text-primary">
          Kayıt Ol
        </h2>
        <p className="mt-2 text-center text-sm text-text-secondary">
          StajOS'a katılın
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-bg-card py-8 px-4 shadow-lg sm:rounded-xl sm:px-10 border border-border">
          <form className="space-y-6" onSubmit={handleSubmit}>
            <Input
              label="Ad Soyad"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
            <Input
              label="E-posta"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <Input
              label="Şifre"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

            <div>
              <Button type="submit" className="w-full" loading={loading}>
                Hesap Oluştur
              </Button>
            </div>
          </form>

          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-border" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-bg-card text-text-muted">
                  Zaten hesabınız var mı?
                </span>
              </div>
            </div>

            <div className="mt-6 text-center">
              <Link to="/login" className="font-medium text-accent hover:text-accent-hover">
                Giriş yapın
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
