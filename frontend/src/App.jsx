// App.jsx
import React, { useState } from 'react';
import './index.css';
import { ToolsScreen } from './tools';
import { ToastProvider, useToast } from './toasts';
import { AuthProvider, useAuth } from './auth';
import Login from './Login';
import { Boxes, PackageCheck, ClipboardList, Users, Settings } from 'lucide-react';
import RequestScreen from './requests';
import DashboardScreen from './dashboard';
import AdminScreen from './admin';     // NEW
import StaffScreen from './staff';     // NEW

const SidebarItem = ({ icon: Icon, label, active, onClick }) => (
  <button
    onClick={onClick}
    className={`flex items-center gap-2 px-3 py-2 rounded-2xl text-sm transition
      ${active ? 'bg-gradient-to-r from-emerald-600 to-green-600 text-white' : 'hover:bg-neutral-100'}`}
  >
    <Icon className="h-4 w-4" />
    <span>{label}</span>
  </button>
);

function Shell() {
  const [tab, setTab] = useState('requests');
  const { me, logout } = useAuth();
  const { push } = useToast();

  if (!me) return <Login />;

  const role = (me.role || me.roles || 'user').toLowerCase();
  const isAdmin = role === 'admin';

  const go = (nextTab, adminOnly = false) => {
    if (adminOnly && !isAdmin) {
      push("You're not an admin", 'error');
      return;
    }
    setTab(nextTab);
  };

  return (
    <div className="min-h-screen bg-neutral-50 text-neutral-900 dark:bg-neutral-950 dark:text-neutral-100">
      <div className="flex">
        <aside className="hidden lg:flex lg:w-64 flex-col gap-1 border-r border-neutral-200 dark:border-neutral-800 p-3">
          <div className="flex items-center justify-between px-1 py-2">
            <div className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-white shadow overflow-hidden">
                <img src="/ecews-logo.png" alt="ECEWS" className="h-7 w-7 object-contain" />
              </div>
              <div>
                <div className="text-sm font-semibold">
                  {me.first_name || me.name || me.username}
                </div>
                <div className="text-xs opacity-70">
                  {me.facility || '—'}
                </div>
              </div>
            </div>
            <span
              className={`ml-2 text-[11px] px-2 py-0.5 rounded-full ${
                isAdmin
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-neutral-100 text-neutral-700'
              }`}
            >
              {role}
            </span>
            <button className="ml-2 text-xs underline opacity-70" onClick={logout}>
              Logout
            </button>
          </div>

          <SidebarItem icon={ClipboardList} label="Requests"  active={tab==='requests'}  onClick={()=>go('requests')} />
          <SidebarItem icon={PackageCheck} label="Tools"     active={tab==='tools'}     onClick={()=>go('tools', true)} />
          <SidebarItem icon={Boxes}         label="Dashboard" active={tab==='dashboard'} onClick={()=>go('dashboard')} />
          <SidebarItem icon={Users}         label="Users" active={tab==='staff'}  onClick={()=>go('staff', true)} />
          <SidebarItem icon={Settings}      label="Admin" active={tab==='admin'}  onClick={()=>go('admin', true)} />
        </aside>

        <main className="flex-1 p-6 max-w-7xl mx-auto">
          {tab === 'requests'  && <RequestScreen />}
          {tab === 'dashboard' && <DashboardScreen />}
          {tab === 'tools'     && (isAdmin ? <ToolsScreen /> : null)}
          {tab === 'staff'     && (isAdmin ? <StaffScreen /> : null)}
          {tab === 'admin'     && (isAdmin ? <AdminScreen /> : null)}
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <Shell />
      </AuthProvider>
    </ToastProvider>
  );
}
