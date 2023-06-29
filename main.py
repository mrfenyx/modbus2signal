import os
import json
import time
import logging
from pymodbus.client import ModbusTcpClient
import requests

# Set up logging
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
numeric_level = getattr(logging, log_level, None)
if not isinstance(numeric_level, int):
    raise ValueError(f'Invalid log level: {log_level}')
logging.basicConfig(level=numeric_level, format='%(asctime)s - %(levelname)s - %(message)s')

modbus_host = os.getenv('MODBUS_HOST')
modbus_port = int(os.getenv('MODBUS_PORT'))
modbus_register = int(os.getenv('MODBUS_REGISTER'))
signal_host = os.getenv('SIGNAL_HOST')
signal_port = os.getenv('SIGNAL_PORT')
signal_own_number = os.getenv('SIGNAL_OWN_NUMBER')
signal_send_number = os.getenv('SIGNAL_SEND_NUMBER')
frequency = int(os.getenv('FREQUENCY'))

# Mapping of register values to statuses
statuses = {
    0: 'available',
    1: 'occupied',
    2: 'reserved',
    3: 'unavailable',
    4: 'faulted',
    5: 'preparing',
    6: 'charging',
    7: 'suspendedevse',
    8: 'suspendedev',
    9: 'finishing'
}

last_status = None

while True:
    logging.debug("Starting new loop iteration")
    try:
        client = ModbusTcpClient(modbus_host, port=modbus_port)
        connection = client.connect()
        logging.debug(f"Connected to client at {modbus_host}:{modbus_port}")
    except Exception as e:
        logging.error(f"Failed to connect to Modbus host: {e}")
        time.sleep(frequency)
        continue

    if connection:
        try:
            result = client.read_holding_registers(modbus_register, 1, slave=1)
            logging.debug(f"Got the following result for register {modbus_register}: {result.registers[0]}")  
        except Exception as e:
            logging.error(f"Failed to read from Modbus register: {e}")
            client.close()
            time.sleep(frequency)
            continue

        client.close()

        if not result.isError():
            status = statuses.get(result.registers[0], 'unknown')
            logging.debug(f"The status is {status}. Last status is {last_status}")
            if status != last_status:
                last_status = status
                logging.debug(f"Setting last status to {last_status}")
                url = f'http://{signal_host}:{signal_port}/v2/send'
                headers = {'Content-Type': 'application/json'}
                data = {
                    "message": f"Your charging point status is {status} ({result.registers[0]})",
                    "number": f"{signal_own_number}",
                    "recipients": [f"{signal_send_number}"]
                }
                
                try:
                    response = requests.post(url, headers=headers, data=json.dumps(data))
                    response.raise_for_status()
                    logging.info(f"Successfully sent message: {response.text}")
                except requests.exceptions.HTTPError as http_err:
                    logging.error(f"HTTP error occurred: {http_err}")
                except Exception as e:
                    logging.error(f"Failed to send message: {e}")
    
    logging.debug(f"Loop iteration complete, sleeping for {frequency} seconds")
    time.sleep(frequency)
