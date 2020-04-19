#!/usr/bin/env python

"""
 IoT Gateway Modbus
 (C)2020 - Michael Feil 
 This is distributed under MIT license, see LICENSE
"""

"""g_schema_check.py

Function: Handling the setup_modbus.json 

Defines Valid Schema for the setup_modbus.json 
Reads setup_modbus.json for g_modbus classes
Replaces setup_modbus.json content if new message received from mqtt_clients subscription on config messages
"""

#[Start includes ]
import json
import time
import random
import logging
import shutil
import os
import queue

#schema is licensed under MIT Licence and available at https://pypi.org/project/schema/
from schema import Schema, Or, And, Use, Optional, SchemaError
#[End includes]

#[includes own scripts]
import g_mqtt_client as gmc
import g_shared_utils as su
from g_shared_utils import logger
#[includes own scripts]

#[Start Global Variables]
FILE_LOCK = False

supported_baudrates = [50, 75, 110, 134, 150, 200, 300, 600, 1200, 1800, 2400, 4800, 9600, 19200, 38400, 57600, 115200,
                       230400, 460800, 500000, 576000, 921600, 1000000, 1152000, 1500000, 2000000, 2500000, 3000000, 3500000, 4000000] #sometimes supported, add as needed.
#[End Global Variables]


# [Start Schemas]
#Define Rules for the JSON Schema to fullfill:
operation_schema = Schema({
    "startadress": And(lambda n: (0 <= n <= 9999), int),
    "function_code": And(lambda n: (0 <= n <= 30), int),
    "display_name": str,
    "sampling_interval": Or( And(lambda n: (0.05 <= n <= 864001), (Or(int, float))), 0),
    And(lambda n: bool("quantity_of_x" == n)^bool("output_value" == n), str) : And(lambda n: (0 <= n <= 500), int),  #Xor: A string: (quantity_of_x Xor output_value) is == integer
}, name="operation_schema", as_reference=True)

slave_schema = Schema({
    "slave_id":And(lambda n: (0 <= n <= 256), int),
    "operations": {
        str: operation_schema,
    }
}, name="Slave_schema", as_reference=True)

conf_Schema = Schema({
  "port_config": {
    "port": And(lambda n: Or(("/dev/tty" in n),("COM" in n)), str), 
    "baudrate": And(lambda n: n in supported_baudrates, int),   
    "databits": And(lambda n: n in [5, 6, 7, 8], int),    
    "parity": And(lambda n: n in ['N', 'E', 'O', 'M', 'S'], str), 
    "stopbits": And(lambda n: n in (1, 1.5, 2), (Or(int, float))), 
    "timeout_connection": And(lambda n: (0.02 <= n <= 99.9), (Or(int, float))),
  },
  "slaveconfig": {
      str: slave_schema,
      }
})
# [End Schemas]

# [Start Schema check]
def modbus_json_check(file=str(), dictio=dict(), autolock_file=True):
    """checks the JSON Format from file or from dictionary"""
    global FILE_LOCK


    response = "\t This is the modbus_json_check check \n"

    try:
        #[Start Read Data]

        if dictio and file: #not possible
            logger.error("Error: Using file and dict at the same time")
            return False, "Error: Using file and dict at the same time", json.dumps({"empty": "empty"})
        elif file:
            #[Start read file]
            opened = False
            

            while opened == False:
                #[Start sleep until available]
                sleep_max=0
                while (FILE_LOCK == True and autolock_file==True) or sleep_max>50:
                    time.sleep(0.05)
                    sleep_max+=1
                #[End sleep until available]
                
                try:
                    if autolock_file: FILE_LOCK = True

                    if (file != su.setup_modbus_temp_filepath) and (os.path.exists(su.setup_modbus_temp_filepath)):  #setup_modbus_temp_filepath exists, but we did not plan to check it
                        logger.critical("The System had a crash updating the Temp file, fixing the update") 
                        shutil.copy(su.setup_modbus_temp_filepath, su.setup_modbus_filepath)
                        os.remove(su.setup_modbus_temp_filepath)


                    with open(file) as f:
                        data_json = json.load(f)
                    opened = True
                    if autolock_file: FILE_LOCK = False
                except Exception as e:
                    logger.debug("ERROR reading json: {}".format(e))
                    if autolock_file: FILE_LOCK = False
                    time.sleep(random.randint(1,10)) #try to open after sleep
            #[End read file]

        elif dictio:
            data_json = dictio

        #[End Read Data]   
        #[Start Validate Schema]   
        try:
            conf_Schema.validate(data_json)
        
            response = response+" \n FINAL RESPONSE: Schema correct"
            checkresult = True
        except SchemaError as e:
            response = response+" \n FINAL RESPONSE: Schema INCORRECT due to " + str(e)
            checkresult = False
        #[End Validate Schema]   

        return checkresult, response, data_json

    except Exception as e:
        response = response + "error in completing check" +str(e)
        return False, response, json.dumps({"empty": "empty"})
# [End Schema check]

# [Start Read JSON]
def read_setup(pub_queue, sleeptime=True, send_answer_to_cloud = False):
    
    port_config = dict()
    slave_config = dict()
    checkresult = False
    time.sleep(random.randint(5,15)/10)
    read_complete = 0

    logger.debug("check the setup_modbus.json")

    

    while not read_complete >= 5:

        try:
            checkresult, response, data_json = modbus_json_check(file=su.setup_modbus_filepath)
            
            if send_answer_to_cloud: logger.debug("setup_modbus.json response:"+str( response))

            port_config = data_json["port_config"]
            slave_config = data_json["slaveconfig"]
            read_complete = 5


            if send_answer_to_cloud:
                gmc.formatted_publish_message(topic=gmc.TOPIC_STATE, payload="Start up with modbus config: {}       JSON CHECKUP {}".format(data_json, response), c_queue=pub_queue)     

        except Exception as e:
            try:
                if read_complete>1:
                    gmc.formatted_publish_message(topic=gmc.TOPIC_STATE, payload="ERROR reading setup_modbus:"+str(e), c_queue=pub_queue)
            finally:
                time.sleep(3+random.randint(0,10)) #randomized access if multiple read at the same time
                read_complete = read_complete+1
    if not checkresult: #unsuccessful, default
        port_config = {"port": "COM6", "baudrate": 9600, "databits": 8, "parity": "N", "stopbits": 1, "timeout_connection": 10 }
        
        slave_config = {}
    return port_config, slave_config
# [End Read JSON]

# [Start manuipulate existing JSON ]

# [Start check Configuration Updates]
def check_configuration_message(config_payload, scheduler_obj, modbus_reader_obj, publising_queue):
    logger.info("check new message on content")
    """checks for the Configuration Messages and applies them when the new and deployment formally correct"""

    answer_config_update = " /Config Subscription Message received"
        
    novel_json_content = False #
    absolute_success_update = False #whether successfull update
    replacing_file_success = False # 
    content_correct = False # 
    received_json_checkresult = False #
    
    current_checkresult, current_response, current_json = modbus_json_check(file=su.setup_modbus_filepath)
    #answer_config_update = answer_config_update + str(" \n CURRENT JSON running is ") + str(current_json) #current json
    
    content_correct = bool("content_start" in config_payload and "content_end" in config_payload and "configuration_update_modbus" in config_payload)

    if content_correct: #elements of a correct config message exists
        try: 
            
            received_json_string = config_payload.split("content_start")[1].split("content_end")[0]
            received_json = json.loads(received_json_string) #will not work, if a invalid json it throws an error

            received_json_checkresult, received_json_response, unused_json = modbus_json_check(dictio = received_json)

            if received_json_checkresult == True:
                

                answer_config_update = answer_config_update + str("\n Received JSON is valid") #json is currently used
                if current_json != received_json:
                    novel_json_content = True
                    logger.debug("SUCCESS! Received a new, valid JSON. Will update an use:  {}".format(received_json))
                    result = "UPDATING"
                    
                    # [Start UPDATE]
                    replacing_file_success, answer_update = execute_configuration_message(received_json) #use the new json
                    answer_config_update = answer_config_update + answer_update
                    # [End UPDATE]
                elif current_json == received_json:
                    answer_config_update = answer_config_update + str("\n CURRENT JSON is the SAME as received JSON, not changing setup ") #json is currently used
            elif received_json_checkresult == False:
                
                answer_config_update = answer_config_update + "\n received JSON is invalid: {} ".format(received_json_response)
        except Exception as e:
            received_json_checkresult = False
            answer_config_update = answer_config_update + "\n ERROR content between content_start and content_end is not a JSON {} ".format(e)

    elif not content_correct:
        answer_config_update = answer_config_update + str("\n  configuration_update_modbus, content_start, content_end is missing as header, not valid configuration")
    
    


    if replacing_file_success:
        try:
            logger.debug("config about to be implemented ") 
            
            scheduler_obj.stopkill()
            modbus_reader_obj.stopkill()
            logger.debug("stopped all, wait before starting up")
            time.sleep(3)
            logger.debug("starting modbus and scheduler back up")

            scheduler_obj.startup()
            modbus_reader_obj.startup()
            absolute_success_update = True
        except Exception as e:
            absolute_success_update = False
            result = result + "BUT FAILED"
        logger.debug("config implemented ")
    
    

    
    if not content_correct:
        result = " configuration_update_modbus, content_start, content_end is missing as header - NO Further Processing "
    elif not received_json_checkresult:
        result = "JSON between content_start and  content_end is invalid - NO Further Processing "
    elif not novel_json_content:
        result = "JSON sent already in use"
    else:
        # JSON was further Processed "
        
        if replacing_file_success:
            if absolute_success_update:
                result = "SUCCESS, using received_json {} ".format(received_json)
            elif not absolute_success_update:
                result = "ERROR JSON was further processed and saved, but not implemented due to an error"
        if not replacing_file_success:
            result = "Fatal ERROR JSON was further processed, but writing failed"

    answer_config_update = answer_config_update + "\n  RESULT: {} \n".format(result)
    logger.info(answer_config_update)
    gmc.formatted_publish_message(topic=gmc.TOPIC_STATE, payload=answer_config_update, c_queue=publising_queue)     
    
    return  
# [End check Configuration Updates]

def execute_configuration_message(update_json):
    
    global FILE_LOCK
    written = False
    while written == False:
        try:
            #[Start sleep until available]
            
            while FILE_LOCK == True:
                time.sleep(0.05)
            
            #[End sleep until available]

            logger.debug("executing update")
            FILE_LOCK = True


            with open(su.setup_modbus_temp_filepath, 'w') as f: #write to temp file is not corrupted
                json.dump(update_json, f, ensure_ascii=False, indent=4)


            new_result, new_response, new_json = modbus_json_check(file=su.setup_modbus_temp_filepath, autolock_file=False)

            if (new_json) == update_json and new_result == True: #if new temp file is not corrupted
                shutil.copy(su.setup_modbus_temp_filepath, su.setup_modbus_filepath) #overwrite old setup
                time.sleep(0.1)
                os.remove(su.setup_modbus_temp_filepath) #delete temp setup
            else: #temp file is for some reason corrupted
                os.remove(su.setup_modbus_temp_filepath) 
                FILE_LOCK = False
                return False, "Failed to update the new file"

            written = True
            FILE_LOCK = False
        except Exception as e:
            logger.critical("ERROR writing new json: {}".format(e))
            FILE_LOCK = False
            time.sleep(random.randint(1,10)) #try to open after sleep
            double_check, unused, unused2 = modbus_json_check(dictio=update_json)
            if double_check == False: #should never be false, as this would mean the json that should be implemented is corrupted
                logger.critical("FATAL ERROR Trying to implement corrupted JSON {}".format(e))
                return False, "FATAL ERROR Trying to implement corrupted JSON"

    
    return True, "SUCCESS"
    
# [End manipulate existing JSON ]



#tests
def test():
    logger.info('call test()')
    logger.info(modbus_json_check(file=su.setup_modbus_filepath))

if __name__ == '__main__':
   test()

   time.sleep(10)