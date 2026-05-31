from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import warnings
import sqlite3
import secrets
import os
import sys
import random
import string
import time
import threading
from datetime import datetime, timedelta
from functools import wraps
import requests
import urllib3

warnings.filterwarnings('ignore')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import agen

app = Flask(__name__)
CORS(app)

# ============ CONFIG ============
WATERMARK = "TikTok @qrnlay"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
API_DOMAIN = os.environ.get('API_DOMAIN', 'https://accang-api.vercel.app')
DEFAULT_NAME_PREFIX = "shuoi-"
DEFAULT_PASS_PREFIX = "shu"
DEFAULT_REGION = "ID"

# ============ DATABASE ============
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_keys.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT UNIQUE NOT NULL,
            owner_name TEXT NOT NULL,
            email TEXT,
            plan TEXT DEFAULT 'basic',
            max_requests INTEGER DEFAULT -1,
            requests_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            notes TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS request_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT,
            endpoint TEXT,
            status TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            user_agent TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS generated_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT,
            uid TEXT,
            account_id TEXT,
            password TEXT,
            name TEXT,
            region TEXT,
            is_same_digit BOOLEAN,
            same_digit_count INTEGER,
            same_digit_reason TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def create_api_key(owner_name, email, plan, max_requests, expiry_days, notes):
    conn = get_db()
    cursor = conn.cursor()
    api_key = secrets.token_urlsafe(32)
    
    if max_requests == -1:
        if plan == 'basic':
            max_requests = 1000
        elif plan == 'premium':
            max_requests = 10000
        else:
            max_requests = -1
    
    expires_at = None
    if expiry_days > 0:
        expires_at = (datetime.now() + timedelta(days=expiry_days)).isoformat()
    
    cursor.execute('''
        INSERT INTO api_keys (api_key, owner_name, email, plan, max_requests, expires_at, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (api_key, owner_name, email, plan, max_requests, expires_at, notes))
    
    conn.commit()
    conn.close()
    return api_key

def validate_api_key(api_key):
    if not api_key:
        return None
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, owner_name, plan, max_requests, requests_used, expires_at, is_active FROM api_keys WHERE api_key = ?', (api_key,))
    key_data = cursor.fetchone()
    
    if not key_data:
        conn.close()
        return None
    
    key_id, owner_name, plan, max_req, used_req, expires_at, is_active = key_data
    
    if expires_at:
        expires_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        if datetime.now() > expires_date:
            conn.close()
            return None
    
    if not is_active:
        conn.close()
        return None
    
    if max_req != -1 and used_req >= max_req:
        conn.close()
        return None
    
    cursor.execute('UPDATE api_keys SET requests_used = requests_used + 1 WHERE api_key = ?', (api_key,))
    conn.commit()
    conn.close()
    
    return {
        'id': key_id,
        'owner_name': owner_name,
        'plan': plan,
        'max_requests': max_req,
        'requests_used': used_req + 1,
        'remaining': -1 if max_req == -1 else max_req - (used_req + 1)
    }

def log_request(api_key, endpoint, status, ip_address, user_agent):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO request_logs (api_key, endpoint, status, ip_address, user_agent) VALUES (?, ?, ?, ?, ?)', 
                   (api_key, endpoint, status, ip_address, user_agent))
    conn.commit()
    conn.close()

def log_account(api_key, uid, account_id, password, name, region, is_same_digit, same_digit_count, same_digit_reason):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO generated_accounts (api_key, uid, account_id, password, name, region, is_same_digit, same_digit_count, same_digit_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (api_key, uid, account_id, password, name, region, is_same_digit, same_digit_count, same_digit_reason))
    conn.commit()
    conn.close()

def get_key_info(api_key):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT owner_name, plan, max_requests, requests_used, created_at, expires_at, is_active FROM api_keys WHERE api_key = ?', (api_key,))
    result = cursor.fetchone()
    conn.close()
    return dict(result) if result else None

def get_all_keys():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT api_key, owner_name, email, plan, max_requests, requests_used, created_at, expires_at, is_active, notes FROM api_keys ORDER BY created_at DESC')
    keys = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return keys

def toggle_key(api_key, activate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE api_keys SET is_active = ? WHERE api_key = ?', (1 if activate else 0, api_key))
    conn.commit()
    conn.close()

def delete_key(api_key):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM api_keys WHERE api_key = ?', (api_key,))
    conn.commit()
    conn.close()

def get_logs(limit=100):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT timestamp, api_key, endpoint, status, ip_address FROM request_logs ORDER BY timestamp DESC LIMIT ?', (limit,))
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return logs

def get_system_stats():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM api_keys')
    total_keys = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM api_keys WHERE is_active = 1')
    active_keys = cursor.fetchone()[0]
    cursor.execute('SELECT SUM(requests_used) FROM api_keys')
    total_requests = cursor.fetchone()[0] or 0
    cursor.execute('SELECT COUNT(*) FROM generated_accounts')
    total_accounts = cursor.fetchone()[0] or 0
    conn.close()
    return {'total_keys': total_keys, 'active_keys': active_keys, 'total_requests': total_requests, 'total_accounts': total_accounts}

def get_user_accounts(api_key, limit=50):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT uid, account_id, password, name, region, is_same_digit, same_digit_count, same_digit_reason, timestamp FROM generated_accounts WHERE api_key = ? ORDER BY timestamp DESC LIMIT ?', (api_key, limit))
    accounts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return accounts

init_db()

# ============ AUTH DECORATOR ============
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        if not api_key:
            return jsonify({'success': False, 'error': 'API_KEY_REQUIRED'}), 401
        key_info = validate_api_key(api_key)
        if not key_info:
            return jsonify({'success': False, 'error': 'INVALID_API_KEY'}), 401
        request.api_key = api_key
        request.key_info = key_info
        log_request(api_key, request.endpoint, 'success', request.remote_addr, request.headers.get('User-Agent', ''))
        return f(*args, **kwargs)
    return decorated

# ============ WORKER ============
_original_values = {}

def save_original():
    if 'NAME_PREFIX' not in _original_values:
        _original_values['NAME_PREFIX'] = agen.NAME_PREFIX
        _original_values['PASS_PREFIX'] = agen.PASS_PREFIX
        _original_values['REGION_CHOICE'] = agen.REGION_CHOICE
        _original_values['REGION'] = agen.REGION
        _original_values['REGION_NAME'] = agen.REGION_NAME

def restore_original():
    if 'NAME_PREFIX' in _original_values:
        agen.NAME_PREFIX = _original_values['NAME_PREFIX']
        agen.PASS_PREFIX = _original_values['PASS_PREFIX']
        agen.REGION_CHOICE = _original_values['REGION_CHOICE']
        agen.REGION = _original_values['REGION']
        agen.REGION_NAME = _original_values['REGION_NAME']

def set_config(name_prefix=None, pass_prefix=None, region=None):
    save_original()
    if name_prefix:
        agen.NAME_PREFIX = name_prefix
    else:
        agen.NAME_PREFIX = DEFAULT_NAME_PREFIX
    if pass_prefix:
        agen.PASS_PREFIX = pass_prefix
    else:
        agen.PASS_PREFIX = DEFAULT_PASS_PREFIX
    if region:
        for r_id, r_info in agen.REGION_MAP.items():
            if r_info['code'] == region.upper():
                agen.REGION_CHOICE = r_id
                agen.REGION = r_info['code']
                agen.REGION_NAME = r_info['name']
                break
    else:
        for r_id, r_info in agen.REGION_MAP.items():
            if r_info['code'] == DEFAULT_REGION:
                agen.REGION_CHOICE = r_id
                agen.REGION = r_info['code']
                agen.REGION_NAME = r_info['name']
                break

def generate_one():
    try:
        account = agen.generate_account()
        if account and account.get('success'):
            aid = account.get('account_id', str(account.get('uid')))
            max_count, best_digit, filtered_counts, skipped, analyzed = agen.count_same_digits_skip1(aid)
            reason = ''
            if filtered_counts:
                reason = ', '.join([f"{d}x{c}" for d, c in sorted(filtered_counts.items())])
            return {
                'uid': account.get('uid'),
                'account_id': aid,
                'password': account.get('password'),
                'name': account.get('name'),
                'is_same_digit': max_count >= 4,
                'same_digit_count': max_count,
                'same_digit_reason': reason
            }
        return None
    except Exception as e:
        return None

def generate_multiple(count):
    accounts = []
    for i in range(min(count, 100)):
        acc = generate_one()
        if acc:
            accounts.append(acc)
        time.sleep(0.05)
    return accounts

# ============ ADMIN TEMPLATE ============
ADMIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ACCANG API Admin</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #0a0e27; font-family: monospace; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { background: #0f3460; border: 1px solid #e94560; border-radius: 10px; padding: 20px; margin-bottom: 20px; text-align: center; }
        .header h1 { color: #e94560; }
        .stats { display: grid; grid-template-columns: repeat(4,1fr); gap: 15px; margin-bottom: 20px; }
        .stat-box { background: #0f3460; border: 1px solid #e94560; border-radius: 10px; padding: 15px; text-align: center; }
        .stat-box .number { color: #e94560; font-size: 28px; font-weight: bold; }
        .card { background: #0f3460; border: 1px solid #e94560; border-radius: 10px; padding: 20px; margin-bottom: 20px; }
        .card h3 { color: #e94560; margin-bottom: 15px; }
        input, select, textarea { width: 100%; padding: 10px; background: #0a0e27; border: 1px solid #e94560; border-radius: 5px; color: #fff; }
        button { background: #e94560; color: #fff; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #16213e; color: #ccc; }
        th { color: #e94560; }
        .badge-active { color: #0f0; }
        .badge-inactive { color: #f00; }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .tab { background: #0f3460; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
        .tab.active { background: #e94560; color: #fff; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .code { background: #0a0e27; padding: 10px; border-radius: 5px; color: #0f0; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="container">
        {% if not logged_in %}
        <div class="card" style="max-width:400px; margin:100px auto;">
            <h3>Admin Login</h3>
            <form method="POST" action="/admin/login">
                <input type="text" name="username" placeholder="Username" required><br><br>
                <input type="password" name="password" placeholder="Password" required><br><br>
                <button type="submit">LOGIN</button>
            </form>
        </div>
        {% else %}
        <div class="header"><h1>ACCANG API ADMIN</h1><p>{{ watermark }}</p></div>
        <div class="stats">
            <div class="stat-box"><div class="number">{{ stats.total_keys }}</div><div>Total Keys</div></div>
            <div class="stat-box"><div class="number">{{ stats.active_keys }}</div><div>Active Keys</div></div>
            <div class="stat-box"><div class="number">{{ stats.total_requests }}</div><div>Total Requests</div></div>
            <div class="stat-box"><div class="number">{{ stats.total_accounts }}</div><div>Accounts Generated</div></div>
        </div>
        <div class="tabs">
            <div class="tab active" onclick="showTab('create')">CREATE KEY</div>
            <div class="tab" onclick="showTab('list')">LIST KEYS</div>
            <div class="tab" onclick="showTab('logs')">LOGS</div>
        </div>
        <div id="tab-create" class="tab-content active">
            <div class="card">
                <h3>Create API Key</h3>
                <form id="createForm">
                    <input type="text" name="owner_name" placeholder="Owner Name" required><br><br>
                    <input type="email" name="email" placeholder="Email"><br><br>
                    <select name="plan"><option value="basic">Basic (1000)</option><option value="premium">Premium (10000)</option><option value="unlimited">Unlimited</option></select><br><br>
                    <input type="number" name="max_requests" value="-1" placeholder="Max Requests (-1 unlimited)"><br><br>
                    <input type="number" name="expiry_days" value="30" placeholder="Expiry Days"><br><br>
                    <textarea name="notes" rows="3" placeholder="Notes"></textarea><br><br>
                    <button type="submit">CREATE</button>
                </form>
                <div id="createResult"></div>
            </div>
        </div>
        <div id="tab-list" class="tab-content">
            <div class="card"><h3>API Keys</h3><table id="keysTable"><thead><tr><th>Key</th><th>Owner</th><th>Plan</th><th>Used/Max</th><th>Expires</th><th>Status</th><th>Action</th></tr></thead><tbody></tbody></table></div>
        </div>
        <div id="tab-logs" class="tab-content">
            <div class="card"><h3>Request Logs</h3><table id="logsTable"><thead><tr><th>Time</th><th>API Key</th><th>Endpoint</th><th>IP</th></tr></thead><tbody></tbody></table></div>
        </div>
        {% endif %}
    </div>
    <script>
        function showTab(tab) {
            document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c=>c.classList.remove('active'));
            document.querySelector(`.tab[onclick="showTab('${tab}')"]`).classList.add('active');
            document.getElementById(`tab-${tab}`).classList.add('active');
            if(tab==='list') loadKeys();
            if(tab==='logs') loadLogs();
        }
        async function loadKeys() {
            const res=await fetch('/admin/keys'); const data=await res.json();
            const tbody=document.querySelector('#keysTable tbody'); tbody.innerHTML='';
            data.keys.forEach(k=>{
                const row=tbody.insertRow();
                row.insertCell(0).innerHTML=`<span style="font-family:monospace">${k.api_key.substring(0,16)}...</span>`;
                row.insertCell(1).textContent=k.owner_name;
                row.insertCell(2).textContent=k.plan;
                row.insertCell(3).textContent=`${k.requests_used}/${k.max_requests===-1?'unlimited':k.max_requests}`;
                row.insertCell(4).textContent=k.expires_at?k.expires_at.substring(0,10):'never';
                row.insertCell(5).innerHTML=`<span class="${k.is_active?'badge-active':'badge-inactive'}">${k.is_active?'ACTIVE':'INACTIVE'}</span>`;
                row.insertCell(6).innerHTML=`<button onclick="toggleKey('${k.api_key}',${!k.is_active})">${k.is_active?'DISABLE':'ENABLE'}</button> <button onclick="deleteKey('${k.api_key}')" style="background:#f00">DEL</button>`;
            });
        }
        async function loadLogs() {
            const res=await fetch('/admin/logs'); const data=await res.json();
            const tbody=document.querySelector('#logsTable tbody'); tbody.innerHTML='';
            data.logs.slice(0,50).forEach(l=>{const row=tbody.insertRow();row.insertCell(0).textContent=l.timestamp;row.insertCell(1).textContent=l.api_key.substring(0,16)+'...';row.insertCell(2).textContent=l.endpoint;row.insertCell(3).textContent=l.ip_address;});
        }
        async function toggleKey(apiKey,activate){await fetch('/admin/toggle-key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key:apiKey,activate:activate})});loadKeys();}
        async function deleteKey(apiKey){if(confirm('Delete?')){await fetch('/admin/delete-key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key:apiKey})});loadKeys();}}
        document.getElementById('createForm').addEventListener('submit',async(e)=>{
            e.preventDefault();const data=Object.fromEntries(new FormData(e.target));data.max_requests=parseInt(data.max_requests);data.expiry_days=parseInt(data.expiry_days);
            const res=await fetch('/admin/create-key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
            const result=await res.json();
            if(result.success){document.getElementById('createResult').innerHTML=`<div style="background:#0f0;color:#000;padding:10px;">API KEY: <code>${result.api_key}</code><br>SAVE THIS NOW!</div>`;e.target.reset();loadKeys();}
            else{document.getElementById('createResult').innerHTML=`<div style="background:#f00;padding:10px;">ERROR: ${result.error}</div>`;}
        });
        setInterval(()=>{if(document.querySelector('#tab-list').classList.contains('active'))loadKeys();},30000);
    </script>
</body>
</html>
'''

# ============ ROUTES ============
@app.route('/')
def admin():
    logged_in = request.cookies.get('admin_logged_in') == 'true'
    return render_template_string(ADMIN_TEMPLATE, watermark=WATERMARK, logged_in=logged_in, stats=get_system_stats())

@app.route('/admin/login', methods=['POST'])
def admin_login():
    username = request.form.get('username')
    password = request.form.get('password')
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        resp = jsonify({'success': True})
        resp.set_cookie('admin_logged_in', 'true', max_age=86400, httponly=True)
        return resp
    return jsonify({'success': False}), 401

@app.route('/admin/logout')
def admin_logout():
    resp = jsonify({'success': True})
    resp.set_cookie('admin_logged_in', '', expires=0)
    return resp

@app.route('/admin/keys')
def admin_keys():
    if request.cookies.get('admin_logged_in') != 'true':
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify({'keys': get_all_keys()})

@app.route('/admin/logs')
def admin_logs():
    if request.cookies.get('admin_logged_in') != 'true':
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify({'logs': get_logs(100)})

@app.route('/admin/create-key', methods=['POST'])
def admin_create():
    if request.cookies.get('admin_logged_in') != 'true':
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    api_key = create_api_key(data.get('owner_name'), data.get('email', ''), data.get('plan', 'basic'), int(data.get('max_requests', -1)), int(data.get('expiry_days', 30)), data.get('notes', ''))
    return jsonify({'success': True, 'api_key': api_key})

@app.route('/admin/toggle-key', methods=['POST'])
def admin_toggle():
    if request.cookies.get('admin_logged_in') != 'true':
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    toggle_key(data.get('api_key'), data.get('activate', True))
    return jsonify({'success': True})

@app.route('/admin/delete-key', methods=['POST'])
def admin_delete():
    if request.cookies.get('admin_logged_in') != 'true':
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    delete_key(data.get('api_key'))
    return jsonify({'success': True})

@app.route('/api/status', methods=['GET'])
@require_api_key
def api_status():
    return jsonify({'success': True, 'owner': request.key_info['owner_name'], 'plan': request.key_info['plan'], 'requests_used': request.key_info['requests_used'], 'max_requests': request.key_info['max_requests'], 'remaining': request.key_info['remaining']})

@app.route('/api/stats', methods=['GET'])
@require_api_key
def api_stats():
    key_info = get_key_info(request.api_key)
    system_stats = get_system_stats()
    return jsonify({'success': True, 'your_stats': key_info, 'system_stats': system_stats})

@app.route('/api/accounts', methods=['GET'])
@require_api_key
def api_accounts():
    limit = request.args.get('limit', 50, type=int)
    accounts = get_user_accounts(request.api_key, limit)
    return jsonify({'success': True, 'accounts': accounts, 'total': len(accounts)})

@app.route('/api/generate', methods=['POST'])
@require_api_key
def api_generate():
    data = request.json or {}
    count = min(int(data.get('count', 1)), 100)
    region = data.get('region', 'ID')
    name_prefix = data.get('name_prefix')
    pass_prefix = data.get('pass_prefix')
    
    set_config(name_prefix, pass_prefix, region)
    accounts = generate_multiple(count)
    restore_original()
    
    for acc in accounts:
        log_account(request.api_key, acc.get('uid'), acc.get('account_id'), acc.get('password'), acc.get('name'), region, acc.get('is_same_digit', False), acc.get('same_digit_count', 0), acc.get('same_digit_reason', ''))
    
    return jsonify({'success': True, 'owner': request.key_info['owner_name'], 'accounts': accounts, 'total': len(accounts), 'timestamp': datetime.now().isoformat()})

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'watermark': WATERMARK})

# Untuk Vercel
app = app
