'use client';
import { useState } from 'react';
import Layout from '../components/Layout';

export default function SettingsPage() {
  const [notifications, setNotifications] = useState({
    overdue: true,
    upcoming: true,
    completed: false,
  });
  const [theme, setTheme] = useState('dark');
  const [defaultView, setDefaultView] = useState('actions');

  return (
    <Layout>
      <div className="space-y-6 max-w-2xl">
        <div>
          <h1 className="text-2xl font-bold text-white">Settings</h1>
          <p className="text-slate-400 text-sm mt-1">Configure your meeting prep experience</p>
        </div>

        {/* Notifications */}
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Notifications</h2>
          <div className="space-y-3">
            {[
              { key: 'overdue' as const, label: 'Overdue item alerts', desc: 'Get notified when action items become overdue' },
              { key: 'upcoming' as const, label: 'Upcoming deadlines', desc: 'Remind me 1 day before due date' },
              { key: 'completed' as const, label: 'Completion summaries', desc: 'Weekly summary of completed items' },
            ].map(item => (
              <div key={item.key} className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-slate-200">{item.label}</div>
                  <div className="text-xs text-slate-500">{item.desc}</div>
                </div>
                <button
                  onClick={() => setNotifications(n => ({ ...n, [item.key]: !n[item.key] }))}
                  className={`w-11 h-6 rounded-full transition-colors relative ${
                    notifications[item.key] ? 'bg-indigo-600' : 'bg-slate-600'
                  }`}
                >
                  <div className={`w-5 h-5 bg-white rounded-full absolute top-0.5 transition-transform ${
                    notifications[item.key] ? 'translate-x-5' : 'translate-x-0.5'
                  }`} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Appearance */}
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Appearance</h2>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-slate-400 mb-2 block">Theme</label>
              <div className="flex gap-2">
                {['dark', 'light', 'system'].map(t => (
                  <button
                    key={t}
                    onClick={() => setTheme(t)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-lg capitalize transition-colors ${
                      theme === t ? 'bg-indigo-600 text-white' : 'bg-slate-700 text-slate-400 hover:text-white'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-2 block">Default View</label>
              <div className="flex gap-2">
                {[
                  { v: 'actions', label: 'Actions' },
                  { v: 'meetings', label: 'Meetings' },
                  { v: 'calendar', label: 'Calendar' },
                ].map(opt => (
                  <button
                    key={opt.v}
                    onClick={() => setDefaultView(opt.v)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-lg capitalize transition-colors ${
                      defaultView === opt.v ? 'bg-indigo-600 text-white' : 'bg-slate-700 text-slate-400 hover:text-white'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Data */}
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Data Management</h2>
          <div className="space-y-3">
            <button className="w-full px-4 py-2.5 bg-slate-700 hover:bg-slate-600 text-slate-200 text-sm font-medium rounded-lg transition-colors text-left">
              Export all data as JSON
            </button>
            <button className="w-full px-4 py-2.5 bg-red-900/30 hover:bg-red-900/50 border border-red-800/40 text-red-400 text-sm font-medium rounded-lg transition-colors text-left">
              Clear all completed items
            </button>
          </div>
        </div>

        {/* About */}
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-white mb-3">About</h2>
          <div className="space-y-1.5 text-xs text-slate-500">
            <div>Meeting Prep v1.0.0</div>
            <div>Built for Desmond's personal use</div>
            <div className="pt-2 text-slate-600">All data stored locally in your browser.</div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
