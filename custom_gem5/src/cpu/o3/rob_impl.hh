/*
 * Copyright (c) 2012 ARM Limited
 * All rights reserved
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
 *          Korey Sewell
 */

#ifndef __CPU_O3_ROB_IMPL_HH__
#define __CPU_O3_ROB_IMPL_HH__

#include <list>
#include <iomanip>

#include "cpu/o3/rob.hh"
#include "debug/Fetch.hh"
#include "debug/ROB.hh"
#include "debug/DumpROB.hh"
#include "debug/DumpROB_show_addr.hh"
#include "debug/DumpROB_showSrcRegs.hh"
#include "debug/DumpROB_showEffectiveAddr.hh"
#include "debug/CD_Allow_NonLoads_AfterBranch.hh"
#include "debug/CD_MarkUnsafeIf_LoadtInstruction.hh"
#include "debug/CD_Runahead_ifMoreThanNBranches.hh"
#include "debug/CD_Runahead_ifBranchLoadIsStalling.hh"
#include "debug/CD_LimitWakeDependandsToWBWidth.hh"
#include "params/DerivO3CPU.hh"

using namespace std;

template <class Impl>
ROB<Impl>::ROB(O3CPU *_cpu, DerivO3CPUParams *params)
    : cpu(_cpu),
      numEntries(params->numROBEntries),
      squashWidth(params->squashWidth),
      numInstsInROB(0),
      numThreads(params->numThreads)
{
    for (ThreadID tid = 0; tid < numThreads; tid++) {
        numInstThatMayCauseSquash[tid] = 0;
        inRunaheadMode[tid] = false;
    }

    std::string policy = params->smtROBPolicy;

    //Convert string to lowercase
    std::transform(policy.begin(), policy.end(), policy.begin(),
                   (int(*)(int)) tolower);

    //Figure out rob policy
    if (policy == "dynamic") {
        robPolicy = Dynamic;

        //Set Max Entries to Total ROB Capacity
        for (ThreadID tid = 0; tid < numThreads; tid++) {
            maxEntries[tid] = numEntries;
        }

    } else if (policy == "partitioned") {
        robPolicy = Partitioned;
        DPRINTF(Fetch, "ROB sharing policy set to Partitioned\n");

        //@todo:make work if part_amt doesnt divide evenly.
        int part_amt = numEntries / numThreads;

        //Divide ROB up evenly
        for (ThreadID tid = 0; tid < numThreads; tid++) {
            maxEntries[tid] = part_amt;
        }

    } else if (policy == "threshold") {
        robPolicy = Threshold;
        DPRINTF(Fetch, "ROB sharing policy set to Threshold\n");

        int threshold =  params->smtROBThreshold;;

        //Divide up by threshold amount
        for (ThreadID tid = 0; tid < numThreads; tid++) {
            maxEntries[tid] = threshold;
        }
    } else {
        assert(0 && "Invalid ROB Sharing Policy.Options Are:{Dynamic,"
                    "Partitioned, Threshold}");
    }

    runaheadROBThreshold = params->runaheadROBThreshold;
    runaheadLoadAgeThreshhold = params->runaheadLoadAgeThreshhold;

    resetState();
}

template <class Impl>
void
ROB<Impl>::resetState()
{
    for (ThreadID tid = 0; tid  < numThreads; tid++) {
        doneSquashing[tid] = true;
        threadEntries[tid] = 0;
        squashIt[tid] = instList[tid].end();
        squashedSeqNum[tid] = 0;
        numInstThatMayCauseSquash[tid] = 0;
    }
    numInstsInROB = 0;

    // Initialize the "universal" ROB head & tail point to invalid
    // pointers
    head = instList[0].end();
    tail = instList[0].end();
}

template <class Impl>
std::string
ROB<Impl>::name() const
{
    return cpu->name() + ".rob";
}

template <class Impl>
void
ROB<Impl>::setActiveThreads(list<ThreadID> *at_ptr)
{
    DPRINTF(ROB, "Setting active threads list pointer.\n");
    activeThreads = at_ptr;
}

template <class Impl>
void
ROB<Impl>::drainSanityCheck() const
{
    for (ThreadID tid = 0; tid  < numThreads; tid++)
        assert(instList[tid].empty());
    assert(isEmpty());
}

template <class Impl>
std::string 
ROB<Impl>::InstToPCStr(DynInstPtr& inst)
{
    std::ostringstream os;
    os << "0x" 
       << std::hex  /* <<  std::setfill('0')  << std::setw(12) */
       << inst->instAddr();
    return os.str();
}

template <class Impl>
void
ROB<Impl>::PrintROBContents( uint32_t tid, IQ& instQueue )
{
    int slotIdx = 0;
    DPRINTF( DumpROB, "=============== Dumping ROB contents ===== Runahead %s ========== \n",
                        inRunaheadMode[tid] ? "ON" : "OFF" );
    DPRINTF( DumpROB, "numInstThatMayCauseSquash[%d] == %d "
                      "(note that decrements from the IEW will apear only in the next cycle)\n", 
                        tid, numInstThatMayCauseSquash[tid] );


    for(InstIt it = instList[tid].begin(); it != instList[tid].end(); ++it) {
        DPRINTF( DumpROB, "%3d:%s [sn:%lli] %s/%s/%s/%s/%s%7s" 
                            "%12s%i %s/%s/%s/%s %3d %s%-35s %s%s\r\n",
                slotIdx++,
                DTRACE( DumpROB_show_addr ) ? InstToPCStr(*it) : "",
                (*it)->seqNum,
                /* (*it)->staticInst->getName(), */
                /* (*it)->threadNumber, */
                (*it)->readyToIssue() ? "RDY" : "---",
                (*it)->isIssued() ? "ISS" : "---",
                (*it)->isExecuting() ? "XING" : "----",
                (*it)->isExecuted() ? "XED" : "---",
                (*it)->readyToCommit() ? "CMT" : "---",
                (*it)->isSquashed() ? "SQSHED" : "------",
                (*it)->canCauseMisprediction() ? "CanMisPred/" : "-------/",
                (*it)->maySquashOthers(),
                (*it)->isUnsafe()                              ? "U" : "-",
                (*it)->isRunahead()                            ? "R" : "-",
                (*it)->isBranchPrequisite() && (*it)->isLoad() ? "B" : "-",
                (*it)->isSecureSpec()                          ? "S" : "-",
                (*it)->ageInLSQ(),
                DTRACE( DumpROB_showEffectiveAddr ) && (*it)->isMemRef() ?
                    ( (*it)->readyToIssue() ? 
                                      (*it)->getEffectiveAddrStr()  
                                      : "0x############" )
                    : "--------------",
                (*it)->staticInst->disassemble( (*it)->instAddr() ),
                DTRACE( DumpROB_showSrcRegs ) ? 
                    instQueue.getSrcInstructionsStr(*it) : "",
                (*it)==(*head) ? " <= HEAD" : ((*it)==(*tail) ? " <= TAIL" : "" )
        );
    }
    DPRINTF( DumpROB, "=============== End of ROB contents =============== \n" ); 
}

template <class Impl>
unsigned
ROB<Impl>::reduceNumMaySquashOthers(    ThreadID tid,
                                        int numClearedMaySquashOthers,
                                        unsigned maxInstructionsToWakeup,
                                        IQ& instQueue,
                                        Scoreboard* scoreboard )
{
    if( numClearedMaySquashOthers > 0 ) {
        numInstThatMayCauseSquash[tid] -= numClearedMaySquashOthers;

        DPRINTF( DumpROB, "%d instructions may no longer squash. "
                "numInstThatMayCauseSquash[%d] == %d\n",  
                numClearedMaySquashOthers, tid,  numInstThatMayCauseSquash[tid] );
    }

	// Potentially some instructions are now not speculative, after a few branches
	// can no longer squash them.
    return markFollowingInstructionsAsSafe(   instList[tid].begin(),
                                                instList[tid].end(),
                                                maxInstructionsToWakeup,
                                                instQueue,
                                                scoreboard);
}

template <class Impl>
void
ROB<Impl>::takeOverFrom()
{
    resetState();
}

template <class Impl>
void
ROB<Impl>::resetEntries()
{
    if (robPolicy != Dynamic || numThreads > 1) {
        int active_threads = activeThreads->size();

        list<ThreadID>::iterator threads = activeThreads->begin();
        list<ThreadID>::iterator end = activeThreads->end();

        while (threads != end) {
            ThreadID tid = *threads++;

            if (robPolicy == Partitioned) {
                maxEntries[tid] = numEntries / active_threads;
            } else if (robPolicy == Threshold && active_threads == 1) {
                maxEntries[tid] = numEntries;
            }
        }
    }
}

template <class Impl>
int
ROB<Impl>::entryAmount(ThreadID num_threads)
{
    if (robPolicy == Partitioned) {
        return numEntries / num_threads;
    } else {
        return 0;
    }
}

template <class Impl>
int
ROB<Impl>::countInsts()
{
    int total = 0;

    for (ThreadID tid = 0; tid < numThreads; tid++)
        total += countInsts(tid);

    return total;
}

template <class Impl>
int
ROB<Impl>::countInsts(ThreadID tid)
{
    return instList[tid].size();
}

template <class Impl>
void
ROB<Impl>::leaveRunaheadMode(ThreadID tid)
{
    if( !inRunaheadMode[tid] )
        panic( "Trying to leave runahead mode while not in runahead\n" );

    inRunaheadMode[tid] = false;
}

template <class Impl>
void
ROB<Impl>::insertInst(DynInstPtr &inst, IQ& instQueue, LSQ& lsq)
{
    assert(inst);

    robWrites++;

    DPRINTF(ROB, "Adding inst [sn:%i] PC %s to the ROB.\n", inst->seqNum, inst->pcState());

    assert(numInstsInROB != numEntries);

    ThreadID tid = inst->threadNumber;

    instList[tid].push_back(inst);

    //Set Up head iterator if this is the 1st instruction in the ROB
    if (numInstsInROB == 0) {
        head = instList[tid].begin();
        assert((*head) == inst);
    }

    //Must Decrement for iterator to actually be valid  since __.end()
    //actually points to 1 after the last inst
    tail = instList[tid].end();
    tail--;

    inst->setInROB();

    //OW TODO: add debug condition CD_XXX, only in branch protection mode
    if( numInstThatMayCauseSquash[tid] > 0 ) {
        // We should mark the instruction as Unsafe, unless it's exempted:
        // If CD_Allow_NonLoads_AfterBranch is set then any non-load instruction is "safe"
        // in the sense that their output can be propogated.
        bool exemptInstruction = DTRACE( CD_Allow_NonLoads_AfterBranch ) && ! inst->isLoad();
       
        if( ! exemptInstruction )
            inst->setUnsafe();
    } 
    else if( DTRACE( CD_MarkUnsafeIf_LoadtInstruction ) && inst->isLoad() ) {
        // inst is NOT after an unresolved branch, however, since CD_MarkUnsafeIf_LoadtInstruction
        // is set ALL loads are considered unsafe until retirement.
        inst->setUnsafe();
    }

    // Only Unsafe instructions can be Runahead
    if( inRunaheadMode[tid] && inst->isUnsafe() ) {
        DPRINTF( DumpROB, "In Runahead mode and NOT SAFE: setting [sn:%i] as Runahead "
                          "instruction.\n", inst->seqNum );
        inst->setRunahead();
    }

    if( inst->maySquashOthers() ) {
        if( inRunaheadMode[tid] ) {
            // We record the branch that started runahead by keeping its maySquashOthers Flag
            // on. All following branches are considered as if they can't squash others. This
            // is fine because all folowing instructions will be marked as "runahead" anyways,
            // their output will be bogus, and they will be squashed eventuall when we leave
            // Runahed mode.
            inst->clearMaySquashOthers();
        } else {
            numInstThatMayCauseSquash[tid]++;
            DPRINTF( DumpROB, "numInstThatMayCauseSquash[%d] == %d\n", 
                    tid, numInstThatMayCauseSquash[tid] );

            if( ShouldEnterRunaheadMode(tid, lsq) ) {
                inst->setRunahead();
                inRunaheadMode[tid] = true;
                DPRINTF( DumpROB, "Entering Runahead mode!\n" );
            }
        }
    }

    ++numInstsInROB;
    ++threadEntries[tid];

    assert((*tail) == inst);

    DPRINTF(ROB, "[tid:%i] Now has %d instructions.\n", tid, threadEntries[tid]);
}

template <class Impl>
bool
ROB<Impl>::ShouldEnterRunaheadMode(ThreadID tid, LSQ& lsq)
{
    if( DTRACE( CD_Runahead_ifMoreThanNBranches ) && 
        numInstThatMayCauseSquash[tid] > runaheadROBThreshold ) {
        /* If there are more than runaheadROBThreshold unresolved branched in the ROB:
         * enter Runahead mode. We keep the maySquashOthers flag in this branch. This
         * flag together with the runahead flag on the branch marks the "initiating"
         * runahead branch. All forllowin branches in the ROB will have their 
         * maySquashOthers flag cleared. */
        return true;
    }

    if( DTRACE( CD_Runahead_ifBranchLoadIsStalling ) &&
        lsq.getEldestBranchPrequisiteAge(tid) > runaheadLoadAgeThreshhold ) {
        DPRINTF(ROB, "Eldest branch prequisite is older than %d!\n", runaheadLoadAgeThreshhold );
        return true;
    }

    return false;
}

template <class Impl>
void
ROB<Impl>::wakeupSafeInstructionDependants( DynInstPtr inst, 
                                            IQ& instQueue, 
                                            Scoreboard* scoreboard)
{
    /* int dependents = */ 
        instQueue.wakeDependents(inst);

    for (int i = 0; i < inst->numDestRegs(); i++) {
        //mark as Ready
        DPRINTF(IEW,"Setting Destination Register %i (%s)\n",
                inst->renamedDestRegIdx(i)->index(),
                inst->renamedDestRegIdx(i)->className());
        scoreboard->setReg(inst->renamedDestRegIdx(i));
    }
}

template <class Impl>
unsigned
ROB<Impl>::markFollowingInstructionsAsSafe(InstIt start,
                                           InstIt end,
                                           unsigned maxInstructionsToWakeup,
                                           IQ& instQueue,
                                           Scoreboard* scoreboard)
{
    unsigned numWokenInstructions = 0;

    for(    InstIt it = start; 
            it != end && numWokenInstructions < maxInstructionsToWakeup; 
            ++it) {
        // head instruction is cleared seperately, here we only clear instructions after 
        // a branch is resolved
        bool instructionIsUnsafeUntilRetirement =
            DTRACE( CD_MarkUnsafeIf_LoadtInstruction ) && (*it)->isLoad();

        if( ! (*it)->isSquashed() &&
              (*it)->isUnsafe()   &&
            ! instructionIsUnsafeUntilRetirement ) {
            (*it)->clearUnsafe();
            DPRINTF( DumpROB, "Cleared Unsafe flag from [sn:%i]\n", (*it)->seqNum );
 
            if( (*it)->isWritebackDone() ) {
                // writeback could not wake dependants since this instructiojn was squashable.
                // Now that instruction is not squashable, complete the writeback.

                DPRINTF(DumpROB, "[sn:%lli] Writeback done, instruction is NOT squashable - "
                                 "waking up dependants and marking scoreboard\n",
                                 (*it)->seqNum );
                wakeupSafeInstructionDependants( *it, instQueue, scoreboard ); 
                numWokenInstructions++;
                //TODO: update producer consumer stats. See IEW DefaultIEW<Impl>::writebackInsts() 
            } else {
                DPRINTF( DumpROB, "[sn:%lli] Writeback NOT DONE\n", (*it)->seqNum );
            }
        }
 
        if( (*it)->maySquashOthers() )
            break;
    }

    if( numWokenInstructions > 0 )
        DPRINTF( DumpROB, "Woken up %d instructions\n", numWokenInstructions );

    return numWokenInstructions;
}


template <class Impl>
void
ROB<Impl>::retireHead(  ThreadID tid, 
                        IQ& instQueue, 
                        Scoreboard* scoreboard )
{
    robWrites++;

    assert(numInstsInROB > 0);

    // Get the head ROB instruction.
    InstIt head_it = instList[tid].begin();
    InstIt post_head_it = head_it;
    post_head_it++;

    DynInstPtr head_inst = (*head_it);

    assert(head_inst->readyToCommit());

    DPRINTF(ROB, "[tid:%u]: Retiring head %s instruction, "
            "instruction PC %s, [sn:%lli] Latency to issue:%3llu%s\n", 
            tid, 
            head_inst->isSquashed() ? "SQUASHED" : "PENDING",
            head_inst->pcState(),
            head_inst->seqNum, 
            head_inst->latencyToIssue,
            head_inst->staticInst->disassemble(head_inst->pcState().pc()));

    if( !head_inst->isSquashed() ) {
        latencyToIssue_totalCycles += head_inst->latencyToIssue;

        /* if( head_inst->isLastMicroop() || !head_inst->isMicroop() ) */
        latencyToIssue_numInstructions++; //We count micro_ops
    }

    --numInstsInROB;
    --threadEntries[tid];
    
    head_inst->clearInROB();
    head_inst->setCommitted();
    


    if( head_inst->isUnsafe() && ! head_inst->isSquashed() ) {
        // If CD_MarkUnsafeIf_LoadtInstruction is set, loads become safe only when retired.
        // They will not be cleared by markFollowingInstructionsAsSafe, so we must clear
        // them now and wakeup any dependants.
        head_inst->clearUnsafe();
        DPRINTF(ROB, "[sn:%lli] waking up dependants\n", head_inst->seqNum );
        wakeupSafeInstructionDependants( head_inst, instQueue, scoreboard );
    }

    if( head_inst->maySquashOthers() ) {
        if( head_inst->isSquashed() )
            panic( "Squahed instruction should never be marked as maySquashOthers" );

        numInstThatMayCauseSquash[tid]--;
        DPRINTF( DumpROB, "Head instruction could cause squash - updating counter: "
                            "numInstThatMayCauseSquash[%d] == %d\n", 
                            tid, numInstThatMayCauseSquash[tid] );


        // TODO: consider calling markFollowingInstructionsAsSafe only if maySquashOthers
		head_inst->clearMaySquashOthers(); // To enable clearing of following instructions
        markFollowingInstructionsAsSafe( head_it,
                                         post_head_it,
                                         1, // Only mark the retired head as safe
                                         instQueue,
                                         scoreboard );
    }

    instList[tid].erase(head_it);

    //Update "Global" Head of ROB
    updateHead();

    // @todo: A special case is needed if the instruction being
    // retired is the only instruction in the ROB; otherwise the tail
    // iterator will become invalidated.
    cpu->removeFrontInst(head_inst);
}

template <class Impl>
bool
ROB<Impl>::isHeadReady(ThreadID tid)
{
    robReads++;
    if (threadEntries[tid] != 0) {
        return instList[tid].front()->readyToCommit();
    }

    return false;
}

template <class Impl>
bool
ROB<Impl>::canCommit()
{
    //@todo: set ActiveThreads through ROB or CPU
    list<ThreadID>::iterator threads = activeThreads->begin();
    list<ThreadID>::iterator end = activeThreads->end();

    while (threads != end) {
        ThreadID tid = *threads++;

        if (isHeadReady(tid)) {
            return true;
        }
    }

    return false;
}

template <class Impl>
unsigned
ROB<Impl>::numFreeEntries()
{
    return numEntries - numInstsInROB;
}

template <class Impl>
unsigned
ROB<Impl>::numFreeEntries(ThreadID tid)
{
    return maxEntries[tid] - threadEntries[tid];
}

template <class Impl>
void
ROB<Impl>::doSquash(ThreadID tid, IQ& instQueue, Scoreboard* scoreboard, bool squashInSingleCycle)
{
    robWrites++;
    int numSquashedInstThatMayCauseSquash = 0;

    DPRINTF(ROB, "[tid:%u]: Squashing instructions until [sn:%i].\n",
            tid, squashedSeqNum[tid]);

    assert(squashIt[tid] != instList[tid].end());

    if ((*squashIt[tid])->seqNum < squashedSeqNum[tid]) {
        DPRINTF(ROB, "[tid:%u]: Done squashing instructions.\n",
                tid);
        squashIt[tid] = instList[tid].end();

        doneSquashing[tid] = true;
        return;
    }

    bool robTailUpdate = false;

    for (int numSquashed = 0;
         (numSquashed < squashWidth || squashInSingleCycle) &&
         squashIt[tid] != instList[tid].end() &&
         (*squashIt[tid])->seqNum > squashedSeqNum[tid];
         ++numSquashed)
    {
        DPRINTF(ROB, "[tid:%u]: Squashing instruction PC %s, seq num %i.\n",
                (*squashIt[tid])->threadNumber,
                (*squashIt[tid])->pcState(),
                (*squashIt[tid])->seqNum);

        // Mark the instruction as squashed, and ready to commit so that
        // it can drain out of the pipeline.
        (*squashIt[tid])->setSquashed();
        (*squashIt[tid])->setCanCommit();

        if( (*squashIt[tid])->maySquashOthers() ) {
            numSquashedInstThatMayCauseSquash++;
            (*squashIt[tid])->clearMaySquashOthers();

            if( (*squashIt[tid])->isRunahead() ) {
                // This branch was the intiator to get into Runahead. We're about
                // to squash all following Runahead instructions anyhow, so it's
                // time to leave Runahead mode
                DPRINTF(ROB, "Squashed a Runahead intiator branch [sn:%i], "
                            "leaving Runahead mode\n",
                            (*squashIt[tid])->seqNum );
                leaveRunaheadMode( tid );
                (*squashIt[tid])->clearRunahead();
            }

        }

        if (squashIt[tid] == instList[tid].begin()) {
            DPRINTF(ROB, "Reached head of instruction list while "
                    "squashing.\n");

            squashIt[tid] = instList[tid].end();

            doneSquashing[tid] = true;

            goto out;
        }

        InstIt tail_thread = instList[tid].end();
        tail_thread--;

        if ((*squashIt[tid]) == (*tail_thread))
            robTailUpdate = true;

        squashIt[tid]--;
    }


    // Check if ROB is done squashing.
    if ((*squashIt[tid])->seqNum <= squashedSeqNum[tid]) {
        DPRINTF(ROB, "[tid:%u]: Done squashing instructions.\n",
                tid);
 
        if( (*squashIt[tid])->seqNum == squashedSeqNum[tid] 
                && (*squashIt[tid])->maySquashOthers() ) {
            // We reached the instruction causing the squash. It can no longer cause 
            // misprediction, so any new instructions added to the ROB should not be 
            // considered speculative.
            DPRINTF(ROB, "[tid:%u]: Marking [sn:%i] as resolved.\n",
                    tid, (*squashIt[tid])->seqNum );
            (*squashIt[tid])->clearMaySquashOthers();

            numSquashedInstThatMayCauseSquash++;

            if( (*squashIt[tid])->isRunahead() ) {
                // This branch was the intiator to get into Runahead. We're about
                // to squash all following Runahead instructions anyhow, so it's
                // time to leave Runahead mode
                DPRINTF(ROB, "Squashed until Runahead intiator branch [sn:%i], "
                            "leaving Runahead mode\n",
                            (*squashIt[tid])->seqNum );
                leaveRunaheadMode( tid );
                (*squashIt[tid])->clearRunahead();
            }
        }

        squashIt[tid] = instList[tid].end();

        doneSquashing[tid] = true;
    }

    if (robTailUpdate) {
        updateTail();
    }

out:
    /* We need to update how many unresolved branches we have in the ROB, 
     * so when we add a new instruction we'll know if it is safe or not. 
     * However, only the IEW will wakeup relevant dependants.*/
    const unsigned DONT_WAKE_DEPENDANTS = 0;
    unsigned maxWakeups = DTRACE( CD_LimitWakeDependandsToWBWidth ) ? 
                                DONT_WAKE_DEPENDANTS :
                                getMaxEntries(tid);
    reduceNumMaySquashOthers(  tid,
                               numSquashedInstThatMayCauseSquash,
                               maxWakeups,
                               instQueue,
                               scoreboard );
}


template <class Impl>
void
ROB<Impl>::updateHead()
{
    InstSeqNum lowest_num = 0;
    bool first_valid = true;

    // @todo: set ActiveThreads through ROB or CPU
    list<ThreadID>::iterator threads = activeThreads->begin();
    list<ThreadID>::iterator end = activeThreads->end();

    while (threads != end) {
        ThreadID tid = *threads++;

        if (instList[tid].empty())
            continue;

        if (first_valid) {
            head = instList[tid].begin();
            lowest_num = (*head)->seqNum;
            first_valid = false;
            continue;
        }

        InstIt head_thread = instList[tid].begin();

        DynInstPtr head_inst = (*head_thread);

        assert(head_inst != 0);

        if (head_inst->seqNum < lowest_num) {
            head = head_thread;
            lowest_num = head_inst->seqNum;
        }
    }

    if (first_valid) {
        head = instList[0].end();
    }

}

template <class Impl>
void
ROB<Impl>::updateTail()
{
    tail = instList[0].end();
    bool first_valid = true;

    list<ThreadID>::iterator threads = activeThreads->begin();
    list<ThreadID>::iterator end = activeThreads->end();

    while (threads != end) {
        ThreadID tid = *threads++;

        if (instList[tid].empty()) {
            continue;
        }

        // If this is the first valid then assign w/out
        // comparison
        if (first_valid) {
            tail = instList[tid].end();
            tail--;
            first_valid = false;
            continue;
        }

        // Assign new tail if this thread's tail is younger
        // than our current "tail high"
        InstIt tail_thread = instList[tid].end();
        tail_thread--;

        if ((*tail_thread)->seqNum > (*tail)->seqNum) {
            tail = tail_thread;
        }
    }
}


template <class Impl>
void
ROB<Impl>::squash(InstSeqNum    squash_num, 
                  ThreadID      tid, 
                  IQ&           instQueue, 
                  Scoreboard*   scoreboard,
                  bool          squashInSingleCycle)
{
    if (isEmpty(tid)) {
        DPRINTF(ROB, "Does not need to squash due to being empty "
                "[sn:%i]\n",
                squash_num);

        return;
    }

    DPRINTF(ROB, "Starting to squash within the ROB.\n");
    
    if( squashInSingleCycle )
        DPRINTF(ROB, "Squashing in a single cycle.\n");

    robStatus[tid] = ROBSquashing;

    doneSquashing[tid] = false;

    squashedSeqNum[tid] = squash_num;

    if (!instList[tid].empty()) {
        InstIt tail_thread = instList[tid].end();
        tail_thread--;

        squashIt[tid] = tail_thread;

        doSquash(tid, instQueue, scoreboard, squashInSingleCycle);
    }
}

template <class Impl>
typename Impl::DynInstPtr
ROB<Impl>::readHeadInst(ThreadID tid)
{
    if (threadEntries[tid] != 0) {
        InstIt head_thread = instList[tid].begin();

        assert((*head_thread)->isInROB());

        return *head_thread;
    } else {
        return dummyInst;
    }
}

template <class Impl>
typename Impl::DynInstPtr
ROB<Impl>::readTailInst(ThreadID tid)
{
    InstIt tail_thread = instList[tid].end();
    tail_thread--;

    return *tail_thread;
}

template <class Impl>
void
ROB<Impl>::regStats()
{
    using namespace Stats;
    robReads
        .name(name() + ".rob_reads")
        .desc("The number of ROB reads");

    robWrites
        .name(name() + ".rob_writes")
        .desc("The number of ROB writes");

    latencyToIssue_totalCycles
        .name(name() + ".latencyToIssue_totalCycles")
        .desc("Latency from entering ROB to become ready to issue, ONLY FOR "
                "successfully retired, non-squashed, instructions");

    latencyToIssue_numInstructions
        .name(name() + ".latencyToIssue_numInstructions")
        .desc("Latency from entering ROB to become ready to issue. "
                "To get the avergae latency divide "
                "latencyToIssue_totalCycles/latencyToIssue_numInstructions");
    
    robNumEntries_accumulator
        .name(name() + ".robNumEntries_accumulator")
        .desc("An accumulator of number of entries in ROB. divide this number in "
                "number of ticks to get an average.");
}

template <class Impl>
typename Impl::DynInstPtr
ROB<Impl>::findInst(ThreadID tid, InstSeqNum squash_inst)
{
    for (InstIt it = instList[tid].begin(); it != instList[tid].end(); it++) {
        if ((*it)->seqNum == squash_inst) {
            return *it;
        }
    }
    return NULL;
}

#endif//__CPU_O3_ROB_IMPL_HH__
