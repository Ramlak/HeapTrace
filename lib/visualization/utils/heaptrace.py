from Queue import Queue
from PyQt5.QtCore import QThread, QObject
import os
import signal
from settings import settings
from utils.heap import heap_op_type_t
from utils.misc import getcmd, PopenAndCall, PinCommunication
from utils.windows import HeapWindow, Block

__author__ = 'kalmar'


class HeapTrace(object):
    def __init__(self, mainWindow):
        self.mainWindow = mainWindow
        self.reader = None
        self.thread = None
        self.proc = None
        self.blocks = []

    def run(self):
        self.log = []
        self.bits = int(settings.get('new trace', 'BITS'))
        self.mainWindow.textLog.clear()
        invocation = PopenAndCall(getcmd(self.bits), shell=False)
        invocation.finished.connect(self.on_proc_finished)
        invocation.started.connect(self.on_proc_started)
        invocation.start(self)

    def kill(self):
        if self.thread:
            self.thread.quit()
        if self.proc:
            self.proc.terminate()
        try:
            os.kill(self.pin_proc, signal.SIGKILL)
        except Exception:
            pass

    def find_block_by_addr(self, addr):
        for i, block in enumerate(self.heapView.layoutHeapView.children()):
            print block
            if block.base_addr == addr:
                return i, block
        return None, None

    def on_got_heap_op(self, packet):
        if packet.code == heap_op_type_t.PKT_FREE:
            i, freed = self.find_block_by_addr(packet.args[0])
            if freed == None:
                print "Hacking is not nice."
            else:
                freed.new_packet(packet)
        else:
            i, old = self.find_block_by_addr(packet.return_value)
            if not old:
                block = Block(packet)
                self.heapView.push_new_block(block)
                self.blocks.append(block)
            else:
                if old.packet.chunk.size != packet.chunk.size:
                    self.heapView.layoutHeapView.removeWidget(old)
                else:
                    old.new_packet(packet)

        self.log.append(packet)
        self.mainWindow.textLog.append(packet.text_dump() + "\n")

    def on_proc_started(self):
        self.mainWindow.status("Process started")
        self.events = Queue(maxsize=0)
        self.reader = PinCommunication('localhost', 12345, self.bits, self.events)
        self.thread = QThread()
        self.reader.moveToThread(self.thread)
        self.reader.got_heap_op.connect(self.on_got_heap_op)
        self.reader.pin_PID.connect(self.on_pin_pid_received)
        self.thread.started.connect(self.reader.event_loop)
        self.reader.finished.connect(self.on_reader_finished)
        self.thread.finished.connect(self.on_thread_finished)
        self.thread.start()

    def on_pin_pid_received(self, pid):
        self.pin_proc = pid
        self.heapView = HeapWindow(self.mainWindow)
        self.heapView.show()

    def on_proc_finished(self):
        if self.thread:
            self.thread.quit()
        self.proc = None
        self.kill()
        self.mainWindow.status("Process finished ({} lines)".format(len(self.log)))

    def on_reader_finished(self):
        self.kill()
        self.reader.deleteLater()

    def on_thread_finished(self):
        self.thread.deleteLater()
        self.thread = None