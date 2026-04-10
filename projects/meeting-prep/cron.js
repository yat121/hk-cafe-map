// meeting-prep/cron.js
// Cron script for Fireflies → Notion workflow
// Requires environment variables for Maton connection IDs:
//   MATON_FIRELFIES_CONN=your-fireflies-connection-id
//   MATON_NOTION_CONN=your-notion-connection-id

const https = require('https');
const { execSync } = require('child_process');

// Helper to call Maton proxy endpoint
function matonRequest(path, method = 'GET', data = null) {
  const connId = process.env.MATON_CONN_ID; // set per run
  const options = {
    hostname: 'ctrl.maton.ai',
    path: `/${path}`,
    method,
    headers: {
      'Authorization': `Bearer ${connId}`,
      'Content-Type': 'application/json',
    },
  };
  return new Promise((resolve, reject) => {
    const req = https.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => (body += chunk));
      res.on('end', () => {
        try {
          const json = JSON.parse(body);
          resolve(json);
        } catch (e) {
          reject(e);
        }
      });
    });
    req.on('error', reject);
    if (data) req.write(JSON.stringify(data));
    req.end();
  });
}

async function fetchTranscripts() {
  // Example endpoint – adjust to actual Maton Fireflies API
  return await matonRequest('fireflies/transcripts', 'GET');
}

function extractActionItems(transcript) {
  // Simple heuristic: lines starting with "Action:" or bullet list with verbs
  const lines = transcript.split('\n');
  const items = [];
  for (const line of lines) {
    if (/^Action[:\-]/i.test(line) || /\b(to|will|should)\b/i.test(line)) {
      items.push(line.trim());
    }
  }
  return items;
}

async function syncToNotion(date, items, meetingTopic) {
  const payload = {
    date,
    meetingTopic,
    items: items.map((text) => ({ text })),
  };
  // Example endpoint – adjust to actual Maton Notion API
  return await matonRequest('notion/action-items', 'POST', payload);
}

async function dailyJob() {
  const transcripts = await fetchTranscripts();
  const today = new Date().toISOString().split('T')[0];
  for (const rec of transcripts) {
    const { meetingDate, topic, transcript } = rec;
    const actionItems = extractActionItems(transcript);
    await syncToNotion(meetingDate || today, actionItems, topic || 'Untitled');
  }
  // PRODUCTION
  console.log('Daily Fireflies → Notion sync completed');
}

async function weeklyRetro() {
  // Pull all action items from Notion (placeholder)
  const all = await matonRequest('notion/action-items', 'GET');
  // Simple pattern detection – count occurrences per owner
  const summary = {};
  for (const entry of all) {
    const owner = entry.owner || 'Unassigned';
    summary[owner] = (summary[owner] || 0) + 1;
  }
  // Sync summary back to a Notion page/database for retrospectives
  await matonRequest('notion/weekly-retro', 'POST', { summary });
  // PRODUCTION
  console.log('Weekly retro synced');
}

(async () => {
  const mode = process.argv[2]; // 'daily' or 'weekly'
  if (mode === 'weekly') {
    await weeklyRetro();
  } else {
    await dailyJob();
  }
})();
