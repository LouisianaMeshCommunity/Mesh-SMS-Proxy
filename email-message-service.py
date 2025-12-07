#imports
from flask import Flask, request, jsonify
import requests
import json

import smtplib 

app = Flask(__name__)

#config

# pull from config.json
with open('config.json', 'r') as f:
    config = json.load(f)

SMTP_SERVER = config['smtp_server']
SMTP_PORT = config['smtp_port']
SMTP_USERNAME = config['smtp_username']
SMTP_PASSWORD = config['smtp_password']
openweather_api_key = config['openweather_api_key']

meshtastic_ip = 0
meshcore_ip = 0

#functions

def _send_email_helper(recipient, subject, body): 
    # Use '\r\n' for proper email message separation
    message = f"Subject: {subject}\r\n\r\n{body}" 
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_USERNAME, recipient, message)
        server.quit()
        # Optionally return success status
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        # Optionally return failure status
        return False

@app.route('/', methods=['GET'])
def status():
    return ("Email Message Service is running, built by Lenley Ngo for LMesh", 200)





#Allow clients to send their ip to connect to
@app.route('/connect-meshtastic', methods=['POST'])
def connect_meshtastic_ip():
    global meshtastic_ip

    if 'meshtastic_ip' not in request.json:
        return jsonify({"error": "Missing 'meshtastic_ip' in request body"}), 400
        
    meshtastic_ip = request.json['meshtastic_ip']
    return ("Received meshtastic ip", 200)


@app.route('/connect-meshcore', methods=['POST'])
def connect_meshcore_ip():
    global meshcore_ip

    if 'meshcore_ip' not in request.json:
        return jsonify({"error": "Missing 'meshcore_ip' in request body"}), 400
        
    meshcore_ip = request.json['meshcore_ip']
    return ("Received meshcore ip", 200)

# weather api route

@app.route('/get-weather', methods=['POST'])
def get_weather():
    print("Received weather request")
    try:
        zipcode = request.json['zipcode']
        gps_x = request.json['gps_x']
        gps_y = request.json['gps_y']
    except Exception as e:
        print(e)
        return jsonify({"error": f"Missing required data in request: {e}"}), 400

    print(zipcode)
    if zipcode != 0:
        #send request to openweather api
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={zipcode}&limit=1&appid={openweather_api_key}"
        response = requests.get(url)
        print(response)
        if response.status_code == 200:
            data = response.json()
            gps_x = data[0]['lat']
            gps_y = data[0]['lon']
        else:
            return jsonify({"error": "Failed to fetch zipcode data"}), 500
        

    url = f"https://api.openweathermap.org/data/2.5/weather?lat={gps_x}&lon={gps_y}&appid={openweather_api_key}"
    print(url)
    
    response = requests.get(url)
    print(response)
    if response.status_code == 200:
        data = response.json()
        return jsonify(data), 200
        print(data)
    else:
        return jsonify({"error": "Failed to fetch weather data"}), 500



# Send message 
@app.route('/send-email', methods=['POST'])

def send_email(): 

    try:
        phone_number = request.json['phone_number']
        message = request.json['message']
        device_id = request.json['device_id']
        gps_x = request.json['gps_x']
        gps_y = request.json['gps_y']
        moc = request.json['moc']
        celluar_provider = request.json['celluar_provider']
    except Exception as e:
        return jsonify({"error": f"Missing required data in request: {e}"}), 400

    if gps_x == "0" and gps_y == "0":
        gps_combined = "Not Provided"
    else:
        gps_combined = f"{gps_x}, {gps_y}"

    sendmessage = (f"This is a message sent by the SMS Proxy Service provided by the Louisiana Mesh Community. \n \n Device Info: \n Device ID: {device_id} - {moc} \n GPS: {gps_combined} \n \n \n Message: {message}")

    if celluar_provider.lower() == "at&t":
        recipient = f"{phone_number}@txt.att.net" # Assuming 'att' prefix was a typo
    elif celluar_provider.lower() == "google-fi":
        recipient = f"{phone_number}@msg.fi.google.com"
    elif celluar_provider.lower() == "verizon":
        recipient = f"{phone_number}@vtext.com"
    elif celluar_provider.lower() == "t-mobile" or celluar_provider.lower() == "tmobile":
        recipient = f"{phone_number}@tmomail.net"
    elif celluar_provider.lower() == "consumer-cellular" or celluar_provider.lower() == "consumercellular":
        recipient = f"{phone_number}@mailmymobile.net"
    else:
        return jsonify({"error": f"Unknown cellular provider"}), 400 

    print(f"Sending email to: {recipient}, message: {sendmessage}")

    email_success = _send_email_helper(recipient, "", sendmessage) 
    
    if email_success:
        return ("Email sent successfully", 200)
    else:
        # Return a 500 status code for server-side errors
        return ("Error sending email", 500) 

if __name__ == '__main__':
    app.run(debug=True)