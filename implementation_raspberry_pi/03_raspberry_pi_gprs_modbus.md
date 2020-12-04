# (Optional) Adding a GSM/GPRS Modem to the raspberry pi:

Prerequiste: have your raspberry pi working and set up before via Ethernet Port or Wifi

In Deployment locations where no Wifi & Ethernet is available, a GSM module can be used. 

you can follow a tutorial:
e.g. this one [from waveshare](https://www.waveshare.com/wiki/SIM800C_GSM/GPRS_HAT) 
or this [one from rhydolabz] (https://www.rhydolabz.com/wiki/?p=16325) or
this [one from sixfab](https://sixfab.com/ppp-installer-for-sixfab-shield-hat/)

All of the tutorials advertise their own product. Follow the one you choose. 
#finished!

Alternativley follow this tutorial:
Step 1.0.0: Buy a GSM / GPRS / LTE.. Modem.
- I cant give a recommendation on this one.

Step 1.1.0: power up and connect modem / PI HAT to raspberry pi over GPIO
- externat power supply for modem needed!
- the modem should be now connected over the UART GPIO input. On Raspbian this is the /dev/ttyS0 port

Step 2.0.0:
- check modem functionality, e.g. with python:
```python
import serial   
import os, time

#connect serial port (modem)
port = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=1)
#write AT command
port.write('AT'+'\r\n')
# get OK Response
rcv = port.read(10)
print (rcv) #OK: is powered up
```

Step 3.0.0: use modem for dial-up networking using PPP
- check out  [tutorial](https://www.waveshare.com/wiki/SIM868_PPP_Dail-up_Networking)
just in case this tutorial is not working anymore, there are the steps:


```bash
#get ppp
sudo apt-get install ppp
sudo su

#configure ppp
cd /etc/ppp/peers
cp provider gprs

#configure gprs sim card and modem settings
sudo nano gprs

#run in the background
pppd call gprs &

#close existing network
ifconfig eth0 down
ifconfig wlan0 down
route add -net 0.0.0.0 ppp0

#test network:
ping google.com

```

sudo apt-get install wvdial

/etc/ppp/peers/wvdial
noauth
name wvdial
usepeerdns
defaultroute
replacedefaultroute