# Based on UPS Lite v1.1 from https://github.com/xenDE
#
# Gets status of attached Pisugar2 - needs enable "i2c" in raspi-config
#
# https://github.com/PiSugar/pisugar-power-manager/blob/master/core/PiSugarCore.py
# https://www.tindie.com/products/pisugar/pisugar2-battery-for-raspberry-pi-zero/
import logging
import struct

from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK
import pwnagotchi.ui.fonts as fonts
import pwnagotchi.plugins as plugins
import pwnagotchi

class UPS:
    def __init__(self):
        # only import when the module is loaded and enabled
        import smbus
        # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
        self._bus = smbus.SMBus(1)
        self._is_pro = False

    def voltage(self):
        try:
            address = 0x75
            if self._is_pro:
                low = self._bus.read_byte_data(address, 0x64)
                high = self._bus.read_byte_data(address, 0x65)
            else:
                low = self._bus.read_byte_data(address, 0xa2)
                high = self._bus.read_byte_data(address, 0xa3)
            if high & 0x20:
                low = ~low & 0xff
                high = ~high & 0x1f
                v = (((high | 0b1100_0000) << 8) + low)
                return (2600.0 - v * 0.26855) / 1000
            else:
                v = ((high & 0x1f) << 8 ) + low
                return (2600 + v * 0.26855) / 1000
        except:
            return 0.0

    def capacity(self):
        battery_curve = [
            [4.16, 5.5, 100, 100],
            [4.05, 4.16, 87.5, 100],
            [4.00, 4.05, 75, 87.5],
            [3.92, 4.00, 62.5, 75],
            [3.86, 3.92, 50, 62.5],
            [3.79, 3.86, 37.5, 50],
            [3.66, 3.79, 25, 37.5],
            [3.52, 3.66, 12.5, 25],
            [3.49, 3.52, 6.2, 12.5],
            [3.1, 3.49, 0, 6.2],
            [0, 3.1, 0, 0],
        ]
        battery_level = 0
        battery_v = self.voltage()
        for range in battery_curve:
            if range[0] < battery_v <= range[1]:
                level_base = ((battery_v - range[0]) / (range[1] - range[0])) * (range[3] - range[2])
                battery_level = level_base + range[2]
        return battery_level

class PiSugar2(plugins.Plugin):
    __author__ = 'tom@dankmemes2020.com'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = 'A plugin that will add a voltage indicator for the PiSugar 2'

    def __init__(self):
        self.ups = None

    def on_loaded(self):
        self.ups = UPS()
        logging.info("[pisugar2] plugin loaded.")

    def on_ui_setup(self, ui):
        ui.add_element('bat', LabeledValue(color=BLACK, label='BAT', value='0%/0V', position=(ui.width() / 2 + 15, 0),
                                           label_font=fonts.Bold, text_font=fonts.Medium))

    def on_unload(self, ui):
        with ui._lock:
            ui.remove_element('bat')

    def on_ui_update(self, ui):
        capacity = self.ups.capacity()
        ui.set('bat', "%2i%%" % capacity)
        if capacity <= self.options['shutdown']:
            logging.info('[pisugar2] Empty battery (<= %s%%): shuting down' % self.options['shutdown'])
            ui.update(force=True, new_data={'status': 'Battery exhausted, bye ...'})
            pwnagotchi.shutdown()
