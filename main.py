import os
import json
import time
import logging
from pymodbus.client import ModbusTcpClient
import requests
import yaml


class SignalMessenger:
    
    def __init__(self, signal_host, signal_port, own_number, send_number):
        self.signal_host = signal_host
        self.signal_port = signal_port
        self.own_number = own_number
        self.send_number = send_number
    
    def send_message(self, message):
        url = f'http://{self.signal_host}:{self.signal_port}/v2/send'
        headers = {'Content-Type': 'application/json'}
        data = {
            "message": message,
            "number": self.own_number,
            "recipients": [self.send_number]
        }
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response.raise_for_status()
            logging.info(f"Successfully sent message: {response.text}")
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err}")
        except Exception as e:
            logging.error(f"Failed to send message: {e}")


def load_config(config_file):
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)


def setup_logging(log_level):
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    logging.basicConfig(level=numeric_level, format='%(asctime)s - %(levelname)s - %(message)s')


def read_register(client, address, length):
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

def read_idtag(client, modbus_config):
    idtag_registers = ['idtag_1', 'idtag_2', 'idtag_3', 'idtag_4', 'idtag_5']
    idtag = ''
    
    for reg in idtag_registers:
        try:
            value = read_register(client, int(modbus_config['registers'][reg]['address']), int(modbus_config['registers'][reg]['length']))
            if value is not None:
                # Convert the 32-bit value into bytes and decode into string, then strip leading whitespaces
                idtag += bytes.fromhex(f'{value:08x}').decode('ascii', errors='ignore').lstrip()
        except Exception as e:
            logging.error(f"Failed to read {reg} register: {e}")
    logging.debug(f"Got RFID Tag {idtag}")
    return idtag


if __name__ == "__main__":
    # Load configuration
    config = load_config('config.yaml')
    
    # Setup logging
    setup_logging(config['log_level'])
    
    # Extract configuration variables
    modbus_config = config['modbus']
    signal_config = config['signal']
    
    # Create SignalMessenger instance
    messenger = SignalMessenger(signal_config['host'], signal_config['port'], signal_config['own_number'], signal_config['send_number'])
    
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
            client = ModbusTcpClient(modbus_config['host'], port=int(modbus_config['port']))
            connection = client.connect()
            logging.debug(f"Connected to client at {modbus_config['host']}:{modbus_config['port']}")
        except Exception as e:
            logging.error(f"Failed to connect to Modbus host: {e}")
            time.sleep(int(signal_config['check_frequency']))
            continue

        if connection:
            # Use the read_register function to get the status value
            status_value = read_register(
                client,
                int(modbus_config['registers']['status']['address']),
                int(modbus_config['registers']['status']['length'])
            )
            client.close()

            if status_value is not None:
                status = statuses.get(status_value, 'unknown')
                logging.debug(f"The status is {status}. Last status is {last_status}")

                if status_value == 6:
                    total_energy = read_register(
                        client,
                        int(modbus_config['registers']['total_energy']['address']),
                        int(modbus_config['registers']['total_energy']['length'])
                    )
                    
                    idtag = read_idtag(client, modbus_config)
                    
                    if idtag:
                        message = f"RFID Card detected: {idtag}. Total Energy when charging started was {total_energy}."
                        messenger.send_message(message)

                if status != last_status:
                    last_status = status
                    message = f"Your charging point status is {status} ({status_value})"
                    messenger.send_message(message)

        logging.debug(f"Loop iteration complete, sleeping for {signal_config['check_frequency']} seconds")
        time.sleep(int(signal_config['check_frequency']))
