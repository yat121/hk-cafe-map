'use client';
import { useState } from 'react';
import Layout from '../components/Layout';

type Meeting = {
  id: string;
  title: string;
  date: string;
  time: string;
  attendees: string[];
  source: string;
  actionCount: number;
  status: 'upcoming' | 'completed';
};

const sampleMeetings: Meeting[] = [
  { id: '1', title: 'Strategy Planning Session', date: '2025-04-10', time: '10:00', attendees: ['Alex Chen', 'Sarah Miller', 'David Kim'], source: 'Weekly', actionCount: 3, status: 'upcoming' },
  { id: '2', title: 'Operations Sync', date: '2025-04-09', time: '14:00', attendees: ['Sarah Miller', 'James Park'], source: 'Bi-weekly', actionCount: 2, status: 'upcoming' },
  { id: '3', title: 'Board Prep Meeting', date: '2025-04-14', time: '09:00', attendees: ['James Park', 'Emma Wilson', 'Lisa Wong'], source: 'Monthly', actionCount: 4, status: 'upcoming' },
  { id: '4', title: 'Tech Review', date: '2025-04-11', time: '15:00', attendees: ['Lisa Wong', 'David Kim'], source: 'Weekly', actionCount: 1, status: 'upcoming' },
  { id: '5', title: 'Product Sync', date: '2025-04-16', time: '11:00', attendees: ['Emma Wilson', 'Alex Chen', 'James Park'], source: 'Weekly', actionCount: 2, status: 'upcoming' },
  { id: '6', title: 'Budget Meeting', date: '2025-04-08', time: '10:00', attendees: ['David Kim', 'Sarah Miller'], source: 'Monthly', actionCount: 1, status: 'completed' },
  { id: '7', title: 'Investor Update', date: '2025-04-05', time: '09:00', attendees: ['James Park', 'Alex Chen'], source: 'Quarterly', actionCount: 0, status: 'completed' },
];

export default function MeetingsPage() {
  const [filter, setFilter] = useState<'all' | 'upcoming' | 'completed'>('all');
  const [showAdd, setShowAdd] = useState(false);
  const [newMeeting, setNewMeeting] = useState({ title: '', date: '', time: '', attendees: '', source: '' });

  const filtered = sampleMeetings.filter(m => filter === 'all' || m.status === filter);

  const addMeeting = (e: React.FormEvent) => {
    e.preventDefault();
    setShowAdd(false);
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Meetings</h1>
            <p className="text-slate-400 text-sm mt-1">
              {sampleMeetings.filter(m => m.status === 'upcoming').length} upcoming · {sampleMeetings.filter(m => m.status === 'completed').length} completed
            </p>
          </div>
          <button
            onClick={() => setShowAdd(true)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg transition-colors shadow-lg shadow-indigo-900/50"
          >
            + New Meeting
          </button>
        </div>

        {/* Filter tabs */}
        <div className="flex gap-1 bg-slate-800/60 border border-slate-700/50 rounded-xl p-1 w-fit">
          {(['all', 'upcoming', 'completed'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-colors capitalize ${
                filter === f ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        {/* Add form */}
        {showAdd && (
          <div className="bg-slate-800/70 border border-slate-700/50 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">Schedule New Meeting</h3>
            <form onSubmit={addMeeting} className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <input
                  placeholder='Meeting title'
                  value={newMeeting.title}
                  onChange={e => setNewMeeting({...newMeeting, title: e.target.value})}
                  required
                  className="w-full px-3 py-2 bg-slate-900/80 border border-slate-600 text-slate-200 rounded-lg text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
                <input
                  placeholder='Source / recurring'
                  value={newMeeting.source}
                  onChange={e => setNewMeeting({...newMeeting, source: e.target.value})}
                  className="w-full px-3 py-2 bg-slate-900/80 border border-slate-600 text-slate-200 rounded-lg text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
                <input
                  type='date'
                  value={newMeeting.date}
                  onChange={e => setNewMeeting({...newMeeting, date: e.target.value})}
                  required
                  className="w-full px-3 py-2 bg-slate-900/80 border border-slate-600 text-slate-200 rounded-lg text-sm focus:outline-none focus:border-indigo-500"
                />
                <input
                  type='time'
                  value={newMeeting.time}
                  onChange={e => setNewMeeting({...newMeeting, time: e.target.value})}
                  required
                  className="w-full px-3 py-2 bg-slate-900/80 border border-slate-600 text-slate-200 rounded-lg text-sm focus:outline-none focus:border-indigo-500"
                />
                <input
                  placeholder='Attendees (comma separated)'
                  value={newMeeting.attendees}
                  onChange={e => setNewMeeting({...newMeeting, attendees: e.target.value})}
                  className="w-full px-3 py-2 bg-slate-900/80 border border-slate-600 text-slate-200 rounded-lg text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500 sm:col-span-2"
                />
              </div>
              <div className="flex gap-2">
                <button type='submit' className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg transition-colors">Add Meeting</button>
                <button type='button' onClick={() => setShowAdd(false)} className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm font-medium rounded-lg transition-colors">Cancel</button>
              </div>
            </form>
          </div>
        )}

        {/* Meeting cards */}
        <div className="space-y-3">
          {filtered.length === 0 && (
            <div className="text-center py-16 text-slate-500">
              <div className="text-4xl mb-3">📅</div>
              <div className="text-sm">No meetings found</div>
            </div>
          )}
          {filtered.map(meeting => {
            const isUpcoming = meeting.status === 'upcoming';
            const meetingDate = new Date(meeting.date + 'T00:00:00');
            const isToday = meetingDate.toDateString() === new Date().toDateString();
            const isSoon = isUpcoming && meetingDate <= new Date(Date.now() + 3 * 86400000);

            return (
              <div
                key={meeting.id}
                className={`bg-slate-800/60 border rounded-xl p-4 backdrop-blur transition-all hover:bg-slate-800/80 ${
                  isSoon && isToday ? 'border-amber-600/50' :
                  isSoon ? 'border-indigo-800/50' :
                  isUpcoming ? 'border-slate-700/50' : 'border-slate-700/30'
                }`}
              >
                <div className="flex items-start gap-4">
                  {/* Date badge */}
                  <div className={`flex-shrink-0 w-14 h-14 rounded-xl flex flex-col items-center justify-center text-sm font-bold ${
                    isToday ? 'bg-amber-500 text-black' :
                    isUpcoming ? 'bg-indigo-600 text-white' : 'bg-slate-700 text-slate-400'
                  }`}>
                    <div className="text-[10px] uppercase tracking-wide opacity-80">{meetingDate.toLocaleString('default', { month: 'short' })}</div>
                    <div>{meetingDate.getDate()}</div>
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h3 className={`font-semibold text-sm ${isUpcoming ? 'text-white' : 'text-slate-400'}`}>{meeting.title}</h3>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs text-slate-400">{meeting.time}</span>
                          <span className="text-slate-600 text-xs">·</span>
                          <span className="text-xs text-slate-500">{meeting.source}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {meeting.actionCount > 0 && (
                          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                            isUpcoming ? 'bg-indigo-900/50 text-indigo-300 border border-indigo-700/50' : 'bg-slate-700 text-slate-400'
                          }`}>
                            {meeting.actionCount} action{meeting.actionCount !== 1 ? 's' : ''}
                          </span>
                        )}
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                          isUpcoming ? 'bg-emerald-900/50 text-emerald-400' : 'bg-slate-700 text-slate-400'
                        }`}>
                          {isUpcoming ? 'Upcoming' : 'Completed'}
                        </span>
                      </div>
                    </div>

                    {/* Attendees */}
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {meeting.attendees.map(a => (
                        <span key={a} className="text-xs bg-slate-700/80 text-slate-300 px-2 py-0.5 rounded-full">
                          {a}
                        </span>
                      ))}
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
