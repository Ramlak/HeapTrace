from Queue import Queue
from PyQt5.QtCore import QThread
from settings import settings
from utils.misc import getcmd, PopenAndCall, PinCommunication

__author__ = 'kalmar'


class HeapTrace(object):
    def __init__(self, mainWindow):
        self.mainWindow = mainWindow
        self.reader = None
        self.thread = None
        self.proc = None

    def run(self):
        self.log = []
        self.bits = int(settings.get('new trace', 'BITS'))
        self.mainWindow.textLog.clear()
        invocation = PopenAndCall(getcmd(self.bits), shell=False)
        invocation.finished.connect(self.on_proc_finished)
        invocation.started.connect(self.on_proc_started)
        invocation.start(self)

    def kill(self):
        print "Kill them all!"
        if self.thread:
            self.thread.quit()
        if self.proc:
            print "Terminating process!"
            self.proc.terminate()

    def newHeapOperation(self, line):
        self.log.append(line)
        self.mainWindow.textLog.append(line)

    def on_proc_started(self):
        print "Started process.."
        self.mainWindow.status("Process started")
        self.events = Queue(maxsize=0)
        self.reader = PinCommunication('localhost', 12345, self.bits, self.events)
        self.thread = QThread()
        self.reader.moveToThread(self.thread)
        self.reader.got_heap_op.connect(self.newHeapOperation)
        self.thread.started.connect(self.reader.event_loop)
        self.reader.finished.connect(self.on_reader_finished)
        self.thread.finished.connect(self.on_thread_finished)
        self.thread.start()

    def on_proc_finished(self):
        if self.thread:
            self.thread.quit()
        self.proc = None
        self.mainWindow.status("Process finished ({} lines)".format(len(self.log)))

    def on_reader_finished(self):
        print "Reader finished"
        self.kill()
        self.reader.deleteLater()

    def on_thread_finished(self):
        print "Thread finished"
        self.thread.deleteLater()
        self.thread = None