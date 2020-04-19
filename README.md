# iot_gateway_modbus
 A MQTT Gateway connecting Modbus RTU and the Google IoT Core MQTT Bridge

 For the software documentation see src/readme.md [TODO LINK]




 Related software:
 - other clouds platforms: this module is designed for the GCP and Google IoT Core, however would also work with other MQTT Bridges. For Azure, a similar module exists in C#
    https://github.com/MicrosoftDocs/azure-docs/blob/master/articles/iot-edge/deploy-modbus-gateway.md


 About:

     Required Python 3.7.7 libaries that are not included and must be installed separatley with the requirements.txt:
         1. "schema" is licensed under MIT Licence; available at https://pypi.org/project/schema/
         1. "PyJWT"  MIT Licence, 2015 Jose Padilla; available at https://pypi.org/project/PyJWT/
         1. "paho-mqtt"  is licensed under Eclipse Public License v1.0 / Eclipse Distribution License 1.0 ; available at https://pypi.org/project/paho-mqtt/
         1. "Modbus Test Kit" is licensed under LGPL Licence; available at https://pypi.org/project/modbus_tk/
         1. "pyserial"  is licensed under BSD-3-Clause (BSD Licence); available at https://pypi.org/project/pyserial/

