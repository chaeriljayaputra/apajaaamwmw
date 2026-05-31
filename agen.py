import warnings
warnings.filterwarnings('ignore')

import requests
import random
import string
import time
import os
import threading
import json
import codecs
import base64
import sys
import signal
import platform
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque, Counter

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if platform.system() == 'Windows':
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

WATERMARK = "TikTok @qrnlay"

class Colors:
    # Reset & style
    RESET = '\033[0m'
    BOLD = '\033[1m'
    BLINK = '\033[5m'          # efek berkedip (didukung banyak terminal)

    # Warna teks
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    WHITE = '\033[97m'
    MAGENTA = '\033[35m'
    BLACK = '\033[30m'

    # Warna latar (background) 256-color
    # Semakin tinggi nilainya, semakin "hoki", warna dibuat lebih mencolok
    BG_4  = '\033[48;5;220m'   # x4  = kuning terang
    BG_5  = '\033[48;5;214m'   # x5  = oranye
    BG_6  = '\033[48;5;208m'   # x6  = oranye tua
    BG_7  = '\033[48;5;202m'   # x7  = merah-oranye
    BG_8  = '\033[48;5;201m'   # x8  = pink terang (rainbow vibes)
    BG_9  = '\033[48;5;51m'    # x9  = cyan terang
    BG_10 = '\033[48;5;46m'    # x10 = hijau neon
    BG_11 = '\033[48;5;226m'   # x11+= kuning neon paling terang

    # Untuk x8 ke atas kita tambahkan efek BLINK agar makin "hoki"
    @staticmethod
    def get_hoki_bg(count):
        """Kembalikan string ANSI untuk background + teks, mungkin dengan efek khusus."""
        if count >= 11:
            return Colors.BLINK + Colors.BG_11 + Colors.BLACK + Colors.BOLD
        if count >= 10:
            return Colors.BLINK + Colors.BG_10 + Colors.BLACK + Colors.BOLD
        if count >= 9:
            return Colors.BLINK + Colors.BG_9 + Colors.BLACK + Colors.BOLD
        if count >= 8:
            return Colors.BLINK + Colors.BG_8 + Colors.WHITE + Colors.BOLD
        if count >= 7:
            return Colors.BG_7 + Colors.WHITE + Colors.BOLD
        if count >= 6:
            return Colors.BG_6 + Colors.WHITE + Colors.BOLD
        if count >= 5:
            return Colors.BG_5 + Colors.BLACK + Colors.BOLD
        if count >= 4:
            return Colors.BG_4 + Colors.BLACK + Colors.BOLD
        return None

c = Colors()

def get_bg_for_count(count):
    """Wrapper agar kompatibel dengan kode sebelumnya."""
    return Colors.get_hoki_bg(count)

REGION_CHOICE = 1

REGION_MAP = {
    1: {"code": "ID", "name": "INDONESIA", "lang": "id"},
    2: {"code": "ME", "name": "MIDDLE EAST", "lang": "ar"},
    3: {"code": "IND", "name": "INDIA", "lang": "hi"},
    4: {"code": "TH", "name": "THAILAND", "lang": "th"},
    5: {"code": "VN", "name": "VIETNAM", "lang": "vi"},
    6: {"code": "BD", "name": "BANGLADESH", "lang": "bn"},
    7: {"code": "PK", "name": "PAKISTAN", "lang": "ur"},
    8: {"code": "TW", "name": "TAIWAN", "lang": "zh"},
    9: {"code": "CIS", "name": "RUSSIA", "lang": "ru"},
    10: {"code": "SAC", "name": "SPAIN", "lang": "es"},
    11: {"code": "BR", "name": "BRAZIL", "lang": "pt"}
}

SELECTED = REGION_MAP.get(REGION_CHOICE, REGION_MAP[1])
REGION = SELECTED["code"]
REGION_LANG = {REGION: SELECTED["lang"]}
REGION_NAME = SELECTED["name"]

NAME_PREFIX = input(f"{c.YELLOW}[?] NAME PREFIX {c.RESET}: ").strip() or "shuoi-"
PASS_PREFIX = input(f"{c.YELLOW}[?] PASSWORD PREFIX {c.RESET}: ").strip() or "shu"

THREAD_COUNT = 100
REQUEST_DELAY = 0.00001
FAIL_SLEEP = 1

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_FOLDER = os.path.join(CURRENT_DIR, "AccangGen")
ACCOUNTS_FOLDER = os.path.join(BASE_FOLDER, "ACCOUNTS")
SAME_DIGIT_FOLDER = os.path.join(BASE_FOLDER, "SAME-DIGIT-4PLUS")

for folder in [BASE_FOLDER, ACCOUNTS_FOLDER, SAME_DIGIT_FOLDER]:
    os.makedirs(folder, exist_ok=True)

file_locks = {}
stats = {
    'total': 0,
    'same_4plus': 0,
    'same_4': 0, 'same_5': 0, 'same_6': 0, 'same_7': 0,
    'same_8': 0, 'same_9': 0, 'same_10': 0, 'same_11plus': 0,
    'start_time': time.time()
}
stats_lock = threading.Lock()
running = True

def get_file_lock(filename):
    if filename not in file_locks:
        file_locks[filename] = threading.Lock()
    return file_locks[filename]

def shutdown_handler(signum=None, frame=None):
    global running
    print(f"\n{c.YELLOW}[!] Shutting down...{c.RESET}")
    running = False
    time.sleep(1)
    print(f"{c.MAGENTA}{WATERMARK}{c.RESET}")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)
try:
    signal.signal(signal.SIGTSTP, shutdown_handler)
except:
    pass

HEX_KEY = bytes.fromhex("32656534343831396539623435393838343531343130363762323831363231383734643064356437616639643866376530306331653534373135623764316533")

def generate_cool_name():
    base = f"{NAME_PREFIX}{random.randint(10, 999)}"
    syms = ['~','!','@','#','$','%','^','&','*','-','_','+','=','|',':',';','.','?','/','あ','い','う','え','お','ア','イ','ウ','エ','オ','月','火','水','木','金','愛','夢','星','龍','虎','刀','忍','魂','影','光','闇','炎','龙','凤','虎','剑','刀','王','皇','帝','天','地','人','金','木','水','火','土','福','禄','寿','喜','財','戰','無','超','極','ก','ข','ค','ง','จ','ช','ซ','พญานาค','ครุฑ','ช้าง','เสือ','สิงห์','นักรบ','เทพ','ทอง','เงิน','เพชร','◎','◉','☆','★','♪','♫','〆']
    p = random.randint(1, 5)
    if p == 1:
        s = random.choice(syms)
        return f"{s}{base}{s}"
    elif p == 2:
        s1, s2 = random.sample(syms, 2)
        return f"{s1}{s2}{base}"
    elif p == 3:
        s1, s2 = random.sample(syms, 2)
        return f"{base}{s1}{s2}"
    elif p == 4:
        s1, s2 = random.sample(syms, 2)
        return f"{s1}{base}{s2}"
    else:
        return base

DEVICE_POOL = []
samsung = [f"SM-{c}{random.randint(100,999)}" for _ in range(1000) for c in "AGNFMSJE"]
xiaomi = [f"{p} {random.randint(7,14)}" for _ in range(800) for p in ["Redmi Note", "Redmi", "Poco F", "Poco X", "Mi", "Xiaomi"]]
oppo = [f"OPPO {m}{random.randint(2,9999)}" for _ in range(600) for m in ["CPH", "Find X", "Reno", "A", "F"]]
vivo = [f"vivo {m}{random.randint(1,9999)}" for _ in range(600) for m in ["V", "X", "Y", "T", "S"]]
realme = [f"Realme {m}{random.randint(7,70)}" for _ in range(500) for m in ["", " Pro", " GT ", " C", " Narzo "]]
oneplus = [f"OnePlus {random.randint(8,14)}" for _ in range(400)]
moto = [f"Moto {m}{random.randint(10,100)}" for _ in range(400) for m in ["G", "E", "Edge "]]
other = ["ASUS_I005DA","ASUS Zenfone 8","ASUS ROG Phone 5","Google Pixel 6","Google Pixel 7","Sony Xperia 1 III","Nokia G50","LG V60","Nothing Phone 1","SHARP AQUOS R8"] * 200
all_models = samsung + xiaomi + oppo + vivo + realme + oneplus + moto + other
brands = ["samsung","xiaomi","oppo","vivo","realme","oneplus","motorola","asus","google","sony","nokia","lg","nothing"]
android_versions = ["9","10","11","12","13","14","15"]

for _ in range(20000):
    DEVICE_POOL.append({
        "model": random.choice(all_models),
        "brand": random.choice(brands),
        "android": random.choice(android_versions)
    })

session_pool = deque()
session_lock = threading.Lock()

def get_session():
    with session_lock:
        if session_pool:
            return session_pool.popleft()
    s = requests.Session()
    s.verify = False
    return s

def return_session(s):
    with session_lock:
        if len(session_pool) < THREAD_COUNT * 2:
            session_pool.append(s)
        else:
            s.close()

for _ in range(min(10, THREAD_COUNT)):
    s = requests.Session()
    s.verify = False
    session_pool.append(s)

def get_random_ip():
    return f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}"

def get_headers():
    device = random.choice(DEVICE_POOL)
    return {
        "User-Agent": f"GarenaMSDK/4.0.39({device['model']};Android {device['android']};en;ID;)",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Connection": "Keep-Alive",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": f"v1 {random.randint(100000, 999999)}",
        "X-Forwarded-For": get_random_ip(),
        "X-Real-IP": get_random_ip(),
    }

def get_headers_form():
    h = get_headers()
    h["Content-Type"] = "application/x-www-form-urlencoded"
    return h

def encode_varint(n):
    if n < 0: return b''
    result = []
    while True:
        byte = n & 0x7F
        n >>= 7
        if n: byte |= 0x80
        result.append(byte)
        if not n: break
    return bytes(result)

def create_proto_field(field_num, value):
    if isinstance(value, dict):
        nested = b''
        for k, v in value.items():
            nested += create_proto_field(k, v)
        header = (field_num << 3) | 2
        return encode_varint(header) + encode_varint(len(nested)) + nested
    elif isinstance(value, int):
        header = (field_num << 3) | 0
        return encode_varint(header) + encode_varint(value)
    elif isinstance(value, (str, bytes)):
        encoded_val = value.encode() if isinstance(value, str) else value
        header = (field_num << 3) | 2
        return encode_varint(header) + encode_varint(len(encoded_val)) + encoded_val
    return b''

def build_proto(fields):
    return b''.join(create_proto_field(k, v) for k, v in fields.items())

def aes_encrypt(hex_data):
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    data = bytes.fromhex(hex_data)
    aes_key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(data, AES.block_size))

def encrypt_api(plain_hex):
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    plain = bytes.fromhex(plain_hex)
    aes_key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(plain, AES.block_size)).hex()

def major_login(uid, password, access_token, open_id, region):
    try:
        lang = REGION_LANG.get(region, "en")
        payload_parts = [
            b'\x1a\x132025-08-30 05:19:21"\tfree fire(\x01:\x081.114.13B2Android OS 9 / API-28 (PI/rel.cjw.20220518.114133)J\x08HandheldR\nATM MobilsZ\x04WIFI`\xb6\nh\xee\x05r\x03300z\x1fARMv7 VFPv3 NEON VMH | 2400 | 2\x80\x01\xc9\x0f\x8a\x01\x0fAdreno (TM) 640\x92\x01\rOpenGL ES 3.2\x9a\x01+Google|dfa4ab4b-9dc4-454e-8065-e70c733fa53f\xa2\x01\x0e105.235.139.91\xaa\x01\x02',
            lang.encode("ascii"),
            b'\xb2\x01 1d8ec0240ede109973f3321b9354b44d\xba\x01\x014\xc2\x01\x08Handheld\xca\x01\x10Asus ASUS_I005DA\xea\x01@afcfbf13334be42036e4f742c80b956344bed760ac91b3aff9b607a610ab4390\xf0\x01\x01\xca\x02\nATM Mobils\xd2\x02\x04WIFI\xca\x03 7428b253defc164018c604a1ebbfebdf\xe0\x03\xa8\x81\x02\xe8\x03\xf6\xe5\x01\xf0\x03\xaf\x13\xf8\x03\x84\x07\x80\x04\xe7\xf0\x01\x88\x04\xa8\x81\x02\x90\x04\xe7\xf0\x01\x98\x04\xa8\x81\x02\xc8\x04\x01\xd2\x04=/data/app/com.dts.freefireth-PdeDnOilCSFn37p1AH_FLg==/lib/arm\xe0\x04\x01\xea\x04_2087f61c19f57f2af4e7feff0b24d9d9|/data/app/com.dts.freefireth-PdeDnOilCSFn37p1AH_FLg==/base.apk\xf0\x04\x03\xf8\x04\x01\x8a\x05\x0232\x9a\x05\n2019118692\xb2\x05\tOpenGLES2\xb8\x05\xff\x7f\xc0\x05\x04\xe0\x05\xf3F\xea\x05\x07android\xf2\x05pKqsHT5ZLWrYljNb5Vqh//yFRlaPHSO9NWSQsVvOmdhEEn7W+VHNUK+Q+fduA3ptNrGB0Ll0LRz3WW0jOwesLj6aiU7sZ40p8BfUE/FI/jzSTwRe2\xf8\x05\xfb\xe4\x06\x88\x06\x01\x90\x06\x01\x9a\x06\x014\xa2\x06\x014\xb2\x06"GQ@O\x00\x0e^\x00D\x06UA\x0ePM\r\x13hZ\x07T\x06\x0cm\\V\x0ejYV;\x0bU5'
        ]
        payload = b''.join(payload_parts)
        
        if region in ["ME", "TH"]:
            url = "https://loginbp.common.ggbluefox.com/MajorLogin"
        else:
            url = "https://loginbp.ggblueshark.com/MajorLogin"
        
        headers = {
            "Accept-Encoding": "gzip", "Authorization": "Bearer", "Connection": "Keep-Alive",
            "Content-Type": "application/x-www-form-urlencoded", "Expect": "100-continue",
            "Host": "loginbp.ggblueshark.com" if region not in ["ME","TH"] else "loginbp.common.ggbluefox.com",
            "ReleaseVersion": "OB53", "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_I005DA Build/PI)",
            "X-GA": "v1 1", "X-Unity-Version": "2018.4.11f1"
        }
        
        data = payload.replace(b'afcfbf13334be42036e4f742c80b956344bed760ac91b3aff9b607a610ab4390', access_token.encode())
        data = data.replace(b'1d8ec0240ede109973f3321b9354b44d', open_id.encode())
        d = encrypt_api(data.hex())
        
        session = get_session()
        response = session.post(url, headers=headers, data=bytes.fromhex(d), timeout=15)
        
        if response.status_code == 200 and len(response.text) > 10:
            jwt_start = response.text.find("eyJ")
            if jwt_start != -1:
                jwt_token = response.text[jwt_start:]
                second_dot = jwt_token.find(".", jwt_token.find(".") + 1)
                if second_dot != -1:
                    jwt_token = jwt_token[:second_dot + 44]
                try:
                    parts = jwt_token.split('.')
                    if len(parts) >= 2:
                        payload_part = parts[1]
                        padding = 4 - len(payload_part) % 4
                        if padding != 4: 
                            payload_part += '=' * padding
                        decoded = base64.urlsafe_b64decode(payload_part)
                        data = json.loads(decoded)
                        account_id = data.get('account_id') or data.get('external_id')
                        if account_id:
                            return {"account_id": str(account_id), "jwt_token": jwt_token}
                except:
                    pass
        return {"account_id": "N/A", "jwt_token": ""}
    except:
        return {"account_id": "N/A", "jwt_token": ""}

def generate_account():
    if not running:
        return None
    
    session = get_session()
    
    for retry in range(2):
        try:
            password = f"{PASS_PREFIX}{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
            name = generate_cool_name()
            
            resp = session.post(
                "https://100067.connect.garena.com/api/v2/oauth/guest:register",
                headers=get_headers(),
                json={"app_id": 100067, "client_type": 2, "password": password, "source": 2},
                timeout=15
            )
            
            if resp.status_code == 200:
                data = resp.json()
                if "data" in data and "uid" in data["data"]:
                    uid = data["data"]["uid"]
                    
                    time.sleep(0.03)
                    
                    resp2 = session.post(
                        "https://100067.connect.garena.com/oauth/guest/token/grant",
                        headers=get_headers_form(),
                        data={"uid": uid, "password": password, "response_type": "token", "client_type": "2", "client_secret": HEX_KEY, "client_id": "100067"},
                        timeout=15
                    )
                    
                    if resp2.status_code == 200:
                        token_data = resp2.json()
                        open_id = token_data.get('open_id', '')
                        access_token = token_data.get('access_token', '')
                        
                        if open_id and access_token:
                            keystream = [0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30]
                            encoded = ""
                            for i in range(len(open_id)):
                                encoded += chr(ord(open_id[i]) ^ keystream[i % len(keystream)])
                            hex_str = ''.join(c if 32 <= ord(c) <= 126 else '\\u{:04x}'.format(ord(c)) for c in encoded)
                            field = codecs.decode(hex_str, 'unicode_escape').encode('latin1')
                            
                            if REGION in ["ME", "TH"]:
                                url_major = "https://loginbp.common.ggbluefox.com/MajorRegister"
                            else:
                                url_major = "https://loginbp.ggblueshark.com/MajorRegister"
                            
                            lang_code = REGION_LANG.get(REGION, "en")
                            payload = {1: name, 2: access_token, 3: open_id, 5: 102000007, 6: 4, 7: 1, 13: 1, 14: field, 15: lang_code, 16: 1, 17: 1}
                            payload_bytes = build_proto(payload)
                            encrypted_payload = aes_encrypt(payload_bytes.hex())
                            
                            headers_major = {
                                "Accept-Encoding": "gzip", "Authorization": "Bearer", "Connection": "Keep-Alive",
                                "Content-Type": "application/x-www-form-urlencoded", "Expect": "100-continue",
                                "Host": "loginbp.ggblueshark.com" if REGION not in ["ME","TH"] else "loginbp.common.ggbluefox.com",
                                "ReleaseVersion": "OB53", "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_I005DA Build/PI)",
                                "X-GA": "v1 1", "X-Unity-Version": "2018.4."
                            }
                            
                            session.post(url_major, headers=headers_major, data=encrypted_payload, timeout=15)
                            
                            time.sleep(0.03)
                            
                            login_result = major_login(uid, password, access_token, open_id, REGION)
                            account_id = login_result.get("account_id", "N/A")
                            jwt_token = login_result.get("jwt_token", "")
                            
                            if account_id != "N/A":
                                return_session(session)
                                return {
                                    "uid": uid,
                                    "password": password,
                                    "name": name,
                                    "account_id": account_id,
                                    "jwt_token": jwt_token,
                                    "success": True
                                }
        except:
            pass
        
        time.sleep(0.5)
    
    return_session(session)
    return None

def count_same_digits_skip1(account_id):
    """Skip first digit, count same digits in the rest. Returns max_count, best_digit, filtered dict, skipped, analyzed."""
    aid = str(account_id)
    if not aid.isdigit() or len(aid) < 5:
        return 0, '', {}, aid, ''
    
    skipped = aid[:1]
    analyzed = aid[1:]
    
    if len(analyzed) < 4:
        return 0, '', {}, skipped, analyzed
    
    digit_counts = Counter(analyzed)
    filtered = {d: c for d, c in digit_counts.items() if c >= 4}
    
    if filtered:
        best_digit = max(filtered, key=filtered.get)
        max_count = filtered[best_digit]
        return max_count, best_digit, filtered, skipped, analyzed
    
    return 0, '', {}, skipped, analyzed

class Logger:
    def __init__(self):
        self.lock = threading.Lock()
        self.last_speed_time = time.time()
        self.last_count = 0
    
    def add(self, uid, account_id, password, same_count, best_digit, filtered_counts, skipped, analyzed):
        with self.lock:

            stats['total'] += 1
            
            if same_count >= 4:
                stats['same_4plus'] += 1
                
                if same_count == 4: stats['same_4'] += 1
                elif same_count == 5: stats['same_5'] += 1
                elif same_count == 6: stats['same_6'] += 1
                elif same_count == 7: stats['same_7'] += 1
                elif same_count == 8: stats['same_8'] += 1
                elif same_count == 9: stats['same_9'] += 1
                elif same_count == 10: stats['same_10'] += 1
                else: stats['same_11plus'] += 1
                
                multi_digits = [f"{d}x{c}" for d, c in sorted(filtered_counts.items())]
                reason = ', '.join(multi_digits)
                
                bg = get_bg_for_count(same_count)
                # bg sudah mengandung kombinasi warna teks + latar + efek
                print(f"{bg}[{stats['total']}] UID:{uid} | ID:{account_id} | PW:{password} | {reason}{c.RESET}")
            else:
                print(f"{c.WHITE}[{stats['total']}] UID:{uid} | ID:{account_id} | PW:{password}{c.RESET}")
            
            now = time.time()
            if now - self.last_speed_time >= 10:
                elapsed = now - stats['start_time']
                speed = stats['total'] / elapsed if elapsed > 0 else 0
                recent_speed = (stats['total'] - self.last_count) / (now - self.last_speed_time)
                print(f"{c.YELLOW} {recent_speed:.1f} acc/s | AVG: {speed:.1f} acc/s | SAME: {stats['same_4plus']}{c.RESET}")
                self.last_speed_time = now
                self.last_count = stats['total']
    
    def summary(self):
        elapsed = time.time() - stats['start_time']
        print(f"\n{c.MAGENTA}{c.BOLD} ACCANG GEN - DONE {c.RESET}")
        print(f"  TOTAL   : {c.GREEN}{stats['total']}{c.RESET}")
        print(f"  4+ SAME : {stats['same_4plus']}")
        print(f"  TIME    : {elapsed:.1f}s")
        if elapsed > 0:
            print(f"  SPEED   : {stats['total']/elapsed:.2f} acc/s")
        print(f"{c.MAGENTA}{WATERMARK}{c.RESET}")

logger = Logger()

def save_same_digit(uid, password, account_id, name, max_count, best_digit, filtered_counts, skipped, analyzed, region):
    try:
        date_created = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        wm = WATERMARK
        
        digit_summary = [f"{d}={c}" for d, c in sorted(filtered_counts.items())]
        summary_str = ', '.join(digit_summary)
        
        reason_str = ', '.join([f"{d}x{c}" for d, c in sorted(filtered_counts.items())])
        
        id_file = os.path.join(SAME_DIGIT_FOLDER, "id.txt")
        with get_file_lock(id_file):
            with open(id_file, 'a', encoding='utf-8') as f:
                f.write(f"{account_id}\n")
        
        idpw_file = os.path.join(SAME_DIGIT_FOLDER, "2-ID_PW_UID.txt")
        with get_file_lock(idpw_file):
            with open(idpw_file, 'a', encoding='utf-8') as f:
                f.write(f"[{date_created}] {reason_str} | UID:{uid} | ID:{account_id} | PW:{password} | NAME:{name}\n")
                f.write(f"{wm}\n\n")
        
        json_file = os.path.join(SAME_DIGIT_FOLDER, "accounts_samedigit.json")
        with get_file_lock(json_file):
            data = []
            if os.path.exists(json_file):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except:
                    data = []
            data.append({
                'uid': uid,
                'password': password,
                'account_id': account_id,
                'name': name,
                'region': region,
                'max_count': max_count,
                'best_digit': best_digit,
                'skipped': skipped,
                'analyzed': analyzed,
                'reason': reason_str,
                'digit_counts': {str(k): v for k, v in filtered_counts.items()},
                'date_created': date_created,
                'watermark': wm
            })
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
    except Exception as e:
        pass

def save_normal(uid, password, account_id, name, region):
    try:
        date_created = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        wm = WATERMARK
        
        txt_file = os.path.join(ACCOUNTS_FOLDER, f"accounts-{region}.txt")
        with get_file_lock(txt_file):
            with open(txt_file, 'a', encoding='utf-8') as f:
                f.write(f"[{date_created}] UID:{uid} | ID:{account_id} | PW:{password} | NAME:{name}\n")
                f.write(f"{wm}\n")
        
        json_file = os.path.join(ACCOUNTS_FOLDER, f"accounts-{region}.json")
        with get_file_lock(json_file):
            data = []
            if os.path.exists(json_file):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except:
                    data = []
            data.append({
                'uid': uid, 'password': password, 'account_id': account_id,
                'name': name, 'region': region, 'date_created': date_created, 'watermark': wm
            })
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
    except Exception as e:
        pass

def worker(thread_id):
    consecutive_fails = 0
    
    while running:
        account = generate_account()
        
        if account and account.get("success"):
            uid = account["uid"]
            aid = account["account_id"]
            password = account["password"]
            name = account["name"]
            
            if aid == "N/A":
                aid = str(uid)
            
            max_count, best_digit, filtered_counts, skipped, analyzed = count_same_digits_skip1(aid)
            
            logger.add(uid, aid, password, max_count, best_digit, filtered_counts, skipped, analyzed)
            
            if max_count >= 4:
                save_same_digit(uid, password, aid, name, max_count, best_digit, filtered_counts, skipped, analyzed, REGION)
            else:
                save_normal(uid, password, aid, name, REGION)
            
            consecutive_fails = 0
        else:
            consecutive_fails += 1
            if consecutive_fails > 20:
                time.sleep(FAIL_SLEEP)
                consecutive_fails = 0
        
        time.sleep(REQUEST_DELAY)

def main():
    global running
    
    print(f"{c.CYAN}{c.BOLD}  ACCANG {c.RESET}")
    print(f"{c.YELLOW}  NAME PREFIX   : {NAME_PREFIX}{c.RESET}")
    print(f"{c.YELLOW}  PASSWORD PREFIX: {PASS_PREFIX}{c.RESET}")
    print(f"{c.CYAN}  Region        : {REGION_NAME} ({REGION}){c.RESET}")
    print(f"{c.CYAN}  Threads       : {THREAD_COUNT}{c.RESET}")
    print(f"{c.CYAN}  Devices Pool  : {len(DEVICE_POOL)}{c.RESET}")
    print(f"{c.GREEN}[+] Starting...{c.RESET}")
    print()
    
    try:
        with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
            futures = [executor.submit(worker, i+1) for i in range(THREAD_COUNT)]
            for future in as_completed(futures):
                if not running:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                future.result()
    except KeyboardInterrupt:
        print(f"\n{c.RED}[!] Stopping...{c.RESET}")
        running = False
    except Exception as e:
        print(f"\n{c.RED}[!] ERROR: {e}{c.RESET}")
    
    time.sleep(1)
    logger.summary()

if __name__ == "__main__":
    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad
        main()
    except Exception as e:
        print(f"\n{c.RED}[!] ERROR: {e}{c.RESET}")
        sys.exit(0)