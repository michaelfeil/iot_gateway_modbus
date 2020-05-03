#!/usr/bin/env python
"""
 IoT Gateway Modbus
 (C)2020 - Michael Feil 
 This is distributed under MIT license, see LICENSE
""" 

"""
Starts up the Gateway solution"""


# [START includes]
import queue
import sys, os
import time

dirname = os.path.dirname(os.path.abspath(__file__))
sys.path.append(dirname)                                #only needed if not executing in current directory

from g_modbus import Scheduler, Modbus_reader
from g_mqtt_client import handle_mqtt
import g_shared_utils as su
from g_shared_utils import logger
# [End includes]


def main():
    logger.debug("Starting Application")
    
    timing_queue = queue.Queue(maxsize=100)                                                 #everything that lands here will get requested from the modbus
    publishing_queue = queue.Queue(maxsize=100)                                              #everything that lands here will get send to the cloud (telemetry, statusupdates, errors)
    
    schedule = Scheduler(timing_queue, publishing_queue)                                    #making sure to fill requests for the modbus_reader according to documentation
    modbus_client = Modbus_reader(timing_queue, publishing_queue)                           #making sure to fullfill all modbus_reader requests from timing_queue and gives them to handle_mqtt
    mqtt_handler = handle_mqtt(publishing_queue, schedule, modbus_client)                    #making sure to renew cloud connection

    schedule.daemon = True
    modbus_client.daemon = True
    mqtt_handler.daemon = True

    mqtt_handler.start()
    schedule.start() 
    modbus_client.start() 

    # endless loop
    while True:
        time.sleep(1000)
        
        
    logger.info("Quitting Application")

if __name__ == "__main__":
    main()