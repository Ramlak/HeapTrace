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

#define BADADDR -1

#pragma pack(push, 1)

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
enum heap_op_type_t
{
	HO_IDLE		=	0x00000000, //	nothing (should not be sent normally)
	HO_MALLOC	=	0x00000001,	//	malloc
	HO_REALLOC	=	0x00000002, //	realloc
	HO_CALLOC	=	0x00000004,	//	calloc
	HO_FREE		=	0x00000008,	//	free
};

struct heap_op_packet_t			//	standard packet registering heap operations 
{
	heap_op_type_t code;
	ADDRINT return_value;
	ADDRINT return_ip;
	ADDRINT args[MAX_ARGS];
	malloc_chunk chunk;

	heap_op_packet_t()	:	code(HO_IDLE)	{}
};

//--------------------------------------------------------------------------
enum cmd_type_t
{
	CTT_ACK				=	0,	//	do nothing
	CTT_ERROR			=	1,	//	signal an error
	CTT_HELLO			=	2,	//	first packet
	CTT_READ_MEMORY		=	3,	//	read 'size' bytes of memory from 'data'
	CTT_WRITE_MEMORY	=	4,	//	write 'size' bytes to 'data'
	CTT_START_PROCESS	=	5,	//	start application
	CTT_EXIT_PROCESS	=	6,	//	exit process
	CTT_HEAP_INFO		=	7,	//	get heap info
	CTT_CHECK_HEAP_OP	=	8,	// 	check for heap operations
	CTT_GET_HEAP_OP		=	9,	//	get heap operations
	CTT_END				=	10,	//	marks end of enum
};

struct idacmd_packet_t
{
	cmd_type_t code;
	size_t size;
	ADDRINT data;
	idacmd_packet_t(): code(CTT_ACK), size(0), data(BADADDR){};
};

//--------------------------------------------------------------------------
#define MEM_CHUNK_SIZE 1024
struct idamem_response_pkt_t
{
  cmd_type_t code;
  size_t size;
  unsigned char buf[MEM_CHUNK_SIZE];
};

#endif