__author__ = 'kalmar'

import string
import random
import os
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QProcess
from select import select


def randoms(count, alphabet=string.lowercase):
    return ''.join(random.choice(alphabet) for _ in xrange(count))


class BlockingFIFOReader(QObject):

    """A worker which reads commands from a FIFO endlessly."""

    got_line = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, filename):
        super(BlockingFIFOReader, self).__init__()
        self.filename = filename
        self.fifo = None

    def read_fifo(self):
        # We open as R/W so we never get EOF and have to reopen the pipe.
        # See http://www.outflux.net/blog/archives/2008/03/09/using-select-on-a-fifo/
        # We also use os.open and os.fdopen rather than built-in open so we can
        # add O_NONBLOCK.
        oshandle = os.open(self.filename, os.O_RDWR | os.O_NONBLOCK)
        self.fifo = os.fdopen(oshandle, 'r')
        while True:
            print("thread loop")
            ready_r, ready_w, ready_e = select([self.fifo], [], [], 1)
            if ready_r:
                print("reading data")
                lines = self.fifo.readlines()
                for line in lines:
                    self.got_line.emit(line.rstrip())
            if QThread.currentThread().isInterruptionRequested():
                self.finished.emit()
                return