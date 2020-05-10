# IoT_Gateway_Modbus: A MQTT Gateway connecting Modbus RTU with MQTT Bridge of Google IoT Core


## Scope of this solution:
This software is a "IoT Gateway Solution" for Modbus RTU. 

The intitial reason for starting this solution was the need for a Gateway for Solar Microgrids.
Microgrids installed e.g. by NGOs in Eastern Africa, require a monitoring system. On the one hand to prove project success and other hand to help predictive maintainance. 
Using a Linux/Windows computer, e.g. a Raspberry PI,  Modbus RTU sensors can be read and a cost-effective monitoring solution is possible. 

## As provided this solution offers:
- Cloud: Google IoT Core
	- deploying and changing Modbus configuration from the GCP.
	- Connection using Paho MQTT Client
	- low data usage: compression using gzip and multiple sensor measurement at once

- Modbus: Modbus RTU: RS232, RS485 over USB.
	- read 5-10 Modbus RTU Slaves per Second
	- schedule indivdual for every sensor
	- handling of all modbus

## Documentation Software:
- For the software documentation and installation see: [README_gateway_software.md](/src/README_gateway_software.md) 
- For additional instructions for the installation on a Raspberry Pi, follow [01_installation_raspberry_pi.md.](/implementation_raspberry_pi/01_installation_raspberry_pi.md) 

 ### Related software:
 - other clouds platforms: this module is designed for the GCP and Google IoT Core, however would also work with other MQTT Bridges. For Azure, a [Modbus Gateway](https://github.com/MicrosoftDocs/azure-docs/blob/master/articles/iot-edge/deploy-modbus-gateway.md)  module exists.
    
 ### About:
 Required Python 3.7.7 libaries that are not included and must be installed separatley with the [requirements.txt](/src/requirements.txt):
- "schema" is licensed under MIT Licence; available [here](https://pypi.org/project/schema/)  
- "PyJWT"  MIT Licence, 2015 Jose Padilla; available [here](https://pypi.org/project/PyJWT/)   
- "paho-mqtt"  is licensed under Eclipse Public License v1.0 / Eclipse Distribution License 1.0 ; available [here](https://pypi.org/project/paho-mqtt/)   
- "Modbus Test Kit" is licensed under LGPL Licence; available [here](https://pypi.org/project/modbus_tk/)   
- "pyserial"  is licensed under BSD-3-Clause (BSD Licence); available [here](https://pypi.org/project/pyserial/)   

