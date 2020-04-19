#!/usr/bin/env python

"""
 IoT Gateway Modbus
 (C)2020 - Michael Feil 
 This is distributed under MIT license, see LICENSE
"""

"""g_mqtt_client.py

Function: Opening the MQTT connection to the MQTT Bridge, maintaining connectivity, publish data and receiving configuration updates.

If publishing data, try to check for open connection and publish data, refresh connection as needed, sending constant heartbeats in background

If receiving configuration updates, check for validity with "g_schema_check". 
If valid, update setup_modbus.json and restart modbus g_modbus modules
"""

# [START includes]
import datetime
import os
import random
import ssl
import time
import threading
import queue
import json
import gzip, lzma
import sys



"""Python Samples for Google IoT Core: https://github.com/GoogleCloudPlatform/python-docs-samples/tree/master/iot/api-client/mqtt_example under Apache License 2.0"""
# [End includes]

#[includes own scripts]
from g_schema_check import modbus_json_check, logger, check_configuration_message
import g_shared_utils as su
from g_shared_utils import logger
#[includes own scripts]

# [Start GLOBAL Variables]
global publish_telemetry_list
publish_telemetry_list = list()

with open(su.setup_mqtt_filepath) as file: #open setup_mqtt.json
    global ALGORITHM, CA_CERTS, PRIVATE_KEY_FILE, JWT_EXPIRES_MINUTES
    global CLOUD_REGION, PROJECT_ID, REGISTRY_ID, DEVICE_ID, MQTT_BRIDGE_HOSTNAME, MQTT_BRIDGE_PORT, KEEPALIVE
    global PUFFER_LENGH, COMPRESSION
    global TOPIC_EVENT, TOPIC_STATE

    setup_json = json.load(file)

    ALGORITHM = setup_json["jwt_config"]["algorithm"]
    CA_CERTS            = os.path.join(su.directory_path, setup_json["jwt_config"]["ca_certs"])  
    PRIVATE_KEY_FILE    = os.path.join(su.directory_path, setup_json["jwt_config"]["private_key_file"])
    JWT_EXPIRES_MINUTES = int(setup_json["jwt_config"]["jwt_expires_minutes"])

    CLOUD_REGION = setup_json["cloud_destination"]["cloud_region"]
    PROJECT_ID = setup_json["cloud_destination"]["project_id"]
    REGISTRY_ID = setup_json["cloud_destination"]["registry_id"]
    DEVICE_ID = setup_json["cloud_destination"]["device_id"]
    MQTT_BRIDGE_HOSTNAME = setup_json["cloud_destination"]["mqtt_bridge_hostname"]
    MQTT_BRIDGE_PORT = int(setup_json["cloud_destination"]["mqtt_bridge_port"])
    KEEPALIVE = int(setup_json["cloud_destination"]["keepalive"])

    COMPRESSION = setup_json["paramteter_settings"]["compression"].lower()
    PUFFER_LENGH = setup_json["paramteter_settings"]["puffer_lengh"]

    TOPIC_EVENT = setup_json["global_topics"]["topic_event"]
    TOPIC_STATE = setup_json["global_topics"]["topic_state"]
    
# [End GLOBAL Variables]


# [Start helper_functions]
def formatted_publish_message(topic, payload, c_queue):
    global publish_telemetry_list
    global PUFFER_LENGH, COMPRESSION
    
    
    if topic == TOPIC_EVENT:
        publish_telemetry_list.append(payload)
        
        if len(publish_telemetry_list)>PUFFER_LENGH:
            accumulated_list = json.dumps(publish_telemetry_list, indent=0)
            
            if COMPRESSION == "gzip":
                accumulated_list = gzip.compress(data=accumulated_list.encode('utf-8'), compresslevel=9)
            elif COMPRESSION == "lzma":
                accumulated_list = lzma.compress(data=accumulated_list.encode('utf-8'),  preset=9)
                
            #print("size of {}".format(asizeof.asizeof(accumulated_list)))
            dic = {"sub_topic": TOPIC_EVENT,
                    "payload": accumulated_list,
                    "qos":1,
            }
            try:
                c_queue.put(dic, False)
            except queue.Full:
                pass

            
            publish_telemetry_list = list()

    if topic == TOPIC_STATE:
        payload = json.dumps(payload, indent=0)
        dic = {"sub_topic": TOPIC_STATE,
                "payload": payload,
                "qos":0,                    #qos 0 can improve stability of connection, as multiple send of different state messages with period of >1s leads to interval.
                }
        try:
            c_queue.put(dic, False)
        except queue.Full:
            pass
# [End helper_functions]

# [Start jwt]
def create_jwt(PROJECT_ID, PRIVATE_KEY_FILE, ALGORITHM):
    """Creates a JWT (https://jwt.io) to establish an MQTT connection.
        
         PROJECT_ID: Cloud Project ID
         PRIVATE_KEY_FILE: A path to the RSA256 or ES256 private key file.
         ALGORITHM: Either 'RS256' or 'ES256'

        Returns:
            A JWT generated from the given PROJECT_ID and private key, which
            expires after JWT_EXPIRES_MINUTES. After this time, the client will be
            disconnected.
        Raises:
            ValueError: If the PRIVATE_KEY_FILE does not contain a known key.
        """

    token = {
            # The time that the token was issued at
            'iat': datetime.datetime.utcnow(),
            # The time the token expires.
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=int(JWT_EXPIRES_MINUTES)),
            # The audience field should always be set to the GCP project id.
            'aud': PROJECT_ID
    }

    # Read the private key file.
    with open(PRIVATE_KEY_FILE, 'r') as f:
        private_key = f.read()

    logger.info('Creating JWT using {} from private key file {}'.format(
            ALGORITHM, PRIVATE_KEY_FILE))

    return jwt.encode(token, private_key, algorithm=ALGORITHM)
# [End jwt]
        
# [Start Class handle_mqtt]

class handle_mqtt(threading.Thread):
    global ALGORITHM, CA_CERTS, PRIVATE_KEY_FILE, JWT_EXPIRES_MINUTES
    global CLOUD_REGION, PROJECT_ID, REGISTRY_ID, DEVICE_ID, MQTT_BRIDGE_HOSTNAME, MQTT_BRIDGE_PORT, KEEPALIVE

    def __init__(self, publishing_queue, scheduler_obj, modbus_reader_obj):
        threading.Thread.__init__(self)

        self.publishing_queue = publishing_queue

        self.minimum_backoff_time = 2       # The initial backoff time after a disconnection occurs, in seconds, must be >1
        self.maximum_backoff_time = 128      # The maximum backoff time before giving up, in seconds.
        # flag the current connetion status
        self.should_backoff = False
        self.connection_working = False     
        self.run_publish = True
        
        self.scheduler_obj = scheduler_obj
        self.modbus_reader_obj = modbus_reader_obj

        self.last_messages_payloads = list() #last received messages of config subscription
        self.last_state_message_queued = datetime.datetime.utcnow()

        self.initial_start_client()
    
    def initial_start_client(self):
        #set up client

        #create unique client identifier in google cloud
        client_id = 'projects/{}/locations/{}/registries/{}/devices/{}'.format(
                PROJECT_ID, CLOUD_REGION, REGISTRY_ID, DEVICE_ID)
        logger.info('Device client_id is \'{}\''.format(client_id))
        self.client = mqtt.Client(client_id=client_id, clean_session=False) #broker remembers subscriptions, once connected

        # Enable SSL/TLS support.
        self.client.tls_set(ca_certs=CA_CERTS, tls_version=ssl.PROTOCOL_TLSv1_2)

        # enables maximum messages for publishing queued, further messages dropped
        self.client.max_queued_messages_set(queue_size=200)

        # This is the topic that the device will receive configuration updates on.
        self.mqtt_config_topic = '/devices/{}/config'.format(DEVICE_ID)

        # The topic that the device will receive commands on.
        self.mqtt_command_topic = '/devices/{}/commands/#'.format(DEVICE_ID)

        
     # [Start Paho MQTT CALLBACKS]
    def on_connect(self, unused_client, unused_userdata, unused_flags, rc):
        try:
            """Callback for when a device connects."""
            logger.info('on_connect:{}'.format( mqtt.connack_string(rc)))

            # After a successful connect, reset backoff time and stop backing off.
            self.should_backoff = False
            self.minimum_backoff_time = 2
            logger.info('Subscribing to {} and {}'.format(self.mqtt_command_topic, self.mqtt_config_topic))

            # Subscribe to the config topic, QoS 1 enables message acknowledgement.
            self.client.subscribe(self.mqtt_config_topic, qos=1)          

            # Subscribe to the commands topic, QoS not used
            self.client.subscribe(self.mqtt_command_topic, qos=0)
            
        except Exception as e:
            logger.error("Error in Paho Callback on_connect{}",format(e))


    def on_disconnect(self, unused_client, unused_userdata, rc):
        """Paho callback for when a device disconnects."""
        try:
            logger.warning('on_disconnect callback reason:  {}: {}'.format(rc, mqtt.error_string(rc)))

            # Since a disconnect occurred, the next loop iteration will wait with
            # exponential backoff.
            self.should_backoff = True
        except Exception as e:
            logger.error("Error in Paho Callback on_disconnect{}",format(e))


    def on_publish(self, unused_client, unused_userdata, unused_mid):
        """Paho callback when a message is sent to the broker."""
        try:
            logger.info('on_publish')
        except Exception as e:
            logger.error("Error in Paho Callback on_publish {}",format(e))

    def on_log(self,client, userdata, level, buf):
        """Paho callback when a client has logging information """
        
        logger.debug("Paho Log: {} ".format(buf))
        


    def on_message(self, unused_client, unused_userdata, message):
        """Callback when the device receives a message on a subscription."""
        try:
            payload = str(message.payload.decode('utf-8'))
            logger.info(' Received message \'{}\' on topic \'{}\' with Qos {}'.format(
                    payload, message.topic, str(message.qos)))

        except Exception as e:
            logger.error("Error in Paho Callback on_message {}",format(e))


    def config_on_message(self, unused_client, unused_userdata, message):
        """Callback when the device receives a config message on the config subscription."""
        try:
            config_payload = str(message.payload.decode('utf-8'))

            if config_payload not in self.last_messages_payloads:
                """if config message received that was not received earlier"""
                logger.info("new config message received")
                self.last_messages_payloads.append(config_payload)
                
                self.last_messages_payloads = self.last_messages_payloads[-5:] #keep only most recent messages
            
                #[Start Config Update]
                #check_configuration_message(config_payload, self.scheduler_obj, self.modbus_reader_obj, self.publishing_queue) #gets final result update implemented [True/False] and log
                #[End Config Update]
                
                t = threading.Thread(target=check_configuration_message, args=(config_payload, self.scheduler_obj, self.modbus_reader_obj, self.publishing_queue,) )
                t.setDaemon = True
                t.start()

            else:
                """if config message received that was received earlier, e.g. through QoS1 MQTT Subscription"""
                logger.info("Existing config message received again")
        except Exception as e:
            logger.error("Error in Paho Callback config_on_message {}",format(e))

    
    # [END Paho MQTT CALLBACKS]



    # [START iot_mqtt_connection]          
    def do_exponential_backoff(self):
        """How long to wait with exponential backoff before publishing, when backoff"""
        if self.minimum_backoff_time <= 1 or self.maximum_backoff_time < self.minimum_backoff_time: #no exponential backoff possible
            self.minimum_backoff_time = 2

        # If backoff time is too large, give up.
        if self.minimum_backoff_time > self.maximum_backoff_time:
            logger.warning('Exceeded maximum backoff time.')
            self.should_backoff = False
            self.minimum_backoff_time = 16

        # Otherwise, wait and connect again.
        delay = self.minimum_backoff_time + random.randint(0, 1000) / 1000.0
        logger.info('Waiting for {} seconds before reconnecting.'.format(delay))
        time.sleep(max(0,delay)) 
        self.minimum_backoff_time *= 2
        

    def start_new_connection(self):
        """restarts the connection"""

        self.connection_working = False

        

        while self.connection_working == False:
            try:
                # Register message callbacks. https://eclipse.org/paho/clients/python/docs/

                self.client.on_connect = self.on_connect
                self.client.on_publish = self.on_publish
                self.client.on_disconnect = self.on_disconnect
                self.client.on_message = self.on_message
                self.client.on_log = self.on_log
                self.client.message_callback_add(self.mqtt_config_topic, self.config_on_message)


                self.jwt_iat = datetime.datetime.utcnow()
                # With Google Cloud IoT Core, the username field is ignored, and the
                # password field is used to transmit a JWT to authorize the device.
                self.client.username_pw_set(
                        username='unused',
                        password=create_jwt(
                                PROJECT_ID, PRIVATE_KEY_FILE, ALGORITHM))

                # Connect to the Google MQTT bridge.
                self.client.connect(MQTT_BRIDGE_HOSTNAME, MQTT_BRIDGE_PORT, KEEPALIVE)

                
                #runs a thread in the background to call loop() for paho mqtt client automatically
                self.client.loop_start() #should ignore if running

                

                #success, set flags
                self.should_backoff = False #not guaranteed yet, in case of immidiate disconnect, flag will be set in 2-3 seconds
                self.connection_working = True
                self.should_backoff = False
                self.last_client_restart = datetime.datetime.utcnow()  #logging startup time, so in the next seconds, don't publish to many messages

                time.sleep(2)


            except Exception as e:
                self.connection_working = False
                logger.warning('An error occured during setting up the connection {}'.format(e))
                self.do_exponential_backoff()

    # [END iot_mqtt_connection]

    # [START iot_mqtt_run]
    def publish_data(self):
        """Publish data from the publishing queue via MQTT

        start_new_connection and initial_start_client must be run first. 
        Will do nothing if self.connection_working and self.run_publish are not set to true beforehand.
        """
        
        try:
            while self.connection_working == True and self.run_publish == True:
                
                # [Start Queue message from queue]
                while True:
                    try:
                        #[Start Do Exponential Backoff and Reconnect]
                        if self.should_backoff and (datetime.datetime.utcnow() - self.last_client_restart).seconds > 5:
                            logger.info("Backoff detected, reconnect")
                            self.do_exponential_backoff()
                            self.start_new_connection() 
                    
                        #[End Do Exponential Backoff and Reconnect]

                        publish_request = self.publishing_queue.get(timeout=1) #wait for newest message from publishing_queue that is queued to be puplished
                        break #if element was in queue 
                    
                    except queue.Empty:
                        pass
                        
                sub_topic = publish_request["sub_topic"]
                payload = publish_request["payload"]
                qos = int(publish_request["qos"])
                
                mqtt_topic = "/devices/{}/{}".format(DEVICE_ID, sub_topic) #where message is published
                # [End message from queue]

                # [START jwt_refresh]
                seconds_since_issue = (datetime.datetime.utcnow() - self.jwt_iat).seconds 
                if seconds_since_issue + 60 >= int(60 * JWT_EXPIRES_MINUTES):
                    logger.info("Refreshing JWT token and connection after {}s".format(seconds_since_issue))
                    self.start_new_connection()
                # [END jwt_refresh]

                # [START Precaution before publish on recent opened connection]
                elapsed_seconds_since_restart = (datetime.datetime.utcnow() - self.last_client_restart).seconds
                if elapsed_seconds_since_restart < 20: #if paho mqtt not ready
                    if elapsed_seconds_since_restart < 5:
                        logger.debug("MQTT just after connection restart, pausing message send for 5 seconds")
                        time.sleep(max(0, 5-elapsed_seconds_since_restart)) #up to 5 seconds sleep
                    if qos == 0:
                        logger.debug("Set message from qos 0 to qos 1")
                        qos = 1 #set to qos 1 until stable connection and fully set up
                # [END Precaution before publish on recent opened connection]
                
                # [Start State messages delay]
                if sub_topic == TOPIC_STATE:
                    #TOPIC_STATE can be refreshed no more than once per second & 6000 times per minute per project in the Google Cloud, optimum once each 5 or 10 seconds max.
                    time_difference_state = (datetime.datetime.utcnow() - self.last_state_message_queued).seconds

                    if 0 <= time_difference_state < 5:
                        logger.info("State message, Sleeping for {}".format(5-time_difference_state))
                        time.sleep(max(0, 5-time_difference_state))            

                    self.last_state_message_queued = datetime.datetime.utcnow()
                # [End State messages delay]

                self.client.publish(mqtt_topic, payload, qos=qos, retain=True) # Publish payload to the MQTT topic. 
                
                self.publishing_queue.task_done()    

        except Exception as e:
            logger.error('An error occured during publishing data {}'.format(e))
            self.connection_working == False            

    def run(self):
        self.start_publish()

    def start_publish(self):
        logger.debug("Start the MQTT CLIENT")
        self.run_publish = True
        while self.run_publish == True:
            self.start_new_connection()
            self.publish_data()
        logger.debug("Ended the MQTT CLIENT")

    def end_publish(self):
        self.run_publish = False

# [END Class handle_mqtt]