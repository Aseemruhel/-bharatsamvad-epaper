// Cloudflare Pages Function — Poll API backed by KV
// Route: /api/poll
//
// GET  /api/poll?id=POLL_ID            -> { id, counts: {optionId: n, ...} }
// POST /api/poll  body {id, option}    -> records one vote, returns updated counts
//
// Requires a KV namespace binding named  POLLS  (set in the Cloudflare dashboard).
// Votes are stored as one JSON object per poll under key  "poll:<id>".

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });

async function readPoll(env, id) {
  const raw = await env.POLLS.get("poll:" + id);
  return raw ? JSON.parse(raw) : { id, counts: {} };
}

export async function onRequestGet({ request, env }) {
  if (!env.POLLS) return json({ error: "KV not bound" }, 500);
  const id = new URL(request.url).searchParams.get("id");
  if (!id) return json({ error: "missing id" }, 400);
  const poll = await readPoll(env, id);
  return json(poll);
}

export async function onRequestPost({ request, env }) {
  if (!env.POLLS) return json({ error: "KV not bound" }, 500);
  let body;
  try { body = await request.json(); } catch { return json({ error: "bad json" }, 400); }
  const { id, option } = body || {};
  if (!id || !option) return json({ error: "missing id or option" }, 400);

  // basic sanity limits
  if (String(id).length > 60 || String(option).length > 60) return json({ error: "too long" }, 400);

  const poll = await readPoll(env, id);
  poll.counts[option] = (poll.counts[option] || 0) + 1;
  await env.POLLS.put("poll:" + id, JSON.stringify(poll));
  return json(poll);
}
