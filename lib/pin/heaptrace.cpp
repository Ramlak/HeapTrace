#include "pin.H"
#include <iostream>

VOID RecordMalloc(ADDRINT addr)
{
	if(addr == 0)
	{
		cerr << "Heap full!";
		return;
	}
	cerr << "Malloc recorded! " << hex << addr << endl;
}

VOID RecordFree(ADDRINT addr)
{
	cerr << "Freeing " << hex << addr << endl;
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
	PIN_StartProgram();
	return 0;
}