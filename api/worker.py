import sys
import os
import random
import string
import time
import threading
import warnings

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agen
from config import DEFAULT_NAME_PREFIX, DEFAULT_PASS_PREFIX, DEFAULT_REGION

# Store original values
_original_values = {
    'NAME_PREFIX': None,
    'PASS_PREFIX': None,
    'REGION_CHOICE': None,
    'REGION': None,
    'REGION_NAME': None,
    'REGION_LANG': None
}

def save_original():
    if _original_values['NAME_PREFIX'] is None:
        _original_values['NAME_PREFIX'] = agen.NAME_PREFIX
        _original_values['PASS_PREFIX'] = agen.PASS_PREFIX
        _original_values['REGION_CHOICE'] = agen.REGION_CHOICE
        _original_values['REGION'] = agen.REGION
        _original_values['REGION_NAME'] = agen.REGION_NAME
        _original_values['REGION_LANG'] = agen.REGION_LANG.copy() if hasattr(agen, 'REGION_LANG') else None

def restore_original():
    if _original_values['NAME_PREFIX'] is not None:
        agen.NAME_PREFIX = _original_values['NAME_PREFIX']
        agen.PASS_PREFIX = _original_values['PASS_PREFIX']
        agen.REGION_CHOICE = _original_values['REGION_CHOICE']
        agen.REGION = _original_values['REGION']
        agen.REGION_NAME = _original_values['REGION_NAME']
        if _original_values['REGION_LANG'] is not None:
            agen.REGION_LANG = _original_values['REGION_LANG']

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
                agen.REGION_LANG = {r_info['code']: r_info['lang']}
                break
    else:
        for r_id, r_info in agen.REGION_MAP.items():
            if r_info['code'] == DEFAULT_REGION:
                agen.REGION_CHOICE = r_id
                agen.REGION = r_info['code']
                agen.REGION_NAME = r_info['name']
                agen.REGION_LANG = {r_info['code']: r_info['lang']}
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
    for i in range(count):
        acc = generate_one()
        if acc:
            accounts.append(acc)
        time.sleep(0.05)
    return accounts
