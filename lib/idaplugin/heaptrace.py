#!/usr/bin/env python
#

# IDA libraries
import idaapi
import idautils
import idc
from idaapi import Form, Choose2, plugin_t

# Python libraries
import os
import binascii
import string
import copy
from time import sleep
import threading

from struct import pack, unpack
from ctypes import *
from socket import socket, AF_INET, SOCK_STREAM, timeout, error

HEAPTRACER_VERSION = "0.1"


class Packet(Structure):
    _pack_ = 1

    def export(self):
        return buffer(self)[:]

    def fill(self, bytes):
        memmove(addressof(self), bytes, min(len(bytes), sizeof(self)))
        return self

    def __str__(self):
        return self.export()

    def __getitem__(self, i):
        if not isinstance(i, int):
            raise TypeError('subindices must be integers %r', i)
        return self._fields_[i][0], getattr(self, self._fields_[i][0])

    def text_dump(self, recursion=0):
        string = ""
        i = 0
        for name, val in self:
            i += 1
            string += " "*(20*recursion) + name.ljust(20)
            if isinstance(val, Packet):
                string += "\n"
                string += val.text_dump(recursion=recursion+1)
            else:
                if isinstance(val, (int, long)):
                    string += hex(val).ljust(20) + "\n"
                elif isinstance(val, Array):
                    string += "[" + ", ".join([hex(x) for x in val]) + "]\n"
        return string


# Communication packets declarations for 32 and 64 bit
CTT_ACK				=	0  #	do nothing
CTT_ERROR			=	1  #	signal an error
CTT_HELLO			=	2  #	first packet
CTT_READ_MEMORY		=	3  #	read 'size' bytes of memory from 'data'
CTT_WRITE_MEMORY	=	4  #	write 'size' bytes to 'data'
CTT_START_PROCESS	=	5  #	start application
CTT_EXIT_PROCESS	=	6  #	exit process
CTT_HEAP_INFO		=	7  #	get heap info
CTT_CHECK_HEAP_OP	=	8  # 	check for heap operations
CTT_GET_HEAP_OP		=	9  #	get heap operations
CTT_END             =   10

heap_op_type_t = ["IDLE", "MALLOC", "REALLOC", "CALLOC", "FREE"]

# 32
class malloc_chunk_32(Packet):
    _fields_ = [
        ("prev_size", c_uint32),
        ("size", c_uint32),
        ("fd", c_uint32),
        ("bk", c_uint32),
        ("fd_nextsize", c_uint32),
        ("bk_nextsize", c_uint32),
    ]


class heap_op_packet_t_32(Packet):
    _fields_ = [
        ("code", c_uint32),
        ("return_value", c_uint32),
        ("call_addr", c_uint32),
        ("args", c_uint32*3),
        ("chunk", malloc_chunk_32),
    ]


class idacmd_packet_t_32(Packet):
    _fields_ = [
        ("code", c_uint32),
        ("size", c_uint32),
        ("data", c_uint32),
    ]

# 64

class malloc_chunk_64(Packet):
    _fields_ = [
        ("prev_size", c_uint64),
        ("size", c_uint64),
        ("fd", c_uint64),
        ("bk", c_uint64),
        ("fd_nextsize", c_uint64),
        ("bk_nextsize", c_uint64),
    ]


class heap_op_packet_t_64(Packet):
    _fields_ = [
        ("code", c_uint32),
        ("return_value", c_uint64),
        ("call_addr", c_uint64),
        ("args", c_uint64*3),
        ("chunk", malloc_chunk_64),
    ]


class idacmd_packet_t_64(Packet):
    _fields_ = [
        ("code", c_uint32),
        ("size", c_uint64),
        ("data", c_uint64),
    ]

idacmd_packet_t = Packet
heap_op_packet_t = Packet


class PinConnection(socket):
    def __init__(self, host, port, bits):
        super(PinConnection, self).__init__(AF_INET, SOCK_STREAM)
        self.bits = bits
        self.running = False
        self.settimeout(2)
        try:
            self.connect((host, port))
            assert self.bits == self.hello()
            self.running = True
        except timeout:
            idaapi.warning("Cannot connect!")

    def send_cmd(self, **kwargs):
        self.sendall(str(idacmd_packet_t(**kwargs)))
        return self.get_ans()

    def get_ans(self):
        return self.recv(1024)

    def exit(self):
        self.send_cmd(CTT_EXIT_PROCESS)

    def hello(self):
        return idacmd_packet_t().fill(self.send_cmd(code=CTT_HELLO)).size * 8

    def get_heap_ops(self):
        left = idacmd_packet_t().fill(self.send_cmd(code=CTT_CHECK_HEAP_OP)).size
        ops = []
        while left > 0:
            ops.append(heap_op_packet_t().fill(self.send_cmd(code=CTT_GET_HEAP_OP)))
            left -= 1
        return ops


class HeapTracer(object):
    def __init__(self, settings):
        self.trace = []
        self.connection = None
        self.settings = settings
        global idacmd_packet_t, heap_op_packet_t
        if self.settings.bits == 32:
            idacmd_packet_t = idacmd_packet_t_32
            heap_op_packet_t = heap_op_packet_t_32
        elif self.settings.bits == 64:
            idacmd_packet_t = idacmd_packet_t_64
            heap_op_packet_t = heap_op_packet_t_64
        else:
            idaapi.warning("WTF! Bits not 32 or 64!?")

    def new_trace(self):
        self.trace = []
        self.connection = PinConnection(self.settings.host, self.settings.port, self.settings.bits)

        if not self.connection.running:
            self.show_heaptracer_menu()
            return

        while 1:
            try:
                ops = self.connection.get_heap_ops()
                for op in ops:
                    print "="*10+heap_op_type_t[op.code]+"="*10
                    print op.text_dump()
                sleep(1)
            except error:
                self.connection.running = False
                idaapi.warning("Process finished!")
                break

    def show_heaptracer_menu(self):
        f = ConfigureForm(self)
        ok = f.Execute()
        if ok == 1:
            f.Free()
            self.new_trace()
            return
        f.Free()


class Settings(object):
    def __init__(self, bits):
        self.port = 29678
        self.host = "192.168.1.1"
        self.pin_path = "/usr/bin/pin"
        self.exec_path = ""
        self.bits = bits


class ConfigureForm(Form):
    def __init__(self, heaptracer):
        self.heaptracer = heaptracer
        Form.__init__(self, 
r"""Heap Tracer
{FormChangeCb}
Pin path       <##:{strPinPath}>
Executable path<##:{strExecPath}>
<Host:{strHost}>{spacer}<Port:{intPort}>
""", {
            'spacer'          : Form.StringLabel("       "),
            'strPinPath'      : Form.StringInput(swidth=35,tp=Form.FT_ASCII),
            'strExecPath'     : Form.StringInput(swidth=35,tp=Form.FT_ASCII),
            'FormChangeCb'    : Form.FormChangeCb(self.OnFormChange),
            'strHost'         : Form.StringInput(swidth=25,tp=Form.FT_ASCII),
            'intPort'         : Form.NumericInput(swidth=10,tp=Form.FT_DEC),
            })

        self.Compile()

    def OnFormChange(self, fid):

        # Form initialization
        if fid == -1:

            # Set initial checkboxes for the classic metasploit 3-byte pattern
            self.SetControlValue(self.strPinPath, self.heaptracer.settings.pin_path)
            self.SetControlValue(self.strExecPath, self.heaptracer.settings.exec_path)
            self.SetControlValue(self.strHost, self.heaptracer.settings.host)
            self.SetControlValue(self.intPort, self.heaptracer.settings.port)
            pass
            # Set initial charsets values

        # Form OK pressed
        elif fid == -2:
            self.heaptracer.settings.pin_path = self.GetControlValue(self.strPinPath)
            self.heaptracer.settings.exec_path = self.GetControlValue(self.strExecPath)
            self.heaptracer.settings.host = self.GetControlValue(self.strHost)
            self.heaptracer.settings.port = self.GetControlValue(self.intPort)
            return 1

        return 0

    def pattern_create(self, size):
        return

    def update_complete_pattern(self, c4, c3, c2, c1):
        return


###############################################################################
# Plugin Manager
###############################################################################

class HeapTracerManager():
    """ Class that manages GUI forms and standard configuration of the plugin. """

    def __init__(self):
        self.addmenu_item_ctxs = list()
        self.heaptracer = HeapTracer(settings=Settings(bits=idc.GetSegmentAttr(list(idautils.Segments())[0], idc.SEGATTR_BITNESS)*32))
    ###########################################################################
    # Menu Items
    def add_menu_item_helper(self, menupath, name, hotkey, flags, pyfunc, args):

        # add menu item and report on errors
        addmenu_item_ctx = idaapi.add_menu_item(menupath, name, hotkey, flags, pyfunc, args)
        if addmenu_item_ctx is None:
            return 1
        else:
            self.addmenu_item_ctxs.append(addmenu_item_ctx)
            return 0

    def add_menu_items(self):
        if self.add_menu_item_helper("View/Open subviews/Segments", "Heap Trace", "CTRL+ALT+H", 0, self.show_heaptracer_menu, None) : return 1

        return 0

    def del_menu_items(self):
        for addmenu_item_ctx in self.addmenu_item_ctxs:
            idaapi.del_menu_item(addmenu_item_ctx)

    ###########################################################################
    # Utility Functions

    ###########################################################################
    # View Callbacks

    def show_heaptracer_menu(self):
        self.heaptracer.show_heaptracer_menu()


###############################################################################

class heaptracer_t(plugin_t):

    flags = idaapi.PLUGIN_UNL
    comment = "Heap tracer and profiler."
    help = "Heap tracer and profiler."
    wanted_name = "Heap Tracer"
    wanted_hotkey = ""

    def init(self):

        # Only Intel x86/x86-64 are supported
        if idaapi.ph_get_id() == idaapi.PLFM_386:

            global heaptracer_manager

            # Check if already initialized
            if not 'heaptracer_manager' in globals():

                heaptracer_manager = HeapTracerManager()
                if heaptracer_manager.add_menu_items():
                    print "Failed to initialize Heap Tracer."
                    heaptracer_manager.del_menu_items()
                    del heaptracer_manager
                    return idaapi.PLUGIN_SKIP
                else:
                    print("Initialized Heap Tracer v%s (c) Marcin Kalinowski <kalmar2718@gmail.com>" % HEAPTRACER_VERSION)

            return idaapi.PLUGIN_KEEP
        else:
            return idaapi.PLUGIN_SKIP

    def run(self, arg):
        pass

    def term(self):
        pass


def PLUGIN_ENTRY():
    return heaptracer_t()