#ifndef __DEBUG_TOOLS_HH__
#define __DEBUG_TOOLS_HH__

#include <stdint.h>

extern uint64_t breakOnSequenceNumber;

void considerBreakingToDebugger( uint64_t seq ) ;

void __attribute__ ((noinline)) breakToDebugger(); 

#endif //__DEBUG_TOOLS_HH__


