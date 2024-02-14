# Modbus Wallbox Monitor and Signal Messenger

## Overview
This project consists of a Python application designed to monitor a Modbus-enabled Wallbox (charging station) and send updates via Signal Messenger. It reads various parameters like the status of the charging point, total energy, and RFID tags from the Wallbox, and then sends notifications about these parameters to a specified Signal Messenger recipient.

## Features
- Monitor status, total energy, and charged energy of a Wallbox via Modbus TCP.
- Read RFID tags associated with charging sessions.
- Send updates and alerts via Signal Messenger.
- Log data to a CSV file for each Wallbox.

## Configuration
The application is configured through a `config.yaml` file. This file contains settings for:
- Modbus connection (Host, Port, and Wallbox Name).
- Modbus register addresses for different parameters (status, total energy, etc.).
- Signal Messenger settings (Host, Port, Own Number, Send Number, and Check Frequency).

An example configuration is as follows:
```yaml
log_level: DEBUG
modbus: 
  host: 192.168.178.95
  ...
signal:
  host: 192.168.178.23
  ...
```

## Installation
To run this project, you need Python 3 and several Python packages including `pymodbus`, `requests`, `pyyaml`, and `csv`. These packages can be installed using pip.

## Usage
Start the application by running the `main.py` script. This script will continuously monitor the Wallbox, read data from the configured registers, and send updates via Signal Messenger based on status changes or charging session events. Transactions are logged into a CSV file named after the Wallbox, with spaces in names replaced by underscores.

## Logging
The application's operational details are logged, and the level of verbosity can be adjusted through the `log_level` setting in the `config.yaml` file.
