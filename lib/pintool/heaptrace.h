#ifndef _HEAPTRACE_H
#define _HEAPTRACE_H

#include <iostream>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <deque>
#include <map>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <errno.h>
#include <assert.h>

#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>
#include "pin.H" 

#define MAX_ARGS 3

using namespace std;

typedef unsigned int uint32;
typedef unsigned char uchar;

//--------------------------------------------------------------------------
struct malloc_chunk
{
	ADDRINT prev_size;
	ADDRINT size;
	malloc_chunk* fd;
	malloc_chunk* bk;
	malloc_chunk* fd_nextsize;
	malloc_chunk* bk_nextsize;
};

//--------------------------------------------------------------------------
enum heap_op_id_t
{
	HO_IDLE		=	0x00000000, //	nothing (should not be sent normally)
	HO_MALLOC	=	0x00000001,	//	malloc
	HO_REALLOC	=	0x00000002, //	realloc
	HO_CALLOC	=	0x00000004,	//	calloc
	HO_FREE		=	0x00000008,	//	free
};

struct heap_op_packet_t			//	standard packet registering heap operations 
{
	heap_op_id_t id;
	ADDRINT return_value;
	ADDRINT return_ip;
	ADDRINT args[MAX_ARGS];
	malloc_chunk chunk;

	heap_op_packet_t()	:	id(HO_IDLE)	{}
};

//--------------------------------------------------------------------------

struct idacmd_packet_t
{

};

#endif