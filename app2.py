from flask import Flask, request, jsonify
import requests
import socket
from stem import Signal
from stem.control import Controller

# List of URLs to fetch proxies from
PROXY_URLS = [
    "https://raw.githubusercontent.com/B4RC0DE-TM/proxy-list/main/SOCKS5.txt",
    "https://raw.githubusercontent.com/saschazesiger/Free-Proxies/master/proxies/socks5.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt",
    "https://raw.githubusercontent.com/HyperBeats/proxy-list/main/socks5.txt",
    "https://api.openproxylist.xyz/socks5.txt",
    "https://raw.githubusercontent.com/manuGMG/proxy-365/main/SOCKS5.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies_anonymous/socks5.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/BlackSnowDot/proxylist-update-every-minute/main/socks.txt",
    "https://proxyspace.pro/socks5.txt",
    "https://api.proxyscrape.com/?request=displayproxies&proxytype=socks5",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all&simplified=true",
    "http://worm.rip/socks5.txt",
    "http://www.socks24.org/feeds/posts/default",
    "https://www.proxy-list.download/api/v1/get?type=socks5",
    "https://www.proxyscan.io/download?type=socks5",
    "https://www.my-proxy.com/free-socks-5-proxy.html"
]

app = Flask(__name__)

# Use a function to change IP via Tor
def renew_tor_ip():
    with Controller.from_port(port=9051) as controller:
        controller.authenticate(password='your_password')  # Set your Tor password in the config
        controller.signal(Signal.NEWNYM)  # Request a new identity

# Function to fetch and validate proxies
def fetch_and_test_proxies():
    working_proxies = []
    for url in PROXY_URLS:
        try:
            # Fetch the proxy list from the URL
            response = requests.get(url)
            if response.status_code == 200:
                proxies = response.text.splitlines()
                # Test each proxy
                for proxy in proxies:
                    proxy = proxy.strip()
                    if test_proxy(proxy):
                        working_proxies.append(proxy)
        except Exception as e:
            print(f"Error fetching proxy list from {url}: {e}")
    
    return working_proxies

# Test if a proxy is working by sending a request through it
def test_proxy(proxy):
    test_url = "http://httpbin.org/ip"
    proxies = {
        'http': f'socks5://{proxy}',
        'https': f'socks5://{proxy}'
    }
    try:
        response = requests.get(test_url, proxies=proxies, timeout=5)
        if response.status_code == 200:
            print(f"Proxy {proxy} is working.")
            return True
    except Exception as e:
        print(f"Proxy {proxy} failed: {e}")
    return False

# Function to resolve the onion site via Tor proxy or working proxy
def resolve_onion(onion_url, proxies=None):
    session = requests.Session()

    if proxies:
        # Choose a random proxy from the working proxy list
        proxy = proxies[0]  # Use the first working proxy; you can shuffle or randomize as needed
        session.proxies = {
            'http': f'socks5h://{proxy}',
            'https': f'socks5h://{proxy}'
        }
    else:
        # Use Tor as the proxy
        session.proxies = {
            'http': 'socks5h://127.0.0.1:9050',
            'https': 'socks5h://127.0.0.1:9050'
        }

    try:
        # Try to access the .onion site through Tor or the proxy
        response = session.get(onion_url, timeout=10)

        # Grab server headers
        server_headers = response.headers

        # Check for any IP-related leaks in headers (e.g., via X-Forwarded-For)
        ip_leak_info = server_headers.get('X-Forwarded-For', 'No IP leak detected')

        return {
            "status_code": response.status_code,
            "headers": dict(server_headers),
            "ip_leak_info": ip_leak_info,
            "content": response.text[:500]  # Return first 500 chars of the response content
        }

    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

# Function to attempt direct DNS resolution (may not work if the onion service is properly hidden)
def attempt_dns_resolution(onion_url):
    try:
        hostname = onion_url.replace("http://", "").replace("https://", "").split('/')[0]
        ip_address = socket.gethostbyname(hostname)
        return ip_address
    except socket.gaierror:
        return "DNS resolution failed (expected for .onion sites)"

@app.route('/resolve', methods=['POST'])
def resolve():
    # Get the onion URL from the request
    data = request.json
    onion_url = data.get('url')

    if not onion_url:
        return jsonify({"error": "No URL provided"}), 400

    if not onion_url.endswith('.onion'):
        return jsonify({"error": "Invalid .onion URL"}), 400

    # Fetch and test proxies
    working_proxies = fetch_and_test_proxies()

    # Resolve the onion URL through Tor proxy or working proxy
    onion_result = resolve_onion(onion_url, working_proxies)

    # Attempt to resolve the onion URL via DNS (this likely fails unless there's a misconfiguration)
    dns_result = attempt_dns_resolution(onion_url)

    return jsonify({
        "onion_result": onion_result,
        "dns_resolution": dns_result
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
