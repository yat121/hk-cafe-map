'use client';
import { useEffect, useState } from 'react';
import Layout from '../components/Layout';

type ActionItem = {
  id: string;
  person: string;
  description: string;
  dueDate: string;
  meetingDate: string;
  status: 'Pending' | 'Done';
  source: string;
  priority?: 'low' | 'medium' | 'high';
  createdAt: string;
};

const STORAGE_KEY = 'meeting-prep-actions';

const sampleData: ActionItem[] = [
  { id: '1', person: 'Alex Chen', description: 'Review Q2 financial projections and provide feedback on growth assumptions', dueDate: '2025-04-15', meetingDate: '2025-04-10', status: 'Pending', source: 'Strategy Planning', priority: 'high', createdAt: '2025-04-08' },
  { id: '2', person: 'Sarah Miller', description: 'Send updated vendor contracts for legal review', dueDate: '2025-04-12', meetingDate: '2025-04-09', status: 'Pending', source: 'Operations Sync', priority: 'medium', createdAt: '2025-04-07' },
  { id: '3', person: 'James Park', description: 'Prepare investor update deck with latest metrics', dueDate: '2025-04-20', meetingDate: '2025-04-14', status: 'Pending', source: 'Board Prep', priority: 'high', createdAt: '2025-04-06' },
  { id: '4', person: 'Lisa Wong', description: 'Follow up on OpenClaw integration documentation', dueDate: '2025-04-18', meetingDate: '2025-04-11', status: 'Pending', source: 'Tech Review', priority: 'low', createdAt: '2025-04-05' },
  { id: '5', person: 'David Kim', description: 'Approve budget reallocation for marketing campaign', dueDate: '2025-04-10', meetingDate: '2025-04-08', status: 'Done', source: 'Budget Meeting', priority: 'medium', createdAt: '2025-04-03' },
  { id: '6', person: 'Emma Wilson', description: 'Schedule follow-up with product team on new feature roadmap', dueDate: '2025-04-25', meetingDate: '2025-04-16', status: 'Pending', source: 'Product Sync', priority: 'medium', createdAt: '2025-04-04' },
];

function loadItems(): ActionItem[] {
  if (typeof window === 'undefined') return sampleData;
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return JSON.parse(stored);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sampleData));
    return sampleData;
  } catch {
    return sampleData;
  }
}

function saveItems(items: ActionItem[]) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

const priorityColor = {
  high: 'bg-red-500/20 text-red-400 border border-red-500/30',
  medium: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  low: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
};

const statusConfig = {
  Pending: { label: 'Pending', bg: 'bg-slate-700', text: 'text-slate-300', dot: 'bg-amber-400' },
  Done: { label: 'Done', bg: 'bg-emerald-900/50', text: 'text-emerald-400', dot: 'bg-emerald-400' },
};

export default function ActionsPage() {
  const [items, setItems] = useState<ActionItem[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [filterPerson, setFilterPerson] = useState('');
  const [filterStatus, setFilterStatus] = useState<'all' | 'Pending' | 'Done'>('all');
  const [newItem, setNewItem] = useState<{ person: string; description: string; dueDate: string; meetingDate: string; source: string; priority: 'low' | 'medium' | 'high' }>({ person: '', description: '', dueDate: '', meetingDate: '', source: '', priority: 'medium' });

  useEffect(() => { setItems(loadItems()); }, []);

  const toggleStatus = (item: ActionItem) => {
    const updated = items.map(i => i.id === item.id ? { ...i, status: (i.status === 'Pending' ? 'Done' : 'Pending') as 'Pending' | 'Done' } : i);
    setItems(updated);
    saveItems(updated);
  };

  const deleteItem = (id: string) => {
    const updated = items.filter(i => i.id !== id);
    setItems(updated);
    saveItems(updated);
  };

  const addItem = (e: React.FormEvent) => {
    e.preventDefault();
    const item: ActionItem = {
      id: Date.now().toString(),
      ...newItem,
      status: 'Pending',
      createdAt: new Date().toISOString().split('T')[0],
    };
    const updated = [item, ...items];
    setItems(updated);
    saveItems(updated);
    setNewItem({ person: '', description: '', dueDate: '', meetingDate: '', source: '', priority: 'medium' });
    setShowAdd(false);
  };

  const pending = items.filter(i => i.status === 'Pending');
  const done = items.filter(i => i.status === 'Done');
  const overdue = pending.filter(i => i.dueDate && new Date(i.dueDate) < new Date());

  const filtered = items.filter(i => {
    if (filterStatus !== 'all' && i.status !== filterStatus) return false;
    if (filterPerson && !i.person.toLowerCase().includes(filterPerson.toLowerCase())) return false;
    return true;
  });

  const people = [...new Set(items.map(i => i.person))];

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white">Action Items</h1>
            <p className="text-slate-400 text-sm mt-1">
              {pending.length} pending · {overdue.length} overdue · {done.length} completed
            </p>
          </div>
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg transition-colors shadow-lg shadow-indigo-900/50"
          >
            + New Action
          </button>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4">
            <div className="text-2xl font-bold text-white">{pending.length}</div>
            <div className="text-xs text-slate-400 mt-0.5">Pending</div>
          </div>
          <div className="bg-red-900/20 border border-red-800/30 rounded-xl p-4">
            <div className="text-2xl font-bold text-red-400">{overdue.length}</div>
            <div className="text-xs text-red-400/70 mt-0.5">Overdue</div>
          </div>
          <div className="bg-emerald-900/20 border border-emerald-800/30 rounded-xl p-4">
            <div className="text-2xl font-bold text-emerald-400">{done.length}</div>
            <div className="text-xs text-emerald-400/70 mt-0.5">Done</div>
          </div>
        </div>

        {/* Add form */}
        {showAdd && (
          <div className="bg-slate-800/70 border border-slate-700/50 rounded-xl p-5 backdrop-blur">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">New Action Item</h3>
            <form onSubmit={addItem} className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <input
                  placeholder='Owner (person name)'
                  value={newItem.person}
                  onChange={e => setNewItem({...newItem, person: e.target.value})}
                  required
                  className="w-full px-3 py-2 bg-slate-900/80 border border-slate-600 text-slate-200 rounded-lg text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
                <input
                  placeholder='Source meeting'
                  value={newItem.source}
                  onChange={e => setNewItem({...newItem, source: e.target.value})}
                  required
                  className="w-full px-3 py-2 bg-slate-900/80 border border-slate-600 text-slate-200 rounded-lg text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
                <input
                  type='date'
                  value={newItem.dueDate}
                  onChange={e => setNewItem({...newItem, dueDate: e.target.value})}
                  required
                  className="w-full px-3 py-2 bg-slate-900/80 border border-slate-600 text-slate-200 rounded-lg text-sm focus:outline-none focus:border-indigo-500"
                />
                <input
                  type='date'
                  placeholder='Meeting date'
                  value={newItem.meetingDate}
                  onChange={e => setNewItem({...newItem, meetingDate: e.target.value})}
                  required
                  className="w-full px-3 py-2 bg-slate-900/80 border border-slate-600 text-slate-200 rounded-lg text-sm focus:outline-none focus:border-indigo-500"
                />
                <select
                  value={newItem.priority}
                  onChange={e => setNewItem({...newItem, priority: e.target.value as 'low' | 'medium' | 'high'})}
                  className="w-full px-3 py-2 bg-slate-900/80 border border-slate-600 text-slate-200 rounded-lg text-sm focus:outline-none focus:border-indigo-500"
                >
                  <option value="low">Low Priority</option>
                  <option value="medium">Medium Priority</option>
                  <option value="high">High Priority</option>
                </select>
              </div>
              <textarea
                placeholder='Description of the action item...'
                value={newItem.description}
                onChange={e => setNewItem({...newItem, description: e.target.value})}
                required
                rows={2}
                className="w-full px-3 py-2 bg-slate-900/80 border border-slate-600 text-slate-200 rounded-lg text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
              />
              <div className="flex gap-2">
                <button type='submit' className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg transition-colors">
                  Add Action
                </button>
                <button type='button' onClick={() => setShowAdd(false)} className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm font-medium rounded-lg transition-colors">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            placeholder="Filter by person..."
            value={filterPerson}
            onChange={e => setFilterPerson(e.target.value)}
            className="flex-1 px-3 py-2 bg-slate-800/60 border border-slate-700 text-slate-200 rounded-lg text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
          <div className="flex gap-1 bg-slate-800/60 border border-slate-700 rounded-lg p-1">
            {(['all', 'Pending', 'Done'] as const).map(s => (
              <button
                key={s}
                onClick={() => setFilterStatus(s)}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  filterStatus === s ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {s === 'all' ? 'All' : s}
              </button>
            ))}
          </div>
        </div>

        {/* Action cards */}
        {filtered.length === 0 && (
          <div className="text-center py-16 text-slate-500">
            <div className="text-4xl mb-3">📋</div>
            <div className="text-sm">No action items found</div>
          </div>
        )}

        <div className="space-y-3">
          {filtered.map(item => {
            const isOverdue = item.status === 'Pending' && item.dueDate && new Date(item.dueDate) < new Date();
            const sc = statusConfig[item.status];
            return (
              <div
                key={item.id}
                className={`bg-slate-800/60 border rounded-xl p-4 backdrop-blur transition-all hover:bg-slate-800/80 ${
                  isOverdue ? 'border-red-800/50' : item.status === 'Done' ? 'border-emerald-800/30 opacity-75' : 'border-slate-700/50'
                }`}
              >
                <div className="flex items-start gap-3">
                  <button
                    onClick={() => toggleStatus(item)}
                    className={`mt-0.5 w-5 h-5 rounded-full border-2 flex-shrink-0 flex items-center justify-center transition-colors ${
                      item.status === 'Done' ? 'bg-emerald-500 border-emerald-500 text-white' : 'border-slate-600 hover:border-indigo-400'
                    }`}
                  >
                    {item.status === 'Done' && (
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </button>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <p className={`text-sm leading-snug ${item.status === 'Done' ? 'line-through text-slate-500' : 'text-slate-200'}`}>
                          {item.description}
                        </p>
                        <div className="flex flex-wrap items-center gap-2 mt-2">
                          <span className="text-xs text-indigo-400 font-medium">{item.person}</span>
                          <span className="text-slate-600 text-xs">·</span>
                          <span className="text-xs text-slate-400">{item.source}</span>
                          {item.dueDate && (
                            <>
                              <span className="text-slate-600 text-xs">·</span>
                              <span className={`text-xs ${isOverdue ? 'text-red-400 font-medium' : 'text-slate-400'}`}>
                                Due {item.dueDate}
                              </span>
                            </>
                          )}
                          {item.meetingDate && (
                            <>
                              <span className="text-slate-600 text-xs">·</span>
                              <span className="text-xs text-slate-500">From {item.meetingDate}</span>
                            </>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {item.priority && (
                          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${priorityColor[item.priority]}`}>
                            {item.priority}
                          </span>
                        )}
                        <button
                          onClick={() => deleteItem(item.id)}
                          className="text-slate-600 hover:text-red-400 p-1 transition-colors"
                          title="Delete"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </Layout>
  );
}
