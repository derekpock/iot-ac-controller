# IoT AC Controller
Monitor and control an IR-enabled A/C unit with aggregated, IoT-provided temperature data!

What's included:
1. Python [TempServer](TempServer.py) hosted on a low powered server (for example, a Raspberry Pi) which provides:
   1. An [ArduinoServer](ArduinoServer.py) endpoint for receiving temperature data from multiple IoT devices.
   2. A [StatusHttpServer](StatusHttpServer.py) (serving a simple [html script](script.js)) which provides a visual graph detailing temperature history an A/C poweron/off history, with manual controls.
   3. Automatic control of an IR-enabled A/C unit to maintain target temperatures as received from the IoT devices. 
2. Manual checks for controlling Kasa devices for energy output (confirming A/C power usage).
3. Manual temperature updates for testing without an IoT device available.

See the companion repository [iot-ac-controller-arduino](https://github.com/derekpock/iot-ac-controller-arduino) for the IoT code, which is responsible for reporting temperature data to the ArduinoServer and executing IR commands when deemed by the TempServer responses.