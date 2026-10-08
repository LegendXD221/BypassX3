from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
from functools import wraps

app = Flask(__name__)
CORS(app)

# Stats tracking
stats = {
    'total_bypassed': 23387799,
    'success_count': 0,
    'failure_count': 0,
    'service_stats': {},
    'uptime': time.time()
}

# Rate limiting
request_counts = {}

def rate_limit(max_requests=200, window=900):  # 200 requests per 15 minutes
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = request.remote_addr
            current_time = time.time()
            
            if ip not in request_counts:
                request_counts[ip] = []
            
            # Remove old requests
            request_counts[ip] = [t for t in request_counts[ip] if current_time - t < window]
            
            if len(request_counts[ip]) >= max_requests:
                return jsonify({
                    'success': False,
                    'error': 'Too many requests. Please try again later.'
                }), 429
            
            request_counts[ip].append(current_time)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class BypassService:
    TIMEOUT = 30
    
    @staticmethod
    def bypass(url):
        """Main bypass function"""
        start_time = time.time()
        
        try:
            # Validate URL
            if not url or not BypassService.is_valid_url(url):
                return {
                    'success': False,
                    'service': 'Unknown',
                    'error': 'Invalid URL provided',
                    'processingTime': int((time.time() - start_time) * 1000)
                }
            
            # Detect service
            service = BypassService.detect_service(url)
            
            # Try bypass based on service
            if service == 'Linkvertise':
                result = BypassService.bypass_linkvertise(url)
            elif service == 'Work.ink':
                result = BypassService.bypass_workink(url)
            elif service == 'Lootlabs':
                result = BypassService.bypass_lootlabs(url)
            elif service == 'Rekonise':
                result = BypassService.bypass_rekonise(url)
            elif service == 'Platoboost':
                result = BypassService.bypass_platoboost(url)
            else:
                result = BypassService.universal_bypass(url)
            
            result['processingTime'] = int((time.time() - start_time) * 1000)
            result['service'] = service
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'service': 'Unknown',
                'error': str(e),
                'processingTime': int((time.time() - start_time) * 1000)
            }
    
    @staticmethod
    def bypass_linkvertise(url):
        """Linkvertise bypass"""
        try:
            # Try bypass API
            response = requests.post(
                'https://api.bypass.vip/bypass',
                json={'url': url},
                timeout=BypassService.TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('destination'):
                    return {
                        'success': True,
                        'destination': data['destination'],
                        'service': 'Linkvertise',
                        'processingTime': 0
                    }
        except:
            pass
        
        return BypassService.universal_bypass(url)
    
    @staticmethod
    def bypass_workink(url):
        """Work.ink bypass"""
        try:
            response = requests.get(
                url,
                timeout=BypassService.TIMEOUT,
                allow_redirects=False
            )
            
            # Check for redirect
            if 'location' in response.headers:
                return {
                    'success': True,
                    'destination': response.headers['location'],
                    'service': 'Work.ink',
                    'processingTime': 0
                }
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            link = soup.find('a', href=True)
            
            if link and BypassService.is_valid_url(link['href']):
                return {
                    'success': True,
                    'destination': link['href'],
                    'service': 'Work.ink',
                    'processingTime': 0
                }
        except:
            pass
        
        return BypassService.universal_bypass(url)
    
    @staticmethod
    def bypass_lootlabs(url):
        """Lootlabs bypass"""
        try:
            # Extract ID
            match = re.search(r'lootlabs\.gg/([a-zA-Z0-9]+)', url)
            if not match:
                raise Exception('Invalid Lootlabs URL')
            
            link_id = match.group(1)
            
            # Try API
            response = requests.get(
                f'https://api.lootlabs.gg/api/get-link/{link_id}',
                timeout=BypassService.TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('url'):
                    return {
                        'success': True,
                        'destination': data['url'],
                        'service': 'Lootlabs',
                        'processingTime': 0
                    }
        except:
            pass
        
        return BypassService.universal_bypass(url)
    
    @staticmethod
    def bypass_rekonise(url):
        """Rekonise bypass"""
        try:
            response = requests.get(url, timeout=BypassService.TIMEOUT)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try multiple patterns
            patterns = [
                r'destination["\s:]+["\'](https?://[^"\']+)["\']',
                r'target["\s:]+["\'](https?://[^"\']+)["\']',
                r'redirect["\s:]+["\'](https?://[^"\']+)["\']',
                r'url["\s:]+["\'](https?://[^"\']+)["\']'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response.text, re.IGNORECASE)
                if match and BypassService.is_valid_url(match.group(1)):
                    return {
                        'success': True,
                        'destination': match.group(1),
                        'service': 'Rekonise',
                        'processingTime': 0
                    }
        except:
            pass
        
        return BypassService.universal_bypass(url)
    
    @staticmethod
    def bypass_platoboost(url):
        """Platoboost bypass"""
        return BypassService.universal_bypass(url)
    
    @staticmethod
    def universal_bypass(url):
        """Universal bypass with multiple APIs"""
        apis = [
            {'url': 'https://api.bypass.vip/bypass', 'key': 'destination'},
            {'url': 'https://bypass.pm/bypass', 'key': 'result'},
        ]
        
        for api in apis:
            try:
                response = requests.post(
                    api['url'],
                    json={'url': url},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    destination = data.get(api['key'])
                    
                    if destination and BypassService.is_valid_url(destination):
                        return {
                            'success': True,
                            'destination': destination,
                            'service': 'Universal',
                            'processingTime': 0
                        }
            except:
                continue
        
        # Try direct extraction
        try:
            destination = BypassService.direct_extraction(url)
            if destination:
                return {
                    'success': True,
                    'destination': destination,
                    'service': 'Universal',
                    'processingTime': 0
                }
        except:
            pass
        
        return {
            'success': False,
            'service': 'Universal',
            'error': 'Unable to bypass this link',
            'processingTime': 0
        }
    
    @staticmethod
    def direct_extraction(url):
        """Direct extraction from HTML"""
        try:
            response = requests.get(
                url,
                timeout=BypassService.TIMEOUT,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            
            patterns = [
                r'destination["\s:]+["\'](https?://[^"\']+)["\']',
                r'target["\s:]+["\'](https?://[^"\']+)["\']',
                r'redirect["\s:]+["\'](https?://[^"\']+)["\']',
                r'href=["\'](https?://[^"\']+)["\']'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response.text, re.IGNORECASE)
                if match and BypassService.is_valid_url(match.group(1)):
                    return match.group(1)
            
            return None
        except:
            return None
    
    @staticmethod
    def detect_service(url):
        """Detect service from URL"""
        url_lower = url.lower()
        
        if 'linkvertise' in url_lower:
            return 'Linkvertise'
        elif 'work.ink' in url_lower:
            return 'Work.ink'
        elif 'lootlabs' in url_lower or 'loot-labs' in url_lower:
            return 'Lootlabs'
        elif 'admaven' in url_lower:
            return 'Admaven'
        elif 'lockr.so' in url_lower:
            return 'Lockr.so'
        elif 'shortfly' in url_lower or 'shrtfly' in url_lower:
            return 'Shrtfly'
        elif 'sub2unlock' in url_lower:
            return 'Sub2Unlock'
        elif 'rekonise' in url_lower:
            return 'Rekonise'
        elif 'boost.ink' in url_lower:
            return 'Boost.ink'
        elif 'mboost' in url_lower:
            return 'mBoost'
        elif 'platoboost' in url_lower:
            return 'Platoboost'
        
        return 'Universal'
    
    @staticmethod
    def is_valid_url(url):
        """Validate URL"""
        try:
            from urllib.parse import urlparse
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

# Routes

@app.route('/')
def home():
    return jsonify({
        'name': 'EVO Bypass API',
        'version': '2.0.0',
        'status': 'operational',
        'endpoints': {
            'health': '/api/health',
            'stats': '/api/stats',
            'bypass': '/api/bypass (POST)',
            'supported': '/api/supported'
        }
    })

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'operational',
        'uptime': int(time.time() - stats['uptime']),
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0'
    })

@app.route('/api/stats')
def get_stats():
    """Get statistics"""
    success_rate = '0%'
    if stats['success_count'] > 0:
        total = stats['success_count'] + stats['failure_count']
        success_rate = f"{(stats['success_count'] / total * 100):.2f}%"
    
    return jsonify({
        'success': True,
        'stats': {
            'total': stats['total_bypassed'],
            'success': stats['success_count'],
            'failure': stats['failure_count'],
            'successRate': success_rate,
            'services': stats['service_stats'],
            'uptime': int(time.time() - stats['uptime'])
        }
    })

@app.route('/api/bypass', methods=['POST'])
@rate_limit()
def bypass():
    """Main bypass endpoint"""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({
                'success': False,
                'error': 'URL is required'
            }), 400
        
        print(f'[BYPASS] Processing: {url}')
        
        # Perform bypass
        result = BypassService.bypass(url)
        
        # Update stats
        if result['success']:
            stats['total_bypassed'] += 1
            stats['success_count'] += 1
            service = result['service']
            stats['service_stats'][service] = stats['service_stats'].get(service, 0) + 1
            print(f'[SUCCESS] {service}: {result["destination"]}')
        else:
            stats['failure_count'] += 1
            print(f'[FAILURE] {result["error"]}')
        
        return jsonify(result)
        
    except Exception as e:
        print(f'[ERROR] {str(e)}')
        stats['failure_count'] += 1
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/api/supported')
def supported():
    """Get supported services"""
    return jsonify({
        'success': True,
        'services': [
            {'name': 'Linkvertise', 'status': 'active', 'category': 'Link Shortener'},
            {'name': 'Work.ink', 'status': 'active', 'category': 'Link Shortener'},
            {'name': 'Lootlabs', 'status': 'active', 'category': 'Link Shortener'},
            {'name': 'Rekonise', 'status': 'active', 'category': 'Social Unlock'},
            {'name': 'Platoboost', 'status': 'active', 'category': 'Key System'},
            {'name': 'Admaven', 'status': 'active', 'category': 'Link Shortener'},
            {'name': 'Lockr.so', 'status': 'active', 'category': 'Link Shortener'},
            {'name': 'Shrtfly', 'status': 'active', 'category': 'Link Shortener'},
            {'name': 'Sub2Unlock', 'status': 'active', 'category': 'Social Unlock'},
            {'name': 'Boost.ink', 'status': 'active', 'category': 'Link Shortener'},
            {'name': 'mBoost', 'status': 'active', 'category': 'Link Shortener'},
            {'name': 'Universal', 'status': 'active', 'category': 'Fallback'}
        ],
        'total': 30,
        'categories': ['Link Shortener', 'Social Unlock', 'Key System', 'Fallback']
    })

@app.route('/api/test')
def test():
    """Test endpoint"""
    return jsonify({
        'success': True,
        'message': 'API is working!',
        'timestamp': datetime.now().isoformat()
    })

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    print('=' * 50)
    print('   🚀 EVO BYPASS SERVER (Python/Flask)')
    print('=' * 50)
    print(f'   Port: 3000')
    print(f'   API: http://localhost:3000/api')
    print(f'   Health: http://localhost:3000/api/health')
    print('=' * 50)
    print('   Server is ready!')
    print('=' * 50)
    
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
