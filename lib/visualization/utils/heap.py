__author__ = 'kalmar'
from ctypes import *


class cmd_type_t(object):
    CTT_ACK				=	0	#	do nothing
    CTT_ERROR			=	1	#	signal an error
    CTT_HELLO			=	2	#	first packet
    CTT_READ_MEMORY		=	3	#	read 'size' bytes of memory from 'data'
    CTT_WRITE_MEMORY	=	4	#	write 'size' bytes to 'data'
    CTT_START_PROCESS	=	5	#	start application
    CTT_EXIT_PROCESS	=	6	#	exit process
    CTT_HEAP_INFO		=	7	#	get heap info
    CTT_CHECK_HEAP_OP	=	8	# 	check for heap operations
    CTT_GET_HEAP_OP		=	9	#	get heap operations
    CTT_END	            =   10  #

CMD_TYPE_T_NAMES = ["ACK", "ERROR", "HELLO", "READ MEMORY", "WRITE MEMORY", "START PROCESS", "EXIT PROCESS", "HEAP INFO", "CHECK HEAP OPERATIONS", "GET HEAP OPERATION", "END"]
HEAP_OP_TYPE_t_NAMES = ["IDLE", "MALLOC", "REALLOC", "CALLOC", "FREE"]


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
        string = "="*10+HEAP_OP_TYPE_t_NAMES[self.code]+"="*10+"\n" if recursion == 0 else ""
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