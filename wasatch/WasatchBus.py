import logging
import os

from DeviceListFID import DeviceListFID

from usb import USBError

log = logging.getLogger(__name__)

# ##############################################################################
#                                                                              #
#                                WasatchBus                                    #
#                                                                              #
# ##############################################################################

##
# The different bus classes don't use inheritance and don't follow a common ABC
# or interface, but each should have an update() method, and each should have a 
# 'device_ids' array (TODO: USE INHERITANCE!) 
class WasatchBus(object):
    def __init__(self, monitor_dir = None):

        self.monitor_dir = monitor_dir

        self.device_ids = []

        self.file_bus = None
        self.usb_bus = None

        if self.monitor_dir:
            self.file_bus = FileBus(self.monitor_dir) 
        else:
            self.usb_bus = USBBus()

        # iterate buses on creation
        self.update()

    ## called by Controller.update_connections
    def update(self):
        self.device_ids = []

        if self.file_bus:
            self.device_ids.extend(self.file_bus.update())

        if self.usb_bus:
            self.device_ids.extend(self.usb_bus.update())

    ## called by Controller.update_connections
    def dump(self):
        log.debug("WasatchBus.dump: %s", self.device_ids)

# ##############################################################################
#                                                                              #
#                                    USBBus                                    #
#                               (file private)                                 #
#                                                                              #
# ##############################################################################

class USBBus(object):

    def __init__(self):
        self.backend_error_raised = False
        self.update()

    ## Return a list of connected USB device keys, in the format
    # "VID:PID:order:pidOrder", e.g. [ "0x24aa:0x1000:0:0", "0x24aa:0x4000:1:0", "0x24aa:0x1000:2:1" ]
    def update(self):
        log.debug("USBBus.update: instantiating DeviceListFID")
        device_ids = []

        try:
            log.debug("USBBus.update: instantiating DeviceListFID")
            lister = DeviceListFID()
            device_ids.extend(lister.device_ids)
        except USBError:
            # MZ: this seems to happen when I run from Git Bash shell
            #     (resolved on MacOS with 'brew install libusb')
            if not self.backend_error_raised:
                log.warn("No libusb backend", exc_info=1)
                self.backend_error_raised = True

        except Exception:
            log.critical("LIBUSB error", exc_info=1)

        return device_ids

# ##############################################################################
#                                                                              #
#                                   FileBus                                    #
#                               (file private)                                 #
#                                                                              #
# ##############################################################################

class FileBus(object):
    def __init__(self, directory):
        super(B, self).__init__()
        self.directory = directory
        self.configfile = os.path.join(self.directory, "spectrometer.json")

    def update(self):
        device_ids = []
        if os.access(self.directory, os.W_OK) and os.path.isfile(self.configfile):
            device_ids.append("FILE:%s", self.directory)
        return device_ids

