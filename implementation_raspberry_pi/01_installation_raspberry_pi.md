Installation guide for the raspberry pi / unix based systems:


## Step 1.0.0: Flash the SD Card:
- Flash the  raspbian os on the raspberry pi sd card. this can be done, e.g. see the guide of [raspberrypi website](https://www.raspberrypi.org/documentation/installation/installing-images/)   

## Step 2.0.0: Set up the OS initially: 
- connect to internet (ethernet port / wifi)
- Update Software on installation of the os 


## Step 3.0.0: Test if python skript is working properly.
- [clone this repository](https://github.com/michaelfeil/iot_gateway_modbus) to /home/pi on your raspberry.

### Step 3.1.0: install python dependencies:
```bash
sudo apt-get update && sudo apt-get upgrade
sudo apt-get autoremove
#pip should be installed (otherwise do: sudo apt install python3-pip)
#move to folder
sudo pip3 install -r /home/pi/iot_gateway_modbus/src/requirements.txt
```
### Step 3.2.0: set up certificates and setup files:
- follow [installation guide first.](/src/README_gateway_software.md) This includes:
	- get CA root and generate keys with openssl:
	```bash
	cd /home/pi/iot_gateway_modbus/src/certificates
	openssl genpkey -algorithm RSA -out rsa_private.pem -pkeyopt rsa_keygen_bits:2048
	openssl rsa -in rsa_private.pem -pubout -out rsa_public.pem
	```
	- modyfy to setup_mqtt.json and setup_modbus.json
	```bash
	cd /home/pi/iot_gateway_modbus/src/setup_files
	nano setup_modbus.json
	nano setup_mqtt.json
	```

### Step 3.3.0: check functionality of script:	```

- startup python solution: 
```bash
python3 /home/pi/iot_gateway_modbus/src/startup_solution.py
```
- Check if fully functions the way you want it (Modbus / Cloud connection). 
- If it not works, check if you installed the python dependencies and configured the setup_mqtt.json and setup_modbus.json correctly

## Step 4.0.0: Set up python script as a systemd service on startup of raspberry pi
- Read general info from [raspberrypi website on systemd](https://www.raspberrypi.org/documentation/linux/usage/systemd.md)   

For the implementation you will need to
- adjust iot_gateway_modbus.service based on your system configuration (file path & user, see TODOs)
- copy iot_gateway_modbus.service to /lib/systemd/system, and then enable and start service.

For this, execute the following line by line:
```bash
#move to iot_gateway_modbus.service file
cd /home/pi/iot_gateway_modbus/implementation_raspberry_pi
# modify the service file:
nano iot_gateway_modbus.service

#move the service file in the systemd
sudo cp iot_gateway_modbus.service /lib/systemd/system
#start service
sudo systemctl daemon-reload
sleep 1
sudo systemctl enable iot_gateway_modbus.service
sudo systemctl start iot_gateway_modbus.service
sleep 2
#finished, the service should be running now
sudo systemctl status iot_gateway_modbus.service

#view the logs with journalctl:
journalctl -u iot_gateway_modbus -n 100 -f

#now you can reboot, the service should be executed on start
reboot
```

Step 5.0.0: (optional, in case raspberry pi and gprs is used) add gprs module to a raspberry pi over the gpio (uart) 
- follow the gprs implementation guide TODO: Link
