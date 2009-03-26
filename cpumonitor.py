#!/usr/bin/python

from time import time
from math import floor

from twisted.internet import reactor, task

import play

DT_SAMPLE = 0.5

class CPUReader(object):
    def __init__(self):
        self.cpu, self.time = 0, 0
        self.read_values()
        self.ncpus = self.countcpus()
        print "#%s" % self.ncpus

    def countcpus(self):
        fd = open('/proc/stat')
        return len([l for l in fd.readlines()[1:] if l.find('cpu') != -1])

    def sample(self):
        self.read_values()
        percent = (self.cpu - self.last_cpu) / (self.time - self.last_time) / self.ncpus
        self.last_cpu = self.cpu
        self.last_time = self.time
        return percent

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
        self.lpt = play.open()
        self.cpu = CPUReader()

    def install(self):
        self.sampler = task.LoopingCall(self.OnSample)
        self.sampler.start(DT_SAMPLE)

    def OnSample(self):
        percent_f = self.cpu.sample()
        mask = (1<<int(floor(percent_f/12.5)))-1
        print mask, percent_f
        self.lpt.look_for_device()
        self.lpt.write_one(0, mask)

def main():
    updater = Updater()
    updater.install()
    reactor.run()

if __name__ == '__main__':
    main()

