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
static VOID Image(IMG img, VOID *v);

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
// thread related stuff
static PIN_SEMAPHORE listener_sem;
static PIN_THREAD_UID listener_uid;
static PIN_LOCK heap_op_lock;

//--------------------------------------------------------------------------
// constants for heap handling
//static size_t SIZE_SZ = sizeof(size_t);
//static size_t MALLOC_ALIGN_MASK = ~(2 * SIZE_SZ - 1);

//--------------------------------------------------------------------------
// global variables
heap_op_packet_t heap_operation;
static const char *last_packet = "NONE";
static int debug_tracer = 2;
// do we want to continue running listener?
static bool run_listener = false;
// is process exiting?
static bool process_exit = false;
size_t HEAP_BASE = 0;

// list of all the heap operation that will be passed to IDA
typedef std::deque<heap_op_packet_t> heap_op_list_t;
static heap_op_list_t heap_ops;

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

static ssize_t pin_send(int fd, const void *buf, size_t n, const char *from_where)
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
} 

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
static VOID ida_listener(VOID *)
{
  MSG("Listener started...\n");
  run_listener = true;

  while ( run_listener )
  {
    DEBUG("Handling events in ida_listener\n");
    idacmd_packet_t res;
    ssize_t bytes = pin_recv(cli_socket, &res, sizeof(res), "ida_pin_listener");
    if ( bytes == -1 )
    {
      error_msg("recv");
      continue;
    }

    if ( !handle_packet(&res) )
    {
      MSG("Error handling %s packet, exiting...\n", last_packet);
      PIN_ExitThread(0);
    }

    if ( PIN_IsProcessExiting() && heap_ops.empty() && process_exit )
    {
      MSG("Process is exiting...\n");
      break;
    }
  }
}

static VOID fini_cb(INT32, VOID *)
{
  DEBUG("Marking the trace as full\n");

  MSG("Waiting for listener thread to exit...\n");
  if ( PIN_WaitForThreadTermination(listener_uid, 10000, NULL) )
  {
    MSG("Everything OK\n");
  }
  else
  {
    MSG("Timeout waiting for listener thread.\n");
  }
}

//--------------------------------------------------------------------------
// ida_listener callbacks
static void start_process(void)
{
	IMG_AddInstrumentFunction(Image, NULL);
    
    // initialize listener_semaphore
    PIN_SemaphoreInit(&listener_sem);
  	PIN_SemaphoreClear(&listener_sem);

  	PIN_InitLock(&heap_op_lock);

	// Register fini_cb to be called when the application exits
  	PIN_AddFiniUnlockedFunction(fini_cb, 0);

  	// Create thread for communication with IDA
	THREADID thread_id = PIN_SpawnInternalThread(ida_listener, NULL, 0, &listener_uid);
  	if ( thread_id == INVALID_THREADID )
	{
	    MSG("PIN_SpawnInternalThread(BufferProcessingThread) failed\n");
	    exit(-1);
	}

	// Start the program, never returns
  	PIN_StartProgram();
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
  bool ret = handle_packets(3);
  MSG("Exiting from listen_to_ida\n");

  return ret;
}

static const char *const packet_names[] =
{
  "ACK",           "ERROR",       "HELLO",       "READ MEMORY",
  "WRITE MEMORY",	"START PROCESS",	"EXIT PROCESS", "HEAP INFO", 
};

static bool handle_packet(idacmd_packet_t *res)
{
	bool ret = false;
	idacmd_packet_t ans;
	ans.size = 0;
	ans.code = CTT_ERROR;

	if ( res->code > CTT_END )
	{
		MSG("Unknown packet type %d, exiting...\n", res->code);
		PIN_ExitProcess(0);
	}
	last_packet = packet_names[res->code];
	switch ( res->code )
	{
		case CTT_HELLO:
			ans.code = CTT_ACK;
			ans.data = sizeof(ADDRINT);
			ret = send_packet(&ans, sizeof(idacmd_packet_t), NULL, 0, __FUNCTION__);
		case CTT_START_PROCESS:
			// does not return
			start_process();
			break;
		default:
	    	MSG("UNKNOWN PACKET RECEIVED WITH CODE %d\n", res->code);
	      	last_packet = "UNKNOWN " + res->code;
	      	PIN_ExitProcess(0);
	      	break;
	}
  	DEBUG("LAST PACKET WAS %s\n", last_packet);
  	return ret;
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
/*static bool InHeap(ADDRINT addr)
{
	ADDRINT compare = HEAP_BASE & (ADDRINT)0xfff00000;
	return (addr & (ADDRINT)0xfff00000) == compare;
}*/

static VOID add_last_heap_op()
{
	PIN_GetLock(&heap_op_lock, PIN_GetTid());
	heap_ops.push_back(heap_operation);
	PIN_ReleaseLock(&heap_op_lock);
}

//--------------------------------------------------------------------------
// realloc callbacks
static VOID RecordReallocInvocation(ADDRINT ptr, size_t requested_size)
{
	heap_operation.code = HO_REALLOC;
	heap_operation.args[0] = ptr;
	heap_operation.args[1] = requested_size;
}

static VOID RecordReallocReturned(ADDRINT * addr, ADDRINT return_ip)
{
	heap_operation.return_value=(ADDRINT)addr;
	heap_operation.return_ip = return_ip;
	PIN_SafeCopy(&heap_operation.chunk, addr-2, sizeof(malloc_chunk));
	add_last_heap_op();
}

//--------------------------------------------------------------------------
// malloc callbacks
static VOID RecordMallocInvocation(size_t requested_size)
{
	heap_operation.code = HO_MALLOC;
	heap_operation.args[0] = requested_size;
}

static VOID RecordMallocReturned(ADDRINT * addr, ADDRINT return_ip)
{
	heap_operation.return_value=(ADDRINT)addr;
	heap_operation.return_ip = return_ip;
	PIN_SafeCopy(&heap_operation.chunk, addr-2, sizeof(malloc_chunk));
	add_last_heap_op();
}

//--------------------------------------------------------------------------
// calloc callbacks
static VOID RecordCallocInvocation(size_t num, size_t requested_size) // After certain size calloc is not caught 0_o
{
	heap_operation.code = HO_CALLOC;
	heap_operation.args[0] = num;
	heap_operation.args[1] = requested_size;
}

static VOID RecordCallocReturned(ADDRINT * addr, ADDRINT return_ip)
{
	heap_operation.return_value=(ADDRINT)addr;
	heap_operation.return_ip = return_ip;
	PIN_SafeCopy(&heap_operation.chunk, addr-2, sizeof(malloc_chunk));
	add_last_heap_op();
}

//--------------------------------------------------------------------------
// free callbacks
static VOID RecordFreeInvocation(ADDRINT addr)
{
	heap_operation.code = HO_FREE;
	heap_operation.args[0] = addr;
}

static VOID RecordFreeReturned(ADDRINT return_ip)
{
	heap_operation.return_value = 0;
	heap_operation.return_ip = return_ip;
	add_last_heap_op();
}

//--------------------------------------------------------------------------
// image instrumentation
static VOID Image(IMG img, VOID *v)
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
	HEAP_BASE = (size_t)sbrk(0);
	if ( !listen_to_ida() )
	    PIN_ExitApplication(-1);
	return 0;
}