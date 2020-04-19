# IoT_Gateway_Modbus: A MQTT Gateway connecting Modbus RTU with MQTT Bridge of Google IoT Core

## Documentation Software:
- For the software documentation and installation see: [README_gateway_software.md](/src/README_gateway_software.md) 




 ### Related software:
 - other clouds platforms: this module is designed for the GCP and Google IoT Core, however would also work with other MQTT Bridges. For Azure, a [Modbus Gateway](https://github.com/MicrosoftDocs/azure-docs/blob/master/articles/iot-edge/deploy-modbus-gateway.md)  module exists.
    
 ### About:
 Required Python 3.7.7 libaries that are not included and must be installed separatley with the [requirements.txt](/src/requirements.txt):
- "schema" is licensed under MIT Licence; available [here](https://pypi.org/project/schema/)  
- "PyJWT"  MIT Licence, 2015 Jose Padilla; available [here](https://pypi.org/project/PyJWT/)   
- "paho-mqtt"  is licensed under Eclipse Public License v1.0 / Eclipse Distribution License 1.0 ; available [here](https://pypi.org/project/paho-mqtt/)   
- "Modbus Test Kit" is licensed under LGPL Licence; available [here](https://pypi.org/project/modbus_tk/)   
- "pyserial"  is licensed under BSD-3-Clause (BSD Licence); available [here](https://pypi.org/project/pyserial/)   

