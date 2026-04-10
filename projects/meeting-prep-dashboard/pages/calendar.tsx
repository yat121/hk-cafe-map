'use client';
import { useState } from 'react';
import Layout from '../components/Layout';

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];

const events = [
  { date: '2025-04-08', title: 'Budget Meeting', type: 'meeting', color: 'indigo' },
  { date: '2025-04-09', title: 'Operations Sync', type: 'meeting', color: 'indigo' },
  { date: '2025-04-10', title: 'Strategy Planning', type: 'meeting', color: 'indigo' },
  { date: '2025-04-11', title: 'Tech Review', type: 'meeting', color: 'indigo' },
  { date: '2025-04-14', title: 'Board Prep', type: 'meeting', color: 'purple' },
  { date: '2025-04-15', title: 'Q2 Review deadline', type: 'deadline', color: 'amber' },
  { date: '2025-04-16', title: 'Product Sync', type: 'meeting', color: 'indigo' },
  { date: '2025-04-12', title: 'Vendor contracts due', type: 'deadline', color: 'amber' },
  { date: '2025-04-20', title: 'Investor deck due', type: 'deadline', color: 'red' },
  { date: '2025-04-18', title: 'OpenClaw docs follow-up', type: 'action', color: 'emerald' },
  { date: '2025-04-25', title: 'Product team follow-up', type: 'action', color: 'emerald' },
];

export default function CalendarPage() {
  const today = new Date();
  const [currentMonth, setCurrentMonth] = useState(today.getMonth());
  const [currentYear, setCurrentYear] = useState(today.getFullYear());

  const firstDay = new Date(currentYear, currentMonth, 1).getDay();
  const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
  const prevDays = new Date(currentYear, currentMonth, 0).getDate();

  const prevMonth = () => {
    if (currentMonth === 0) { setCurrentMonth(11); setCurrentYear(y => y - 1); }
    else setCurrentMonth(m => m - 1);
  };
  const nextMonth = () => {
    if (currentMonth === 11) { setCurrentMonth(0); setCurrentYear(y => y + 1); }
    else setCurrentMonth(m => m + 1);
  };

  const getEvents = (day: number) => {
    const dateStr = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    return events.filter(e => e.date === dateStr);
  };

  const cells = [
    ...Array(firstDay).fill(null).map((_, i) => prevDays - firstDay + i + 1),
    ...Array(daysInMonth).fill(0).map((_, i) => i + 1),
    ...Array(42 - firstDay - daysInMonth).fill(null).map((_, i) => i + 1),
  ];

  const colorMap: Record<string, string> = {
    indigo: 'bg-indigo-500',
    purple: 'bg-purple-500',
    amber: 'bg-amber-500',
    red: 'bg-red-500',
    emerald: 'bg-emerald-500',
  };

  const upcomingEvents = events
    .filter(e => new Date(e.date + 'T00:00:00') >= new Date())
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Calendar</h1>
          <p className="text-slate-400 text-sm mt-1">Monthly overview</p>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Calendar */}
          <div className="xl:col-span-2 bg-slate-800/60 border border-slate-700/50 rounded-xl overflow-hidden">
            {/* Month nav */}
            <div className="flex items-center justify-between p-4 border-b border-slate-700/50">
              <button onClick={prevMonth} className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700 transition-colors">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <div className="text-sm font-semibold text-white">
                {MONTHS[currentMonth]} {currentYear}
              </div>
              <button onClick={nextMonth} className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700 transition-colors">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>

            {/* Day headers */}
            <div className="grid grid-cols-7 border-b border-slate-700/50">
              {DAYS.map(d => (
                <div key={d} className="py-2 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">{d}</div>
              ))}
            </div>

            {/* Calendar grid */}
            <div className="grid grid-cols-7">
              {cells.map((day, i) => {
                if (!day) return <div key={`empty-${i}`} />;
                const dateStr = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                const dayEvents = getEvents(day);
                const isToday = dateStr === today.toISOString().split('T')[0];
                const isPast = new Date(dateStr + 'T00:00:00') < new Date();

                return (
                  <div
                    key={day}
                    className={`min-h-20 p-1.5 border-b border-r border-slate-800/50 ${
                      isPast && dayEvents.length === 0 ? 'bg-slate-900/20' : ''
                    }`}
                  >
                    <div className={`text-xs font-semibold mb-1 ${
                      isToday ? 'w-6 h-6 bg-indigo-600 text-white rounded-full flex items-center justify-center' : 'text-slate-400'
                    }`}>
                      {day}
                    </div>
                    <div className="space-y-0.5">
                      {dayEvents.slice(0, 2).map((e, ei) => (
                        <div key={ei} className={`text-[10px] px-1 py-0.5 rounded truncate text-white ${colorMap[e.color] || 'bg-slate-600'}`}>
                          {e.title}
                        </div>
                      ))}
                      {dayEvents.length > 2 && (
                        <div className="text-[10px] text-slate-500 pl-1">+{dayEvents.length - 2} more</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Upcoming events sidebar */}
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-700/50">
              <h2 className="text-sm font-semibold text-white">Upcoming</h2>
            </div>
            <div className="divide-y divide-slate-700/50">
              {upcomingEvents.slice(0, 12).map((e, i) => {
                const d = new Date(e.date + 'T00:00:00');
                return (
                  <div key={i} className="px-4 py-3 flex items-start gap-3">
                    <div className={`w-8 h-8 rounded-lg flex flex-col items-center justify-center text-xs font-bold flex-shrink-0 ${colorMap[e.color] || 'bg-slate-600'} text-white`}>
                      <div className="text-[9px] opacity-80">{d.toLocaleString('default', { month: 'short' })}</div>
                      <div>{d.getDate()}</div>
                    </div>
                    <div>
                      <div className="text-xs font-medium text-slate-200">{e.title}</div>
                      <div className="text-xs text-slate-500 mt-0.5 capitalize">{e.type} · {e.date}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
