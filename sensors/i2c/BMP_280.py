"""
BMP-280 sensor' controller

This controller only works with interface and it's provides only minimal functionality
necessary for the project

Usually BMP-280 sits on 0x76.

(c) Dr. Dobermann, 2018.
"""

from machine import I2C
from utime import sleep_ms

from ..sens_cont import I2CSensorController

BMP280_ADDR = 0x76
BMP280_DATA = 0xF7
BMP280_COMPENSATE_REGS = 0x88

T1 = 0
T2 = 1
T3 = 2

P1 = 3
P2 = 4
P3 = 5
P4 = 6
P5 = 7
P6 = 8
P7 = 9
P8 = 10
P9 = 11

# signed int16 compensators
sign = {T2, T3, P2, P3, P4, P5, P6, P7, P8, P9}

T_MSB = 3
T_LSB = 4
T_XLSB = 5

P_MSB = 0
P_LSB = 1
P_XLSB = 2

class BMP_280(I2CSensorController):
    def __init__(self, i2c, addr = BMP280_ADDR):
        I2CSensorController.__init__(self, i2c, addr)
        self.temp = 0.0
        self.t_fine = 0
        self.pressure = 0.0
        self.data = bytearray(6)

        # read compensation bytes table
        cb = bytearray(26)
        i2c.readfrom_mem_into(self.addr, BMP280_COMPENSATE_REGS, cb)
        self.dig = []
        # collect compensation words
        for ii in range(13):
            if ii in sign:
                self.dig.append(self.sign16(cb[ii*2 + 1] << 8 | cb[ii*2]))
            else:
                self.dig.append(cb[ii*2 + 1] << 8 | cb[ii*2])

        self.status = self.OK

    def update(self):
        self.value = b""
        # force update
        self.i2c.writeto_mem(self.addr, 0xf4, b"1")
        sleep_ms(100)
        self.i2c.readfrom_mem_into(self.addr, BMP280_DATA, self.data)

        # calculate temp
        rt = ((self.data[T_MSB] << 8 | self.data[T_LSB]) << 8 | self.data[T_XLSB]) >> 4
        t_v1 = (((rt >> 3) - (self.dig[T1] << 1)) * self.dig[T2]) >> 11
        t_v2 = (((((rt >> 4) - self.dig[T1]) * ((rt >> 4) - self.dig[T1])) >> 12) * self.dig[T3]) >> 14
        self.t_fine = t_v1 + t_v2
        self.temp = ((self.t_fine * 5 + 128) >> 8) / 100

        # calculate pressure
        rp = ((self.data[P_MSB] << 8 | self.data[P_LSB]) << 8 | self.data[P_XLSB]) >> 4
    
        p_v1 = self.t_fine - 128000
        p_v2 = p_v1 * p_v1 * self.dig[P6]
        p_v2 += self.dig[P5] << 17
        p_v2 += self.dig[P4] << 35
        p_v1 = ((p_v1 * p_v1 * self.dig[P3]) >> 8) + ((p_v1 * self.dig[P2]) << 12)
        p_v1 = ((1 << 47) + p_v1) * self.dig[P1] >> 33
        if p_v1 != 0:
            p = 1048576 - rp
            p = int((((p << 31) - p_v2) * 3125) / p_v1)
            p_v1 = (self.dig[11] * (p >> 13) * (p >> 13)) >> 25
            p_v2 = (self.dig[10] * p) >> 19
            p = ((p + p_v1 + p_v2) >> 8) + (self.dig[9] << 4)
        else:
            p = 0

        self.pressure = p / 256
        self.value = b"{}".format(self.temp) + " C:" + b"{}".format(self.pressure) + " Pa"
