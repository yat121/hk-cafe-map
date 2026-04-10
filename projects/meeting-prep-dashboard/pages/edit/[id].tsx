'use client';
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';

type ActionItem = {
  id: string;
  person: string;
  description: string;
  dueDate: string;
  meetingDate: string;
  status: 'Pending' | 'Done';
  source: string;
};

export default function EditItem() {
  const router = useRouter();
  const { id } = router.query;
  const [form, setForm] = useState({ person: '', description: '', dueDate: '', meetingDate: '', source: '' });

  useEffect(() => {
    if (!id) return;
    fetch('/api/items')
      .then(r => r.json())
      .then((data: ActionItem[]) => {
        const found = data.find(i => i.id === id);
        if (found) {
          setForm({
            person: found.person,
            description: found.description,
            dueDate: found.dueDate,
            meetingDate: found.meetingDate,
            source: found.source
          });
        }
      });
  }, [id]);

  const handleSubmit = async (e: any) => {
    e.preventDefault();
    await fetch('/api/items', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, ...form, status: 'Pending' })
    });
    router.push('/');
  };

  return (
    <div style={{ padding: '20px', maxWidth: '600px', margin: '0 auto' }}>
      <h1>Edit Action Item</h1>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '20px' }}>
        <input name='person' placeholder='Person' value={form.person} onChange={(e: any) => setForm({ ...form, person: e.target.value })} required style={{ padding: '10px', background: '#1a1a1a', border: '1px solid #333', color: '#fff', borderRadius: '6px' }} />
        <textarea name='description' placeholder='Description' value={form.description} onChange={(e: any) => setForm({ ...form, description: e.target.value })} required style={{ padding: '10px', background: '#1a1a1a', border: '1px solid #333', color: '#fff', borderRadius: '6px', minHeight: '100px' }} />
        <input name='dueDate' type='date' value={form.dueDate} onChange={(e: any) => setForm({ ...form, dueDate: e.target.value })} required style={{ padding: '10px', background: '#1a1a1a', border: '1px solid #333', color: '#fff', borderRadius: '6px' }} />
        <input name='meetingDate' type='date' value={form.meetingDate} onChange={(e: any) => setForm({ ...form, meetingDate: e.target.value })} required style={{ padding: '10px', background: '#1a1a1a', border: '1px solid #333', color: '#fff', borderRadius: '6px' }} />
        <input name='source' placeholder='Source meeting' value={form.source} onChange={(e: any) => setForm({ ...form, source: e.target.value })} required style={{ padding: '10px', background: '#1a1a1a', border: '1px solid #333', color: '#fff', borderRadius: '6px' }} />
        <button type='submit' style={{ padding: '12px', background: '#6366f1', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>Save</button>
      </form>
    </div>
  );
}
