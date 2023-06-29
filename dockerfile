# Use an official Python runtime as a parent image
FROM python:3.9.17-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Define environment variable
ENV LOG_LEVEL='INFO'
ENV MODBUS_HOST='192.168.2.11'
ENV MODBUS_PORT=502
ENV MODBUS_REGISTER=519
ENV SIGNAL_HOST='192.168.2.25'
ENV SIGNAL_PORT='4126'
ENV SIGNAL_OWN_NUMBER='+4915203056948'
ENV SIGNAL_SEND_NUMBER='+4915203056948'
ENV FREQUENCY=10

# Run app.py when the container launches
CMD [ "python", "main.py" ]
