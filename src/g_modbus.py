#!/usr/bin/env python

"""
 IoT Gateway Modbus
 (C)2020 - Michael Feil 
 This is distributed under MIT license, see LICENSE
"""

"""g_modbus.py

Function: 
Part 1: Scheduling reads from the modbus as listed in setup_modbus.json
Part 2: Executing read from Modbus RTU via serial connection according to scheduling module and serial port config of setup_modbus.json.
        Read data will be queued and published in g_mqtt_client.
"""

# [START includes]
import time
import queue
import threading
import random 

#Modbus Test Kit is licensed under LGPL Licence and available at https://pypi.org/project/modbus_tk/
from modbus_tk import modbus_rtu
from modbus_tk.exceptions import ModbusError
#pyserial  is licensed under BSD-3-Clause (BSD Licence) and available at https://pypi.org/project/pyserial/
import serial
# [End includes]


#[includes own scripts]
from g_mqtt_client import TOPIC_EVENT, TOPIC_STATE, formatted_publish_message
from g_schema_check import modbus_json_check, logger, read_setup
#[includes own scripts]


# [START Scheduling]
# [START Helper RepeatedFunction]

class RepeatedFunction(threading.Thread):
    """
    runs a function every interval seconds. until [RepeatedFunction object].stop_event.set() is called
        
    Limitation:
    If execution time of self.function takes longer than interval seconds, runs at every [exceution time of self.function] 
        ...

    Attributes
    ----------
    interval : float
        periodic interval after which it runs the function
    function : function
        name of the function that should be run periodically
        with (*args, **kwargs) of the function
    
   

    Methods
    -------
    run()
        Periodically starts to execute function until [RepeatedFunction object].stop_event is set()
    
    """

    def __init__(self, interval, function, *args, **kwargs):
        threading.Thread.__init__(self)
        #function
        self.function   = function          
        self.args       = args
        self.kwargs     = kwargs
        self.interval   = interval
        #stop
        self.stop_event = threading.Event()

    def run(self):
        """runs a function every interval seconds. """
        self.sleep_until = time.time() 

        while not self.stop_event.is_set(): #until calls [object].stop_event.set()
            self.function(*self.args, **self.kwargs)

            if self.interval == 0:
                logger.debug("Repeating function only once: {} {} ".format(self.args, self.kwargs))
                self.stop_event.set() #self terminate, as with interval = 0 it is wished that is not repeated
            
            self.sleep_until += self.interval
            self.stop_event.wait(timeout=max(0, self.sleep_until - time.time())) #wait until timeout or until stop_event.is_set()
        return #end

# [END Helper RepeatedFunction]

class Scheduler(threading.Thread):
    """
    A class used to schedule a all functions to be run periodically 

    Class Scheduler, class runs in own thread. 
    Gets the setup_modus.json events and schedules the events with a RepeatedFunction.
    When a RepeatedFunction executes, the according task&request will be put in the timing queue.

    The Scheduler is stopped in the case the setup_modbus.json is renewed, and then restarted to schedule new events and RepeatedFunction
    ...

    Attributes
    ----------
    timing_queue : queue.Queue Object
        queue where new request put to be read from the Modbus Reader Objectates
    publishing_queue : queue.Queue Object
        queue where messages are put to be published by the MQTT Module 


    Methods
    -------
    run()
        Starts when Thread is started, calles startup()
    startup()
        Iniitialize Start or Restart scheduling of events / reads from the modbus with RepeatedFunction
    query_task()
        Schedules a new periodic RepeatedFunction to execute function
    stopkill()
        Called to stop all scheduled RepeatedFunction
    """

    def __init__(self, timing_queue, publishing_queue):
        """Init Scheduler Class"""
        threading.Thread.__init__(self)
                
        self.timing_queue = timing_queue
        self.publishing_queue = publishing_queue

        self.running_rep_functions = list()        #all running RepeatedFunction 
        #stop
        self.stop_event = threading.Event()          #ends scheduling RepeatedFunction s

        self.timeout_between_functions = 0.27  #time delay between initial start of two reads from the modbus

    def query_task(self, process_request):
        """When RepeatedFunction executes this function, process_request will be put in timing_queue if queue is not full"""
        
        try:
            self.timing_queue.put(process_request[1], False)
        except queue.Full:
            pass
        
    def run(self):
        """Start of the Thread"""
        logger.debug("Start the Scheduler ")
        self.startup()


    def startup(self):
        """Start or Restart the Scheduling events"""

        #Step 1: Figure out what current setup_modbus.json is and its slaveconfig
        unused_port_config, slaveconfig = read_setup(self.publishing_queue) #wait to get newest setup

        try:
            while not self.stop_event.is_set():
            
                #Step 2: For every operation in slaveconfig: find out details
                for slave_name in slaveconfig: #looping through all exisiting slaves
                    operations = slaveconfig[slave_name]["operations"]
                    slave_id = slaveconfig[slave_name]["slave_id"]
                
                    for operation in operations:    #looping for all operations of a specific slave
                    
                        #[Start get Information of Operation]
                        op = operations[operation]
                        interval=(op["sampling_interval"]) #interval for Scheduling events

                        process_request = {
                                            "slave_id": slave_id,
                                            "startadress": op["startadress"],
                                            "function_code": op["function_code"],
                                            "display_name": op["display_name"],
                                            }

                        if "quantity_of_x" in op:
                            process_request["quantity_of_x"] = op["quantity_of_x"]
                        elif "output_value" in op:
                            process_request["output_value"] = op["output_value"]
                        else:
                            logger.error("FATAL ERROR, no output value or quantity_of_x {}".format(process_request))
                         #[End get Information of Operation]

                        self.stop_event.wait(self.timeout_between_functions) #timeout, so differet request will be executed at different times
                    
                        if self.stop_event.is_set():
                            logger.warning("Error: unwanted break in scheduling new RepeatedFunctions") 
                            return 
                        #Step 3: For a specific operation schedule a specific RepeatedFunction every interval seconds
                        #[Start Schedule new RepeatedFunction]
                        rf = RepeatedFunction(interval, self.query_task, (self,process_request))
                        rf.setDaemon = True
                        rf.start()
                        self.running_rep_functions.append(rf)

                        logger.debug("scheduleded {} \t at interval {} ".format(process_request, (str(interval)+"s") if interval!=0 else "once occuring"))
                    
                        #[End Schedule new RepeatedFunction]

                logger.debug("ending this scheduler thread {}".format(self.running_rep_functions))        
                return

        except Exception as e: #should in no case occur
            logger.error("Error scheduling new timing events, consider restarting device: {}".format(e))
            formatted_publish_message(topic=TOPIC_STATE, payload="Error scheduling new timing events, consider restarting device: {} ".format(e), c_queue=pub_queue)

    def stopkill(self):
        """Called to stop all scheduled RepeatedFunctions"""
        try:
            self.stop_event.set() #no more scheduling new events

            while len(self.running_rep_functions[:]) != 0:
            
                for repfunc_thread in self.running_rep_functions[:]:
                    repfunc_thread.stop_event.set()     #stop this RepeatedFunction

                for repfunc_thread in self.running_rep_functions[:]:
                    if not repfunc_thread.is_alive():
                        self.running_rep_functions.remove(repfunc_thread)
                        logger.debug("removed {}".format(repfunc_thread))

            # now self.running_rep_functions is empty
            self.stop_event.clear()
            
        except Exception as e:
            logger.error("Unexpected Error, sending to cloud {}".format(e))
            formatted_publish_message(topic=TOPIC_STATE, payload="Error scheduling old timing events, consider restarting device: {} ".format(e), c_queue=pub_queue)
# [END Scheduling]
        

# [START Modbus]

class Modbus_reader(threading.Thread):
    """
    
    ...

    Attributes
    ----------
    timing_queue : queue.Queue Object
        queue where new request are received from RepeatedFunction / Schedule Object
    publishing_queue : queue.Queue Object
        queue where new messages are put to be published by the MQTT Module 


    Methods Serial Port Handling
    -------
    connect_serial()
        Renews the serial port connection and Modbus RTU_Master object. 
    read_modbus_event()
        
    reconfigure()
        

    Methods Serial Port Handling
    -------
    run()
        Called as thread started by Thread.
        Endless Loop of reconfigure, connect_serial and read_modbus_event, controlled by startup and stopkill.
    startup()
        Releases run from haltering
    stopkill()
        Called to stop to start haltering run  
    """

    def __init__(self, timing_queue, publishing_queue):
        threading.Thread.__init__(self)
        

        self.timing_queue = timing_queue
        self.publishing_queue = publishing_queue

        self.alive = False
        self.serial_connected = False
        
        self.max_master_attemps = int(10)           #maximum attemps to connect master
        self.master_status = self.max_master_attemps #the higher the status, increase the status

        self.port_config = dict()
        
        self.serial_port = "undefined"
               
    def connect_serial(self): 
        "connect the serial port and modbus rtu master over serial port"
        logger.debug("calling connect serial")
        try:
            if self.serial_port != "undefined": #if initialisized
                self.serial_port.close()
                logger.debug("serial port closed successfully")
        except: 
            pass

        try:
            self.serial_connected = False
            self.master_status = self.max_master_attemps
            
            self.serial_port = serial.Serial(
                port=self.port_config["port"], 
                baudrate=self.port_config["baudrate"],
                bytesize=self.port_config["databits"], 
                parity=self.port_config["parity"], 
                stopbits=self.port_config["stopbits"], 
                xonxoff=0)
            
            
            logger.debug("connected serial")
            
            self.master = modbus_rtu.RtuMaster(
                    self.serial_port
                )
            self.master.set_timeout(self.port_config["timeout_connection"]) #max waittime for modbus answers
            self.master.set_verbose(False) #if True, log additional modbus info

            #Successfull, set flags
            logger.debug("connected rtu master")

            self.serial_connected = True
            self.master_status = 0

            with self.timing_queue.mutex: #reset timing events queue
                self.timing_queue.queue.clear()

        except Exception as e:
            time.sleep(3)
            logger.error("ERROR Serial Port connection not successful{}".format(e))
            self.serial_connected = False

    def read_modbus_event(self):
        """read operations of the timing_queue with the Modbus RTU Master and Execute them with """

        logger.debug("calling read_modbus_event")
        
        while self.serial_connected and self.alive and self.master_status<self.max_master_attemps-1:

            request = self.timing_queue.get() #blocking call until new request is received
            if self.alive == False: #discontinue if function is wished to be stopped
                self.timing_queue.task_done()    
                break

            slave_id = request["slave_id"]
            startadress = request["startadress"]
            function_code = request["function_code"]
            display_name = request["display_name"]   

            result =  (99999,"modbus_request_not_possible") #default
            try:
                if "quantity_of_x" in request:
                    result = self.master.execute(slave=slave_id, function_code=function_code, starting_address=startadress, quantity_of_x= request["quantity_of_x"] ) #read
                elif "output_value" in request:
                    result = self.master.execute(slave=slave_id, function_code=function_code, starting_address=startadress, output_value= request["output_value"] ) #write
                
                
                logger.debug("slave no {}, starting_adress {} with name {} and {} ".format(slave_id, startadress, display_name,  str(result)))        
                
                self.master_status = 0 #successfull read, reset to 0

                
            except ModbusError as exc:
                self.master_status = self.master_status + 1 #unsuccessfull, increase the status
                logger.warning("ModbusError in read_modbus_event {}".format(ex))

            except Exception as ex: #other error, like serial port etc.
                logger.warning("Unexpected error in read_modbus_event {}".format(ex))
                self.master_status = self.master_status + 5 #unsuccessfull, increase the status
                self.serial_connected = False

            payload = {"na": display_name, "res": result, "sl": slave_id, "time": time.time()}
            formatted_publish_message(topic = TOPIC_EVENT, payload=payload, c_queue = self.publishing_queue)

            self.timing_queue.task_done()

        logger.warning("Disconnected the Modbus, restarting")
        try:
            if self.serial_port != "undefined": #if not just initialisized
                self.serial_port.close()
        except Exception as ex:
            logger.error("error closing serial port: {}".format(ex))

    def reconfigure(self):
        """called to reassign new port config"""
        self.port_config, unused_slaveconfig = read_setup(self.publishing_queue, sleeptime=False, send_answer_to_cloud = True)
        
    def run(self):
        self.alive = True
        
        while True:        #Endless Loop of reconfigure, connect_serial and read_modbus_event
            logger.debug("RESTART the Modbus reader")
            
            try: 
                self.reconfigure()

                while self.alive == True: # do until stopkill is callled
                
                    self.connect_serial() #serial connected
                    self.read_modbus_event()
                
                while self.alive == False: # do until startup is callled
                    logger.debug("Modbus reader haltering")
                    time.sleep(2)
            except Exception as ex:
                logger.error("Unexpected run modbus error {}".format(ex))
                time.sleep(1)

    def startup(self):
        self.alive = True

    def stopkill(self):
        self.alive = False
        self.serial_connected = False

# [END Modbus]