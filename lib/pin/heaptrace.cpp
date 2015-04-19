#include "pin.H"
#include <malloc.h>
#include <unistd.h>
#include <iostream>

// Constants for heap handling

size_t SIZE_SZ = sizeof(size_t);
size_t MALLOC_ALIGN_MASK = ~(2 * SIZE_SZ - 1);

// Some global variables

size_t last_malloc_size;
size_t HEAP_BASE = 0;

VOID RecordMallocReturned(ADDRINT * addr)
{
	if(addr == 0)
	{
		cerr << "Heap full!";
		return;
	}
	if(((size_t)addr & (ADDRINT)0xfff00000) == (HEAP_BASE & (size_t)0xfff00000))
	{
		size_t size = 0;
		PIN_SafeCopy(&size, addr-1, SIZE_SZ);
		cerr << "malloc(" << last_malloc_size <<")\treturned "  << addr << " (" << (size & MALLOC_ALIGN_MASK ) << ")" << endl;
	}
}

VOID RecordMallocInvocation(size_t size)
{
	last_malloc_size = size;
}

VOID RecordFreeInvocation(ADDRINT * addr)
{
	cerr << "Freeing " << addr << endl;
}

VOID Image(IMG img, VOID *v)
{
	RTN mallocRtn = RTN_FindByName(img, "malloc");
	if(mallocRtn.is_valid())
	{
		RTN_Open(mallocRtn);
		RTN_InsertCall(mallocRtn, IPOINT_BEFORE, (AFUNPTR)RecordMallocInvocation, IARG_FUNCARG_ENTRYPOINT_VALUE, 0, IARG_END);
		RTN_InsertCall(mallocRtn, IPOINT_AFTER, (AFUNPTR)RecordMallocReturned, IARG_FUNCRET_EXITPOINT_VALUE, IARG_END);
		RTN_Close(mallocRtn);
	}

	RTN freeRtn = RTN_FindByName(img, "free");
	if(freeRtn.is_valid())
	{
		RTN_Open(freeRtn);
		RTN_InsertCall(freeRtn, IPOINT_BEFORE, (AFUNPTR)RecordFreeInvocation, IARG_FUNCARG_ENTRYPOINT_VALUE, 0, IARG_END);
		RTN_Close(freeRtn);
	}
}

int main(int argc, char **argv)
{
	PIN_Init(argc, argv);
	PIN_InitSymbols();
	IMG_AddInstrumentFunction(Image, NULL);
	HEAP_BASE = (size_t)sbrk(0);
	cerr << endl;
	PIN_StartProgram();
	return 0;
}