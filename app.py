import logging
import time
from flask import Flask, request, render_template, jsonify
import requests
from stem import Signal
from stem.control import Controller

app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='tor_dns_resolver.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

# Function to control Tor (for a new IP and anonymity)
def renew_tor_identity():
    try:
        with Controller.from_port(port=9051) as controller:
            controller.authenticate(password='your_password')  # Replace with your password
            controller.signal(Signal.NEWNYM)  # Request a new Tor identity
            logging.info("Tor IP address has been renewed.")
    except Exception as e:
        logging.error(f"Error renewing Tor IP: {str(e)}")

# Proxy through Tor to access .onion websites
def resolve_onion_site(onion_url):
    session = requests.Session()
    session.proxies = {
        'http': 'socks5h://127.0.0.1:9050',  # Use the Tor SOCKS5 proxy
        'https': 'socks5h://127.0.0.1:9050'
    }

    try:
        # Measure the time it takes to resolve the onion service
        start_time = time.time()
        response = session.get(onion_url, timeout=30)
        elapsed_time = time.time() - start_time

        # Log success
        logging.info(f"Successfully resolved {onion_url} with status code {response.status_code}")

        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content_length": len(response.content),
            "latency": round(elapsed_time, 2),  # Time in seconds
        }
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to resolve {onion_url}: {str(e)}")
        return {"error": str(e)}

# Home page with form to input onion URL
@app.route('/')
def index():
    return render_template('index.html')

# Endpoint to resolve the onion service
@app.route('/resolve', methods=['POST'])
def resolve():
    onion_url = request.form.get('onion_url')

    if not onion_url or not onion_url.endswith('.onion'):
        return jsonify({"error": "Invalid .onion URL"}), 400

    # Log the onion URL being resolved
    logging.info(f"Resolving .onion URL: {onion_url}")

    # Renew Tor identity to ensure anonymity
    renew_tor_identity()

    # Try to resolve the .onion website and fetch response info
    result = resolve_onion_site(onion_url)

    return jsonify(result)

# Tor Circuit Info
@app.route('/circuit')
def circuit():
    try:
        with Controller.from_port(port=9051) as controller:
            controller.authenticate(password='your_password')  # Replace with your password
            circuit_info = controller.get_circuits()
            formatted_circuits = []

            for circuit in circuit_info:
                nodes = [controller.get_network_status(fingerprint).address for fingerprint in circuit.path]
                formatted_circuits.append(nodes)

            return jsonify({"circuits": formatted_circuits})
    except Exception as e:
        logging.error(f"Error fetching Tor circuit info: {str(e)}")
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
