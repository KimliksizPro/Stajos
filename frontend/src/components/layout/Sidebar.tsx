import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { GraduationCap, LayoutDashboard, BookOpen, Calendar, Lightbulb, LogOut, Menu, X } from 'lucide-react';
// import { useAuth } from '@/contexts/AuthContext'; // To be implemented later

export const Sidebar: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();
  // const { user, logout } = useAuth();
  const user = { email: 'user@example.com' }; // Placeholder
  const logout = () => console.log('logout'); // Placeholder

  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Günlükler', path: '/logs', icon: BookOpen },
    { name: 'Timeline', path: '/timeline', icon: Calendar },
    { name: 'Konular', path: '/topics', icon: Lightbulb },
  ];

  const closeSidebar = () => setIsOpen(false);

  return (
    <>
      <button
        className="md:hidden fixed top-4 left-4 z-50 p-2 bg-white rounded-md shadow-sm border border-border"
        onClick={() => setIsOpen(!isOpen)}
      >
        {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {isOpen && (
        <div 
          className="md:hidden fixed inset-0 bg-black/50 z-40"
          onClick={closeSidebar}
        />
      )}

      <aside
        className={`fixed md:sticky top-0 left-0 z-40 h-screen w-[260px] bg-bg-sidebar border-r border-border flex flex-col transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div className="flex items-center gap-3 p-6">
          <div className="bg-accent rounded-md p-1.5">
            <GraduationCap className="h-6 w-6 text-white" />
          </div>
          <span className="text-xl font-bold text-text-primary tracking-tight">StajOS</span>
        </div>

        <nav className="flex-1 px-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
            
            return (
              <NavLink
                key={item.name}
                to={item.path}
                onClick={closeSidebar}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-accent-light text-accent'
                    : 'text-text-secondary hover:bg-white hover:text-text-primary'
                }`}
              >
                <Icon className={`h-5 w-5 ${isActive ? 'text-accent' : 'text-text-muted'}`} />
                {item.name}
              </NavLink>
            );
          })}
        </nav>

        <div className="p-4 border-t border-border mt-auto">
          <div className="flex flex-col gap-3">
            <div className="px-3 text-sm text-text-secondary truncate">
              {user?.email}
            </div>
            <button
              onClick={() => {
                logout();
                closeSidebar();
              }}
              className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-error hover:bg-error-light/50 rounded-md transition-colors w-full"
            >
              <LogOut className="h-5 w-5" />
              Çıkış Yap
            </button>
          </div>
        </div>
      </aside>
    </>
  );
};
