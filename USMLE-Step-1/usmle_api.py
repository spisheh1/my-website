#!/usr/bin/env python3
"""
USMLE Step 1 — Server-side API
Stores all user accounts and progress on the server.
Runs on port 8081. Nginx proxies /usmle-api/ to it.
"""

from flask import Flask, request, jsonify
import json, os, secrets, time, hashlib

app = Flask(__name__)

DATA_DIR = '/home/ubuntu/usmle_data'
SESSIONS  = {}   # token -> {username, created}

os.makedirs(DATA_DIR, exist_ok=True)

# ── helpers ──────────────────────────────────────────────────────────
def user_file(u):
    return os.path.join(DATA_DIR, u + '.json')

def load_user(u):
    f = user_file(u)
    if os.path.exists(f):
        with open(f) as fp:
            return json.load(fp)
    return None

def save_user(d):
    with open(user_file(d['username']), 'w') as fp:
        json.dump(d, fp, indent=2)

def hp(p):   # hash password
    return hashlib.sha256(p.encode()).hexdigest()

def get_token():
    a = request.headers.get('Authorization','')
    return a[7:] if a.startswith('Bearer ') else ''

def auth():
    token = get_token()
    sess  = SESSIONS.get(token)
    if not sess:
        return None
    if time.time() - sess['created'] > 86400:   # 24-hour sessions
        SESSIONS.pop(token, None)
        return None
    return sess['username']

# ── seed default users once ───────────────────────────────────────────
for _u, _p, _r, _n in [('vice','vice','admin','Admin'), ('sam','sam','user','Sam')]:
    if not os.path.exists(user_file(_u)):
        save_user({'username':_u, 'password':hp(_p), 'role':_r,
                   'status':'approved', 'name':_n,
                   'created':time.time(), 'progress':{}})

# ── CORS ──────────────────────────────────────────────────────────────
@app.after_request
def cors(r):
    r.headers['Access-Control-Allow-Origin']  = '*'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    r.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return r

@app.route('/usmle-api/<path:p>', methods=['OPTIONS'])
def options(p): return '', 204

# ── auth endpoints ────────────────────────────────────────────────────
@app.route('/usmle-api/login', methods=['POST'])
def login():
    d  = request.json or {}
    u  = d.get('username','').lower().strip()
    p  = d.get('password','')
    if not u or not p:
        return jsonify(error='Missing credentials'), 400
    user = load_user(u)
    if not user:
        return jsonify(error='Account not found'), 401
    if user.get('status') == 'pending':
        return jsonify(error='Account awaiting admin approval'), 403
    if user.get('status') == 'rejected':
        return jsonify(error='Account not approved'), 403
    if user.get('password') != hp(p):
        return jsonify(error='Incorrect password'), 401
    token = secrets.token_hex(32)
    SESSIONS[token] = {'username': u, 'created': time.time()}
    return jsonify(token=token, username=u,
                   role=user.get('role','user'), name=user.get('name',u))

@app.route('/usmle-api/logout', methods=['POST'])
def logout():
    SESSIONS.pop(get_token(), None)
    return jsonify(ok=True)

@app.route('/usmle-api/register', methods=['POST'])
def register():
    d    = request.json or {}
    u    = d.get('username','').lower().strip()
    p    = d.get('password','')
    name = d.get('name', u).strip()
    if not u or not p or not name:
        return jsonify(error='Missing fields'), 400
    if len(u) < 3:
        return jsonify(error='Username must be at least 3 characters'), 400
    if len(p) < 4:
        return jsonify(error='Password must be at least 4 characters'), 400
    if load_user(u):
        return jsonify(error='Username already taken'), 409
    save_user({'username':u, 'password':hp(p), 'role':'user',
               'status':'pending', 'name':name,
               'created':time.time(), 'progress':{}})
    return jsonify(ok=True, message='Account submitted for approval')

# ── progress endpoints ────────────────────────────────────────────────
@app.route('/usmle-api/progress', methods=['GET'])
def get_progress():
    u = auth()
    if not u: return jsonify(error='Unauthorized'), 401
    user = load_user(u)
    return jsonify(progress=user.get('progress',{}))

@app.route('/usmle-api/progress', methods=['POST'])
def save_progress():
    u = auth()
    if not u: return jsonify(error='Unauthorized'), 401
    d    = request.json or {}
    user = load_user(u)
    user['progress']  = d.get('progress', {})
    user['updatedAt'] = time.time()
    save_user(user)
    return jsonify(ok=True)

# ── admin endpoints ───────────────────────────────────────────────────
@app.route('/usmle-api/admin/users', methods=['GET'])
def admin_users():
    u = auth()
    if not u: return jsonify(error='Unauthorized'), 401
    if load_user(u).get('role') != 'admin':
        return jsonify(error='Forbidden'), 403
    users = []
    for f in os.listdir(DATA_DIR):
        if f.endswith('.json'):
            with open(os.path.join(DATA_DIR, f)) as fp:
                ud = json.load(fp)
            users.append({k:v for k,v in ud.items()
                          if k not in ('password','progress')})
    return jsonify(users=users)

@app.route('/usmle-api/admin/approve', methods=['POST'])
def admin_approve():
    u = auth()
    if not u: return jsonify(error='Unauthorized'), 401
    if load_user(u).get('role') != 'admin':
        return jsonify(error='Forbidden'), 403
    d      = request.json or {}
    target = load_user(d.get('username',''))
    if not target: return jsonify(error='User not found'), 404
    target['status'] = d.get('status','approved')
    save_user(target)
    return jsonify(ok=True)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8081, debug=False)
