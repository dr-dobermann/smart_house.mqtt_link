"""
Sensor controller

Base classes for all sensors

(c) Dr. Dobermann, 2018.
"""

class SensorController():
    """
    Base class for all sensor's controllers
    """
    OK    = 1
    ERROR = 0

    def __init__(self):
        self.value = b""
        self.status = self.ERROR

    def update(self):
        pass

    def get_value(self, update = False):
        if update:
            self.update()

        return self.value

    def sign16(self, u16):
        """
        Makes INT16 from UINT16
        """
        if u16 > 0x7FFF:
            return (u16 - (0xFFFF + 1))
        
        return u16
#------------------------------------------------------------------------------



class I2CSensorController(SensorController):
    """
    I2C sensor's controller base class
    """
    def __init__(self, i2c, addr):
        SensorController.__init__(self)
        self.i2c = i2c
        self.addr = addr
#------------------------------------------------------------------------------