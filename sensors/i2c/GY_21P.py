"""
GY-21P Sensor controller

This sensor is actually a combination of two sensors BPM-280 and Si7021-A20

(c) Dr. Dobermann, 2018.
"""

from ..sens_cont import I2CSensorController
from .BMP_280 import BMP_280
from .Si7021_A20 import SI7021

class GY_21P(I2CSensorController):
    def __init__(self, i2c, addr = None):
        I2CSensorController.__init__(self, i2c, addr)
        self.bmp280 = BMP_280(self.i2c)
        self.si7021 = SI7021(self.i2c)
        if self.bmp280.status == self.OK and self.si7021.status == self.OK:
            self.status = self.OK

    def update(self):
        self.bmp280.update()
        self.si7021.update()
        self.value = self.bmp280.get_value() + ":" + self.si7021.get_value()