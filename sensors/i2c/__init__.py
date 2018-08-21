"""
Init for I2C sensors

(c) Dr. Dobermann, 2018.
"""

from sensors.sens_cont import I2CSensorController
from machine import I2C, Pin

i2c_buses = dict()

def get_sensor(sda_, scl_, name):

    global i2c_buses

    #create I2C bus if needed
    if (sda_, scl_) in i2c_buses:
        i2c = i2c_buses[(sda_, scl_)]
    else:
        i2c = I2C(sda = Pin(sda_), scl = Pin(scl_))
        i2c_buses[(sda_, scl_)] = i2c
        print("New I2C bus opened with", (sda_, scl_))

    if name == "BMP-280":
        from sensors.i2c.BMP_280 import BMP_280 as Sensor
    elif name == "SI7021":
        from sensors.i2c.Si7021_A20 import SI7021 as Sensor
    elif name == "GY-21P":
        from sensors.i2c.GY_21P import GY_21P as Sensor
    else:
        print("FATAL: Could not find sensor:", name)
        return None
    
    return Sensor(i2c)
