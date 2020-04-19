# IoT Edge Gateway Software:

## Scope of this solution:
	This software is a "IoT Gateway Solution" for Modbus RTU. 
	
	The intitial reason for starting this solution was the need for a Gateway for Solar Microgrids.
	Microgrids installed e.g. by NGOs in Eastern Africa require a monitoring system, to prove project success and guarantee maintaince. 
	However energy sources occasionally in remote locations and making monitoring difficult. 

	Installed on a Linux/Windows computer, e.g. a Raspberry PI and a Modbus RTU over USB, a cost-effective solution is enabled. 
	Many existing sensors and equipment have the option to communicate over Modbus.

## As provided this solution offers:
- Cloud: Google IoT Core
	- deploying and changing Modbus configuration from the GCP.
	- Connection using Paho MQTT Client
	- low data usage: compression using gzip and multiple sensor measurement at once

- Modbus: Modbus RTU: RS232, RS485 over USB.
	- read 5-10 Modbus RTU Slaves per Second
	- schedule indivdual for every sensor
	- handling of all modbus

## Scope of this readme:

### Part 1:
- Overview over the Source code and Concept
### Part 2: 
- How to configure and use this solution
### Part 3: 
- Overview over the Performance

# Part 1: Overview over the Source code and Concept

![alt text](https://github.com/michaelfeil/iot_gateway_modbus/tree/master/pngs/mqttclient_modbusrtu_communication_workflow.png "Python modules communication workflow")




# Part 2: How to configure and use this solution:

Use this software:
1. install libaries from requirements.txt and python 3.7.7
2. clone "src" folder on computer
3. provide .pem files under "src/certificates/your_private_key.pem" and "src/certificates/ca_root.pem"
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
		"ca_certs"			:	"resources/roots.pem",                      #CA root from https://pki.google.com/roots.pem
		"private_key_file"		:	"resources/your_private_key_file.pem",      #Path to private key file.
		"jwt_expires_minutes"		:	60                                          #Expiration time, in minutes, for JWT tokens. notlonger then 24h, recommended 60mins
	},
	"cloud_destination": {
		"cloud_region"			:	"us-central1",								#Cloud_region
		"device_id"			:	"your_device",								#IoT Core Device name		
		"project_id"			:	"yourproj-0815",							#project name		
		"registry_id"			:	"your_reg_id",							    #IoT Core Registry ID
		"mqtt_bridge_hostname"		:	"mqtt.googleapis.com",                      #MQTT bridge hostname
		"mqtt_bridge_port"		:	8883,	                                    #Choices : 8883 or 443.     MQTT bridge port.
		"keepalive"			:	120                                         #MQTT Heartbeat Frequency in seconds, best practice 60 or 120 seconds,  should not exceed max of 20 minutes
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

![alt text](https://github.com/michaelfeil/iot_gateway_modbus/tree/master/pngs/deployment_instructions.png "Deployment from GCP Portal")


# Part 3: Key Performance Characteristics:

Performance Total RAM Usage:
- less than 20mb

Performance Modbus-Reader:
-   When Reading only 1 Register per Slave at a time: 7-9 Slaves per second at 19200 BAUD
-   When Reading 32-96 Register per Slave at a time: 3-5 Slaves per second,  at 19200 BAUD

Performance MQTT Module:
    - sending MQTT messages containing only a single modbus read: ~1500 Single Modbus Slave Reads per Minute (>> Maximum read of Modbus Slaves per Minute, ~550  )
