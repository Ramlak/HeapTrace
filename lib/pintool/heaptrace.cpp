/*
	PIN tool to trace heap behaviour.

*/

#include "heaptrace.h"

//--------------------------------------------------------------------------
// forward declarations
static bool handle_packet(idacmd_packet_t *res);
static ssize_t pin_recv(int fd, void *buf, size_t n, const char *from_where);
static bool handle_packets(int total, const string &until_packet = "");
static VOID add_last_heap_op();
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
static int debug_tracer = 1;
// do we want to continue running listener?
static bool run_listener = false;
// is process exiting?
static bool process_exit = false;
// is process started?
static bool process_started = false;
// number of recent heap operations
static int recent_heap_ops = 0;
// first instruction visited?
static int first_visited = false;
// range of main executable
ADDRINT min_address, max_address;
// last_instruction
static ADDRINT last_instruction;

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
  	MSG("Network error!\n");
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

static const char *const forbidden_section_names[] =
{
	".got.plt", ".plt", ".got",
};

/*bool is_allowed(const char * sec_name)
{
	DEBUG("%d\n", strcmp(forbidden_section_names[1])==0);
	for(unsigned int i = 0; i < sizeof(forbidden_section_names); i++)
	{
		if(!strcmp(forbidden_section_names[i], sec_name))
			return false;
	}
	return true;
}*/

static VOID app_start_cb(VOID *)
{
  DEBUG("Setting process started to true\n");
  process_started = true;

  IMG img;
  img.invalidate();
  for( img = APP_ImgHead(); IMG_Valid(img); img = IMG_Next(img) )
  {
    if ( IMG_IsMainExecutable(img) )
      break;
  }

  if ( !img.is_valid() )
  {
    MSG("Cannot find the 1st instruction of the main executable!\n");
    abort();
  }
  SEC sec;
  for(sec = IMG_SecHead(img); SEC_Valid(sec); sec = SEC_Next(sec))
  {
  	if(!strcmp(SEC_Name(sec).c_str(), ".text"))
  	{	
  		break;
  	}
  }
  // for now let's just trace .text section. Maybe in future i will add more.
  // We need this because otherwise all calls to malloc would point to .got or .plt
  min_address = SEC_Address(sec);
  max_address = min_address + SEC_Size(sec);
  DEBUG("Address space: %p-%p\n", (void*)min_address, (void*)max_address);
}

//--------------------------------------------------------------------------
static ADDRINT listener_not_running(VOID *)
{
  return !run_listener;
}

static void wait_for_listener(void)
{
  PIN_SemaphoreWait(&listener_sem);
}

bool check_address(ADDRINT addr)
{
  if ( addr >= min_address && addr <= max_address )
 	return true;
  return false;
}

//--------------------------------------------------------------------------
// This function is called before every instruction is executed
static VOID PIN_FAST_ANALYSIS_CALL ins_logic_cb(VOID *ip)
{
  //DEBUG("ADDR: %p\n", ip); // that is heavy output
  if(!first_visited)
  {
  	recent_heap_ops = 0;
  	first_visited = true;
  }
  if(recent_heap_ops == 1)
  {
  	if(heap_operation.code == HO_FREE)
  		PIN_SafeCopy(&heap_operation.chunk, (ADDRINT*)(heap_operation.args[0])-2, sizeof(malloc_chunk));
  	add_last_heap_op();
  } else if(recent_heap_ops > 1)
  {
  	MSG("Too many recent heap operations (%d)...Exiting\n", recent_heap_ops);
  	PIN_ExitProcess(0);
  }
  last_instruction = (ADDRINT)ip;
}

static VOID instruction_cb(INS ins, VOID *)
{

  // Insert a call to ins_logic_cb before every instruction
  ADDRINT addr = INS_Address(ins);
  if ( check_address(addr) )
  {
    if ( !run_listener )
    {
      // add the code for synching with the listener thread
      INS_InsertIfCall(ins, IPOINT_BEFORE, (AFUNPTR)listener_not_running, IARG_END);
      INS_InsertThenCall(ins, IPOINT_BEFORE, (AFUNPTR)wait_for_listener, IARG_END);
    }
    INS_InsertCall(ins, IPOINT_BEFORE, (AFUNPTR)ins_logic_cb, IARG_FAST_ANALYSIS_CALL, IARG_INST_PTR, IARG_END);
  }
}

//--------------------------------------------------------------------------
// ida_listener callbacks
static void start_process(void)
{
	IMG_AddInstrumentFunction(Image, NULL);
	INS_AddInstrumentFunction(instruction_cb, 0);
	// initialize listener_semaphore
	PIN_SemaphoreInit(&listener_sem);
	PIN_SemaphoreClear(&listener_sem);

	PIN_InitLock(&heap_op_lock);

	// Register fini_cb to be called when the application exits
	PIN_AddFiniUnlockedFunction(fini_cb, 0);

	// Register aplication start callback
	PIN_AddApplicationStartFunction(app_start_cb, 0);

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

static bool read_memory(ADDRINT addr, size_t size)
{
	DEBUG("Reading %lu bytes at address %p\n", (long unsigned int)size, (void*)addr);

	idamem_response_pkt_t pkt;
	// read the data asked by IDA
	size_t copy_size = size < sizeof(pkt.buf) ? size : sizeof(pkt.buf);
	ssize_t read_bytes = PIN_SafeCopy(pkt.buf, (void*)addr, copy_size);
	pkt.size = (uint32)read_bytes;
	pkt.code = CTT_READ_MEMORY;

	ssize_t bytes = pin_send(cli_socket, &pkt, sizeof(pkt), __FUNCTION__);
	return bytes == sizeof(pkt);
}

inline static void pop_heap_op(heap_op_packet_t *pkt)
{
	assert(!heap_ops.empty());
	{
		PIN_GetLock(&heap_op_lock, PIN_GetTid());
		*pkt = heap_ops.front();
		heap_ops.pop_front();
		PIN_ReleaseLock(&heap_op_lock);
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
  bool ret = handle_packets(3);
  MSG("Exiting from listen_to_ida\n");
  exit(1);
  return ret;
}

static const char *const packet_names[] =
{
  "ACK",           "ERROR",       "HELLO",       "READ MEMORY",
  "WRITE MEMORY",	"START PROCESS",	"EXIT PROCESS", "HEAP INFO", 
  "CHECK HEAP OPERATIONS", "GET HEAP OPERATION",
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
		case CTT_READ_MEMORY:
			ans.size = 0;
			ans.code = CTT_READ_MEMORY;
			read_memory(res->data, res->size);
			break;
		case CTT_WRITE_MEMORY:
			break;
		case CTT_ACK:
			break;	
		case CTT_EXIT_PROCESS:
			MSG("Received EXIT PROCESS, exiting from process...\n");
			run_listener = false;
			// does not return
			PIN_ExitProcess(0);
		case CTT_CHECK_HEAP_OP:
			ans.data = 0;
			if(!heap_ops.empty() && process_started)
			{
				DEBUG("Total of %d heap operations recorded\n", (uint32)heap_ops.size());
				ans.size = (uint32)heap_ops.size();
				ans.code = CTT_CHECK_HEAP_OP;
			}
			else
			{
				ans.size = 0;
				ans.code = CTT_ACK;
			}
			ret = send_packet(&ans, sizeof(idacmd_packet_t), NULL, 0, __FUNCTION__);
			break;	
		case CTT_GET_HEAP_OP:
			{
				heap_op_packet_t pkt;

				if(!heap_ops.empty())
					pop_heap_op(&pkt);
				else
					pkt.code = HO_IDLE;

				ret = send_packet(&pkt, sizeof(pkt), NULL, 0, __FUNCTION__);
				break;
			}
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

static const char *const operation_names[] =
{
  "IDLE", "MALLOC", "REALLOC", "CALLOC", "FREE",
};


static VOID add_last_heap_op()
{
	PIN_GetLock(&heap_op_lock, PIN_GetTid());
	heap_ops.push_back(heap_operation);
	DEBUG("Last operation on heap is %s\n", operation_names[heap_operation.code]);
	PIN_ReleaseLock(&heap_op_lock);
	recent_heap_ops = 0;
}

//--------------------------------------------------------------------------
// realloc callbacks
static VOID RecordReallocInvocation(ADDRINT ptr, size_t requested_size)
{
	DEBUG("Realloc invoked at %p\n", (void*)last_instruction);
	heap_operation.code = HO_REALLOC;
	heap_operation.args[0] = ptr;
	heap_operation.args[1] = requested_size;
	heap_operation.call_addr = last_instruction;
}

static VOID RecordReallocReturned(ADDRINT * addr)
{
	heap_operation.return_value=(ADDRINT)addr;
	recent_heap_ops += 1;
}

//--------------------------------------------------------------------------
// malloc callbacks
static VOID RecordMallocInvocation(size_t requested_size)
{
	DEBUG("Malloc(%d) invoked at %p\n", (int)requested_size, (void*)last_instruction);
	heap_operation.call_addr = last_instruction;
	heap_operation.code = HO_MALLOC;
	heap_operation.args[0] = requested_size;
}

static VOID RecordMallocReturned(ADDRINT * addr)
{
	heap_operation.return_value=(ADDRINT)addr;
	recent_heap_ops += 1;
}

//--------------------------------------------------------------------------
// calloc callbacks
static VOID RecordCallocInvocation(size_t num, size_t requested_size) // After certain size calloc is not caught 0_o
{
	DEBUG("Calloc invoked at %p\n", (void*)last_instruction);
	heap_operation.code = HO_CALLOC;
	heap_operation.args[0] = num;
	heap_operation.call_addr = last_instruction;
	heap_operation.args[1] = requested_size;
}

static VOID RecordCallocReturned(ADDRINT * addr)
{
	heap_operation.return_value=(ADDRINT)addr;
	recent_heap_ops += 1;
}

//--------------------------------------------------------------------------
// free callbacks
static VOID RecordFreeInvocation(ADDRINT addr) // Free return isn't hooked for some reason (this is serious!)
{
	DEBUG("Free invoked at %p\n", (void*)last_instruction);
	heap_operation.code = HO_FREE;
	heap_operation.call_addr = last_instruction;
	heap_operation.args[0] = addr;
	heap_operation.return_value = 0;
	recent_heap_ops += 1;
}

//--------------------------------------------------------------------------
// image instrumentation
static VOID Image(IMG img, VOID *v)
{
	if(!strstr(IMG_Name(img).c_str(), "libc"))
		return;

	RTN rtn = RTN_FindByName(img, "malloc");
	if(rtn.is_valid())
	{
		DEBUG("Found malloc in %s\n", IMG_Name(img).c_str());
		RTN_Open(rtn);
		RTN_InsertCall(rtn, IPOINT_BEFORE, (AFUNPTR)RecordMallocInvocation, IARG_FUNCARG_ENTRYPOINT_VALUE, 0, IARG_END);
		RTN_InsertCall(rtn, IPOINT_AFTER, (AFUNPTR)RecordMallocReturned, IARG_FUNCRET_EXITPOINT_VALUE, IARG_RETURN_IP, IARG_END);
		RTN_Close(rtn);
	}

	rtn = RTN_FindByName(img, "free");
	if(rtn.is_valid())
	{

		DEBUG("Found free in %s\n", IMG_Name(img).c_str());
		RTN_Open(rtn);
		RTN_InsertCall(rtn, IPOINT_BEFORE, (AFUNPTR)RecordFreeInvocation, IARG_FUNCARG_ENTRYPOINT_VALUE, 0, IARG_END);
		RTN_Close(rtn);
	}
	
	rtn = RTN_FindByName(img, "realloc");
	if(rtn.is_valid())
	{
		DEBUG("Found realloc in %s\n", IMG_Name(img).c_str());
		RTN_Open(rtn);
		RTN_InsertCall(rtn, IPOINT_BEFORE, (AFUNPTR)RecordReallocInvocation, IARG_FUNCARG_ENTRYPOINT_VALUE, 0, IARG_FUNCARG_ENTRYPOINT_VALUE, 1, IARG_END);
		RTN_InsertCall(rtn, IPOINT_AFTER, (AFUNPTR)RecordReallocReturned, IARG_FUNCRET_EXITPOINT_VALUE, IARG_RETURN_IP, IARG_END);
		RTN_Close(rtn);
	}

	rtn = RTN_FindByName(img, "calloc");
	if(rtn.is_valid())
	{
		DEBUG("Found calloc in %s\n", IMG_Name(img).c_str());
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