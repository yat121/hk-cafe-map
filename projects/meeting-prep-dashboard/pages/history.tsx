'use client';
import Layout from '../components/Layout';

const historyItems = [
  { id: 'h1', description: 'Approve budget reallocation for marketing campaign', person: 'David Kim', source: 'Budget Meeting', completedDate: '2025-04-08', meetingDate: '2025-04-08', priority: 'medium' },
  { id: 'h2', description: 'Send Q1 performance report to board members', person: 'Alex Chen', source: 'Quarterly Review', completedDate: '2025-04-05', meetingDate: '2025-04-01', priority: 'high' },
  { id: 'h3', description: 'Update CRM with new client contact details', person: 'Sarah Miller', source: 'Client Onboarding', completedDate: '2025-04-03', meetingDate: '2025-04-02', priority: 'low' },
  { id: 'h4', description: 'Schedule follow-up with engineering team on API v2', person: 'Lisa Wong', source: 'Tech Review', completedDate: '2025-04-01', meetingDate: '2025-03-28', priority: 'medium' },
  { id: 'h5', description: 'Review and sign off on vendor SLA agreements', person: 'Emma Wilson', source: 'Operations Sync', completedDate: '2025-03-28', meetingDate: '2025-03-25', priority: 'high' },
  { id: 'h6', description: 'Prepare draft for investor newsletter', person: 'James Park', source: 'Board Prep', completedDate: '2025-03-25', meetingDate: '2025-03-20', priority: 'medium' },
  { id: 'h7', description: 'Finalize pricing model for new tier', person: 'David Kim', source: 'Strategy Planning', completedDate: '2025-03-22', meetingDate: '2025-03-18', priority: 'high' },
  { id: 'h8', description: 'Send product roadmap to key clients', person: 'Emma Wilson', source: 'Client Sync', completedDate: '2025-03-20', meetingDate: '2025-03-15', priority: 'low' },
];

export default function HistoryPage() {
  const priorityColor: Record<string, string> = {
    high: 'bg-red-500/20 text-red-400 border border-red-500/30',
    medium: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
    low: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  };

  // Group by month
  const grouped: Record<string, typeof historyItems> = {};
  historyItems.forEach(item => {
    const month = new Date(item.completedDate + 'T00:00:00').toLocaleString('default', { month: 'long', year: 'numeric' });
    if (!grouped[month]) grouped[month] = [];
    grouped[month].push(item);
  });

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">History</h1>
          <p className="text-slate-400 text-sm mt-1">{historyItems.length} completed action items</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-emerald-900/20 border border-emerald-800/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-emerald-400">{historyItems.length}</div>
            <div className="text-xs text-emerald-400/70 mt-0.5">Total Done</div>
          </div>
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-white">{historyItems.filter(i => i.priority === 'high').length}</div>
            <div className="text-xs text-slate-400 mt-0.5">High Priority</div>
          </div>
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-white">
              {historyItems.filter(i => {
                const diff = new Date(i.completedDate).getTime() - new Date(i.meetingDate).getTime();
                return diff <= 3 * 86400000;
              }).length}
            </div>
            <div className="text-xs text-slate-400 mt-0.5">≤3 Days</div>
          </div>
        </div>

        {/* Grouped history */}
        {Object.entries(grouped).map(([month, items]) => (
          <div key={month}>
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">{month}</h2>
            <div className="space-y-2">
              {items.map(item => (
                <div key={item.id} className="bg-slate-800/50 border border-slate-700/40 rounded-xl p-4 flex items-start gap-4">
                  <div className="w-8 h-8 bg-emerald-900/50 border border-emerald-700/50 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-300 line-through decoration-slate-600">{item.description}</p>
                    <div className="flex flex-wrap items-center gap-2 mt-2">
                      <span className="text-xs text-indigo-400">{item.person}</span>
                      <span className="text-slate-600 text-xs">·</span>
                      <span className="text-xs text-slate-500">{item.source}</span>
                      <span className="text-slate-600 text-xs">·</span>
                      <span className="text-xs text-slate-500">Due {item.meetingDate}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${priorityColor[item.priority]}`}>
                      {item.priority}
                    </span>
                    <span className="text-xs text-slate-500">{item.completedDate}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Layout>
  );
}
