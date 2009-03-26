#!/usr/bin/python

from time import time
from math import floor

from twisted.internet import reactor, task

import usb2lpt
from usb2lpt import USB2LPTError

DT_SAMPLE = 0.5

DEBUG = False

class CPUReader(object):
    def __init__(self):
        self.cpu, self.time = 0, 0
        self.read_values()
        self.ncpus = self.countcpus()
        if DEBUG:
            print "#%s" % self.ncpus

    def countcpus(self):
        fd = open('/proc/stat')
        return len([l for l in fd.readlines()[1:] if l.find('cpu') != -1])

    def sample(self):
        self.read_values()
        percent = (self.cpu - self.last_cpu) / (self.time - self.last_time) / self.ncpus
        if percent > 100 or percent < 0:
            if DEBUG:
                print "Warning: spurios value? new, old, percent:", self.cpu, self.last_cpu, percent
        self.last_cpu = self.cpu
        self.last_time = self.time
        return max(0.0, min(100.0, percent))

    def read_values(self):
        self.last_cpu = self.cpu
        self.last_time = self.time
        self.time = time()
        fd = open('/proc/stat')
        self.cpu = int(fd.readline().split()[1])
        fd.close()

def reader_test():
    return CPUReader()

class Updater(object):
    def __init__(self):
        try:
            self.lpt = usb2lpt.open()
        except USB2LPTError, e:
            self.quit()
            raise e
        self.cpu = CPUReader()

    def quit(self, e = None):
        if reactor.running:
            # don't print twice - conversly, we assume reactor.running is False
            # because we already got here once
            if e: print "error: %s" % e
            reactor.stop()

    def install(self):
        self.sampler = task.LoopingCall(self.OnSample)
        self.sampler.start(DT_SAMPLE)

    def OnSample(self):
        percent_f = self.cpu.sample()
        mask = (1<<int(floor(percent_f/12.5)))-1
        if DEBUG:
            print mask, percent_f
        self.lpt.look_for_device()
        try:
            self.lpt.write_one(0, mask)
        except USB2LPTError, e:
            self.quit(e)

def main():
    try:
        updater = Updater()
        updater.install()
    except Exception, e:
        print "error: %s" % e
        raise SystemExit
    reactor.run()

if __name__ == '__main__':
    main()

