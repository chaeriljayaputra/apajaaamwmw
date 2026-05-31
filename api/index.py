from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os
import json
from datetime import datetime

from api.auth import require_api_key
from api.database import (
    create_api_key, get_key_info, get_all_keys, toggle_key,
    update_key_limit, update_key_expiry, delete_key,
    get_logs, get_system_stats, log_account, get_user_accounts
)
from api.worker import generate_multiple, set_config, restore_original
from config import ADMIN_USERNAME, ADMIN_PASSWORD, WATERMARK, API_DOMAIN

app = Flask(__name__)
CORS(app)

ADMIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ACCANG API - Admin Panel</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            background: #0a0e27;
            font-family: 'Courier New', monospace;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #0f3460, #16213e);
            border: 1px solid #e94560;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            text-align: center;
        }
        .header h1 { color: #e94560; }
        .header p { color: #888; }
        .stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-box {
            background: #0f3460;
            border: 1px solid #e94560;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }
        .stat-box h4 { color: #888; font-size: 12px; }
        .stat-box .number { color: #e94560; font-size: 28px; font-weight: bold; }
        .card {
            background: #0f3460;
            border: 1px solid #e94560;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .card h3 { color: #e94560; margin-bottom: 15px; border-bottom: 1px solid #e94560; padding-bottom: 10px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; color: #ccc; margin-bottom: 5px; font-size: 12px; }
        input, select, textarea {
            width: 100%;
            padding: 10px;
            background: #0a0e27;
            border: 1px solid #e94560;
            border-radius: 5px;
            color: #fff;
            font-family: monospace;
        }
        button {
            background: #e94560;
            color: #fff;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover { background: #c73e56; }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #16213e;
            color: #ccc;
        }
        th { color: #e94560; }
        .badge-active { color: #00ff88; }
        .badge-inactive { color: #ff4444; }
        .code {
            background: #0a0e27;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            color: #00ff88;
            overflow-x: auto;
        }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .tab {
            background: #0f3460;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            color: #ccc;
        }
        .tab.active {
            background: #e94560;
            color: #fff;
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .login-box {
            max-width: 400px;
            margin: 100px auto;
        }
    </style>
</head>
<body>
    <div class="container">
        {% if not logged_in %}
        <div class="card login-box">
            <h3>Admin Login</h3>
            <form method="POST" action="/admin/login">
                <div class="form-group">
                    <label>USERNAME</label>
                    <input type="text" name="username" required>
                </div>
                <div class="form-group">
                    <label>PASSWORD</label>
                    <input type="password" name="password" required>
                </div>
                <button type="submit">LOGIN</button>
            </form>
        </div>
        {% else %}
        
        <div class="header">
            <h1>ACCANG API ADMIN</h1>
            <p>{{ watermark }}</p>
        </div>
        
        <div class="stats">
            <div class="stat-box">
                <h4>TOTAL KEYS</h4>
                <div class="number">{{ stats.total_keys }}</div>
            </div>
            <div class="stat-box">
                <h4>ACTIVE KEYS</h4>
                <div class="number">{{ stats.active_keys }}</div>
            </div>
            <div class="stat-box">
                <h4>TOTAL REQUESTS</h4>
                <div class="number">{{ stats.total_requests }}</div>
            </div>
            <div class="stat-box">
                <h4>ACCOUNTS GEN</h4>
                <div class="number">{{ stats.total_accounts }}</div>
            </div>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="showTab('create')">CREATE KEY</div>
            <div class="tab" onclick="showTab('list')">LIST KEYS</div>
            <div class="tab" onclick="showTab('logs')">REQUEST LOGS</div>
            <div class="tab" onclick="showTab('docs')">DOCS</div>
        </div>
        
        <div id="tab-create" class="tab-content active">
            <div class="card">
                <h3>Create API Key</h3>
                <form id="createForm">
                    <div class="form-group">
                        <label>OWNER NAME</label>
                        <input type="text" name="owner_name" required>
                    </div>
                    <div class="form-group">
                        <label>EMAIL</label>
                        <input type="email" name="email">
                    </div>
                    <div class="form-group">
                        <label>PLAN</label>
                        <select name="plan">
                            <option value="basic">Basic (1000 requests)</option>
                            <option value="premium">Premium (10000 requests)</option>
                            <option value="unlimited">Unlimited (No limit)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>MAX REQUESTS (-1 for unlimited)</label>
                        <input type="number" name="max_requests" value="-1">
                    </div>
                    <div class="form-group">
                        <label>EXPIRY DAYS (0 = no expiry)</label>
                        <input type="number" name="expiry_days" value="30">
                    </div>
                    <div class="form-group">
                        <label>NOTES</label>
                        <textarea name="notes" rows="3"></textarea>
                    </div>
                    <button type="submit">CREATE</button>
                </form>
                <div id="createResult" style="margin-top: 15px;"></div>
            </div>
        </div>
        
        <div id="tab-list" class="tab-content">
            <div class="card">
                <h3>API Keys</h3>
                <div style="overflow-x: auto;">
                    <table id="keysTable">
                        <thead>
                            <tr><th>Key</th><th>Owner</th><th>Plan</th><th>Used/Max</th><th>Expires</th><th>Status</th><th>Actions</th></tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <div id="tab-logs" class="tab-content">
            <div class="card">
                <h3>Request Logs</h3>
                <div style="overflow-x: auto;">
                    <table id="logsTable">
                        <thead>
                            <tr><th>Time</th><th>API Key</th><th>Endpoint</th><th>IP</th></tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <div id="tab-docs" class="tab-content">
            <div class="card">
                <h3>API Documentation</h3>
                
                <h4>Base URL</h4>
                <div class="code">{{ base_url }}</div>
                
                <h4>Authentication</h4>
                <div class="code">X-API-Key: YOUR_API_KEY</div>
                
                <h4>Endpoints</h4>
                
                <h5>POST /api/generate</h5>
                <div class="code">
{
    "count": 1,
    "region": "ID",
    "name_prefix": "user-",
    "pass_prefix": "pass"
}
                </div>
                
                <h5>GET /api/status</h5>
                <div class="code">Check API key status</div>
                
                <h5>GET /api/stats</h5>
                <div class="code">Get your statistics</div>
                
                <h5>GET /api/accounts</h5>
                <div class="code">Get your generated accounts</div>
                
                <h4>Python Client</h4>
                <div class="code">
import requests

API_KEY = "your-key"
BASE_URL = "{{ base_url }}"

resp = requests.post(
    f"{BASE_URL}/api/generate",
    headers={"X-API-Key": API_KEY},
    json={"count": 5, "region": "ID"}
)

for acc in resp.json()["accounts"]:
    print(f"UID: {acc['uid']} | PW: {acc['password']}")
                </div>
            </div>
        </div>
        
        {% endif %}
    </div>
    
    <script>
        function showTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelector(`.tab[onclick="showTab('${tab}')"]`).classList.add('active');
            document.getElementById(`tab-${tab}`).classList.add('active');
            if (tab === 'list') loadKeys();
            if (tab === 'logs') loadLogs();
        }
        
        async function loadKeys() {
            const res = await fetch('/admin/keys');
            const data = await res.json();
            const tbody = document.querySelector('#keysTable tbody');
            tbody.innerHTML = '';
            data.keys.forEach(k => {
                const row = tbody.insertRow();
                row.insertCell(0).innerHTML = `<span style="font-family:monospace">${k.api_key.substring(0,16)}...</span>`;
                row.insertCell(1).textContent = k.owner_name;
                row.insertCell(2).textContent = k.plan;
                row.insertCell(3).textContent = `${k.requests_used}/${k.max_requests === -1 ? 'unlimited' : k.max_requests}`;
                row.insertCell(4).textContent = k.expires_at ? k.expires_at.substring(0,10) : 'never';
                row.insertCell(5).innerHTML = `<span class="${k.is_active ? 'badge-active' : 'badge-inactive'}">${k.is_active ? 'ACTIVE' : 'INACTIVE'}</span>`;
                row.insertCell(6).innerHTML = `
                    <button onclick="toggleKey('${k.api_key}', ${!k.is_active})" style="margin-right:5px">${k.is_active ? 'DISABLE' : 'ENABLE'}</button>
                    <button onclick="deleteKey('${k.api_key}')" style="background:#ff4444">DELETE</button>
                `;
            });
        }
        
        async function loadLogs() {
            const res = await fetch('/admin/logs');
            const data = await res.json();
            const tbody = document.querySelector('#logsTable tbody');
            tbody.innerHTML = '';
            data.logs.slice(0,50).forEach(l => {
                const row = tbody.insertRow();
                row.insertCell(0).textContent = l.timestamp;
                row.insertCell(1).textContent = l.api_key.substring(0,16) + '...';
                row.insertCell(2).textContent = l.endpoint;
                row.insertCell(3).textContent = l.ip_address;
            });
        }
        
        async function toggleKey(apiKey, activate) {
            await fetch('/admin/toggle-key', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({api_key: apiKey, activate: activate})
            });
            loadKeys();
        }
        
        async function deleteKey(apiKey) {
            if (confirm('Delete this API key?')) {
                await fetch('/admin/delete-key', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({api_key: apiKey})
                });
                loadKeys();
            }
        }
        
        document.getElementById('createForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            data.max_requests = parseInt(data.max_requests);
            data.expiry_days = parseInt(data.expiry_days);
            
            const res = await fetch('/admin/create-key', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const result = await res.json();
            const div = document.getElementById('createResult');
            if (result.success) {
                div.innerHTML = `<div style="background:#00ff88; color:#000; padding:10px; border-radius:5px;">
                    API KEY: <code>${result.api_key}</code><br>Save this now!
                </div>`;
                e.target.reset();
                loadKeys();
            } else {
                div.innerHTML = `<div style="background:#ff4444; padding:10px; border-radius:5px;">ERROR: ${result.error}</div>`;
            }
        });
        
        setInterval(() => {
            if (document.querySelector('#tab-list').classList.contains('active')) loadKeys();
        }, 30000);
    </script>
</body>
</html>
'''

@app.route('/')
def admin():
    logged_in = request.cookies.get('admin_logged_in') == 'true'
    return render_template_string(ADMIN_TEMPLATE, 
                                  watermark=WATERMARK,
                                  logged_in=logged_in,
                                  base_url=API_DOMAIN,
                                  stats=get_system_stats())

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
    owner_name = data.get('owner_name')
    email = data.get('email', '')
    plan = data.get('plan', 'basic')
    max_requests = int(data.get('max_requests', -1))
    expiry_days = int(data.get('expiry_days', 30))
    notes = data.get('notes', '')
    
    if not owner_name:
        return jsonify({'error': 'Owner name required'}), 400
    
    api_key = create_api_key(owner_name, email, plan, max_requests, expiry_days, notes)
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
    return jsonify({
        'success': True,
        'owner': request.key_info['owner_name'],
        'plan': request.key_info['plan'],
        'requests_used': request.key_info['requests_used'],
        'max_requests': request.key_info['max_requests'],
        'remaining': request.key_info['remaining']
    })

@app.route('/api/stats', methods=['GET'])
@require_api_key
def api_stats():
    key_info = get_key_info(request.api_key)
    system_stats = get_system_stats()
    return jsonify({
        'success': True,
        'your_stats': key_info,
        'system_stats': system_stats
    })

@app.route('/api/accounts', methods=['GET'])
@require_api_key
def api_accounts():
    limit = request.args.get('limit', 50, type=int)
    accounts = get_user_accounts(request.api_key, limit)
    return jsonify({
        'success': True,
        'accounts': accounts,
        'total': len(accounts)
    })

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
        log_account(
            request.api_key,
            acc.get('uid'),
            acc.get('account_id'),
            acc.get('password'),
            acc.get('name'),
            region,
            acc.get('is_same_digit', False),
            acc.get('same_digit_count', 0),
            acc.get('same_digit_reason', '')
        )
    
    return jsonify({
        'success': True,
        'owner': request.key_info['owner_name'],
        'accounts': accounts,
        'total': len(accounts),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'watermark': WATERMARK})

app = app
