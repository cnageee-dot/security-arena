// TinyBoard - a fictional team notice board used only as a test fixture for
// Security Arena. Contains intentional weaknesses. Do NOT deploy.
// All names, passwords and keys below are made up.
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { URL } = require('url');

const HOST = '127.0.0.1';
const PORT = 8080;
const UPLOAD_DIR = path.join(__dirname, 'uploads');
const SIGNING_KEY = process.env.TINYBOARD_SIGNING_KEY;
if (!SIGNING_KEY) {
  console.error('TINYBOARD_SIGNING_KEY is required');
  process.exit(1);
}

const md5 = (s) => crypto.createHash('md5').update(s).digest('hex');

const users = [
  { id: 1, name: 'alice', email: 'alice@example.test', role: 'admin', passwordHash: md5('alice-demo-pass') },
  { id: 2, name: 'bob', email: 'bob@example.test', role: 'member', passwordHash: md5('bob-demo-pass') },
];

const notes = [
  { id: 1, ownerId: 1, title: 'Budget draft', body: 'Fictional budget numbers.' },
  { id: 2, ownerId: 2, title: 'Lunch plan', body: 'Pizza on Friday.' },
  { id: 3, ownerId: 1, title: 'Admin todo', body: 'Rotate the demo keys.' },
];

function sign(userId) {
  const mac = crypto.createHmac('sha256', SIGNING_KEY).update(String(userId)).digest('hex');
  return `${userId}.${mac}`;
}

function authUser(req) {
  const header = req.headers['authorization'] || '';
  const token = header.replace(/^Bearer /, '');
  const [id, mac] = token.split('.');
  if (!id || !mac) return null;
  const expected = sign(id).split('.')[1];
  if (mac !== expected) return null;
  return users.find((u) => String(u.id) === id) || null;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function sendJson(res, status, obj) {
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(obj));
}

function readBody(req) {
  return new Promise((resolve) => {
    let data = '';
    req.on('data', (c) => (data += c));
    req.on('end', () => resolve(data));
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${HOST}:${PORT}`);
  const p = url.pathname;

  if (req.method === 'POST' && p === '/login') {
    let body;
    try { body = JSON.parse(await readBody(req)); } catch { return sendJson(res, 400, { error: 'bad json' }); }
    const user = users.find((u) => u.name === body.name && u.passwordHash === md5(body.password || ''));
    if (!user) return sendJson(res, 401, { error: 'invalid credentials' });
    return sendJson(res, 200, { token: sign(user.id) });
  }

  const user = authUser(req);

  if (p === '/api/notes' && req.method === 'GET') {
    if (!user) return sendJson(res, 401, { error: 'login required' });
    return sendJson(res, 200, notes.filter((n) => n.ownerId === user.id));
  }

  const noteMatch = p.match(/^\/api\/notes\/(\d+)$/);
  if (noteMatch && req.method === 'GET') {
    if (!user) return sendJson(res, 401, { error: 'login required' });
    const note = notes.find((n) => n.id === Number(noteMatch[1]));
    if (!note || note.ownerId !== user.id) return sendJson(res, 404, { error: 'not found' });
    return sendJson(res, 200, note);
  }

  if (p === '/api/users' && req.method === 'GET') {
    if (!user) return sendJson(res, 401, { error: 'login required' });
    return sendJson(res, 200, users.map((u) => ({ id: u.id, name: u.name })));
  }

  if (p === '/search' && req.method === 'GET') {
    const q = url.searchParams.get('q') || '';
    res.writeHead(200, { 'Content-Type': 'text/html' });
    return res.end(`<h1>Results for ${escapeHtml(q)}</h1><p>No notices match.</p>`);
  }

  if (p === '/profile' && req.method === 'GET') {
    const name = url.searchParams.get('name') || '';
    res.writeHead(200, { 'Content-Type': 'text/html' });
    return res.end(`<h1>Profile: ${escapeHtml(name)}</h1>`);
  }

  if (p === '/files' && req.method === 'GET') {
    const name = url.searchParams.get('name') || '';
    const target = path.resolve(UPLOAD_DIR, name);
    if (!target.startsWith(UPLOAD_DIR + path.sep)) return sendJson(res, 404, { error: 'not found' });
    return fs.readFile(target, (err, data) => {
      if (err) return sendJson(res, 404, { error: 'not found' });
      res.writeHead(200, { 'Content-Type': 'application/octet-stream' });
      res.end(data);
    });
  }

  if (p === '/avatar' && req.method === 'GET') {
    const name = path.basename(url.searchParams.get('name') || '');
    return fs.readFile(path.join(UPLOAD_DIR, 'avatars', name), (err, data) => {
      if (err) return sendJson(res, 404, { error: 'not found' });
      res.writeHead(200, { 'Content-Type': 'image/png' });
      res.end(data);
    });
  }

  sendJson(res, 404, { error: 'not found' });
});

server.listen(PORT, HOST, () => console.log(`TinyBoard on http://${HOST}:${PORT}`));
