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


class ModbusClient:

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client = ModbusTcpClient(self.host, port=self.port)

    def connect(self):
        return self.client.connect()

    def close(self):
        self.client.close()

    def read_register(self, address, length):
        try:
            result = self.client.read_holding_registers(address, length, slave=1)
            if result.isError():
                logging.error(f"Error reading register at address {address}")
                return None

            if length == 1:
                return result.registers[0]
            elif length == 2:
                return (result.registers[0] << 16) + result.registers[1]
            else:
                logging.error(f"Unsupported register length: {length}")
                return None
        except Exception as e:
            logging.error(f"Failed to read register at address {address}: {e}")
            return None

    def read_idtag(self, modbus_config):
        idtag_registers = ['idtag_1', 'idtag_2', 'idtag_3', 'idtag_4', 'idtag_5']
        idtag = ''
        for reg in idtag_registers:
            value = self.read_register(int(modbus_config['registers'][reg]['address']),
                                       int(modbus_config['registers'][reg]['length']))
            if value is not None:
                idtag += bytes.fromhex(f'{value:08x}').decode('ascii', errors='ignore').lstrip()
        return idtag


def load_config(config_file):
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)


def setup_logging(log_level):
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    logging.basicConfig(level=numeric_level, format='%(asctime)s - %(levelname)s - %(message)s')


if __name__ == "__main__":
    config = load_config('config.yaml')
    setup_logging(config['log_level'])

    signal_messenger = SignalMessenger(config['signal']['host'], config['signal']['port'],
                                       config['signal']['own_number'], config['signal']['send_number'])

    modbus_client = ModbusClient(config['modbus']['host'], int(config['modbus']['port']))

    if not modbus_client.connect():
        logging.error("Failed to connect to Modbus server.")
        exit(1)

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
    
    try:
        while True:
            try:
                # Read status register
                status_value = modbus_client.read_register(
                    int(config['modbus']['registers']['status']['address']),
                    int(config['modbus']['registers']['status']['length'])
                )

                if status_value is not None:
                    status = statuses.get(status_value, 'unknown')
                    logging.debug(f"The status is {status}. Last status is {last_status}")

                    if status_value == 6:
                        # Read total_energy and idtag registers
                        total_energy = modbus_client.read_register(
                            int(config['modbus']['registers']['total_energy']['address']),
                            int(config['modbus']['registers']['total_energy']['length'])
                        )
                        idtag = modbus_client.read_idtag(config['modbus'])

                        if idtag:
                            message = f"RFID Card detected: {idtag}. Total Energy when charging started was {total_energy}."
                            signal_messenger.send_message(message)

                    if status != last_status:
                        last_status = status
                        message = f"Your charging point status is {status} ({status_value})"
                        signal_messenger.send_message(message)

            except Exception as e:
                logging.error(f"Error while reading Modbus registers: {e}")

            logging.debug(f"Loop iteration complete, sleeping for {config['signal']['check_frequency']} seconds")
            time.sleep(int(config['signal']['check_frequency']))

    except KeyboardInterrupt:
    # Handle Ctrl+C gracefully
        logging.info("Script interrupted by user.")
    
    finally:
        # This code will execute even if the script is interrupted
        logging.info("Closing Modbus client.")
        modbus_client.close()
