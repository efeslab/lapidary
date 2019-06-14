from jinja2 import Template
import os, resource
import re

class MemoryMapping:
    def __init__(self, index, paddr, vaddr, size, offset, flags, name):
        self.index  = index
        self.paddr  = paddr
        self.vaddr  = vaddr
        self.size   = size
        self.offset = offset
        self.flags  = flags
        self.name   = name

    def __str__(self):
        return '{}: {} -> {}'.format(self.index, hex(self.vaddr), hex(self.paddr))

    def __lt__(self, other):
        return self.vaddr < other.vaddr

    def __eq__(self, other):
        return self.vaddr == other.vaddr

    def __contains__(self, vaddr):
        return self.vaddr <= vaddr and vaddr < self.vaddr + self.size


class RegisterValues:

    pattern = re.compile('(\w+)\s+(\w+)\s+([-\w]+)')
    eflags  = re.compile('eflags\s+(\w+)\s+(\[.*\])\s*')
    mxcsr   = re.compile('mxcsr\s+(\w+)\s+(\[.*\])\s*')
    floats  = re.compile('(\w+).*v2_int64 = \{(\w+), (\w+)\}.*')

    defaults = {
        'cr0': 2147483699,
        'dr6': 4294905840,
        'dr7': 1024,
        'm5': 243440,
        'efer': 19713,
        'es_attr': 46043,
        'cs_attr': 43731,
        'ss_attr': 46043,
        'ds_attr': 46043,
        'fs_attr': 46043,
        'gs_attr': 46043,
        'hs_attr': 46043,
        'tsl_attr': 46043,
        'tsg_attr': 46043,
        'ls_attr': 46043,
        'ms_attr': 46043,
        'tr_attr': 46043,
        'idtr_attr': 46043
    }

    def __init__(self, fs_base):
        import copy
        import gdb
        raw = gdb.execute('info all-registers', to_string=True)
        self.regvals = copy.deepcopy(RegisterValues.defaults)
        self.fs_base = fs_base

        for entry in raw.split(os.linesep):
            entry = entry.strip()
            matches = RegisterValues.pattern.match(entry)
            if matches:
                self.regvals[matches.group(1)] = int(matches.group(2), 16)

            eflags_matches = RegisterValues.eflags.match(entry)
            if eflags_matches:
                self.regvals['rflags'] = int(eflags_matches.group(1), 16)

            mxcsr_matches = RegisterValues.mxcsr.match(entry)
            if mxcsr_matches:
                self.regvals['mxcsr'] = int(mxcsr_matches.group(1), 16)

        # Parse floats
        for i in range(16):
            entry = gdb.execute('info registers xmm{}'.format(i), to_string=True)
            matches = RegisterValues.floats.match(entry.strip())
            if matches:
                high = 'xmm{}_high'.format(i)
                low = 'xmm{}_low'.format(i)
                self.regvals[high] = int(matches.group(2), 16)
                self.regvals[low] = int(matches.group(3), 16)
                #print('{}: {}, {}'.format(i, self.regvals[high], self.regvals[low]))


    def __getitem__(self, regname):
        if regname not in self.regvals:
            if regname == 'fs_base' or regname == 'fs_eff_base':
                return self.fs_base
            else:
                return 0
        return self.regvals[regname]

    def get_int_reg_string(self):
        reg_str = str()
        regs = ['rax', 'rcx', 'rdx', 'rbx', 'rsp', 'rbp', 'rsi', 'rdi', 'r8', 'r9',
            'r10', 'r11', 'r12', 'r13', 'r14', 'r15']
        for r in regs:
            reg_str += '{} '.format(self[r])
        # Micro-op registers and implict registers
        reg_str += '0 ' * 22
        regs_chk = reg_str.strip().split(' ')
        return reg_str.strip()


    def get_float_reg_string(self):
        reg_str = str()
        for i in range(8):
            regname = '{}'.format(i)
            reg_str += '{} '.format(self[regname])
        for i in range(8):
            regname = 'fpr{}'.format(i)
            reg_str += '{} '.format(self[regname])
        for i in range(32):
            suffix = '_low' if i % 2 else '_high'
            regname = 'xmm{}{}'.format(i // 2, suffix)
            reg_str += '{} '.format(self[regname])
        for i in range(8):
            regname = 'microfp{}'.format(i)
            reg_str += '{} '.format(self[regname])
        return reg_str.strip()


    def get_pc_string(self):
        virt_pc = int(self['rip'])
        return '{}'.format(virt_pc)

    def get_next_pc_string(self):
        import gdb
        raw = gdb.execute('x/2i $pc', to_string=True)
        print(raw)
        next_line = raw.split(os.linesep)[1].strip().replace('\t', ' ')
        print(next_line)
        next_pc = next_line.split(' ')[0].strip().replace(':', '')
        return '{}'.format(int(next_pc, 16))

    def get_misc_reg_string(self):
        ''' For system.cpu.isa regVal string '''
        reg_str = str()
        # Control registers
        for i in range(16):
            reg_str += '{} '.format(self['cr{}'.format(i)])
        # Debug registers
        for i in range(8):
            reg_str += '{} '.format(self['dr{}'.format(i)])

        regs = ['rflags', 'm5', 'tsc', 'mtrrcap', 'sysenter_cs', 'sysenter_esp',
            'sysenter_eip', 'mcg_cap', 'mcg_status', 'mcg_ctl', 'debug_ctl_msr',
            'lbfi', 'lbti', 'lefi', 'leti']
        for r in regs:
            reg_str += '{} '.format(self[r])

        for i in range(8):
            reg_str += '{} '.format(self['mtrr_phys_base{}'.format(i)])
        for i in range(8):
            reg_str += '{} '.format(self['mtrr_phys_mask{}'.format(i)])
        for i in range(11):
            reg_str += '{} '.format(self['mtrr_fix{}'.format(i)])

        regs = ['pat', 'def_type']
        for r in regs:
            reg_str += '{} '.format(self[r])

        for i in range(8):
            reg_str += '{} '.format(self['mc{}_ctl'.format(i)])
        for i in range(8):
            reg_str += '{} '.format(self['mc{}_status'.format(i)])
        for i in range(8):
            reg_str += '{} '.format(self['mc{}_addr'.format(i)])
        for i in range(8):
            reg_str += '{} '.format(self['mc{}_misc'.format(i)])

        regs = ['efer', 'star', 'lstar', 'cstar', 'sf_mask', 'kernel_gs_base',
            'tsc_aux']
        for r in regs:
            reg_str += '{} '.format(self[r])

        for i in range(4):
            reg_str += '{} '.format(self['perf_evt_sel{}'.format(i)])
        for i in range(4):
            reg_str += '{} '.format(self['perf_evt_ctr{}'.format(i)])

        regs = ['syscfg', 'iorr_base0', 'iorr_base1', 'iorr_mask0', 'iorr_mask1',
            'top_mem', 'top_mem2', 'vm_cr', 'ignne', 'smm_ctl', 'vm_hsave_pa',
            'es', 'cs', 'ss', 'ds', 'fs', 'gs', 'hs', 'tsl', 'tsg', 'ls', 'ms',
            'tr', 'idtr', 'es_base', 'cs_base', 'ss_base', 'ds_base', 'fs_base',
            'gs_base', 'hs_base', 'tsl_base', 'tsg_base', 'ls_base', 'ms_base',
            'tr_base', 'idtr_base', 'es_eff_base', 'cs_eff_base', 'ss_eff_base',
            'ds_eff_base', 'fs_eff_base', 'gs_eff_base', 'hs_eff_base', 'tsl_eff_base',
            'tsg_eff_base', 'ls_eff_base', 'ms_eff_base', 'tr_eff_base',
            'idtr_eff_base', 'es_limit', 'cs_limit', 'ss_limit', 'ds_limit',
            'fs_limit', 'gs_limit', 'hs_limit', 'tsl_limit', 'tsg_limit',
            'ls_limit', 'ms_limit', 'tr_limit', 'idtr_limit', 'es_attr', 'cs_attr',
            'ss_attr', 'ds_attr', 'fs_attr', 'gs_attr', 'hs_attr', 'tsl_attr',
            'tsg_attr', 'ls_attr', 'ms_attr', 'tr_attr', 'idtr_attr', 'x87_top',
            'mxcsr', 'fcw', 'fsw', 'ftw', 'ftag', 'fiseg', 'fioff', 'foseg',
            'fooff', 'fop', 'apic_base', 'pci_config_address']
        for r in regs:
            reg_str += '{} '.format(self[r])
        return reg_str.strip()

WORK_DIR = os.path.dirname(__file__)
def fill_checkpoint_template(template_file='%s/check.tmpl/m5.cpt' % WORK_DIR,
                             output_file='%s/check.cpt/m5.cpt' % WORK_DIR, **kwargs):
    with open(template_file, 'r') as tf:
        template = Template(tf.read())
        with open(output_file, 'w') as f:
            f.write(template.render(**kwargs))
