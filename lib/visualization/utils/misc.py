from Queue import Queue, Empty
from _socket import AF_INET
import shlex
from socket import socket
from utils.heap import cmd_type_t, heap_op_packet_t_32, idacmd_packet_t_64, idacmd_packet_t_32, heap_op_packet_t_64

__author__ = 'kalmar'

import string
import random
import os
import subprocess
import threading
from settings import settings, ROOT_DIR
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QProcess


def getcmd():
    final_cmd = ""
    if int(settings.get('new trace', 'BITS')) == 32:
        pin_cmd = "pin -t {} -o {} -- {}".format(os.path.join(ROOT_DIR, "lib/pin/obj-ia32/heaptrace.so"), settings.get('new trace', 'EXECUTABLE'))
    elif int(settings.get('new trace', 'BITS')) == 64:
        pin_cmd = "pin -t {} -o {} -- {}".format(os.path.join(ROOT_DIR, "lib/pin/obj-intel64/heaptrace.so"), settings.get('new trace', 'EXECUTABLE'))
    else:
        raise Exception("WTF!?")

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

    def __init__(self, host, port, bits):
        super(PinCommunication, self).__init__()
        self.s = socket()
        self.events = Queue(maxsize=0)
        self.set_bitness(bits)
        try:
            self.s.connect((host, port))
        except Exception:
            import traceback
            traceback.print_exc()
            exit(1)
        self.run_loop = True

    def sendall(self, data):
        return self.s.sendall(data)

    def recv(self, nb):
        return self.s.recv(nb)

    def set_bitness(self, bits):
        self.bits = bits
        if self.bits == 32:
            self.idacmd_packet_t = idacmd_packet_t_32
            self.heap_op_packet_t = heap_op_packet_t_32
        elif self.bits == 64:
            self.idacmd_packet_t = idacmd_packet_t_64
            self.heap_op_packet_t = heap_op_packet_t_64
        else:
            print "Wtf bits are wrong!!"

    def event_loop(self):
            while self.run_loop:
                try:
                    self.handle_event(self.events.get(timeout=1))
                    self.events.task_done()
                except Empty:
                    self.events.put(cmd_type_t.CTT_GET_HEAP_OP)

    def get_ans(self):
        return self.recv(1024)

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

    def check_heap_op(self):
        left = self.idacmd_packet_t().fill(self.send_cmd(code=cmd_type_t.CTT_CHECK_HEAP_OP)).size
        while left > 0:
            self.events.put(cmd_type_t.CTT_GET_HEAP_OP)
            left -= 1

    def get_heap_op(self):
        self.got_heap_op.emit(str(self.send_cmd(code=cmd_type_t.CTT_GET_HEAP_OP)))

    def hello(self):


class PopenAndCall(QObject):

    finished = pyqtSignal()

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
        os.chdir(cwd)
        self.heaptrace.proc = proc
        proc.wait()
        self.finished.emit()