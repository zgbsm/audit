import { NavLink, Outlet } from 'react-router-dom';
import {
  LayoutDashboard,
  Play,
  Settings,
  Terminal,
  Shield,
} from 'lucide-react';

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/logs', icon: Terminal, label: 'Logs' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export function Layout() {
  return (
    <div className="flex h-screen bg-slate-950 text-slate-100">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 border-r border-slate-800 bg-slate-900 flex flex-col">
        <div className="flex items-center gap-3 px-5 py-4 border-b border-slate-800">
          <Shield className="h-6 w-6 text-blue-500" />
          <div>
            <div className="text-sm font-semibold text-slate-100">Audit Web</div>
            <div className="text-[10px] text-slate-500">Vulnerability Discovery</div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-blue-500/15 text-blue-400 font-medium'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="px-5 py-3 border-t border-slate-800 text-[11px] text-slate-600">
          audit v0.1.0
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
