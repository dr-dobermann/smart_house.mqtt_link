"""
Si7021-A20 sensor controller

This controller works with sensor over I2C interface
Usually the sensor holds x40 address

(c) Dr. Dobermann, 2018.
"""

from machine import I2C
from utime import sleep_ms

from ..sens_cont import I2CSensorController

SI7021_ADDR = 0x40


class SI7021(I2CSensorController):
    
    GET_RHUM_CMD = b"\xF5"
    GET_TEMP_CMD = b"\xE0"

    def __init__(self, i2c, addr = SI7021_ADDR):
        I2CSensorController.__init__(self, i2c, addr)
        self.buf = bytearray(2)
        self.temp = 0.0
        self.rHum = 0.0
        self.status = self.OK

    def update(self):
        # get RH_Code
        self.i2c.writeto(self.addr, self.GET_RHUM_CMD, True)
        # according to datasheet sensors sends NACK until the data isn't ready
        # in the same datasheet max time to data preparation is 12 ms
        # experimentally I found that data is ready after 16 ms
        sleep_ms(20) 
        self.i2c.readfrom_into(self.addr, self.buf, True)
        self.rHum = (125 * (self.buf[0] << 8 | self.buf[1]))/65536 - 6
       
        # get Temp_Code
        self.i2c.writeto(self.addr, self.GET_TEMP_CMD, True)
        self.i2c.readfrom_into(self.addr, self.buf, True)
        self.temp = (175.72 * (self.buf[0] << 8 | self.buf[1]))/65536 - 46.85
        
        # normalize relative humidity
        # it could be slightly lesser than 0 or slightly higher than 100
        # according to datasheet
        if self.rHum < 0:
            self.rHum = 0
        elif self.rHum > 100:
            self.rHum = 100


        self.value = b"{}".format(self.rHum) + " %:" + b"{}".format(self.temp) + " C"
    