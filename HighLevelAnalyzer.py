# High Level Analyzer
# For more information and documentation, please go to https://support.saleae.com/extensions/high-level-analyzer-extensions

from saleae.analyzers import HighLevelAnalyzer, AnalyzerFrame, StringSetting, NumberSetting, ChoicesSetting

import struct

ILI9341_COMMANDS = {
    0x00: {"name": "NOP", "FROM": 0},
    0x01: {"name": "SWRESET", "FROM": 0},
    0x04: {"name": "RDDID", "FROM": 0},
    0x09: {"name": "RDDST", "FROM": 0},
    0x10: {"name": "SLPIN", "FROM": 0},
    0x11: {"name": "SLPOUT", "FROM": 0},
    0x12: {"name": "PTLON", "FROM": 0},
    0x13: {"name": "NORON", "FROM": 0},
    0x0A: {"name": "RDMODE", "FROM": 0},
    0x0B: {"name": "RDMADCTL", "FROM": 0},
    0x0C: {"name": "RDPIXFMT", "FROM": 0},
    0x0D: {"name": "RDIMGFMT", "FROM": 0},
    0x0F: {"name": "RDSELFDIAG", "FROM": 0},
    0x20: {"name": "INVOFF", "FROM": 0},
    0x21: {"name": "INVON", "FROM": 0},
    0x26: {"name": "GAMMASET", "FROM": 0},
    0x28: {"name": "DISPOFF", "FROM": 0},
    0x29: {"name": "DISPON", "FROM": 0},
    0x2A: {"name": "CASET", "FROM": 2},
    0x2B: {"name": "PASET", "FROM": 2},
    0x2C: {"name": "RAMWR", "FROM": 2},
    0x2E: {"name": "RAMRD", "FROM": -2},
    0x30: {"name": "PTLAR", "FROM": 0},
    0x33: {"name": "VSCRDEF", "FROM": 0},
    0x36: {"name": "MADCTL", "FROM": 0},
    0x37: {"name": "VSCRSADD", "FROM": 0},
    0x3A: {"name": "PIXFMT", "FROM": 0},
    0xB1: {"name": "FRMCTR1", "FROM": 0},
    0xB2: {"name": "FRMCTR2", "FROM": 0},
    0xB3: {"name": "FRMCTR3", "FROM": 0},
    0xB4: {"name": "INVCTR", "FROM": 0},
    0xB6: {"name": "DFUNCTR", "FROM": 0},
    0xC0: {"name": "PWCTR1", "FROM": 0},
    0xC1: {"name": "PWCTR2", "FROM": 0},
    0xC2: {"name": "PWCTR3", "FROM": 0},
    0xC3: {"name": "PWCTR4", "FROM": 0},
    0xC4: {"name": "PWCTR5", "FROM": 0},
    0xC5: {"name": "VMCTR1", "FROM": 0},
    0xC7: {"name": "VMCTR2", "FROM": 0},
    0xDA: {"name": "RDID1", "FROM": 0},
    0xDB: {"name": "RDID2", "FROM": 0},
    0xDC: {"name": "RDID3", "FROM": 0},
    0xDD: {"name": "RDID4", "FROM": 0},
    0xE0: {"name": "GMCTRP1", "FROM": 0},
    0xE1: {"name": "GMCTRN1", "FROM": 0}
}

# High level analyzers must subclass the HighLevelAnalyzer class.
class Hla(HighLevelAnalyzer):

    DisplayFormat = ChoicesSetting(
        label='Display Format',
        choices=('Dec', 'Hex')
    )


    # decode commands and data for display
    result_types = {
        "SpiTransactionError": {
            "format": "ERROR: {{data.error_info}}",
        },
        'command': {
            'format': '{{data.command}}'
        },
        'data': {
            'format': '{{data.data}}'
        }
    }

    def __init__(self):
        # Whether SPI is currently enabled
        self.spi_enable = False

        self.base = 10
        if self.DisplayFormat == 'Hex':
            self.base = 16

        # Start time of the transaction - equivalent to the start time of the "Enable" frame
        self.frame_start_time = None

        # Whether there was an error.
        self.error = False

        # about how to process the data
        self.last_from = 0  # How many bytes to read for miso or mosi. per item
        self.data_packet_count = 0
        self.data_packet_value = 0

    def handle_enable(self, frame: AnalyzerFrame):
        self.spi_enable = True
        self.error = False
        self.frame_start_time = frame.start_time
        self.last_from = 0  # How many bytes to read for miso or mosi. per item
        self.data_packet_count = 0
        self.data_packet_value = 0

    def reset(self):
        self.spi_enable = False
        self.error = False
        self.frame_start_time = None

    def handle_result(self, frame):
        miso = frame.data["miso"]
        mosi = frame.data["mosi"]
        dc = frame.data["dc"]
        frame_type = None
        command = mosi[0]
        frame_data = {"command": command}
        our_frame = None
        if dc == b'\x00':
            print("DC=0 Mosi=", command)
            self.frame_start_time = frame.start_time
            frame_type = "command"
            if command in ILI9341_COMMANDS:
                command_line = ILI9341_COMMANDS[command]
                frame_data["command"] = command_line["name"]
                print (frame_data["command"])
                self.last_from = command_line["FROM"]  # How many bytes to read for miso or mosi. per item
                self.data_packet_count = 0
                self.data_packet_value = 0

            else:
                # Unrecognized commands are printed in hexadecimal
                frame_data["command"] = ''.join([ '0x', hex(command).upper()[2:] ])
                self.last_from = 0
        else:
            #data lets see if we can output it reasonably... 
            if self.last_from == 0: #mosi 1 byte
                frame_data["data"] = frame.data["mosi"]
                self.frame_start_time = frame.start_time
                frame_type = "data"
            elif self.last_from == 2:  # mosi 2 bytes
                if self.data_packet_count == 0:
                    self.frame_start_time = frame.start_time
                    self.data_packet_count = 1
                    self.data_packet_value = mosi[0]
                else:
                    self.data_packet_count = 0
                    self.data_packet_value =  (self.data_packet_value * 256) + mosi[0]
                    if self.base == 10:
                        frame_data["data"] = self.data_packet_value
                    else:
                        frame_data["data"] = ''.join([ '0x', hex(self.data_packet_value).upper()[2:] ])
                        
                    frame_type = "data"
            elif self.last_from == -1: #miso 1 byte
                frame_data["data"] = frame.data["miso"]
                self.frame_start_time = frame.start_time
                frame_type = "data"

            elif self.last_from == -1: # mosi 2 bytes
                if self.data_packet_count == 0:
                    self.frame_start_time = frame.start_time
                    self.data_packet_count = 1
                    self.data_packet_value = miso[0]
                else:
                    self.data_packet_count = 0
                    self.data_packet_value =  (self.data_packet_value * 256) + miso[0]
                    frame_data["data"] = self.data_packet_value
                    frame_type = "data"

        if frame_type:
            our_frame = AnalyzerFrame(frame_type,
                                      self.frame_start_time,
                                      frame.end_time,
                                      frame_data)
        output = our_frame
        return output

    def handle_disable(self, frame):

        self.reset()

    def handle_error(self, frame):
        result = AnalyzerFrame(
            "SpiTransactionError",
            frame.start_time,
            frame.end_time,
            {
                "error_info": "The clock was in the wrong state when the enable signal transitioned to active"
            }
        )
        self.reset()

    def decode(self, frame: AnalyzerFrame):
        if frame.type == "enable":
            return self.handle_enable(frame)
        elif frame.type == "result":
            return self.handle_result(frame)
        elif frame.type == "disable":
            return self.handle_disable(frame)
        elif frame.type == "error":
            return self.handle_error(frame)
        else:
            return AnalyzerFrame(
                "SpiTransactionError",
                frame.start_time,
                frame.end_time,
                {
                    "error_info": "Unexpected frame type from input analyzer: {}".format(frame.type)
                }
            )
