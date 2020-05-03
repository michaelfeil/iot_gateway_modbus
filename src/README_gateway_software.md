# IoT Edge Gateway Software:

## Scope of this readme:

### Part 1:
- Overview over the Source code and Concept
### Part 2:
- Deploy Google IoT Core
### Part 3: 
- How to configure the IoT Device
### Part 4: 
- Overview over the Performance

# Part 1: Overview over the Source code and Concept

![alt text](https://github.com/michaelfeil/iot_gateway_modbus/blob/master/pngs/mqttclient_modbusrtu_communication.png "Python modules communication workflow")

# Part 2: 
Deploy a Google IoT Core Instance:
Follow the [instructions from Google](https://cloud.google.com/iot/docs/how-tos/devices). If you already deployed a Google IoT Core to GCP, you should extract the following information:


If you already have a Registry, extract these settings:
- registry ID (e.g. "reg__id")
- cloud region (e.g. "europe-west")
- project_id (e.g."project_id")
- default topic for telemetry (e.g."events")
- default topic for device state (e.g. "state")
- remove CA root or provide your own one. 

- confirm, that MQTT is allowed as protocol!
- Set Stackdriver logging as needed.
![alt text](https://github.com/michaelfeil/iot_gateway_modbus/blob/master/pngs/google_iot_core.png "Demo Deployment of registry")

When creating a new device in this registry, please also remember these two for later:

Device Settings:
- device ID (e.g. "mydeviceid")
- *public* RSA Key file as .pem, following this [tutorial](https://cloud.google.com/iot/docs/how-tos/credentials/keys). Basically in any unix/linux environment type:
```bash
openssl genpkey -algorithm RSA -out rsa_private_key.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -in rsa_private_key.pem -pubout -out rsa_public.pem
```

![alt text](https://github.com/michaelfeil/iot_gateway_modbus/blob/master/pngs/create_device.png "Demo Deployment of device")


# Part 3: How to configure the IoT Device:

Use this software:
1. install libaries from requirements.txt and python 3.7.7
2. clone "src" folder on computer ```bash git clone https://github.com/michaelfeil/iot_gateway_modbus ```
3. provide .pem files. 3.1 private key under "src/certificates/your_private_key.pem" and 3.2 CA root as in registry or from [default](https://pki.google.com/roots.pem) "src/certificates/ca_root.pem"
4. modify "src/setup_files/setup_mqtt.json" according to GCP cloud settings and your key.pem files.
5. connect modbus to serial port
6. modify "src/setup_files/setup_modbus.json" according to connected modbus and 
7. run python startup_solution.py

Optional:
8. Update setup_modbus.json from the GCP IoT Core

Details for 6. setup_modbus.json:
Preconfigure the setup_modbus.json: (This part can be updated from the Google IoT Core and configuration for device.)

```javascript
{
    "port_config": {                                #serial port coniguration, configures python Serial.Serial
        "port"		: "COM6",                   #"/dev/ttySC0" for linux or "COM" for windows
        "baudrate"	: 9600,
        "databits"	: 8,
        "parity"	: "N",
        "stopbits"	: 1,
        "timeout_connection": 2.0
    },
    "slaveconfig": {                                #configuration for all slaves over this port, configures python Modbus_TK
        "slave01": {                                #any custom name, must be unique
            "slave_id": 2,                          #Modbus SlaveID
            "operations": {                         # must be called: "operations"
                "operation01": {                    #any custom name, must be unique
                    "startadress": 6,               #startadress, in this case 0006 or 6
                    "function_code": 3,             #modbus function code
                    "display_name": "sensor01_6-7", #custom name, that will be sent with MQTT
                    "sampling_interval": 1,         #sampling inverval, in seconds between 0.1 and 864001, recommended >0.5
                    "quantity_of_x": 2              #how many reads, in this case, value of 40006 and 40007 will be returned
                },
                "operation02": {                    #any custom name, must be unique, e.g. in this case not "operation01"
                    "startadress": 109,
                    "function_code": 3,
                    "display_name": "myname-109",
                    "sampling_interval": 0.1,
                    "quantity_of_x": 1
                }
            }
        },
        "slave02": {                                #second slave with different slave_id
            "slave_id": 28,
            "operations": {
                "operation01": {
                    "startadress": 107,
                    "function_code": 3,
                    "display_name": "power_02_107-110",
                    "sampling_interval": 60,
                    "quantity_of_x": 4                    
                }
            }
        }
    }
}
```

Details for 4. setup_modbus.json:
Preconfigure the setup_mqtt.json: (This part is static, not changed with the Cloud Connection)

```python
{
	"jwt_config": {
		"algorithm"			:	"RS256",                                    #Which encryption algorithm to use to generate the JWT.
		"ca_certs"			:	"resources/roots.pem",                      #CA root from https://pki.google.com/roots.pem or other CA root
		"private_key_file"		:	"resources/your_private_key_file.pem",      #Path to private key file.
		"jwt_expires_minutes"		:	120                                          #Expiration time, in minutes, for JWT tokens. notlonger then 24h, recommended 60mins
	},
	"cloud_destination": {
		"cloud_region"			:	"us-central1",								#Cloud_region
		"device_id"			:	"your_device",								#IoT Core Device name		
		"project_id"			:	"yourproj-0815",							#project name		
		"registry_id"			:	"your_reg_id",							    #IoT Core Registry ID
		"mqtt_bridge_hostname"		:	"mqtt.googleapis.com",                      #MQTT bridge hostname
		"mqtt_bridge_port"		:	8883,	                                    #Choices : 8883 or 443.     MQTT bridge port.
		"keepalive"			:	240                                         #MQTT Heartbeat Frequency in seconds, best practice 60 or 120 seconds,  should not exceed max of 20 minutes
	},
	"paramteter_settings"	: {
		"puffer_lengh"			:	250,                                        #Now many sensor reads / RTU requests to accumulate before publishing. Best Practice: Size of Slave reads per 10 minutes
		"compression"			:	"gzip"                                      #String, Choice: "gzip", "lzma" or  "None". With "gzip" and "lzma", encoding json as utf-8 message and compressing. Reduces transmit data by Factor ~10
	},
	"global_topics": {                                                          #must be preconfigured in Cloud, IoT Core default is "events" and "state", otherwise will fail
		"topic_event"           	:	"events",                                   #topic for MQTT messages containing telemetry/sensor data, 
		"topic_state"           	:	"state"                                     #topic for MQTT messages containing status updates or critical errors, 
	}
}
```
Details for 8.: Update setup_modbus.json from the GCP IoT Core

To update send the following configuration as "text":

configuration_update_modbus

content_start
{
your_valid_json
}
content_end

once received, the IoT Device will stick to the Configuration. The IoT Device will report the configuration state once received.

If the configuration message is not vaild, the IoT Device will ignore the message and will set a device state, declaring why the configuration is invalid.

![alt text](https://github.com/michaelfeil/iot_gateway_modbus/blob/master/pngs/deployment_instructions.png "Deployment from GCP Portal")


# Part 4: Key Performance Characteristics:

Performance Total RAM Usage:
- irrelevant for most systems
- 20mb / e.g. runs on Raspberry Pi1 b+ without any efforts

Performance Modbus-Reader:
-   When Reading only 1 Register per Slave at a time: 7-9 Slaves per second at 19200 BAUD
-   When Reading 32-96 Register per Slave at a time: 3-5 Slaves per second,  at 19200 BAUD

Performance MQTT Module:
- sending MQTT messages containing with a single value: ~1500 Single values per Minute (bigger than Maximum read of Modbus Slaves per Minute which is ~550  )
