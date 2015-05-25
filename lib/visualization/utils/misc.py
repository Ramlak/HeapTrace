from Queue import Empty
from _socket import error
import shlex
from socket import socket
from time import time, sleep
from utils.heap import cmd_type_t, heap_op_packet_t_32, idacmd_packet_t_64, idacmd_packet_t_32, heap_op_packet_t_64, Packet

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
    pin_cmd = "pin -t {} -d 0 -p {} -- {}".format(pintool_path, int(settings.get('main', 'PIN_SERVER_PORT')),  settings.get('new trace', 'EXECUTABLE'))

    if settings.get('new trace', 'USE_TCP_WRAPPER') != 'False':
        final_cmd += settings.get('main', 'TCP_WRAPPER_COMMAND').replace('[CMD]', pin_cmd).replace('[PORT]', settings.get('new trace', 'TCP_WRAPPER_PORT'))
    else:
        final_cmd += settings.get('main', 'NEW_TERMINAL_COMMAND').replace('[CMD]', pin_cmd)

    return shlex.split(final_cmd)


def randoms(count, alphabet=string.lowercase):
    return ''.join(random.choice(alphabet) for _ in xrange(count))


class PinCommunication(QObject):

    """A worker which reads commands from a FIFO endlessly."""

    got_heap_op = pyqtSignal(Packet)
    finished = pyqtSignal()
    pin_PID = pyqtSignal(int)

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
        count = time()
        while True:
            sleep(1)
            try:
                self.s.connect((self.host, self.port))
                self.s.settimeout(5)
                self.run_loop = True
                self.events.put(cmd_type_t.CTT_HELLO)
                self.events.put(cmd_type_t.CTT_START_PROCESS)
                break
            except error as e:
                if e.errno == 111:
                    if time() - count < 11:
                        print time() - count
                        continue
                    else:
                        break
                else:
                    import traceback
                    traceback.print_exc()
                    break

    def event_loop(self):
            self.connect()
            while self.run_loop:
                try:
                    self.handle_event(self.events.get(timeout=1))
                    self.events.task_done()
                except Empty:
                    self.events.put(cmd_type_t.CTT_CHECK_HEAP_OP)
                except error as e:
                    if e.errno == 32:
                        break
                    import traceback
                    traceback.print_exc()
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
        left = self.fill_cmd(self.send_cmd(code=cmd_type_t.CTT_CHECK_HEAP_OP)).size
        while left > 0:
            self.events.put(cmd_type_t.CTT_GET_HEAP_OP)
            left -= 1

    def get_heap_op(self):
        self.got_heap_op.emit(self.fill_op(self.send_cmd(code=cmd_type_t.CTT_GET_HEAP_OP)))

    def hello(self):
        ans = self.fill_cmd(self.send_cmd(code=cmd_type_t.CTT_HELLO))
        if ans.size*8 != self.bits:
            self.run_loop = False

    def start_process(self):
        self.pin_PID.emit(self.fill_cmd(self.send_cmd(code=cmd_type_t.CTT_START_PROCESS)).data)


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