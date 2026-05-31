import sqlite3
import secrets
import json
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'api_keys.db')

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
    
    cursor.execute('''
        SELECT id, owner_name, plan, max_requests, requests_used, expires_at, is_active
        FROM api_keys WHERE api_key = ?
    ''', (api_key,))
    
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
    cursor.execute('''
        INSERT INTO request_logs (api_key, endpoint, status, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?)
    ''', (api_key, endpoint, status, ip_address, user_agent))
    conn.commit()
    conn.close()

def log_account(api_key, uid, account_id, password, name, region, is_same_digit, same_digit_count, same_digit_reason):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO generated_accounts 
        (api_key, uid, account_id, password, name, region, is_same_digit, same_digit_count, same_digit_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (api_key, uid, account_id, password, name, region, is_same_digit, same_digit_count, same_digit_reason))
    conn.commit()
    conn.close()

def get_key_info(api_key):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT owner_name, plan, max_requests, requests_used, created_at, expires_at, is_active
        FROM api_keys WHERE api_key = ?
    ''', (api_key,))
    result = cursor.fetchone()
    conn.close()
    return dict(result) if result else None

def get_all_keys():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT api_key, owner_name, email, plan, max_requests, requests_used, created_at, expires_at, is_active, notes
        FROM api_keys ORDER BY created_at DESC
    ''')
    keys = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return keys

def toggle_key(api_key, activate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE api_keys SET is_active = ? WHERE api_key = ?', (1 if activate else 0, api_key))
    conn.commit()
    conn.close()

def update_key_limit(api_key, max_requests):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE api_keys SET max_requests = ? WHERE api_key = ?', (max_requests, api_key))
    conn.commit()
    conn.close()

def update_key_expiry(api_key, expiry_days):
    conn = get_db()
    cursor = conn.cursor()
    expires_at = None
    if expiry_days > 0:
        expires_at = (datetime.now() + timedelta(days=expiry_days)).isoformat()
    cursor.execute('UPDATE api_keys SET expires_at = ? WHERE api_key = ?', (expires_at, api_key))
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
    cursor.execute('''
        SELECT timestamp, api_key, endpoint, status, ip_address
        FROM request_logs ORDER BY timestamp DESC LIMIT ?
    ''', (limit,))
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
    
    return {
        'total_keys': total_keys,
        'active_keys': active_keys,
        'total_requests': total_requests,
        'total_accounts': total_accounts
    }

def get_user_accounts(api_key, limit=50):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT uid, account_id, password, name, region, is_same_digit, same_digit_count, same_digit_reason, timestamp
        FROM generated_accounts WHERE api_key = ? ORDER BY timestamp DESC LIMIT ?
    ''', (api_key, limit))
    accounts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return accounts

init_db()
