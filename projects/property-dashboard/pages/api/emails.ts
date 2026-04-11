import type { NextApiRequest, NextApiResponse } from 'next';

const MATON_API_KEY = process.env.MATON_API_KEY || 'D2RGPr7Xov0s0fhqULJATtI9h8GjEhwj8OlCUJkQ08Lza8x2313VQdWKWBbF_HNKTXHdl5oR3YA1wwS2b6cts0Cps3clrCO25U0';

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

interface Attachment {
  id: string;
  filename: string;
  mimeType: string;
  size: number;
  url: string;
}

const PROPERTY_KEYWORDS = [
  'property', 'rent', 'lease', 'tenant', '租金', '租約', '物業',
  'jll', 'ground rent', 'service charge', 'tenancy', 'renewal',
  ' квартира', 'london', 'hong kong', 'die cui', 'landmark',
  'casson', 'waterman', '蝶翠峰', 'property management'
];

function extractPropertyKeywords(body: string): string | undefined {
  const lower = body.toLowerCase();
  if (lower.includes('casson')) return 'uk-casson';
  if (lower.includes('waterman')) return 'uk-waterman';
  if (lower.includes('landmark')) return 'uk-landmark';
  if (lower.includes('die cui') || lower.includes('蝶翠峰')) return 'hk-diecuifeng';
  return undefined;
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Fetch emails from Gmail via Maton
    const response = await fetch('https://gateway.maton.ai/gmail/messages', {
      headers: {
        'Authorization': `Bearer ${MATON_API_KEY}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error(`Maton API error: ${response.status}`);
    }

    const data = await response.json();
    const messages = data.messages || [];

    // Process and filter emails
    const propertyEmails: Email[] = [];

    for (const msg of messages.slice(0, 50)) {
      try {
        const detailRes = await fetch(`https://gateway.maton.ai/gmail/messages/${msg.id}`, {
          headers: { 'Authorization': `Bearer ${MATON_API_KEY}` }
        });

        if (!detailRes.ok) continue;

        const detail = await detailRes.json();
        const email = detail;

        // Check if property-related
        const searchText = `${email.subject || ''} ${email.snippet || ''}`.toLowerCase();
        const isPropertyRelated = PROPERTY_KEYWORDS.some(kw => searchText.includes(kw));

        if (!isPropertyRelated) continue;

        // Extract attachments
        const attachments: Attachment[] = [];
        if (email.attachments) {
          for (const att of email.attachments) {
            attachments.push({
              id: att.id || att.filename,
              filename: att.filename,
              mimeType: att.mimeType || 'application/octet-stream',
              size: att.size || 0,
              url: att.url || `#attachment-${att.id || att.filename}`
            });
          }
        }

        propertyEmails.push({
          id: email.id,
          subject: email.subject || '(No subject)',
          from: email.from || '',
          to: email.to || '',
          date: email.date || email.internalDate || new Date().toISOString(),
          snippet: email.snippet || '',
          body: email.body || email.html || '',
          hasAttachments: attachments.length > 0,
          attachments,
          labels: email.labels || [],
          property: extractPropertyKeywords(`${email.subject || ''} ${email.snippet || ''}`)
        });
      } catch (e) {
        console.error(`Error processing email ${msg.id}:`, e);
      }
    }

    // Sort by date descending
    propertyEmails.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

    res.status(200).json({
      emails: propertyEmails,
      total: propertyEmails.length,
      fetchedAt: new Date().toISOString()
    });

  } catch (error) {
    console.error('Gmail fetch error:', error);
    res.status(500).json({ 
      error: 'Failed to fetch emails',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
}
