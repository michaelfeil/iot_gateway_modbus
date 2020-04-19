import logging
import os

#log
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)7s] [%(filename)24s] [%(funcName)24s]  [%(threadName)8s]  %(message)s')
logger = logging.getLogger(__name__)

#paths
directory_path = os.path.abspath(os.path.dirname(__file__))

setup_mqtt_filepath         = os.path.join(directory_path,'setup_files', 'setup_mqtt.json')
setup_modbus_temp_filepath  = os.path.join(directory_path,'setup_files', 'setup_modbus_temp.json')
setup_modbus_filepath       = os.path.join(directory_path,'setup_files', 'setup_modbus.json')

