import os
import json
import time
import logging
from pymodbus.client import ModbusTcpClient
import requests
import yaml

# Load configuration from config.yaml
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

# Extract configuration variables
modbus_host = config['modbus']['host']
modbus_port = int(config['modbus']['port'])
modbus_register_status_address = int(config['modbus']['registers']['status']['address'])
modbus_register_status_length = int(config['modbus']['registers']['status']['length'])
signal_host = config['signal']['host']
signal_port = config['signal']['port']
signal_own_number = config['signal']['own_number']
signal_send_number = config['signal']['send_number']
frequency = int(config['signal']['check_frequency'])
log_level = config['log_level']

# Set up logging
numeric_level = getattr(logging, log_level, None)
if not isinstance(numeric_level, int):
    raise ValueError(f'Invalid log level: {log_level}')
logging.basicConfig(level=numeric_level, format='%(asctime)s - %(levelname)s - %(message)s')

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

def read_register(client, address, length):
    """
    Reads a register from the Modbus client and returns its value.
    If length is 1, a 16-bit value is returned.
    If length is 2, a 32-bit value is returned by combining two consecutive 16-bit registers.
    """
    try:
        result = client.read_holding_registers(address, length, slave=1)
        if result.isError():
            logging.error(f"Error reading register at address {address}")
            return None
        
        if length == 1:
            value = result.registers[0]
        elif length == 2:
            value = (result.registers[0] << 16) + result.registers[1]
        else:
            logging.error(f"Unsupported register length: {length}")
            return None

        return value
    except Exception as e:
        logging.error(f"Failed to read register at address {address}: {e}")
        return None

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
        # Use the read_register function to get the status value
        status_value = read_register(client, modbus_register_status_address, modbus_register_status_length)
        client.close()
        
        if status_value is not None:
            status = statuses.get(status_value, 'unknown')
            logging.debug(f"The status is {status}. Last status is {last_status}")
            if status != last_status:
                last_status = status
                logging.debug(f"Setting last status to {last_status}")
                url = f'http://{signal_host}:{signal_port}/v2/send'
                headers = {'Content-Type': 'application/json'}
                data = {
                    "message": f"Your charging point status is {status} ({status_value})",
                    "number": f"{signal_own_number}",
                    "recipients": [f"{signal_send_number}"]
                }
                logging.debug(f"URL for Signal: {url}")
                logging.debug(f"Headers for Signal: {headers}")
                logging.debug(f"Data for Signal: {json.dumps(data)}")

                try:
                    response = requests.post(url, headers=headers, data=json.umps(data))
                    response.raise_for_status()
                    logging.info(f"Successfully sent message: {response.text}")
                except requests.exceptions.HTTPError as http_err:
                    logging.error(f"HTTP error occurred: {http_err}")
                except Exception as e:
                    logging.error(f"Failed to send message: {e}")
    
    logging.debug(f"Loop iteration complete, sleeping for {frequency} seconds")
    time.sleep(frequency)
