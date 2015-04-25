#include "pin.H"
#include <malloc.h>
#include <unistd.h>
#include <iostream>
#include <fstream>

// Command line arguments

KNOB<string> PipeName(KNOB_MODE_WRITEONCE, "pintool", "o", "/tmp/example_pipe", "specify pipe name");

// Pipe file

ofstream PipeFile;

// Constants for heap handling

size_t SIZE_SZ = sizeof(size_t);
size_t MALLOC_ALIGN_MASK = ~(2 * SIZE_SZ - 1);

// Some global variables

struct malloc_call
{
	size_t requested_size;
	size_t allocated_size;
	size_t returned_value;
	size_t call_addr; // form now it's return address
};

struct realloc_call
{
	size_t ptr;
	size_t requested_size;
	size_t allocated_size;
	size_t returned_value;
	size_t call_addr;
};

struct free_call
{
	size_t ptr;
	size_t returned_value;
	size_t call_addr;
};

struct calloc_call
{
	size_t num;
	size_t element_size;
	size_t allocated_size;
	size_t returned_value;
	size_t call_addr;
};

struct malloc_call last_malloc;
struct realloc_call last_realloc;
struct calloc_call last_calloc;
struct free_call last_free;

size_t HEAP_BASE = 0;

bool InHeap(ADDRINT addr)
{
	ADDRINT compare = HEAP_BASE & (ADDRINT)0xfff00000;
	return (addr & (ADDRINT)0xfff00000) == compare;
}

VOID RecordReallocReturned(ADDRINT * addr, ADDRINT ret_ip)
{
	if(addr == 0)
	{
		PipeFile<< "Heap full!" << endl;
		return;
	}
	if(InHeap((ADDRINT)addr))
	{
		last_realloc.returned_value=(size_t)addr;
		last_realloc.call_addr = ret_ip;
		PIN_SafeCopy(&last_realloc.allocated_size, addr-1, SIZE_SZ);
		PipeFile<< "realloc(" << (void*)last_realloc.ptr << "," << last_realloc.requested_size << ")\treturned "  << addr << " (" << (last_realloc.allocated_size & MALLOC_ALIGN_MASK ) << ")" << endl;
	}
}

VOID RecordMallocReturned(ADDRINT * addr, ADDRINT ret_ip)
{
	if(addr == 0)
	{
		PipeFile<< "Heap full!" << endl;
		return;
	}
	if(InHeap((ADDRINT)addr))	{
		last_malloc.returned_value=(size_t)addr;
		last_malloc.call_addr = ret_ip;
		PIN_SafeCopy(&last_malloc.allocated_size, addr-1, SIZE_SZ);
		PipeFile<< "malloc(" << last_malloc.requested_size <<")\treturned "  << addr << " (" << (last_malloc.allocated_size & MALLOC_ALIGN_MASK ) << ")" << endl;
	}
}

VOID RecordCallocReturned(ADDRINT * addr, ADDRINT ret_ip)
{
	if(addr == 0)
	{
		PipeFile<< "Heap full!" << endl;
		return;
	}
	if(InHeap((ADDRINT)addr))
	{
		last_calloc.returned_value=(size_t)addr;
		last_calloc.call_addr = ret_ip;
		PIN_SafeCopy(&last_calloc.allocated_size, addr-1, SIZE_SZ);
		PipeFile<< "calloc(" << last_calloc.num << "," << last_calloc.element_size << ")\treturned "  << addr << " (" << (last_calloc.allocated_size & MALLOC_ALIGN_MASK ) << ")" << endl;
	}
}

VOID RecordMallocInvocation(size_t req_size)
{
	last_malloc.requested_size = req_size;
}

VOID RecordReallocInvocation(ADDRINT ptr, size_t req_size)
{
	last_realloc.requested_size = req_size;
	last_realloc.ptr = ptr;
}

VOID RecordCallocInvocation(size_t num, size_t req_size) // After certain size calloc is not caught 0_o
{
	last_calloc.element_size = req_size;
	last_calloc.num = num;
}

VOID RecordFreeInvocation(ADDRINT * addr)
{
	if(InHeap((ADDRINT)addr))
	{
		last_free.ptr=(size_t)addr;
		PipeFile<< "Freeing " << addr << endl;
	}
}

VOID Image(IMG img, VOID *v)
{
	RTN rtn = RTN_FindByName(img, "malloc");
	if(rtn.is_valid())
	{
		RTN_Open(rtn);
		RTN_InsertCall(rtn, IPOINT_BEFORE, (AFUNPTR)RecordMallocInvocation, IARG_FUNCARG_ENTRYPOINT_VALUE, 0, IARG_END);
		RTN_InsertCall(rtn, IPOINT_AFTER, (AFUNPTR)RecordMallocReturned, IARG_FUNCRET_EXITPOINT_VALUE, IARG_RETURN_IP, IARG_END);
		RTN_Close(rtn);
	}

	rtn = RTN_FindByName(img, "free");
	if(rtn.is_valid())
	{
		RTN_Open(rtn);
		RTN_InsertCall(rtn, IPOINT_BEFORE, (AFUNPTR)RecordFreeInvocation, IARG_FUNCARG_ENTRYPOINT_VALUE, 0, IARG_END);
		RTN_Close(rtn);
	}
	
	rtn = RTN_FindByName(img, "realloc");
	if(rtn.is_valid())
	{
		RTN_Open(rtn);
		RTN_InsertCall(rtn, IPOINT_BEFORE, (AFUNPTR)RecordReallocInvocation, IARG_FUNCARG_ENTRYPOINT_VALUE, 0, IARG_FUNCARG_ENTRYPOINT_VALUE, 1, IARG_END);
		RTN_InsertCall(rtn, IPOINT_AFTER, (AFUNPTR)RecordReallocReturned, IARG_FUNCRET_EXITPOINT_VALUE, IARG_RETURN_IP, IARG_END);
		RTN_Close(rtn);
	}

	rtn = RTN_FindByName(img, "calloc");
	if(rtn.is_valid())
	{
		RTN_Open(rtn);
		RTN_InsertCall(rtn, IPOINT_BEFORE, (AFUNPTR)RecordCallocInvocation, IARG_FUNCARG_ENTRYPOINT_VALUE, 0, IARG_FUNCARG_ENTRYPOINT_VALUE, 1, IARG_END);
		RTN_InsertCall(rtn, IPOINT_AFTER, (AFUNPTR)RecordCallocReturned, IARG_FUNCRET_EXITPOINT_VALUE, IARG_RETURN_IP, IARG_END);
		RTN_Close(rtn);
	}
}

int main(int argc, char **argv)
{
	PIN_Init(argc, argv);
	PIN_InitSymbols();
	IMG_AddInstrumentFunction(Image, NULL);
	HEAP_BASE = (size_t)sbrk(0);
	PipeFile.open(PipeName.Value().c_str());
	PIN_StartProgram();
	return 0;
}