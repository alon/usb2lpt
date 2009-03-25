#!/usr/bin/python
"""
Talk to the usb2lpt adapter. For API See:

    http://www-user.tu-chemnitz.de/~heha/bastelecke/Rund um den PC/USB2LPT/API.htm.en

Simple usage:

import play
lpt = play.open()
lpt.write_one(0, 255) # turn on all data port (8 bits) pins

Simple command line usage: (count from 0 to 255)

for ((i=0;i<256;++i)); do ./play.py --out 0 $i; done

"""

import struct

import usb

__all__ = ['open', 'Usb2lpt', 'USB2LPT_VENDOR']

PRINTER_CLASS    = 0x07
VENDOR_CLASS     = 0xff # This is the one we need for general purpose parallel port use

USB2LPT_VENDOR = 0x5348

def get_device(vendorid):
    busses = usb.busses() # enumerate, takes a little while
    device = sum([[y for y in x.devices if y.idVendor == vendorid] for x in busses], [])[0]
    return device

def get_interface(configuration, which_class):
    return sum([[i for i in ifs if i.interfaceClass == which_class] for ifs in configuration.interfaces], [])

def open():
    return Usb2lpt()

class Usb2lpt(object):
    def __init__(self):
        self.init()

    def init(self):
        self.device = get_device(USB2LPT_VENDOR)
        self.configuration = self.device.configurations[0]
        self.interface = get_interface(self.configuration, VENDOR_CLASS)[0]
        self.out_ep = [ep for ep in self.interface.endpoints if ep.address < 128][0]
        self.in_ep = [ep for ep in self.interface.endpoints if ep.address >= 128][0]
        self.handle = None
    
    def open_handle(self):
        if self.handle is not None:
            try:
                self.handle.releaseInterface()
            except ValueError:
                pass
        if self.handle is None:
            self.handle = self.device.open()
            self.handle.claimInterface(self.interface)

    def write_one(self, a, b):
        """ A single output instruction. a determines address, b is contents.
        0 <= b <= 255. a's meanings:
            * 0 = data port (see Beyond Logic)
            * 2 = control port (with bits like "Strobe", "AutoFeed", but "Direction" (do data port) too)
            * 3 = EPP address write cycle (see Beyond Logic)
            * 4 = EPP data write cycle (a = 5, 6 and 7 do data cycles too)
            * 8 = ECP FIFO write (see Beyond Logic)
            * 10 = set ECP configuration register "ECR"
        """
        self.open_handle()
        self.handle.bulkWrite(self.out_ep.address, struct.pack('BB', a, b))

    def read_one(self, a):
        """ The meaning of a:
            * 0 = data port
            * 1 = status port (with bits "Busy", "Acknowledge", "Paper End" etc.)
            * 2 = control port (real line states)
            * 3 = EPP address read cycle (see Beyond Logic)
            * 4 = EPP data read cycle (a = 5, 6 and 7 do data cycles too)
            * 8 = ECP FIFO read or reading of "Configuration Register A"
            * 9 = read "Konfiguration Register B" (always 0)
            * 10 = read ECP Configuration Register "ECR" (e.g. FIFO state)
        """
        self.open_handle()
        self.handle.bulkWrite(self.out_ep.address, struct.pack('B', a | 0x10))
        return self.handle.bulkRead(self.in_ep.address, 1)

    def write(self, pairs):
        self.write_raw(struct.pack('BB'*len(pairs), *sum(pairs, [])))

    def write_raw(self, bytes_out, num_in=0):
        """ we can only write 64 bytes at a time
        """
        self.open_handle()
        n = len(bytes_out)
        for start in xrange(0, n, 64):
            self.handle.bulkWrite(self.out_ep.address, bytes_out[start:start+64])
        if num_in > 0:
            # TODO: does reading also have a limit of 64 bytes?
            return self.handle.bulkRead(self.in_ep.address, num_in)
        return None

    def reset(self):
        handle = self.device.open()
        handle.reset()
        # invalidates the handle, need to re-enumerate and get device
        self.init()
    
    def makePrinter(self, i):
        """ usbprint comes with the examples of python-usb module.
        It is only used by this function, and untested.
        """
        import usbprint
        return usbprint.Printer(self.device, self.configurations, get_interface(self.configuration, PRINTER_CLASS)[i])

def main():
    """ simple command line usage for demo purposes. You can output, sleep, input,
    and the count is just a test for multiple writes in one bulkWrite
    """
    import sys
    import time

    def help():
        print i, n
        print "usage: %s [[--out a b] [--in a]]" % sys.argv[0]
        raise SystemExit

    cmds = []
    lpt = open()
    n = len(sys.argv)
    i = 1
    while i < n:
        f = sys.argv[i]
        i += 1
        if f == '--out':
            if i + 2 > n: help()
            try:
                a = int(sys.argv[i])
                b = int(sys.argv[i+1])
            except:
                help()
            cmds.append(lambda lpt=lpt, a=a, b=b: lpt.write_one(a, b))
            i += 2
        elif f == '--in':
            if i + 1 > n: help()
            try:
                a = int(sys.argv[i])
            except:
                help()
            cmds.append(lambda lpt=lpt, a=a: lpt.read_one(a))
            i += 1
        elif f == '--count':
            cmds.append(lambda lpt=lpt: lpt.write([[0, i] for i in xrange(256)]))
        elif f == '--sleep':
            try:
                t = float(sys.argv[i])/1000
            except:
                help()
            cmds.append(lambda t=t: time.sleep(t))
            i += 1
    print ', '.join([str(cmd()) for cmd in cmds])

if __name__ == '__main__':
    main()

