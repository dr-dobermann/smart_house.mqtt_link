"""
MQTT Controller configuration file

Consists of controller ID and mqtt links definition

(c) Dr. Dobermann, 2018.
"""

import mqtt_link_consts as mlc

MQTT_CLI_NAME = b"esp_01"

# mqtt_links dictionary format described in README.md
# 
mqtt_links = { 
    MQTT_CLI_NAME + b"/pump_control/tomatos"  : [b"MOSFET", [12, mlc.OFF, 30, mlc.NO_GROUP, mlc.NO_SEQ], []],
    MQTT_CLI_NAME + b"/pump_control/cucumbers": [b"MOSFET", [14, mlc.OFF, 30, mlc.NO_GROUP, mlc.NO_SEQ], []],

    MQTT_CLI_NAME + b"/w_station/outside"     : [b"SENSOR_I2C", [(5, 4), "GY-21P", 60], []]
    }