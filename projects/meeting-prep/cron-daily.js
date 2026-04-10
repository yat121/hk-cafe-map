// cron-daily.js
// Pull Fireflies transcripts, extract action items, sync to Notion, and output briefing

const fetch = globalThis.fetch;
const fs = require('fs');

const MATON_API_KEY = process.env.MATON_API_KEY;
if (!MATON_API_KEY) {
  console.error('MATON_API_KEY not set');
  process.exit(1);
}

const FIREFLIES_URL = 'https://gateway.maton.ai/fireflies/graphql';
const NOTION_URL = 'https://gateway.maton.ai/notion/v1';

// Parent page for meeting notes (n8n AI Personal Assistant)
const NOTION_PARENT_PAGE = '30f24618-bb0c-815e-9b69-ec17ba720405';

async function firefliesQuery(query) {
  const res = await fetch(FIREFLIES_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${MATON_API_KEY}`,
    },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error(`Fireflies request failed: ${res.status}`);
  const json = await res.json();
  if (json.errors) throw new Error(JSON.stringify(json.errors));
  return json.data;
}

async function notionCreatePage(page) {
  const res = await fetch(`${NOTION_URL}/pages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${MATON_API_KEY}`,
    },
    body: JSON.stringify(page),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Notion create failed: ${res.status} - ${err}`);
  }
  return await res.json();
}

// Extract action items from sentences
function extractActions(transcript) {
  const patterns = [
    /can you\s+.*\?/i,
    /i will\s+.*\./i,
    /i'll\s+.*\./i,
    /should\s+.*\./i,
    /need to\s+.*\./i,
    /follow up\s+.*\./i,
    /i think\s+.*\./i,
    /you (can|should|need to|will)\s+.*\./i,
  ];
  const actions = [];
  for (const s of transcript.sentences || []) {
    if (!s.text || s.text.trim().length < 10) continue;
    if (!s.speaker_name || s.speaker_name === 'null') continue;
    for (const p of patterns) {
      if (p.test(s.text)) {
        const clean = s.text.trim().replace(/\n/g, ' ').substring(0, 200);
        actions.push({ speaker: s.speaker_name, text: clean });
        break;
      }
    }
  }
  return actions;
}

function formatDate(ts) {
  return new Date(ts).toLocaleDateString('en-GB', {
    weekday: 'short', day: 'numeric', month: 'short', year: 'numeric'
  });
}

// Build Notion page for a single meeting
function buildMeetingPage(transcript, actions) {
  const date = formatDate(transcript.date);
  const participantList = (transcript.participants || []).join(', ');

  const children = [
    {
      object: 'block',
      type: 'callout',
      callout: {
        icon: { emoji: '📅' },
        rich_text: [{ text: { content: `Date: ${date} | Duration: ${Math.round(transcript.duration)} min` } }]
      }
    },
    {
      object: 'block',
      type: 'callout',
      callout: {
        icon: { emoji: '👥' },
        rich_text: [{ text: { content: `Participants: ${participantList}` } }]
      }
    },
    {
      object: 'block',
      type: 'heading_2',
      heading_2: { rich_text: [{ text: { content: '🎯 Action Items' } }] }
    },
    ...actions.map((act, i) => ({
      object: 'block',
      type: 'to_do',
      to_do: {
        checked: false,
        rich_text: [{
          text: { content: `[${act.speaker}] ${act.text}` }
        }]
      }
    }))
  ];

  return {
    parent: { page_id: NOTION_PARENT_PAGE },
    properties: {
      title: {
        title: [{ text: { content: `📋 ${transcript.title} (${date})` } }]
      }
    },
    children
  };
}

(async () => {
  try {
    const query = `query { transcripts(limit: 20) { id title date duration participants organizer_email sentences { text speaker_name } } }`;
    const data = await firefliesQuery(query);
    const transcripts = (data.transcripts || []).filter(t => t.sentences && t.sentences.length > 0);

    // PRODUCTION
  console.log(`\n🔥 FIREFLIES DAILY BRIEFING — ${new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}`);
    // PRODUCTION
  console.log(`Found ${transcripts.length} meetings\n`);

    let totalActions = 0;
    for (const t of transcripts) {
      const actions = extractActions(t);
      if (!actions.length) continue;

      totalActions += actions.length;
      // PRODUCTION
  console.log(`\n📅 ${t.title}`);
      // PRODUCTION
  console.log(`   ${formatDate(t.date)} | ${Math.round(t.duration)} min | ${t.participants.length} participants`);
      // PRODUCTION
  console.log(`   👥 ${t.participants.join(', ')}`);
      // PRODUCTION
  console.log(`   ─── ${actions.length} action item(s)`);
      actions.forEach((a, i) => {
        // PRODUCTION
  console.log(`   ${i + 1}. [${a.speaker}] ${a.text}`);
      });

      // Create Notion page
      try {
        const page = buildMeetingPage(t, actions);
        await notionCreatePage(page);
        // PRODUCTION
  console.log(`   ✅ Synced to Notion`);
        await new Promise(r => setTimeout(r, 500)); // rate limit
      } catch (e) {
        // PRODUCTION
  console.log(`   ⚠️ Notion sync failed: ${e.message.substring(0, 80)}`);
      }
    }

    if (totalActions === 0) {
      // PRODUCTION
  console.log('No action items found today. Either no meetings or no tasks assigned.');
    } else {
      // PRODUCTION
  console.log(`\n\n✅ Total: ${transcripts.length} meeting(s), ${totalActions} action item(s) synced to Notion`);
    }
  } catch (err) {
    console.error('Error:', err.message);
    process.exit(1);
  }
})();
