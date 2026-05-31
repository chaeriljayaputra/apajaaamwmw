#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime

# ============ KONFIGURASI ============
API_KEY = "your-api-key-here"
BASE_URL = "https://your-api-domain.vercel.app"
# =====================================

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    MAGENTA = '\033[35m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_banner():
    print(f"\n{Colors.CYAN}{Colors.BOLD}")
    print("=" * 50)
    print("         ACCANG API CLIENT")
    print("=" * 50)
    print(f"{Colors.RESET}")

def check_status():
    try:
        r = requests.get(f"{BASE_URL}/api/status", headers={"X-API-Key": API_KEY}, timeout=30)
        return r.json()
    except Exception as e:
        return {'success': False, 'error': str(e)}

def generate(count=1, region="ID", name_prefix=None, pass_prefix=None):
    data = {"count": count, "region": region}
    if name_prefix:
        data["name_prefix"] = name_prefix
    if pass_prefix:
        data["pass_prefix"] = pass_prefix
    
    try:
        r = requests.post(f"{BASE_URL}/api/generate", 
                         headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
                         json=data, timeout=60)
        return r.json()
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_stats():
    try:
        r = requests.get(f"{BASE_URL}/api/stats", headers={"X-API-Key": API_KEY}, timeout=30)
        return r.json()
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_accounts(limit=50):
    try:
        r = requests.get(f"{BASE_URL}/api/accounts?limit={limit}", headers={"X-API-Key": API_KEY}, timeout=30)
        return r.json()
    except Exception as e:
        return {'success': False, 'error': str(e)}

def save_accounts(accounts, filename=None):
    if not filename:
        filename = f"accounts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(filename, 'w') as f:
        f.write(f"ACCANG Accounts\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 50 + "\n\n")
        
        for i, acc in enumerate(accounts, 1):
            f.write(f"[{i}] UID: {acc.get('uid')}\n")
            f.write(f"    Account ID: {acc.get('account_id')}\n")
            f.write(f"    Password: {acc.get('password')}\n")
            f.write(f"    Name: {acc.get('name')}\n")
            if acc.get('is_same_digit'):
                f.write(f"    SAME DIGIT: {acc.get('same_digit_count')}x ({acc.get('same_digit_reason')})\n")
            f.write("\n")
    
    return filename

def main():
    print_banner()
    
    print(f"{Colors.YELLOW}[*] Checking API status...{Colors.RESET}")
    status = check_status()
    
    if not status.get('success'):
        print(f"{Colors.RED}[!] Error: {status.get('error', 'Unknown')}{Colors.RESET}")
        print(f"{Colors.YELLOW}[!] Check API_KEY and BASE_URL{Colors.RESET}")
        sys.exit(1)
    
    print(f"{Colors.GREEN}[✓] Connected{Colors.RESET}")
    print(f"    Owner: {status.get('owner')}")
    print(f"    Plan: {status.get('plan')}")
    print(f"    Remaining: {status.get('remaining', 'unlimited')}")
    print()
    
    while True:
        print(f"\n{Colors.CYAN}{'=' * 40}{Colors.RESET}")
        print("1. Generate 1 account")
        print("2. Generate 5 accounts")
        print("3. Generate 10 accounts")
        print("4. Generate custom")
        print("5. Check stats")
        print("6. View my accounts")
        print("0. Exit")
        print(f"{Colors.CYAN}{'=' * 40}{Colors.RESET}")
        
        choice = input(f"{Colors.YELLOW}Choice: {Colors.RESET}").strip()
        
        if choice == '0':
            print(f"{Colors.GREEN}Goodbye!{Colors.RESET}")
            break
        
        elif choice == '1':
            print(f"{Colors.YELLOW}[*] Generating...{Colors.RESET}")
            result = generate(1)
            if result.get('success'):
                for acc in result.get('accounts', []):
                    print(f"\n{Colors.GREEN}SUCCESS{Colors.RESET}")
                    print(f"  UID: {acc.get('uid')}")
                    print(f"  PW: {acc.get('password')}")
                    print(f"  Name: {acc.get('name')}")
                    if acc.get('is_same_digit'):
                        print(f"  SAME DIGIT: {acc.get('same_digit_count')}x")
                save_accounts(result.get('accounts', []), "latest.txt")
            else:
                print(f"{Colors.RED}Failed: {result.get('error')}{Colors.RESET}")
        
        elif choice == '2':
            print(f"{Colors.YELLOW}[*] Generating 5 accounts...{Colors.RESET}")
            result = generate(5)
            if result.get('success'):
                accounts = result.get('accounts', [])
                print(f"\n{Colors.GREEN}Generated {len(accounts)} accounts{Colors.RESET}\n")
                for i, acc in enumerate(accounts, 1):
                    print(f"  [{i}] {acc.get('uid')} | {acc.get('password')}")
                filename = save_accounts(accounts)
                print(f"\nSaved to: {filename}")
            else:
                print(f"{Colors.RED}Failed: {result.get('error')}{Colors.RESET}")
        
        elif choice == '3':
            confirm = input(f"{Colors.YELLOW}Generate 10 accounts? (y/n): {Colors.RESET}")
            if confirm.lower() == 'y':
                print(f"{Colors.YELLOW}[*] Generating 10 accounts...{Colors.RESET}")
                result = generate(10)
                if result.get('success'):
                    accounts = result.get('accounts', [])
                    print(f"\n{Colors.GREEN}Generated {len(accounts)} accounts{Colors.RESET}\n")
                    for i, acc in enumerate(accounts, 1):
                        print(f"  [{i}] {acc.get('uid')} | {acc.get('password')}")
                    filename = save_accounts(accounts)
                    print(f"\nSaved to: {filename}")
                else:
                    print(f"{Colors.RED}Failed: {result.get('error')}{Colors.RESET}")
        
        elif choice == '4':
            try:
                count = int(input(f"{Colors.YELLOW}Count (max 100): {Colors.RESET}"))
                count = min(count, 100)
                region = input(f"{Colors.YELLOW}Region (ID/ME/IND/TH/VN etc): {Colors.RESET}").strip() or "ID"
                name_prefix = input(f"{Colors.YELLOW}Name prefix (optional): {Colors.RESET}").strip() or None
                pass_prefix = input(f"{Colors.YELLOW}Password prefix (optional): {Colors.RESET}").strip() or None
                
                print(f"{Colors.YELLOW}[*] Generating {count} accounts...{Colors.RESET}")
                result = generate(count, region, name_prefix, pass_prefix)
                if result.get('success'):
                    accounts = result.get('accounts', [])
                    print(f"\n{Colors.GREEN}Generated {len(accounts)} accounts{Colors.RESET}")
                    filename = save_accounts(accounts)
                    print(f"Saved to: {filename}")
                else:
                    print(f"{Colors.RED}Failed: {result.get('error')}{Colors.RESET}")
            except ValueError:
                print(f"{Colors.RED}Invalid number{Colors.RESET}")
        
        elif choice == '5':
            stats = get_stats()
            if stats.get('success'):
                your = stats.get('your_stats', {})
                print(f"\n{Colors.CYAN}Your Stats{Colors.RESET}")
                print(f"  Plan: {your.get('plan')}")
                print(f"  Used: {your.get('requests_used')}/{your.get('max_requests', 'unlimited')}")
                print(f"  Created at: {your.get('created_at')}")
                if your.get('expires_at'):
                    print(f"  Expires: {your.get('expires_at')}")
            else:
                print(f"{Colors.RED}Failed: {stats.get('error')}{Colors.RESET}")
        
        elif choice == '6':
            accounts = get_accounts(20)
            if accounts.get('success'):
                acc_list = accounts.get('accounts', [])
                print(f"\n{Colors.CYAN}Your last {len(acc_list)} accounts{Colors.RESET}\n")
                for i, acc in enumerate(acc_list, 1):
                    print(f"  [{i}] {acc.get('uid')} | {acc.get('password')} | {acc.get('timestamp')}")
            else:
                print(f"{Colors.RED}Failed: {accounts.get('error')}{Colors.RESET}")

if __name__ == "__main__":
    main()
