#! /usr/bin/env python3
from argparse import ArgumentParser
from inspect import isclass
from pprint import pprint

class CooldownConfig:

    class Empty:
        @staticmethod
        def before_init(system):
            pass
        @staticmethod
        def after_warmup():
            pass

    class BranchProtection_Conservative:
        @staticmethod
        def before_init(system):
            pass
        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()
            m5.debug.flags[ "CD_LimitWakeDependandsToWBWidth" ].enable()

    class BranchProtection_Conservative_Prevent_SSB:
        @staticmethod
        def before_init(system):
            pass
        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()
            m5.debug.flags[ "CD_LimitWakeDependandsToWBWidth" ].enable()

            # SSB defense
            # 1. Mark loads as unsafe
            # 2. Allow clearing loads once we no there is no store bypass
            m5.debug.flags[ "CD_MarkUnsafeIf_LoadtInstruction" ].enable()
            m5.debug.flags[ "CD_MitigateSSB_ReleaseLoadsWhenThereIsNoBypass" ].enable() 

    class BranchProtection_Conservative_SingleCycleSquash:
        @staticmethod
        def before_init(system):
            pass
        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()
            m5.debug.flags[ "CD_LimitWakeDependandsToWBWidth" ].enable()

            m5.debug.flags[ "CD_SquashInSingleCycle" ].enable()
            m5.debug.flags[ "CD_LimitWakeDependandsToWBWidth" ].enable()
#     class BranchProtection_Conservative_PrioritizeBranchPrequisites:
#         @staticmethod
#         def before_init(system):
#             pass
#         @staticmethod
#         def after_warmup():
#             import m5
#             m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
#             m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
#             m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()

#             # The following will modify the priority queue in the Issue Queue to prefer
#             # load nstrucctions which are prequisites of branches.
#             m5.debug.flags[ "CD_MarkBranchPrequisites" ].enable()
#             m5.debug.flags[ "CD_Prioritize_Branch_Execution" ].enable()


    class BranchProtection_Liberal:
        @staticmethod
        def before_init(system):
            pass
        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()

            m5.debug.flags[ "CD_Allow_NonLoads_AfterBranch" ].enable()
            m5.debug.flags[ "CD_LimitWakeDependandsToWBWidth" ].enable()

    class BranchProtection_Liberal_Prevent_SSB:
        @staticmethod
        def before_init(system):
            pass
        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()

            m5.debug.flags[ "CD_Allow_NonLoads_AfterBranch" ].enable()
            m5.debug.flags[ "CD_LimitWakeDependandsToWBWidth" ].enable()

            # SSB defense
            # 1. Mark loads as unsafe
            # 2. Allow clearing loads once we no there is no store bypass
            m5.debug.flags[ "CD_MarkUnsafeIf_LoadtInstruction" ].enable()
            m5.debug.flags[ "CD_MitigateSSB_ReleaseLoadsWhenThereIsNoBypass" ].enable() 

    class BranchProtection_Liberal_delayedWakeup_0:
        @staticmethod
        def before_init(system):
            cpu = system.cpu[0]
            cpu.unsafeClearingDelay.value = 0

        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()

            m5.debug.flags[ "CD_Allow_NonLoads_AfterBranch" ].enable()
            m5.debug.flags[ "CD_LimitWakeDependandsToWBWidth" ].enable()
            m5.debug.flags[ "CD_DelayUnsafeClearing" ].enable()

    class BranchProtection_Liberal_delayedWakeup_1:
        @staticmethod
        def before_init(system):
            cpu = system.cpu[0]
            cpu.unsafeClearingDelay.value = 1

        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()

            m5.debug.flags[ "CD_Allow_NonLoads_AfterBranch" ].enable()
            m5.debug.flags[ "CD_LimitWakeDependandsToWBWidth" ].enable()
            m5.debug.flags[ "CD_DelayUnsafeClearing" ].enable()

    class BranchProtection_Liberal_delayedWakeup_2:
        @staticmethod
        def before_init(system):
            cpu = system.cpu[0]
            cpu.unsafeClearingDelay.value = 2

        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()

            m5.debug.flags[ "CD_Allow_NonLoads_AfterBranch" ].enable()
            m5.debug.flags[ "CD_LimitWakeDependandsToWBWidth" ].enable()
            m5.debug.flags[ "CD_DelayUnsafeClearing" ].enable()

    class EagerLoadsProtection:
        @staticmethod
        def before_init(system):
            pass
        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_LoadtInstruction" ].enable()
            m5.debug.flags[ "CD_LimitWakeDependandsToWBWidth" ].enable()

    class EagerLoadsProtection_SingleCycleSquash:
        @staticmethod
        def before_init(system):
            pass
        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_LoadtInstruction" ].enable()
            m5.debug.flags[ "CD_LimitWakeDependandsToWBWidth" ].enable()
            m5.debug.flags[ "CD_SquashInSingleCycle" ].enable()

    class EagerLoadsProtection_Runahead_ByNumBlockedBranches_5:
        @staticmethod
        def before_init(system):
            cpu = system.cpu[0]
            cpu.runaheadROBThreshold.value = 5

        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_LoadtInstruction" ].enable()
            m5.debug.flags[ "CD_LimitWakeDependandsToWBWidth" ].enable()
            m5.debug.flags[ "CD_SquashInSingleCycle" ].enable()

            m5.debug.flags[ "CD_Runahead_ifMoreThanNBranches" ].enable()
            m5.debug.flags[ "CD_Runahead_QuickOutputPropagation" ].enable()
            m5.debug.flags[ "CD_Runahead_SquashInSingleCycle" ].enable()
            m5.debug.flags[ "CD_LimitWakeDependandsToWBWidth" ].enable()
            m5.debug.flags[ "CD_SquashInSingleCycle" ].enable()



    class MaximumProtection:
        @staticmethod
        def before_init(system):
            pass
        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()
            m5.debug.flags[ "CD_MarkUnsafeIf_LoadtInstruction" ].enable()
            m5.debug.flags[ "CD_LimitWakeDependandsToWBWidth" ].enable()

    class MaximumProtection_delayedWakeup_0:
        @staticmethod
        def before_init(system):
            cpu = system.cpu[0]
            cpu.unsafeClearingDelay.value = 0

        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()
            m5.debug.flags[ "CD_MarkUnsafeIf_LoadtInstruction" ].enable()
            m5.debug.flags[ "CD_LimitWakeDependandsToWBWidth" ].enable()
            m5.debug.flags[ "CD_DelayUnsafeClearing" ].enable()

    class MaximumProtection_delayedWakeup_1:
        @staticmethod
        def before_init(system):
            cpu = system.cpu[0]
            cpu.unsafeClearingDelay.value = 1

        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()
            m5.debug.flags[ "CD_MarkUnsafeIf_LoadtInstruction" ].enable()
            m5.debug.flags[ "CD_LimitWakeDependandsToWBWidth" ].enable()
            m5.debug.flags[ "CD_DelayUnsafeClearing" ].enable()

    class MaximumProtection_delayedWakeup_2:
        @staticmethod
        def before_init(system):
            cpu = system.cpu[0]
            cpu.unsafeClearingDelay.value = 2

        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()
            m5.debug.flags[ "CD_MarkUnsafeIf_LoadtInstruction" ].enable()
            m5.debug.flags[ "CD_LimitWakeDependandsToWBWidth" ].enable()
            m5.debug.flags[ "CD_DelayUnsafeClearing" ].enable()

    class MaximumProtection_Runahead_ByNumBlockedBranches_5:
        @staticmethod
        def before_init(system):
            cpu = system.cpu[0]
            cpu.runaheadROBThreshold.value = 5

        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()
            m5.debug.flags[ "CD_MarkUnsafeIf_LoadtInstruction" ].enable()

            m5.debug.flags[ "CD_Runahead_ifMoreThanNBranches" ].enable()
            m5.debug.flags[ "CD_Runahead_QuickOutputPropagation" ].enable()
            m5.debug.flags[ "CD_Runahead_SquashInSingleCycle" ].enable()
            m5.debug.flags[ "CD_SquashInSingleCycle" ].enable()
            m5.debug.flags[ "CD_LimitWakeDependandsToWBWidth" ].enable()


#     class BranchProtection_Liberal_PrioritizeBranchPrequisites:
#         @staticmethod
#         def before_init(system):
#             pass
#         @staticmethod
#         def after_warmup():
#             import m5
#             m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
#             m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
#             m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()

#             m5.debug.flags[ "CD_Allow_NonLoads_AfterBranch" ].enable()

#             # The following will modify the priority queue in the Issue Queue to prefer
#             # load nstrucctions which are prequisites of branches.
#             m5.debug.flags[ "CD_MarkBranchPrequisites" ].enable()
#             m5.debug.flags[ "CD_Prioritize_Branch_Execution" ].enable()


    class BranchProtection_Conservative_Runahead_ByNumBlockedBranches_5:
        @staticmethod
        def before_init(system):
            cpu = system.cpu[0]
            cpu.runaheadROBThreshold.value = 5

        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()

            m5.debug.flags[ "CD_Runahead_ifMoreThanNBranches" ].enable()
            m5.debug.flags[ "CD_Runahead_QuickOutputPropagation" ].enable()
            m5.debug.flags[ "CD_Runahead_SquashInSingleCycle" ].enable()
            m5.debug.flags[ "CD_LimitWakeDependandsToWBWidth" ].enable()
            m5.debug.flags[ "CD_SquashInSingleCycle" ].enable()


    class BranchProtection_Conservative_Runahead_ByNumBlockedBranches_4:
        @staticmethod
        def before_init(system):
            cpu = system.cpu[0]
            cpu.runaheadROBThreshold.value = 4

        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()

            m5.debug.flags[ "CD_Runahead_ifMoreThanNBranches" ].enable()
            m5.debug.flags[ "CD_Runahead_QuickOutputPropagation" ].enable()
            m5.debug.flags[ "CD_Runahead_SquashInSingleCycle" ].enable()


    class BranchProtection_Conservative_Runahead_ByNumBlockedBranches_3:
        @staticmethod
        def before_init(system):
            cpu = system.cpu[0]
            cpu.runaheadROBThreshold.value = 3

        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()

            m5.debug.flags[ "CD_Runahead_ifMoreThanNBranches" ].enable()
            m5.debug.flags[ "CD_Runahead_QuickOutputPropagation" ].enable()
            m5.debug.flags[ "CD_Runahead_SquashInSingleCycle" ].enable()


    class BranchProtection_Conservative_Runahead_ByNumBlockedBranches_2:
        @staticmethod
        def before_init(system):
            cpu = system.cpu[0]
            cpu.runaheadROBThreshold.value = 2

        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()

            m5.debug.flags[ "CD_Runahead_ifMoreThanNBranches" ].enable()
            m5.debug.flags[ "CD_Runahead_QuickOutputPropagation" ].enable()
            m5.debug.flags[ "CD_Runahead_SquashInSingleCycle" ].enable()


    class BranchProtection_Conservative_Runahead_ByNumBlockedBranches_1:
        @staticmethod
        def before_init(system):
            cpu = system.cpu[0]
            cpu.runaheadROBThreshold.value = 1

        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()

            m5.debug.flags[ "CD_Runahead_ifMoreThanNBranches" ].enable()
            m5.debug.flags[ "CD_Runahead_QuickOutputPropagation" ].enable()
            m5.debug.flags[ "CD_Runahead_SquashInSingleCycle" ].enable()

#     class BranchProtection_Conservative_Runahead_ByNumBlockedBranches:
#         @staticmethod
#         def before_init(system):
#             cpu = system.cpu[0]
#             cpu.runaheadROBThreshold.value = 7

#         @staticmethod
#         def after_warmup():
#             import m5
#             m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
#             m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()

#             m5.debug.flags[ "CD_Runahead_ifMoreThanNBranches" ].enable()
#             m5.debug.flags[ "CD_Runahead_QuickOutputPropagation" ].enable()
#             m5.debug.flags[ "CD_Runahead_SquashInSingleCycle" ].enable()

#     class BranchProtection_Conservative_Runahead_ByAgeOfBranchPreqInLSQ:
#         @staticmethod
#         def before_init(system):
#             cpu = system.cpu[0]
#             cpu.runaheadLoadAgeThreshhold.value = 20

#         @staticmethod
#         def after_warmup():
#             import m5
#             m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
#             m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
#             m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()

#             m5.debug.flags[ "CD_Runahead_ifBranchLoadIsStalling" ].enable()
#             m5.debug.flags[ "CD_Runahead_QuickOutputPropagation" ].enable()
#             m5.debug.flags[ "CD_Runahead_SquashInSingleCycle" ].enable()

#             # This is a requirement for identifying a "branch prequisite load"
#             m5.debug.flags[ "CD_MarkBranchPrequisites" ].enable()

    class BranchProtection_Conservative_Runahead_ByAgeOfBranchPreqInLSQ_5:
        @staticmethod
        def before_init(system):
            cpu = system.cpu[0]
            cpu.runaheadLoadAgeThreshhold.value = 5

        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()

            m5.debug.flags[ "CD_Runahead_ifBranchLoadIsStalling" ].enable()
            m5.debug.flags[ "CD_Runahead_QuickOutputPropagation" ].enable()
            m5.debug.flags[ "CD_Runahead_SquashInSingleCycle" ].enable()

            # This is a requirement for identifying a "branch prequisite load"
            m5.debug.flags[ "CD_MarkBranchPrequisites" ].enable()


    class BranchProtection_Conservative_Runahead_ByAgeOfBranchPreqInLSQ_4:
        @staticmethod
        def before_init(system):
            cpu = system.cpu[0]
            cpu.runaheadLoadAgeThreshhold.value = 4

        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()

            m5.debug.flags[ "CD_Runahead_ifBranchLoadIsStalling" ].enable()
            m5.debug.flags[ "CD_Runahead_QuickOutputPropagation" ].enable()
            m5.debug.flags[ "CD_Runahead_SquashInSingleCycle" ].enable()

            # This is a requirement for identifying a "branch prequisite load"
            m5.debug.flags[ "CD_MarkBranchPrequisites" ].enable()


    class BranchProtection_Conservative_Runahead_ByAgeOfBranchPreqInLSQ_3:
        @staticmethod
        def before_init(system):
            cpu = system.cpu[0]
            cpu.runaheadLoadAgeThreshhold.value = 3

        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()

            m5.debug.flags[ "CD_Runahead_ifBranchLoadIsStalling" ].enable()
            m5.debug.flags[ "CD_Runahead_QuickOutputPropagation" ].enable()
            m5.debug.flags[ "CD_Runahead_SquashInSingleCycle" ].enable()

            # This is a requirement for identifying a "branch prequisite load"
            m5.debug.flags[ "CD_MarkBranchPrequisites" ].enable()


    class BranchProtection_Conservative_Runahead_ByAgeOfBranchPreqInLSQ_2:
        @staticmethod
        def before_init(system):
            cpu = system.cpu[0]
            cpu.runaheadLoadAgeThreshhold.value = 2

        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()

            m5.debug.flags[ "CD_Runahead_ifBranchLoadIsStalling" ].enable()
            m5.debug.flags[ "CD_Runahead_QuickOutputPropagation" ].enable()
            m5.debug.flags[ "CD_Runahead_SquashInSingleCycle" ].enable()

            # This is a requirement for identifying a "branch prequisite load"
            m5.debug.flags[ "CD_MarkBranchPrequisites" ].enable()


    class BranchProtection_Conservative_Runahead_ByAgeOfBranchPreqInLSQ_1:
        @staticmethod
        def before_init(system):
            cpu = system.cpu[0]
            cpu.runaheadLoadAgeThreshhold.value = 1

        @staticmethod
        def after_warmup():
            import m5
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()

            m5.debug.flags[ "CD_Runahead_ifBranchLoadIsStalling" ].enable()
            m5.debug.flags[ "CD_Runahead_QuickOutputPropagation" ].enable()
            m5.debug.flags[ "CD_Runahead_SquashInSingleCycle" ].enable()

            # This is a requirement for identifying a "branch prequisite load"
            m5.debug.flags[ "CD_MarkBranchPrequisites" ].enable()

    class Default:
        @staticmethod
        def before_init(system):
            print('Setting ROB threshhold')
            cpu = system.cpu[0]
            cpu.runaheadROBThreshold.value = 12
            cpu.runaheadLoadAgeThreshhold.value = 20

        @staticmethod
        def after_warmup():
            import m5
            print('Setting debug flags')
            m5.debug.flags[ "CD_MarkUnsafeIf_AfterBranch" ].enable()
            # m5.debug.flags[ "CD_MarkUnsafeIf_LoadtInstruction" ].enable()
            m5.debug.flags[ "CD_Clear_MaySquash_AtExec" ].enable()
            m5.debug.flags[ "CD_Clear_DirectUnconditionalBranches_AtDecode" ].enable()
            # m5.debug.flags[ "CD_Runahead_ifMoreThanNBranches" ].enable()
            # m5.debug.flags[ "CD_Runahead_ifBranchLoadIsStalling" ].enable()
            # m5.debug.flags[ "CD_Runahead_QuickOutputPropagation" ].enable()
            m5.debug.flags[ "CD_MarkBranchPrequisites" ].enable()
            # m5.debug.flags[ "CD_Runahead_SquashInSingleCycle" ].enable()
            # m5.debug.flags[ "CD_SquashInSingleCycle" ].enable()
            # m5.debug.flags[ "Cache" ].enable()
            m5.debug.flags[ "CD_LimitWakeDependandsToWBWidth" ].enable()
            # m5.debug.flags[ "CD_Prioritize_Branch_Execution" ].enable()
            # m5.debug.flags[ "CD_Allow_NonLoads_AfterBranch" ].enable()

            # m5.debug.flags[ "DumpROB" ].enable()
            # m5.debug.flags[ "DumpROB_showSrcRegs" ].enable()
            # m5.debug.flags[ "ROB" ].enable()
            # m5.debug.flags[ "IEW" ].enable()

            # m5.debug.flags[ "Decoder" ].enable()
            # m5.debug.flags[ "DumpROB_showSrcRegs" ].enable()
            # m5.debug.flags[ "DumpROB_show_addr" ].enable()
            # m5.debug.flags[ "DumpInstructionData" ].enable()
            # m5.debug.flags[ "Fetch" ].enable()
            # m5.debug.flags[ "FollowInstruction" ].enable()
            # m5.debug.flags[ "InstLogCalls" ].enable()
            # m5.debug.flags[ "Commit" ].enable()
            # m5.debug.flags[ "IQ" ].enable()
            # m5.debug.flags[ "Branch" ].enable()

            # m5.debug.flags[ "FollowInstruction" ].enable()
            # m5.debug.flags[ "CD_Allow_NonLoads_AfterBranch" ].enable()


    #################################

    GROUPS = {
            'BRANCH_PROTECTION_CONSERVATIVE_RUNAHEAD_NUM_BLOCKED_BRANCHES': [
                BranchProtection_Conservative_Runahead_ByNumBlockedBranches_5,
                BranchProtection_Conservative_Runahead_ByNumBlockedBranches_4,
                BranchProtection_Conservative_Runahead_ByNumBlockedBranches_1,
                BranchProtection_Conservative_Runahead_ByNumBlockedBranches_3,
                BranchProtection_Conservative_Runahead_ByNumBlockedBranches_2,
            ],

            'BRANCH_PROTECTION_CONSERVATIVE_RUNAHEAD_AGE_IN_LSQ': [
                BranchProtection_Conservative_Runahead_ByAgeOfBranchPreqInLSQ_5,
                BranchProtection_Conservative_Runahead_ByAgeOfBranchPreqInLSQ_3,
                BranchProtection_Conservative_Runahead_ByAgeOfBranchPreqInLSQ_2,
                BranchProtection_Conservative_Runahead_ByAgeOfBranchPreqInLSQ_1,
                BranchProtection_Conservative_Runahead_ByAgeOfBranchPreqInLSQ_4,
            ],

            'GRAND_EVAL_PROFILES': [
                BranchProtection_Liberal,
                BranchProtection_Conservative,
                EagerLoadsProtection,
                MaximumProtection,
                Empty # For O3 comparison
            ],

            'KILLING_RUNAHEAD' : [
                BranchProtection_Conservative,
                BranchProtection_Conservative_SingleCycleSquash,
                BranchProtection_Conservative_Runahead_ByNumBlockedBranches_5,
                EagerLoadsProtection,
                EagerLoadsProtection_SingleCycleSquash,
                EagerLoadsProtection_Runahead_ByNumBlockedBranches_5,
            ],

            'DELAYED_CLEAR_UNSAFE' : [
                BranchProtection_Liberal_delayedWakeup_0,
                BranchProtection_Liberal_delayedWakeup_1,
                BranchProtection_Liberal_delayedWakeup_2,

                MaximumProtection_delayedWakeup_0,
                MaximumProtection_delayedWakeup_1,
                MaximumProtection_delayedWakeup_2,
            ],

            'EVERYTHING' : [
                BranchProtection_Liberal_delayedWakeup_0,
                BranchProtection_Liberal_delayedWakeup_1,
                BranchProtection_Liberal_delayedWakeup_2,

                MaximumProtection_delayedWakeup_0,
                MaximumProtection_delayedWakeup_1,
                MaximumProtection_delayedWakeup_2,

                BranchProtection_Liberal,
                BranchProtection_Conservative,
                BranchProtection_Conservative_Prevent_SSB,
                BranchProtection_Liberal_Prevent_SSB,
                EagerLoadsProtection,
                MaximumProtection,
                Empty # For O3 comparison
            ], 

            'PREVENT_SSB': [
                BranchProtection_Conservative_Prevent_SSB,
                BranchProtection_Liberal_Prevent_SSB,
            ],

            'PREVENT_SSB_ALL': [
                BranchProtection_Conservative_Prevent_SSB,
                BranchProtection_Liberal_Prevent_SSB,
                BranchProtection_Liberal,
                BranchProtection_Conservative,
                EagerLoadsProtection,
                MaximumProtection,
                Empty # For O3 comparison
            ],
    }

    @staticmethod
    def add_parser_args(parser):
        parser.add_argument('--cooldown-config', default='empty',
            help='Enable Cooldown with a specific variant')
        parser.add_argument('--config-group', default=None,
            help='Run a specific group of configs (plus in order and OOO')
        parser.add_argument('--list-configs', action='store_true', default=False,
            help='Show available configs')
        parser.add_argument('--list-groups', action='store_true', default=False,
            help='Show available groups')

    @staticmethod
    def add_optparse_args(parser):
        parser.add_option('--cooldown-config', default='empty',
            help='Enable Cooldown with a specific variant')

    @classmethod
    def _get_config_classes(cls):
        return { k.lower(): v for k, v in cls.__dict__.items() if isclass(v) }

    @classmethod
    def _get_config_groups(cls):
        return { k.lower(): v for k, v in cls.GROUPS.items() }

    @classmethod
    def is_valid_config(cls, config_name):
        config_name = config_name.lower()
        return config_name in cls._get_config_classes()

    @classmethod
    def get_all_config_names(cls):
        config_classes = cls._get_config_classes()
        return [ name for name in config_classes ]

    @classmethod
    def get_config(cls, config_name):
        config_name = config_name.lower()
        print('Config: {}'.format(config_name))

        config_classes = cls._get_config_classes()
        if config_name not in config_classes:
            raise Exception('{} not a valid config. Valid configs: {}'.format(
              config_name, ', '.join(config_classes.keys())))

        config_class = config_classes[config_name]
        config_methods = { k: v for k, v in
            config_class.__dict__.items() if isinstance(v, staticmethod)}

        before_init_fn = config_methods['before_init'].__func__
        after_warmup_fn = config_methods['after_warmup'].__func__
        return before_init_fn, after_warmup_fn

    @classmethod
    def get_config_group_names(cls, group_name):
        group_name = group_name.upper()
        for group, classes in cls.GROUPS.items():
            if group_name in group:
                for config_class in classes:
                    yield config_class.__name__

    @classmethod
    def maybe_show_configs(cls, args):
        do_exit = False
        if args.list_configs:
            do_exit = True
            pprint([k for k in cls._get_config_classes().keys()])
        if args.list_groups:
            do_exit = True
            pprint([k for k in cls._get_config_groups().keys()])

        if do_exit:
            exit()


def main():
    parser = ArgumentParser(description='For testing')
    CooldownConfig.add_parser_args(parser)

    args = parser.parse_args()
    before, after = CooldownConfig.get_config(args.cooldown_config)
    print(before)
    print(after)

if __name__ == '__main__':
    exit(main())
