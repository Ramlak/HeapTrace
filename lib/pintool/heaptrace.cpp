/*
	PIN tool to trace heap behaviour.

*/

#include "heaptrace.h"

//--------------------------------------------------------------------------
// forward declarations
static bool handle_packet(idacmd_packet_t *res);
static ssize_t pin_recv(int fd, void *buf, size_t n, const char *from_where);
//static ssize_t pin_send(int fd, const void *buf, size_t n, const char *from_where);
static bool handle_packets(int total, const string &until_packet = "");
static void check_network_error(ssize_t ret, const char *from_where);

//--------------------------------------------------------------------------
// macros
#define MSG(fmt, ...)                                     \
  do                                                      \
  {                                                       \
    if ( debug_tracer > 0 )                               \
    {                                                     \
      char buf[1024];                                     \
      snprintf(buf, sizeof(buf), fmt, ##__VA_ARGS__); 	  \
      fprintf(stderr, "%s", buf);                         \
      LOG(buf);                                           \
    }                                                     \
  }                                                       \
  while ( 0 )

#define DEBUG(fmt, ...)                                   \
  do                                                      \
  {                                                       \
    if ( debug_tracer > 1 )                               \
      MSG(fmt, ##__VA_ARGS__);                            \
  }                                                       \
  while ( 0 )


//--------------------------------------------------------------------------
// Command line arguments

KNOB<int> IdaPort(KNOB_MODE_WRITEONCE, "pintool", "p", "12345", "Port where IDA Pro connects to PIN");

//--------------------------------------------------------------------------
// sockets and port number
static int srv_socket, portno, cli_socket;

//--------------------------------------------------------------------------
// semaphores
//static PIN_SEMAPHORE listener_sem;

//--------------------------------------------------------------------------
// constants for heap handling
//static size_t SIZE_SZ = sizeof(size_t);
//static size_t MALLOC_ALIGN_MASK = ~(2 * SIZE_SZ - 1);

//--------------------------------------------------------------------------
// global variables
heap_op_packet_t last_op;
static const char *last_packet = "NONE";
static int debug_tracer = 2;

size_t HEAP_BASE = 0;

//--------------------------------------------------------------------------
// error message
inline static void error_msg(const char *msg)
{
  MSG("%s: %s\n", msg, strerror(errno));
}

//--------------------------------------------------------------------------
// basic network functionality
static bool init_socket(void)
{
	portno	= IdaPort;
	srv_socket = socket(AF_INET, SOCK_STREAM, 0);
	if ( srv_socket == (int)-1 )
	{
		error_msg("socket");
		return false;
	}

	int optval = 1;
	setsockopt(srv_socket, SOL_SOCKET, SO_REUSEADDR, &optval, sizeof(optval));

	struct sockaddr_in sa;
	memset(&sa, '\0', sizeof(sa));
	sa.sin_family = AF_INET;
	sa.sin_port   = htons(portno);
	if ( bind(srv_socket, (sockaddr *)&sa, sizeof(sa)) != 0 )
	{
		error_msg("bind");
		return false;
	}

	if ( listen(srv_socket, 1) == 0 )
	{
	MSG("Listening at port %d...\n", (int)portno);

	socklen_t clilen = sizeof(sa);

	cli_socket = accept(srv_socket, ((struct sockaddr *)&sa), &clilen);
	if ( cli_socket > 0 )
	  return true;
	}
	return false;
}

/*static ssize_t pin_send(int fd, const void *buf, size_t n, const char *from_where)
{
  ssize_t ret = send(fd, buf, n, 0);
  check_network_error(ret, from_where);
  return ret;
}

static bool send_packet(
        const void *pkt,
        size_t size,
        void *answer,
        size_t ans_size,
        const char *from)
{
  ssize_t bytes = pin_send(cli_socket, pkt, size, from);
  if ( bytes > -1 )
  {
    if ( answer != NULL )
      bytes = pin_recv(cli_socket, answer, ans_size, from);
  }
  return bytes != -1;
} */

static ssize_t pin_recv(int fd, void *buf, size_t n, const char *from_where)
{
  char *bufp = (char*)buf;
  ssize_t total = 0;
  while ( n > 0 )
  {
    ssize_t ret = recv(fd, bufp, n, 0);
    check_network_error(ret, from_where);
    if ( ret != - 1 )
    {
      n -= ret;
      bufp += ret;
      total += ret;
    }
    else
    {
      break;
    }
  }
  return total;
}

static void check_network_error(ssize_t ret, const char *from_where)
{
  if ( ret == -1 )
  {
    int err = errno;
    bool timeout = err == EAGAIN;

    if ( !timeout )
    {
      MSG("A network error %d happened in %s, exiting from application...\n", err, from_where);
      PIN_ExitProcess(-1);
    }
    MSG("Timeout, called from %s\n", from_where);
  }
}

//--------------------------------------------------------------------------
// conversation with ida functions
static bool listen_to_ida(void)
{
  // initialize the socket and connect to ida
  if ( !init_socket() )
  {
    MSG("listen_to_ida: init_socket() failed!\n");
    return false;
  }

  MSG("CONNECTED TO IDA\n");

  // Handle the 1st packets. Then, we will handle the next (variable
  // number) of packets to add breakpoints in the application start
  // callback and, finally, handle all the rest of packets send to the
  // PIN tool in the handle_packet function
  bool ret = handle_packets(5);
  MSG("Exiting from listen_to_ida\n");

  return ret;
}

static bool handle_packet(idacmd_packet_t *res)
{
	return true;
}

static bool handle_packets(int total, const string &until_packet)
{
  int packets = 0;
  while ( (total != -1 && packets++ < total) || (!until_packet.empty() && last_packet != until_packet) )
  {
    DEBUG("Receiving packet %d, expected %d bytes...\n", packets, (uint32)sizeof(idacmd_packet_t));
    idacmd_packet_t res;
    ssize_t bytes = pin_recv(cli_socket, &res, sizeof(res), __FUNCTION__);
    if ( bytes != sizeof(res) )
    {
      error_msg("pin_recv");
      return false;
    }

    DEBUG("Handling packet ... \n");
    if ( !handle_packet(&res) )
    {
      MSG("Error handling %s packet, exiting...\n", last_packet);
      return false;
    }
  }

  if ( total == packets )
    DEBUG("Maximum number of packets reached, exiting from handle_packets...\n");
  else
    DEBUG("Expected packet '%s' received, exiting from handle_packets...\n", until_packet.c_str());

  return true;
}

//--------------------------------------------------------------------------
// instrumentation functions

bool InHeap(ADDRINT addr)
{
	ADDRINT compare = HEAP_BASE & (ADDRINT)0xfff00000;
	return (addr & (ADDRINT)0xfff00000) == compare;
}

//--------------------------------------------------------------------------
// realloc callbacks
VOID RecordReallocInvocation(ADDRINT ptr, size_t requested_size)
{
	last_op.id = HO_REALLOC;
	last_op.args[0] = ptr;
	last_op.args[1] = requested_size;
}

VOID RecordReallocReturned(ADDRINT * addr, ADDRINT return_ip)
{
	last_op.return_value=(ADDRINT)addr;
	last_op.return_ip = return_ip;
	PIN_SafeCopy(&last_op.chunk, addr-2, sizeof(malloc_chunk));
}

//--------------------------------------------------------------------------
// malloc callbacks
VOID RecordMallocInvocation(size_t requested_size)
{
	last_op.id = HO_MALLOC;
	last_op.args[0] = requested_size;
}

VOID RecordMallocReturned(ADDRINT * addr, ADDRINT return_ip)
{
	last_op.return_value=(ADDRINT)addr;
	last_op.return_ip = return_ip;
	PIN_SafeCopy(&last_op.chunk, addr-2, sizeof(malloc_chunk));
}

//--------------------------------------------------------------------------
// calloc callbacks
VOID RecordCallocInvocation(size_t num, size_t requested_size) // After certain size calloc is not caught 0_o
{
	last_op.id = HO_CALLOC;
	last_op.args[0] = num;
	last_op.args[1] = requested_size;
}

VOID RecordCallocReturned(ADDRINT * addr, ADDRINT return_ip)
{
	last_op.return_value=(ADDRINT)addr;
	last_op.return_ip = return_ip;
	PIN_SafeCopy(&last_op.chunk, addr-2, sizeof(malloc_chunk));
}

//--------------------------------------------------------------------------
// free callbacks
VOID RecordFreeInvocation(ADDRINT addr)
{
	last_op.id = HO_FREE;
	last_op.args[0] = addr;
}

VOID RecordFreeReturned(ADDRINT return_ip)
{
	last_op.return_value = 0;
	last_op.return_ip = return_ip;
}

//--------------------------------------------------------------------------
// image instrumentation
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
		RTN_InsertCall(rtn, IPOINT_AFTER, (AFUNPTR)RecordFreeReturned, IARG_RETURN_IP, IARG_END);
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

//--------------------------------------------------------------------------
// main
int main(int argc, char **argv)
{
	PIN_Init(argc, argv);
	PIN_InitSymbols();
	IMG_AddInstrumentFunction(Image, NULL);
	HEAP_BASE = (size_t)sbrk(0);
	if ( !listen_to_ida() )
	    PIN_ExitApplication(-1);
	return 0;
}