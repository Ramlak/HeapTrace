from Queue import Queue, Empty
from _socket import error
import shlex
from socket import socket
from time import time, sleep
from utils.heap import cmd_type_t, heap_op_packet_t_32, idacmd_packet_t_64, idacmd_packet_t_32, heap_op_packet_t_64, \
    CMD_TYPE_T_NAMES

__author__ = 'kalmar'

import string
import random
import os
import subprocess
import threading
from settings import settings, ROOT_DIR
from PyQt5.QtCore import QObject, pyqtSignal


def getcmd(bits):
    final_cmd = ""
    pintool_path = os.path.join(ROOT_DIR, "lib/pintool/obj-{}/heaptrace.so".format(["", "ia32", "intel64"][bits/32]))
    pin_cmd = "pin -t {} -d 2 -p {} -- {}".format(pintool_path, int(settings.get('main', 'PIN_SERVER_PORT')),  settings.get('new trace', 'EXECUTABLE'))

    if settings.get('new trace', 'USE_TCP_WRAPPER') != 'False':
        final_cmd += settings.get('main', 'TCP_WRAPPER_COMMAND').replace('[CMD]', pin_cmd).replace('[PORT]', settings.get('new trace', 'TCP_WRAPPER_PORT'))
    else:
        final_cmd += settings.get('main', 'NEW_TERMINAL_COMMAND').replace('[CMD]', pin_cmd)

    return shlex.split(final_cmd)


def randoms(count, alphabet=string.lowercase):
    return ''.join(random.choice(alphabet) for _ in xrange(count))


class PinCommunication(QObject):

    """A worker which reads commands from a FIFO endlessly."""

    got_heap_op = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, host, port, bits, events):
        super(PinCommunication, self).__init__()
        self.host, self.port, self.bits = host, port, bits
        self.s = socket()
        self.events = events
        self.set_bitness()
        self.run_loop = False

    def sendall(self, data):
        self.s.sendall(data)

    def recv(self, nb):
        return self.s.recv(nb)

    def set_bitness(self):
        if self.bits == 32:
            self.idacmd_packet_t = idacmd_packet_t_32
            self.heap_op_packet_t = heap_op_packet_t_32
        elif self.bits == 64:
            self.idacmd_packet_t = idacmd_packet_t_64
            self.heap_op_packet_t = heap_op_packet_t_64
        else:
            print "Wtf bits are wrong!!"

    def connect(self):
        print "Trying to connect"
        count = time()
        while True:
            sleep(0.5)
            try:
                self.s.connect((self.host, self.port))
                self.run_loop = True
                self.events.put(cmd_type_t.CTT_HELLO)
                self.events.put(cmd_type_t.CTT_START_PROCESS)
                print "Connected!"
                break
            except error as e:
                if error.errno == 111:
                    if time() - count < 10000:
                        print time() - count
                        continue
                    else:
                        print "Cannot connect"
                        break
                else:
                    import traceback
                    traceback.print_exc()
                    break

    def event_loop(self):
            self.connect()
            while self.run_loop:
                try:
                    print "Entering try,except"
                    x = self.events.get(block=0, timeout=1)
                    print CMD_TYPE_T_NAMES[x]
                    self.handle_event(x)
                    self.events.task_done()
                    print "End of try - task done"
                except Empty:
                    print "Queue empty"
                    self.events.put(cmd_type_t.CTT_CHECK_HEAP_OP)
            self.finished.emit()

    def get_ans(self):
        return self.recv(1024)

    def fill_cmd(self, bytes):
        return self.idacmd_packet_t().fill(bytes)

    def fill_op(self, bytes):
        return self.heap_op_packet_t().fill(bytes)

    def send_cmd(self, **kwargs):
        self.sendall(self.idacmd_packet_t(**kwargs))
        return self.get_ans()

    def handle_event(self, event):
        if event == cmd_type_t.CTT_CHECK_HEAP_OP:
            self.check_heap_op()
        elif event == cmd_type_t.CTT_GET_HEAP_OP:
            self.get_heap_op()
        elif event == cmd_type_t.CTT_HELLO:
            self.hello()
        elif event == cmd_type_t.CTT_START_PROCESS:
            self.start_process()

    def check_heap_op(self):
        print "CHECK HEAP OP"
        left = self.fill_cmd(self.send_cmd(code=cmd_type_t.CTT_CHECK_HEAP_OP)).size
        print "%d heap operations found" % left
        while left > 0:
            self.events.put(cmd_type_t.CTT_GET_HEAP_OP)
            left -= 1

    def get_heap_op(self):
        self.got_heap_op.emit(str(self.send_cmd(code=cmd_type_t.CTT_GET_HEAP_OP)))

    def hello(self):
        ans = self.fill_cmd(self.send_cmd(code=cmd_type_t.CTT_HELLO))
        if ans.size*8 != self.bits:
            self.run_loop = False

    def start_process(self):
        self.send_cmd(code=cmd_type_t.CTT_START_PROCESS)


class PopenAndCall(QObject):

    finished = pyqtSignal()
    started = pyqtSignal()

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        super(PopenAndCall, self).__init__()

    def start(self, heaptrace):
        self.heaptrace = heaptrace
        threading.Thread(target=self.runInThread, args=[]).start()

    def runInThread(self):
        cwd = os.getcwd()
        os.chdir(settings.get('new trace', 'START_DIR'))
        proc = subprocess.Popen(*self.args, **self.kwargs)
        self.heaptrace.proc = proc
        self.started.emit()
        os.chdir(cwd)
        proc.wait()
        self.finished.emit()