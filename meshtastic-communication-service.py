import time
import sys
import meshtastic
import meshtastic.serial_interface
import meshtastic.tcp_interface
from pubsub import pub
import json
import requests


USE_SERIAL = True 


TCP_HOST = "localhost" 

TARGET_NODE_ID = None 

emailmessageservice_host = "localhost"
emailmessageservice_port = 5000


class MeshBot:
    def __init__(self):
        print("Initializing MeshBot...")
        
        try:
            if USE_SERIAL:
                self.interface = meshtastic.serial_interface.SerialInterface()
            else:
                self.interface = meshtastic.tcp_interface.TCPInterface(hostname=TCP_HOST)
        except Exception as e:
            print(f"Error connecting to device: {e}")
            sys.exit(1)

        print(f"Connected to node: {self.interface.getMyNodeInfo()['user']['longName']}")
        print(f"Node ID: {self.interface.getMyNodeInfo()['user']['id']}")

        # 2. Subscribe to incoming text messages
        # The library uses pubsub to trigger events.
        pub.subscribe(self.on_receive, "meshtastic.receive.text")

    def on_receive(self, packet, interface):
        """
        Callback triggered when a text packet is received.
        """
        # Initialize default GPS coordinates to '0' strings
        gps_x = "0"
        gps_y = "0"

        try:
            # Parse packet details
            sender_id = packet.get('fromId')
            text_content = packet.get('decoded', {}).get('text', '')
            to_id = packet.get('toId')
            
            # Check if it is a Direct Message (DM)
            my_id = interface.getMyNodeInfo()['user']['id']
            
            is_dm = (to_id == my_id)
            
            print(f"Received {'DM' if is_dm else 'Broadcast'} from {sender_id}: {text_content}")

            if is_dm:
                print(f" >> Replying to {sender_id}...")

                if "bot: status" in text_content.lower():
                    self.send_dm(sender_id, f"Status: Online and listening :3")

                if "bot: kofi" in text_content.lower():
                    self.send_dm(sender_id, f"Support the Lousiana Mesh Community and get some cute stickers here: https://ko-fi.com/louisianameshcommunity/shop")

                if "bot: help" in text_content.lower():
                    time.sleep(3)
                    self.send_dm(sender_id, f"Hello, This bot is provided by the Louisiana Mesh Community")
                    time.sleep(3)
                    self.send_dm(sender_id, f"Commands: \n \n - bot: status \n - bot: help \n - bot: discord \n - bot: kofi \n - bot: weather \n - bot: weather help \n - bot: sms (dm's only) \n - bot: sms help (dm's only)")
                    time.sleep(5)
                    self.send_dm(sender_id, f"This bot is still a work in progess, all commands can be sent to either DM or main channel, if you have any bugs please send them in the discord >~<")

                if "bot: discord" in text_content.lower():
                    self.send_dm(sender_id, f"Join the Louisiana Mesh Community Discord here: https://discord.LouisianaMesh.org")

                if "bot: weather help" in text_content.lower():
                    self.send_dm(sender_id, f"You can both run the command [bot: weather] or [bot: weather [your zip code]] to get the current weather in your area")

                elif "bot: weather" in text_content.lower():

                    #check if the user is provided a zipcode
                    words = text_content.lower().split()
                    index = words.index("weather") + 1
                    if index < len(words) and words[index].isdigit():
                        zipcode = int(words[index])
                        print(f"Zipcode provided: {zipcode}")
                        url = f"http://{emailmessageservice_host}:{emailmessageservice_port}/get-weather"
                        payload = {'zipcode': zipcode, 'gps_x': 0, 'gps_y': 0}
                        response = requests.post(url, json=payload)
                        if response.status_code == 200:
                            data = response.json()
                                #convert Kelivin to Farenheit
                            data['main']['temp'] = round((data['main']['temp'] - 273.15) * 1.8 + 32)
                            self.send_dm(sender_id, f"Current weather in your area is: {data['main']['temp']} degrees F with a humidity of {data['main']['humidity']}% and {data['weather'][0]['description']}")
                        else:
                            self.send_dm(sender_id, f"Failed to fetch weather data")
                    else:
                        
                        #grabs user location
                        print("Grabbing location...")
                                # --- BEGIN NEW CODE BLOCK (Lines 92-97) ---
                        print(f"Grabbing location for remote client {sender_id}...")
                                
                                # 1. Attempt to get the last known location from the local node database
                        remote_node = interface.nodes.get(sender_id)
                                
                        if remote_node and 'position' in remote_node and remote_node['position']:
                            position_data = remote_node['position']
                                    
                            gps_x = str(position_data['latitudeI'] / 10000000.0)
                            gps_y = str(position_data['longitudeI'] / 10000000.0)
                            print(f"Location found in database: Lat {gps_x}, Lon {gps_y}")

                            #send request to email message service
                            url = f"http://{emailmessageservice_host}:{emailmessageservice_port}/get-weather"
                            payload = {'zipcode': 0, 'gps_x': gps_x, 'gps_y': gps_y}
                            response = requests.post(url, json=payload)
                            if response.status_code == 200:
                                data = response.json()
                                #convert Kelivin to Farenheit
                                data['main']['temp'] = round((data['main']['temp'] - 273.15) * 1.8 + 32)
                                self.send_dm(sender_id, f"Current weather in your area is: {data['main']['temp']} degrees F with a humidity of {data['main']['humidity']}% and {data['weather'][0]['description']}")
                            else:
                                self.send_dm(sender_id, f"Failed to fetch weather data")


                        else:
                            # If no location found, send a request to the remote node
                            print(f"Location not in database. Sending position request to {sender_id}...")

                            interface.sendPosition(destinationId=sender_id)
                                    
                            gps_x = "0"
                            gps_y = "0"
                                    
                                    # Notify the user that location could not be included in the immediate SMS
                            elf.send_dm(sender_id, "Warning: Your current location could not be retrieved in time. Please provide your Zipcode manually.")


                if "bot: sms help" == text_content.lower():
                    self.send_dm(sender_id, f"Please send the following information structured as seen here: Phone number,, Yes/No if you'd like to share you loction,, Cellular Provider,, Message")

                elif "bot: sms" in text_content.lower():
                    text_content = text_content[9:].strip()
                    parts = text_content.split(",, ")
                    if len(parts) == 4:
                        phone_number = parts[0]
                        send_location = parts[1].lower() == "yes"
                        cellular_provider = parts[2]
                        message = parts[3]
                        print(f" >> Processing message from {sender_id}: {phone_number}, {message}, {send_location}, {cellular_provider}")

                        if send_location:
                            print(f"Grabbing location for remote client {sender_id}...")

                            gps_x = "0"
                            gps_y = "0"

                                # --- BEGIN NEW CODE BLOCK (Lines 92-97) ---
                            print(f"Grabbing location for remote client {sender_id}...")
                                
                                # 1. Attempt to get the last known location from the local node database
                            remote_node = interface.nodes.get(sender_id)
                                    
                            if remote_node and 'position' in remote_node and remote_node['position']:
                                position_data = remote_node['position']
                                        

                                gps_x = str(position_data['latitudeI'] / 10000000.0)
                                gps_y = str(position_data['longitudeI'] / 10000000.0)
                                print(f"Location found in database: Lat {gps_x}, Lon {gps_y}")
                            # --- END NEW CODE BLOCK ---

                        # Only proceed if we received a valid location response
                        
                        #send post to email service

                        url = f"http://{emailmessageservice_host}:{emailmessageservice_port}/send-email"
                        data = {
                            "phone_number": phone_number,
                            "message": message,
                            "device_id": sender_id,
                            "gps_x": gps_x, # This uses the default "0" or the retrieved value
                            "gps_y": gps_y, # This uses the default "0" or the retrieved value
                            "moc": "0", # MOC is just a fancy word for meshtastic or core, 0 is meshtastic, 1 is core. The reason for this is to help with routing in responding to texts.
                            "celluar_provider": cellular_provider
                        }
                        headers = {
                            "Content-Type": "application/json"
                        }

                        response = requests.post(url, json=data, headers=headers)
                        if response.status_code == 200:
                            print(f" >> Email sent successfully to {phone_number}")
                            self.send_dm(sender_id, f"Message sent successfully to {phone_number}")
                        else:
                            print(f" >> Error sending Message to {phone_number}: {response.text}")
                            self.send_dm(sender_id, f"Error sending Message to {phone_number}: {response.text}")
                    else:
                        self.send_dm(sender_id, f"The message format is incorrect. Please try again or run [bot: sms help] for more information.")
                if "good girl" in text_content.lower():
                    self.send_dm(sender_id, f"aw, ty >~<")

                if ":3" in text_content.lower():
                    self.send_dm(sender_id, f":3")

                if "ping" == text_content.lower():
                    self.send_dm(sender_id, f"pong")

                
            # Example: Trigger command based on text
            if not is_dm:

                if "bot: help" in text_content.lower():
                    tine.sleep(3)
                    self.send_broadcast(f"Hello, This bot is provided by the Louisiana Mesh Community")
                    time.sleep(3)
                    self.send_broadcast(f"Commands: \n \n - bot: status \n - bot: help \n - bot: discord \n - bot: kofi \n - bot: weather \n - bot: weather help \n - bot: sms (dm's only) \n - bot: sms help (dm's only)")
                    time.sleep(5)
                    self.send_broadcast(f"This bot is still a work in progess, all commands can be sent to either DM or main channel, if you have any bugs please send them in the discord >~<")

                if "bot: status" in text_content.lower():
                    self.send_broadcast("Status: Online and listening :3")

                if "bot: discord" in text_content.lower():
                    self.send_broadcast(f"Join the Louisiana Mesh Community Discord here: https://discord.LouisianaMesh.org")

                if "bot: sms help" in text_content.lower():
                    self.send_broadcast(f"SMS commands can only be used in DM's")

                if "bot: sms" in text_content.lower():
                    self.send_broadcast(f"SMS commands can only be used in DM's")

                if "bot: kofi" in text_content.lower():
                    self.send_broadcast(f"Support the Lousiana Mesh Community and get some cute stickers here: https://ko-fi.com/louisianameshcommunity/shop")
                    
                if "good girl ><" == text_content.lower():
                    self.send_broadcast("aw, ty >~<")

                if ":3" in text_content.lower():
                    self.send_broadcast(":3")

                if "bot: weather help" in text_content.lower():
                    self.send_broadcast(f"You can both run the command [bot: weather] or [bot: weather [your zip code]] to get the current weather in your area")

                elif "bot: weather" in text_content.lower():

                    #check if the user is provided a zipcode
                    words = text_content.lower().split()
                    index = words.index("weather") + 1
                    if index < len(words) and words[index].isdigit():
                        zipcode = int(words[index])
                        print(f"Zipcode provided: {zipcode}")
                        url = f"http://{emailmessageservice_host}:{emailmessageservice_port}/get-weather"
                        payload = {'zipcode': zipcode, 'gps_x': 0, 'gps_y': 0}
                        response = requests.post(url, json=payload)
                        if response.status_code == 200:
                            data = response.json()
                                #convert Kelivin to Farenheit
                            data['main']['temp'] = round((data['main']['temp'] - 273.15) * 1.8 + 32)
                            self.send_broadcast(f"Current weather in your area is: {data['main']['temp']} degrees F with a humidity of {data['main']['humidity']}% and {data['weather'][0]['description']}")
                        else:
                            self.send_broadcast(f"Failed to fetch weather data")
                    else:
                        
                        #grabs user location
                        print("Grabbing location...")
                                # --- BEGIN NEW CODE BLOCK (Lines 92-97) ---
                        print(f"Grabbing location for remote client {sender_id}...")
                                
                                # 1. Attempt to get the last known location from the local node database
                        remote_node = interface.nodes.get(sender_id)
                                
                        if remote_node and 'position' in remote_node and remote_node['position']:
                            position_data = remote_node['position']
                                    

                            gps_x = str(position_data['latitudeI'] / 10000000.0)
                            gps_y = str(position_data['longitudeI'] / 10000000.0)
                            print(f"Location found in database: Lat {gps_x}, Lon {gps_y}")

                            #send request to email message service
                            url = f"http://{emailmessageservice_host}:{emailmessageservice_port}/get-weather"
                            payload = {'zipcode': 0, 'gps_x': gps_x, 'gps_y': gps_y}
                            response = requests.post(url, json=payload)
                            if response.status_code == 200:
                                data = response.json()
                                #convert Kelivin to Farenheit
                                data['main']['temp'] = round((data['main']['temp'] - 273.15) * 1.8 + 32)
                                self.send_broadcast(f"Current weather in your area is: {data['main']['temp']} degrees F with a humidity of {data['main']['humidity']}% and {data['weather'][0]['description']}")
                            else:
                                self.send_broadcast(f"Failed to fetch weather data")


                        else:
                            # 2. If no location found, send a request to the remote node
                            print(f"Location not in database. Sending position request to {sender_id}...")

                            interface.sendPosition(destinationId=sender_id)
                                    
                                    # Set coordinates to default "0" since we don't have the real-time answer yet
                            gps_x = "0"
                            gps_y = "0"
                                    
                                    # Notify the user that location could not be included in the immediate SMS
                            elf.send_broadcast("Warning: Your current location could not be retrieved in time. Please provide your Zipcode manually.")


                if "ping" == text_content.lower():
                    self.send_broadcast(f"pong")

        except KeyError:
            print("Error parsing packet fields.")

    def send_dm(self, destination_id, message):
        """
        Sends a Direct Message to a specific Node ID.
        """
        if not self.interface:
            print("Interface not initialized.")
            return

        print(f"Sending DM to {destination_id}: {message}")
        self.interface.sendText(message, destinationId=destination_id)
        time.sleep(3)

    def send_broadcast(self, message):
        """
        Sends a message to the public channel (Broadcast).
        """
        print(f"Broadcasting: {message}")
        self.interface.sendText(message)
        time.sleep(3)

    def run(self):
        """
        Keep the script running to listen for packets.
        """
        print("Bot is running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.interface.close()

if __name__ == "__main__":
    bot = MeshBot()
    
        
    bot.run()