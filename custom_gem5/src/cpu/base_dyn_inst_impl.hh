/*
 * Copyright (c) 2011 ARM Limited
 * All rights reserved.
 *
 * The license below extends only to copyright in the software and shall
 * not be construed as granting a license to any other intellectual
 * property including but not limited to intellectual property relating
 * to a hardware implementation of the functionality of the software
 * licensed hereunder.  You may use the software subject to the license
 * terms below provided that you ensure that this notice is replicated
 * unmodified and in its entirety in all distributions of the software,
 * modified or unmodified, in source code or in binary form.
 *
 * Copyright (c) 2004-2006 The Regents of The University of Michigan
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met: redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer;
 * redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution;
 * neither the name of the copyright holders nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 * Authors: Kevin Lim
 */

#ifndef __CPU_BASE_DYN_INST_IMPL_HH__
#define __CPU_BASE_DYN_INST_IMPL_HH__

#include <iostream>
#include <set>
#include <sstream>
#include <string>

#include "base/cprintf.hh"
#include "base/trace.hh"
#include "config/the_isa.hh"
#include "cpu/base_dyn_inst.hh"
#include "cpu/exetrace.hh"
#include "debug/DynInst.hh"
#include "debug/SS_PrintSrcRegs.hh"
#include "debug/IQ.hh"
#include "mem/request.hh"
#include "sim/faults.hh"
#include "arch/x86/insts/static_inst.hh"

template <class Impl>
BaseDynInst<Impl>::BaseDynInst(const StaticInstPtr &_staticInst,
                               const StaticInstPtr &_macroop,
                               TheISA::PCState _pc, TheISA::PCState _predPC,
                               InstSeqNum seq_num, ImplCPU *cpu)
  : staticInst(_staticInst), cpu(cpu), traceData(NULL), macroop(_macroop)
{
    seqNum = seq_num;

    pc = _pc;
    predPC = _predPC;

    initVars();
}

template <class Impl>
BaseDynInst<Impl>::BaseDynInst(const StaticInstPtr &_staticInst,
                               const StaticInstPtr &_macroop)
    : staticInst(_staticInst), traceData(NULL), macroop(_macroop)
{
    seqNum = 0;
    initVars();
}

// iangneal: this assertion breaks certain spec benchmarks
//#ifndef NDEBUG
//#define NDEBUG
//#endif

template <class Impl>
void
BaseDynInst<Impl>::initVars()
{
    memData = NULL;
    effAddr = 0;
    physEffAddrLow = 0;
    physEffAddrHigh = 0;
    readyRegs = 0;
    memReqFlags = 0;
    addedToLSQTimestamp = (Tick)(-1);
    addedToROBTimestamp = (Tick)(-1);
    latencyToIssue      = (Tick)(-1);

    status.reset();

    instFlags.reset();
    instFlags[RecordResult] = true;
    instFlags[Predicate] = true;

    lqIdx = -1;
    sqIdx = -1;

    // Eventually make this a parameter.
    threadNumber = 0;

    // Also make this a parameter, or perhaps get it from xc or cpu.
    asid = 0;

    // Initialize the fault to be NoFault.
    fault = NoFault;

#ifndef NDEBUG
    ++cpu->instcount;

    if (cpu->instcount > 4000) {
#ifdef DEBUG
        cpu->dumpInsts();
        dumpSNList();
#endif
        assert(cpu->instcount <= 4000);
    }

    DPRINTF(DynInst,
        "DynInst: [sn:%lli] Instruction created. Instcount for %s = %i\n",
        seqNum, cpu->name(), cpu->instcount);
#endif

#ifdef DEBUG
    cpu->snList.insert(seqNum);
#endif

}

template <class Impl>
BaseDynInst<Impl>::~BaseDynInst()
{
    if (memData) {
        delete [] memData;
    }

    if (traceData) {
        delete traceData;
    }

    fault = NoFault;

#ifndef NDEBUG
    --cpu->instcount;

    DPRINTF(DynInst,
        "DynInst: [sn:%lli] Instruction destroyed. Instcount for %s = %i\n",
        seqNum, cpu->name(), cpu->instcount);
#endif
#ifdef DEBUG
    cpu->snList.erase(seqNum);
#endif

}

#ifdef DEBUG
template <class Impl>
void
BaseDynInst<Impl>::dumpSNList()
{
    std::set<InstSeqNum>::iterator sn_it = cpu->snList.begin();

    int count = 0;
    while (sn_it != cpu->snList.end()) {
        cprintf("%i: [sn:%lli] not destroyed\n", count, (*sn_it));
        count++;
        sn_it++;
    }
}
#endif

template <class Impl>
void
BaseDynInst<Impl>::dump()
{
    cprintf("T%d : %#08d `", threadNumber, pc.instAddr());
    std::cout << staticInst->disassemble(pc.instAddr());
    cprintf("'\n");
}

template <class Impl>
void
BaseDynInst<Impl>::dump(std::string &outstring)
{
    std::ostringstream s;
    s << "T" << threadNumber << " : 0x" << pc.instAddr() << " "
      << staticInst->disassemble(pc.instAddr());

    outstring = s.str();
}

template <class Impl>
void
BaseDynInst<Impl>::markSrcRegReady()
{
    if (++readyRegs == numSrcRegs()) {
        setCanIssue();
    }

    if( readyRegs > numSrcRegs() )
        panic( "More registers are ready than needed: "
                "readyRegs = %d; numSrcRegs = %d\n",
                readyRegs, numSrcRegs() );

    DPRINTF(IQ, "[sn:%lli] Source registers ready: (%d/%d), RTI %d;\n",
                seqNum, readyRegs, numSrcRegs(),
                numSrcRegs(), readyToIssue() );
}

template <class Impl>
void
BaseDynInst<Impl>::markSrcRegReady(RegIndex src_idx)
{
    _readySrcRegIdx[src_idx] = true;

    markSrcRegReady();
}

template <class Impl>
void
BaseDynInst<Impl>::markDestRegsAsSecureSpec()
{
    unsigned num_dest_regs = numDestRegs();

    for (int dest_idx = 0; dest_idx < num_dest_regs; dest_idx++) {
        // We are tainting the register, which doesn't really change its
        // contents. Therefore, the const cast is safe.
        PhysRegId* dest_reg = const_cast<PhysRegId*>(renamedDestRegIdx(dest_idx));

        std::stringstream regName;
        X86ISA::X86StaticInst* x86StaticInst = 
            dynamic_cast<X86ISA::X86StaticInst*>(staticInst.get());
        if( x86StaticInst )
            x86StaticInst->printDestReg( regName, dest_idx, 8 );
        
        DPRINTF( SS_TaintRegs, "[sn:%i] Instruction at 0x%lx tainting dest reg "
                "%s/%d (flatIndex=%d)\n",
                seqNum, instAddr(), regName.str(), dest_idx, dest_reg->flatIndex());
        
        dest_reg->setSecureSpecPhysReg();
    }
}

template <class Impl>
bool
BaseDynInst<Impl>::isSrcRegsSecureSpec()
{
    int8_t total_src_regs = numSrcRegs();

    for (int src_reg_idx = 0;
         src_reg_idx < total_src_regs;
         src_reg_idx++)
    {
        PhysRegIdPtr src_reg = renamedSrcRegIdx(src_reg_idx);

        if( src_reg->isSecureSpecPhysReg() ) {
            std::stringstream regName;
            X86ISA::X86StaticInst* x86StaticInst = 
                dynamic_cast<X86ISA::X86StaticInst*>(staticInst.get());
            uint32_t ignoreTaintMask = 0;
            if( x86StaticInst ) {
                x86StaticInst->printSrcReg( regName, src_reg_idx, 8 );
                ignoreTaintMask = x86StaticInst->ignoreTaintFromRegIds;
            }

            // Src regs to ignore:
            // 1. If mov operation is about to overwrite the register
            // 2. If src ref is a CC regs (e.g., EFLAGS)
            // 3. Src reg is RBP, potentially tainted by the secure stack
            bool ignoreTaint = 
                   ( ignoreTaintMask & (1 << src_reg_idx) ) 
                || src_reg->isCCPhysReg()                                        
                || staticInst->srcRegIdx(src_reg_idx).index() == X86ISA::INTREG_RBP
                ;  

            DPRINTF( SS_TaintRegs, 
                    "[sn:%i] @ 0x%lx  src reg %s/%d (index=%d flatIndex=%d) is tainted. "
                    "ignoreTaintMask = 0x%X %s%s\n",
                    seqNum, instAddr(),  regName.str(), src_reg_idx, 
                    staticInst->srcRegIdx(src_reg_idx).index(),
                    src_reg->flatIndex(),
                    ignoreTaintMask,
                    staticInst->isControl() ? "TAINTED BRANCH " :  "", 
                    ignoreTaint ? "IGNORING TAINT!" : "" );

            if( ! ignoreTaint )
                return true;
        } 
        else if( DTRACE( SS_PrintSrcRegs ) ) {
            std::stringstream regName;
            X86ISA::X86StaticInst* x86StaticInst = 
                dynamic_cast<X86ISA::X86StaticInst*>(staticInst.get());
            if( x86StaticInst )
                x86StaticInst->printSrcReg( regName, src_reg_idx, 8 );

            DPRINTF( SS_PrintSrcRegs, "[sn:%i] src reg %s/%d (flatIndex=%d) NOT tainted.\n",
                    seqNum, regName.str(), src_reg_idx, src_reg->flatIndex() );
        }
    }

    return false;
}

template <class Impl>
bool
BaseDynInst<Impl>::eaSrcsReady()
{
    // For now I am assuming that src registers 1..n-1 are the ones that the
    // EA calc depends on.  (i.e. src reg 0 is the source of the data to be
    // stored)

    for (int i = 1; i < numSrcRegs(); ++i) {
        if (!_readySrcRegIdx[i])
            return false;
    }

    return true;
}

#endif//__CPU_BASE_DYN_INST_IMPL_HH__
