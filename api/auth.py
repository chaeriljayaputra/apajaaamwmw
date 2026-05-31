from functools import wraps
from flask import request, jsonify
from api.database import validate_api_key, log_request

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'API_KEY_REQUIRED'
            }), 401
        
        key_info = validate_api_key(api_key)
        
        if not key_info:
            return jsonify({
                'success': False,
                'error': 'INVALID_API_KEY'
            }), 401
        
        request.api_key = api_key
        request.key_info = key_info
        
        log_request(api_key, request.endpoint, 'success', request.remote_addr, request.headers.get('User-Agent', ''))
        
        return f(*args, **kwargs)
    return decorated
