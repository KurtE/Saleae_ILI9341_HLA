# High Level Analyzer
# For more information and documentation, please go to https://support.saleae.com/extensions/high-level-analyzer-extensions

from saleae.analyzers import HighLevelAnalyzer, AnalyzerFrame, StringSetting, NumberSetting, ChoicesSetting

import struct

ILI9341_COMMANDS = {
    0x00: {"name": "NOP", "format": 0},
    0x01: {"name": "SWRESET", "format": 0},
    0x04: {"name": "RDDID", "format": 0},
    0x09: {"name": "RDDST", "format": 0},
    0x10: {"name": "SLPIN", "format": 0},
    0x11: {"name": "SLPOUT", "format": 0},
    0x12: {"name": "PTLON", "format": 0},
    0x13: {"name": "NORON", "format": 0},
    0x0A: {"name": "RDMODE", "format": 0},
    0x0B: {"name": "RDMADCTL", "format": 0},
    0x0C: {"name": "RDPIXFMT", "format": 0},
    0x0D: {"name": "RDIMGFMT", "format": 0},
    0x0F: {"name": "RDSELFDIAG", "format": 0},
    0x20: {"name": "INVOFF", "format": 0},
    0x21: {"name": "INVON", "format": 0},
    0x26: {"name": "GAMMASET", "format": 0},
    0x28: {"name": "DISPOFF", "format": 0},
    0x29: {"name": "DISPON", "format": 0},
    0x2A: {"name": "CASET", "format": 12},
    0x2B: {"name": "PASET", "format": 12},
    0x2C: {"name": "RAMWR", "format": 2},
    0x2E: {"name": "RAMRD", "format": -2},
    0x30: {"name": "PTLAR", "format": 0},
    0x33: {"name": "VSCRDEF", "format": 0},
    0x36: {"name": "MADCTL", "format": 0},
    0x37: {"name": "VSCRSADD", "format": 0},
    0x3A: {"name": "PIXFMT", "format": 0},
    0xB1: {"name": "FRMCTR1", "format": 0},
    0xB2: {"name": "FRMCTR2", "format": 0},
    0xB3: {"name": "FRMCTR3", "format": 0},
    0xB4: {"name": "INVCTR", "format": 0},
    0xB6: {"name": "DFUNCTR", "format": 0},
    0xC0: {"name": "PWCTR1", "format": 0},
    0xC1: {"name": "PWCTR2", "format": 0},
    0xC2: {"name": "PWCTR3", "format": 0},
    0xC3: {"name": "PWCTR4", "format": 0},
    0xC4: {"name": "PWCTR5", "format": 0},
    0xC5: {"name": "VMCTR1", "format": 0},
    0xC7: {"name": "VMCTR2", "format": 0},
    0xDA: {"name": "RDID1", "format": 0},
    0xDB: {"name": "RDID2", "format": 0},
    0xDC: {"name": "RDID3", "format": 0},
    0xDD: {"name": "RDID4", "format": 0},
    0xE0: {"name": "GMCTRP1", "format": 0},
    0xE1: {"name": "GMCTRN1", "format": 0}
}

# High level analyzers must subclass the HighLevelAnalyzer class.
class Hla(HighLevelAnalyzer):

    DisplayFormat = ChoicesSetting(
        label='Display Format',
        choices=('Auto', 'Dec', 'Hex')
    )

    DisplayLevel = ChoicesSetting(
        label='Outputs',
        choices=('All', 'Commands')
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

        self.base = 0 # commands choose. 
        if self.DisplayFormat == 'Hex':
            self.base = 16
        elif self.DisplayFormat == 'Dec':
            self.base = 10

        self.display_all = True
        if self.DisplayLevel == 'Commands':
            self.display_all = False

        # Start time of the transaction - equivalent to the start time of the "Enable" frame
        self.frame_start_time = None

        # Whether there was an error.
        self.error = False

        # about how to process the data
        self.data_packet_save = None
        self.command_line = None
        self.last_format = 0  # How many bytes to read for miso or mosi. per item
        self.data_packet_count = 0
        self.data_packet_value = 0

    def handle_enable(self, frame: AnalyzerFrame):
        self.spi_enable = True
        self.error = False
        self.frame_start_time = frame.start_time
        self.last_format = 0  # How many bytes to read for miso or mosi. per item
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
            if command in ILI9341_COMMANDS:
                self.command_line = ILI9341_COMMANDS[command]
                print (frame_data["command"])
                self.last_format = self.command_line["format"]  # How many bytes to read for miso or mosi. per item

                # if > 10 then special process
                if self.last_format < 10:
                    frame_data["command"] = self.command_line["name"]
                    frame_type = "command"

                self.data_packet_count = 0
                self.data_packet_value = 0

            else:
                # Unrecognized commands are printed in hexadecimal
                frame_data["command"] = ''.join([ '0x', hex(command).upper()[2:] ])
                frame_type = "command"
                self.last_format = 0
        else:
            #data lets see if we can output it reasonably... 
            if self.last_format == 0: #mosi 1 byte
                if  self.display_all == True:
                    frame_data["data"] = frame.data["mosi"]
                    self.frame_start_time = frame.start_time
                    frame_type = "data"
            elif self.last_format == 2:  # mosi 2 bytes
                if  self.display_all == True:
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
            elif self.last_format == 12:  # CMD + mosi 2 bytes + mosi 2 byte
                if self.data_packet_save is None:
                    self.data_packet_save = bytearray()
                #self.data_packet_save.extend(mosi[0])
                self.data_packet_save.extend(frame.data["mosi"])
                self.data_packet_count += 1
                if self.data_packet_count == 4:
                    self.data_packet_count = 0

                    #This has range start/end
                    #start with command
                    frame_type = "command"

                    range_start = (self.data_packet_save[0] * 256) + self.data_packet_save[1]
                    range_end = (self.data_packet_save[2] * 256) + self.data_packet_save[3]

                    if self.base == 16:
                        start_str = ''.join([ '0x', hex(range_start).upper()[2:] ])
                        end_str = ''.join([ '0x', hex(range_end).upper()[2:] ])
                    else:
                        start_str = str(range_start)
                        end_str = str(range_end)

                    frame_data["command"] = self.command_line["name"] + ':(' + start_str + ',' + end_str + ')'
                    self.data_packet_save = None

            elif self.last_format == -1: #miso 1 byte
                if  self.display_all == True:
                    frame_data["data"] = frame.data["miso"]
                    self.frame_start_time = frame.start_time
                    frame_type = "data"

            elif self.last_format == -1: # mosi 2 bytes
                if  self.display_all == True:
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
