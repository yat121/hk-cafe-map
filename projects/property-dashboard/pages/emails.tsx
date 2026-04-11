import { useState, useEffect } from 'react';
import Head from 'next/head';
import Layout from '../components/Layout';

interface Attachment {
  id: string;
  filename: string;
  mimeType: string;
  size: number;
  url: string;
}

interface Email {
  id: string;
  subject: string;
  from: string;
  to: string;
  date: string;
  snippet: string;
  body: string;
  hasAttachments: boolean;
  attachments: Attachment[];
  labels: string[];
  property?: string;
}

const PROPERTY_NAMES: Record<string, string> = {
  'uk-casson': '🏠 Casson Square (London)',
  'uk-waterman': '🅿️ Waterman Parking (London)',
  'uk-landmark': '🏠 Landmark Pinnacle (London)',
  'hk-diecuifeng': '🏠 蝶翠峰 (Hong Kong)'
};

export default function EmailsPage() {
  const [emails, setEmails] = useState<Email[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);
  const [filterProperty, setFilterProperty] = useState<string>('all');

  useEffect(() => {
    fetchEmails();
  }, []);

  async function fetchEmails() {
    try {
      setLoading(true);
      const res = await fetch('/api/emails');
      if (!res.ok) throw new Error('Failed to fetch');
      const data = await res.json();
      setEmails(data.emails || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }

  const filteredEmails = filterProperty === 'all'
    ? emails
    : emails.filter(e => e.property === filterProperty);

  function formatDate(dateStr: string) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  }

  function formatFileSize(bytes: number) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  if (loading) {
    return (
      <Layout>
        <div style={{ textAlign: 'center', padding: '60px 20px' }}>
          <div style={{ fontSize: '2rem', marginBottom: '20px' }}>⏳</div>
          <p>Loading property emails...</p>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div style={{ textAlign: 'center', padding: '60px 20px' }}>
          <div style={{ fontSize: '2rem', marginBottom: '20px' }}>❌</div>
          <p style={{ color: '#ef4444' }}>Error: {error}</p>
          <button onClick={fetchEmails} style={{ marginTop: '20px', padding: '10px 20px', cursor: 'pointer' }}>
            Retry
          </button>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <Head>
        <title>Property Emails | Dashboard</title>
      </Head>

      <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>📧 Property Emails</h1>
          <button onClick={fetchEmails} style={{
            padding: '8px 16px',
            background: '#4f46e5',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer'
          }}>
            🔄 Refresh
          </button>
        </div>

        {/* Filter */}
        <div style={{ marginBottom: '20px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <select
            value={filterProperty}
            onChange={(e) => setFilterProperty(e.target.value)}
            style={{
              padding: '8px 12px',
              borderRadius: '6px',
              border: '1px solid #ccc',
              background: 'white',
              color: 'black'
            }}
          >
            <option value="all">All Properties</option>
            {Object.entries(PROPERTY_NAMES).map(([id, name]) => (
              <option key={id} value={id}>{name}</option>
            ))}
          </select>
          <span style={{ color: '#6b7288', alignSelf: 'center' }}>
            {filteredEmails.length} email{filteredEmails.length !== 1 ? 's' : ''} found
          </span>
        </div>

        {filteredEmails.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: '#6b7288' }}>
            <div style={{ fontSize: '3rem', marginBottom: '20px' }}>📭</div>
            <p>No property-related emails found</p>
            <p style={{ fontSize: '0.875rem', marginTop: '10px' }}>
              Emails with property keywords (rent, lease, JLL, tenant, etc.) will appear here
            </p>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            {/* Email List */}
            <div style={{ background: 'white', borderRadius: '12px', overflow: 'hidden' }}>
              {filteredEmails.map((email) => (
                <div
                  key={email.id}
                  onClick={() => setSelectedEmail(email)}
                  style={{
                    padding: '16px',
                    borderBottom: '1px solid #e5e7eb',
                    cursor: 'pointer',
                    background: selectedEmail?.id === email.id ? '#f3f4f6' : 'transparent'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontWeight: '600', fontSize: '0.875rem', color: '#111827' }}>
                      {email.from.split('<')[0].trim() || email.from}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: '#6b7288' }}>
                      {formatDate(email.date)}
                    </span>
                  </div>
                  <div style={{ fontWeight: '500', marginBottom: '4px', color: '#374151' }}>
                    {email.subject}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#6b7288', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {email.snippet}
                  </div>
                  <div style={{ display: 'flex', gap: '10px', marginTop: '8px', flexWrap: 'wrap' }}>
                    {email.property && (
                      <span style={{
                        fontSize: '0.7rem',
                        padding: '2px 8px',
                        background: '#dbeafe',
                        color: '#1e40af',
                        borderRadius: '4px'
                      }}>
                        {PROPERTY_NAMES[email.property] || email.property}
                      </span>
                    )}
                    {email.hasAttachments && (
                      <span style={{
                        fontSize: '0.7rem',
                        padding: '2px 8px',
                        background: '#fef3c7',
                        color: '#92400e',
                        borderRadius: '4px'
                      }}>
                        📎 {email.attachments.length} attachment{email.attachments.length !== 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Email Detail */}
            <div style={{ background: 'white', borderRadius: '12px', padding: '20px' }}>
              {selectedEmail ? (
                <div>
                  <h2 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '16px' }}>
                    {selectedEmail.subject}
                  </h2>
                  <div style={{ fontSize: '0.875rem', color: '#6b7288', marginBottom: '16px' }}>
                    <div><strong>From:</strong> {selectedEmail.from}</div>
                    <div><strong>To:</strong> {selectedEmail.to}</div>
                    <div><strong>Date:</strong> {formatDate(selectedEmail.date)}</div>
                  </div>
                  <div
                    style={{
                      padding: '16px',
                      background: '#f9fafb',
                      borderRadius: '8px',
                      marginBottom: '16px',
                      maxHeight: '300px',
                      overflow: 'auto',
                      fontSize: '0.875rem',
                      lineHeight: '1.6'
                    }}
                  >
                    {selectedEmail.snippet}
                  </div>

                  {/* Attachments */}
                  {selectedEmail.hasAttachments && (
                    <div>
                      <h3 style={{ fontSize: '0.875rem', fontWeight: '600', marginBottom: '10px' }}>
                        📎 Attachments ({selectedEmail.attachments.length})
                      </h3>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {selectedEmail.attachments.map((att) => (
                          <a
                            key={att.id}
                            href={att.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              padding: '10px 12px',
                              background: '#f3f4f6',
                              borderRadius: '6px',
                              textDecoration: 'none',
                              color: '#374151',
                              fontSize: '0.875rem'
                            }}
                          >
                            <span>📄 {att.filename}</span>
                            <span style={{ color: '#6b7288' }}>{formatFileSize(att.size)}</span>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '60px 20px', color: '#6b7288' }}>
                  <div style={{ fontSize: '2rem', marginBottom: '10px' }}>👈</div>
                  <p>Select an email to view details</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <style jsx global>{`
        body { background: #f3f4f6; margin: 0; }
      `}</style>
    </Layout>
  );
}
