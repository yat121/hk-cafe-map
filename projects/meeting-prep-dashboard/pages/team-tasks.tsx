'use client';
import { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';

// ─── Types ───────────────────────────────────────────────────────────────────

interface TrelloCard {
  id: string;
  name: string;
  desc: string;
  idList: string;
  due: string | null;
  start: string | null;
  dueComplete: boolean;
  labels: { id: string; name: string; color: string }[];
  shortUrl: string;
  shortLink: string;
  pos: number;
  idMembers: string[];
  createdAt?: string;
}

interface TrelloList {
  id: string;
  name: string;
  pos: number;
  closed: boolean;
}

interface TrelloMember {
  id: string;
  fullName: string;
  username: string;
}

// ─── Config ──────────────────────────────────────────────────────────────────

const BOARD_ID = '69d5c9da8c454337882bc82d';
const API_KEY = 'D2RGPr7Xov0s0fhqULJATtI9h8GjEhwj8OlCUJkQ08Lza8x2313VQdWKWBbF_HNKTXHdl5oR3YA1wwS2b6cts0Cps3clrCO25U0';
const API_BASE = `https://gateway.maton.ai/trello/1/boards/${BOARD_ID}`;

// Person → list-id mapping (derived from task spec)
const PERSON_LISTS: Record<string, { listId: string; label: string }[]> = {
  'David Ho': [
    { listId: '69d5cd6dc155817f11b18d1e', label: 'To Do' },
    { listId: '69d5cd6ef0e3079313a8b6ad', label: 'Doing' },
    { listId: '69d5cd6f0b2992f57ceac37b', label: 'Done' },
  ],
  'Codee Wong': [
    { listId: '69d5cd701d84b6387e87c0ff', label: 'To Do' },
    { listId: '69d5cd71f7813777381a430c', label: 'Doing' },
    { listId: '69d5cd728c4543378835b6ce', label: 'Done' },
  ],
  'All Team': [
    { listId: '69d5cd73288814c6e0ffd357', label: 'To Do' },
    { listId: '69d5cd74a6e640209057f8cd', label: 'Doing' },
    { listId: '69d5cd75c641d4731e979613', label: 'Done' },
  ],
};

// All 9 list IDs
const ALL_LIST_IDS = Object.values(PERSON_LISTS).flat().map(l => l.listId);

// Status → list-label suffix mapping
const STATUS_LISTS: Record<string, string[]> = {
  'To Do':     ['69d5cd6dc155817f11b18d1e', '69d5cd701d84b6387e87c0ff', '69d5cd73288814c6e0ffd357'],
  'Doing':     ['69d5cd6ef0e3079313a8b6ad', '69d5cd71f7813777381a430c', '69d5cd74a6e640209057f8cd'],
  'Done':      ['69d5cd6f0b2992f57ceac37b', '69d5cd728c4543378835b6ce', '69d5cd75c641d4731e979613'],
};

// Person → accent color
const PERSON_COLORS: Record<string, { border: string; badge: string; tag: string }> = {
  'David Ho': {
    border: 'border-blue-600/50 hover:border-blue-500',
    badge:  'bg-blue-500/20 text-blue-400 border-blue-500/30',
    tag:    'bg-blue-500/10 text-blue-300',
  },
  'Codee Wong': {
    border: 'border-emerald-600/50 hover:border-emerald-500',
    badge:  'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    tag:    'bg-emerald-500/10 text-emerald-300',
  },
  'All Team': {
    border: 'border-purple-600/50 hover:border-purple-500',
    badge:  'bg-purple-500/20 text-purple-400 border-purple-500/30',
    tag:    'bg-purple-500/10 text-purple-300',
  },
};

const STATUS_COLORS: Record<string, { dot: string; header: string }> = {
  'To Do':  { dot: 'bg-slate-500',   header: 'bg-slate-800/60' },
  'Doing':  { dot: 'bg-amber-400',   header: 'bg-amber-900/20' },
  'Done':   { dot: 'bg-emerald-400', header: 'bg-emerald-900/20' },
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function detectPerson(listId: string): string | null {
  for (const [person, lists] of Object.entries(PERSON_LISTS)) {
    if (lists.some(l => l.listId === listId)) return person;
  }
  return null;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

function getAge(createdStr: string): string {
  const created = new Date(createdStr);
  const now = new Date();
  const diffMs = now.getTime() - created.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return '1d ago';
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return `${Math.floor(diffDays / 30)}mo ago`;
}

function extractMeetingSource(desc: string): string | null {
  // Look for "Meeting:", "Source:", "From:" patterns
  const patterns = [
    /[Mm]eeting:\s*([^\n]+)/,
    /[Ss]ource:\s*([^\n]+)/,
    /[Ff]rom:\s*([^\n]+)/,
    /[Oo]rigin:\s*([^\n]+)/,
  ];
  for (const p of patterns) {
    const m = desc.match(p);
    if (m) return m[1].trim();
  }
  return null;
}

function getDescPreview(desc: string, lines = 2): string {
  if (!desc) return '';
  const parts = desc.split('\n').filter(l => l.trim());
  return parts.slice(0, lines).join('\n').trim();
}

// ─── Card Detail Modal ───────────────────────────────────────────────────────

function CardModal({ card, person, onClose }: { card: TrelloCard; person: string | null; onClose: () => void }) {
  const colors = person ? PERSON_COLORS[person] : null;

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-slate-800 border border-slate-700 rounded-2xl w-full max-w-lg shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-slate-700/50">
          <div className="flex-1 pr-4">
            <h2 className="text-lg font-semibold text-white leading-snug">{card.name}</h2>
            {person && colors && (
              <span className={`inline-block mt-2 text-xs font-medium px-2 py-0.5 rounded-full border ${colors.badge}`}>
                {person}
              </span>
            )}
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4">
          {card.desc && (
            <div>
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Description</div>
              <p className="text-sm text-slate-300 whitespace-pre-wrap">{card.desc}</p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            {card.due && (
              <div>
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Due Date</div>
                <div className={`text-sm font-medium ${card.dueComplete ? 'text-emerald-400 line-through' : new Date(card.due) < new Date() ? 'text-red-400' : 'text-slate-200'}`}>
                  {formatDate(card.due)}
                </div>
              </div>
            )}
            {card.start && (
              <div>
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Created</div>
                <div className="text-sm text-slate-300">{formatDate(card.start)}</div>
              </div>
            )}
          </div>

          {card.labels.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Labels</div>
              <div className="flex flex-wrap gap-1.5">
                {card.labels.map(label => (
                  <span
                    key={label.id}
                    className="text-xs px-2 py-0.5 rounded-full font-medium text-white"
                    style={{ backgroundColor: labelColorMap[label.color] || '#475569' }}
                  >
                    {label.name || label.color}
                  </span>
                ))}
              </div>
            </div>
          )}

          {card.shortUrl && (
            <div>
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Trello Link</div>
              <a
                href={card.shortUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-indigo-400 hover:text-indigo-300 underline break-all"
              >
                {card.shortUrl}
              </a>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-slate-700/50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 text-sm font-medium rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

const labelColorMap: Record<string, string> = {
  blue:   '#3b82f6',
  green:  '#22c55e',
  orange: '#f97316',
  red:    '#ef4444',
  purple: '#a855f7',
  pink:   '#ec4899',
  sky:    '#0ea5e9',
  lime:   '#84cc16',
  black:  '#1e293b',
  null:   '#475569',
};

// ─── Kanban Card ─────────────────────────────────────────────────────────────

function KanbanCard({ card, person }: { card: TrelloCard; person: string | null }) {
  const [expanded, setExpanded] = useState(false);
  const colors = person ? PERSON_COLORS[person] : null;
  const isOverdue = card.due && !card.dueComplete && new Date(card.due) < new Date();
  const descPreview = getDescPreview(card.desc);
  const meetingSource = extractMeetingSource(card.desc);

  return (
    <>
      <div
        onClick={() => setExpanded(true)}
        className={`
          bg-slate-800/70 border rounded-xl p-3.5 cursor-pointer
          transition-all duration-150 backdrop-blur
          hover:bg-slate-800/90 hover:-translate-y-0.5 hover:shadow-lg
          ${colors ? `${colors.border} border` : 'border-slate-700/50 hover:border-slate-600'}
          ${isOverdue ? 'ring-1 ring-red-500/30' : ''}
        `}
      >
        {/* Card title */}
        <p className="text-sm font-medium text-slate-200 leading-snug mb-2">{card.name}</p>

        {/* Description preview */}
        {descPreview && (
          <p className="text-xs text-slate-400 leading-relaxed mb-2 line-clamp-2">{descPreview}</p>
        )}

        {/* Meeting source badge */}
        {meetingSource && (
          <div className="flex items-center gap-1 mb-2">
            <span className="text-[10px] text-indigo-400 font-medium">📌 {meetingSource}</span>
          </div>
        )}

        {/* Labels */}
        {card.labels.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {card.labels.slice(0, 3).map(label => (
              <span
                key={label.id}
                className="text-[10px] px-1.5 py-0.5 rounded-full font-medium text-white"
                style={{ backgroundColor: labelColorMap[label.color] || '#475569' }}
              >
                {label.name || label.color}
              </span>
            ))}
          </div>
        )}

        {/* Footer row: due date + age */}
        <div className="flex items-center justify-between mt-1">
          <div className="flex items-center gap-2">
            {card.due && (
              <span className={`text-[11px] font-medium ${isOverdue ? 'text-red-400' : 'text-slate-400'}`}>
                {isOverdue ? '⚠️ ' : '📅 '}{formatDate(card.due)}
              </span>
            )}
          </div>
          {card.start && (
            <span className="text-[10px] text-slate-500">{getAge(card.start)}</span>
          )}
        </div>
      </div>

      {expanded && (
        <CardModal card={card} person={person} onClose={() => setExpanded(false)} />
      )}
    </>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

type FilterOption = 'All' | 'David Ho' | 'Codee Wong' | 'All Team';

export default function TeamTasksPage() {
  const [cards, setCards] = useState<TrelloCard[]>([]);
  const [lists, setLists] = useState<TrelloList[]>([]);
  const [members, setMembers] = useState<TrelloMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterOption>('All');
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const headers = { Authorization: `Bearer ${API_KEY}` };

      const [cardsRes, listsRes, membersRes] = await Promise.all([
        fetch(`${API_BASE}/cards?filter=all`, { headers }),
        fetch(`${API_BASE}/lists`, { headers }),
        fetch(`${API_BASE}/members`, { headers }),
      ]);

      const [cardsData, listsData, membersData] = await Promise.all([
        cardsRes.json(),
        listsRes.json(),
        membersRes.json(),
      ]);

      setCards(Array.isArray(cardsData) ? cardsData : []);
      setLists(Array.isArray(listsData) ? listsData : []);
      setMembers(Array.isArray(membersData) ? membersData : []);
      setLastRefresh(new Date());
    } catch (err) {
      setError('Failed to load data. Check your connection.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Filter cards based on person filter
  const filteredCards = cards.filter(card => {
    if (filter === 'All') return true;
    const person = detectPerson(card.idList);
    return person === filter;
  });

  // Build columns from STATUS_LISTS
  const COLUMNS: { id: string; label: string }[] = [
    { id: 'To Do',  label: 'To Do' },
    { id: 'Doing',  label: 'Doing' },
    { id: 'Done',   label: 'Done' },
  ];

  function getCardsForColumn(colId: string) {
    const listIds = STATUS_LISTS[colId];
    return filteredCards.filter(card => listIds.includes(card.idList));
  }

  const totalCards = cards.length;
  const doneCards = cards.filter(c => STATUS_LISTS['Done'].includes(c.idList)).length;
  const doingCards = cards.filter(c => STATUS_LISTS['Doing'].includes(c.idList)).length;
  const todoCards = cards.filter(c => STATUS_LISTS['To Do'].includes(c.idList)).length;

  const FILTER_OPTIONS: FilterOption[] = ['All', 'David Ho', 'Codee Wong', 'All Team'];

  return (
    <Layout>
      <div className="space-y-6">
        {/* ── Header ── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white">Team Tasks</h1>
            <p className="text-slate-400 text-sm mt-1">
              {loading
                ? 'Loading...'
                : `${totalCards} total · ${todoCards} to do · ${doingCards} doing · ${doneCards} done`
              }
            </p>
          </div>
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-colors shadow-lg shadow-indigo-900/50"
          >
            <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>

        {/* ── Error state ── */}
        {error && (
          <div className="bg-red-900/20 border border-red-800/30 rounded-xl p-4 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* ── Stats row ── */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4">
            <div className="text-2xl font-bold text-white">{todoCards}</div>
            <div className="text-xs text-slate-400 mt-0.5">To Do</div>
          </div>
          <div className="bg-amber-900/20 border border-amber-800/30 rounded-xl p-4">
            <div className="text-2xl font-bold text-amber-400">{doingCards}</div>
            <div className="text-xs text-amber-400/70 mt-0.5">In Progress</div>
          </div>
          <div className="bg-emerald-900/20 border border-emerald-800/30 rounded-xl p-4">
            <div className="text-2xl font-bold text-emerald-400">{doneCards}</div>
            <div className="text-xs text-emerald-400/70 mt-0.5">Done</div>
          </div>
        </div>

        {/* ── Person filter ── */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-slate-500 font-medium mr-1">Filter:</span>
          {FILTER_OPTIONS.map(opt => (
            <button
              key={opt}
              onClick={() => setFilter(opt)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-all ${
                filter === opt
                  ? opt === 'David Ho'    ? 'bg-blue-500/20 text-blue-400 border-blue-500/40' :
                    opt === 'Codee Wong' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40' :
                    opt === 'All Team'   ? 'bg-purple-500/20 text-purple-400 border-purple-500/40' :
                    opt === 'All'         ? 'bg-indigo-600 text-white border-indigo-500 shadow-lg shadow-indigo-900/50' : ''
                  : 'bg-slate-800/60 text-slate-400 border-slate-700 hover:border-slate-600'
              }`}
            >
              {opt}
              {opt !== 'All' && (
                <span className="ml-1.5 text-[10px] opacity-70">
                  ({cards.filter(c => detectPerson(c.idList) === opt).length})
                </span>
              )}
            </button>
          ))}

          {lastRefresh && (
            <span className="ml-auto text-[11px] text-slate-600 hidden sm:block">
              Updated {lastRefresh.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>

        {/* ── Kanban Board ── */}
        {loading ? (
          <div className="flex items-center justify-center py-24">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-slate-400">Loading tasks from Trello...</span>
            </div>
          </div>
        ) : filteredCards.length === 0 ? (
          <div className="text-center py-24">
            <div className="text-5xl mb-4">📋</div>
            <h3 className="text-slate-300 font-medium mb-1">No tasks found</h3>
            <p className="text-sm text-slate-500">
              {filter !== 'All'
                ? `No cards for ${filter} yet. Add cards in Trello to see them here.`
                : 'No cards on this board yet. Add cards in Trello to see them here.'}
            </p>
            <button
              onClick={fetchData}
              className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
            >
              Retry
            </button>
          </div>
        ) : (
          <>
            {/* Desktop: 3-column Kanban */}
            <div className="hidden md:grid md:grid-cols-3 gap-4">
              {COLUMNS.map(col => {
                const colCards = getCardsForColumn(col.id);
                const sc = STATUS_COLORS[col.id];
                return (
                  <div key={col.id} className="flex flex-col">
                    {/* Column header */}
                    <div className={`flex items-center gap-2 px-3 py-2.5 rounded-t-xl ${sc.header} border border-b-0 border-slate-700/50 mb-0`}>
                      <div className={`w-2 h-2 rounded-full ${sc.dot}`} />
                      <span className="text-sm font-semibold text-slate-200">{col.label}</span>
                      <span className="ml-auto text-xs text-slate-400 bg-slate-900/60 px-1.5 py-0.5 rounded-full">
                        {colCards.length}
                      </span>
                    </div>
                    {/* Column body */}
                    <div className={`border border-slate-700/50 rounded-b-xl p-3 space-y-2.5 min-h-48 ${sc.header.replace('bg-', 'bg-opacity-10 ')}`}
                      style={{ background: sc.header === 'bg-slate-800/60' ? 'rgba(30,41,59,0.3)' : undefined }}>
                      {colCards.length === 0 ? (
                        <div className="flex items-center justify-center h-24 text-xs text-slate-600 italic">
                          No cards
                        </div>
                      ) : (
                        colCards.map(card => {
                          const person = detectPerson(card.idList);
                          return (
                            <KanbanCard key={card.id} card={card} person={person} />
                          );
                        })
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Mobile: stacked per column */}
            <div className="md:hidden space-y-4">
              {COLUMNS.map(col => {
                const colCards = getCardsForColumn(col.id);
                if (colCards.length === 0) return null;
                const sc = STATUS_COLORS[col.id];
                return (
                  <div key={col.id} className="bg-slate-800/60 border border-slate-700/50 rounded-xl overflow-hidden">
                    <div className={`flex items-center gap-2 px-4 py-3 ${sc.header}`}>
                      <div className={`w-2 h-2 rounded-full ${sc.dot}`} />
                      <span className="text-sm font-semibold text-slate-200">{col.label}</span>
                      <span className="ml-auto text-xs text-slate-400 bg-slate-900/60 px-1.5 py-0.5 rounded-full">
                        {colCards.length}
                      </span>
                    </div>
                    <div className="p-3 space-y-2.5">
                      {colCards.map(card => {
                        const person = detectPerson(card.idList);
                        return (
                          <KanbanCard key={card.id} card={card} person={person} />
                        );
                      })}
                    </div>
                  </div>
                );
              })}
              {filteredCards.length === 0 && (
                <div className="text-center py-16 text-slate-500">
                  <div className="text-4xl mb-3">📋</div>
                  <div className="text-sm">No cards in this view</div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </Layout>
  );
}
