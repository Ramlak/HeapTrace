#include "pin.H"
#include <malloc.h>
#include <iostream>

size_t SIZE_SZ = sizeof(size_t);
size_t MALLOC_ALIGN_MASK = ~(2 * SIZE_SZ - 1);


VOID RecordMalloc(ADDRINT * addr)
{
	if(addr == 0)
	{
		cerr << "Heap full!";
		return;
	}

	size_t size = 0;
	PIN_SafeCopy(&size, addr-1, SIZE_SZ);
	cerr << "Malloc recorded! "  << addr << " " << (size & MALLOC_ALIGN_MASK ) << endl;
}

VOID RecordFree(ADDRINT * addr)
{
	cerr << "Freeing " << addr << endl;
}

VOID Image(IMG img, VOID *v)
{
	RTN mallocRtn = RTN_FindByName(img, "malloc");
	if(mallocRtn.is_valid())
	{
		RTN_Open(mallocRtn);
		RTN_InsertCall(mallocRtn, IPOINT_AFTER, (AFUNPTR)RecordMalloc, IARG_FUNCRET_EXITPOINT_VALUE, IARG_END);
		RTN_Close(mallocRtn);
	}

	RTN freeRtn = RTN_FindByName(img, "free");
	if(freeRtn.is_valid())
	{
		RTN_Open(freeRtn);
		RTN_InsertCall(freeRtn, IPOINT_BEFORE, (AFUNPTR)RecordFree, IARG_FUNCARG_ENTRYPOINT_VALUE, 0, IARG_END);
		RTN_Close(freeRtn);
	}
}

int main(int argc, char **argv)
{
	PIN_Init(argc, argv);
	PIN_InitSymbols();
	IMG_AddInstrumentFunction(Image, NULL);
	cerr << endl;
	PIN_StartProgram();
	return 0;
}