from argparse import ArgumentParser
import cmd
import gdb
from pprint import pprint
import readline

class GDBShell(cmd.Cmd):
    intro  = ('User-defined breakpoint reached. Type "help" for help from this '
              'shell, or "gdb help" for traditional help from gdb.')
    prompt = '(py-gdb) '
    #use_rawinput = False

    def __init__(self, engine, **kwargs):
        super().__init__(**kwargs)
        self.engine = engine
        self.previous = ''

    def do_gdb(self, arg):
        'Execute a gdb command.'
        try:
            gdb.execute(arg)
            self.previous = 'gdb ' + arg
        except gdb.error as e:
            print(e)
        return False

    def do_exit(self, arg):
        'Exit this shell and continue running gdb.'
        return True

    def do_quit(self, arg):
        'Alias for "exit".'
        return True

    def do_checkpoint(self, arg):
        'Take a checkpoint for gem5 simulation at this point.'
        self.engine._try_create_checkpoint(False)
        return False

    def precmd(self, line):
        'If a command is not a shell-specific command, redirect it to gdb.'
        commands = [x.replace('do_', '') for x in self.__dir__() if 'do_' in x ]
        line = line if len(line) else self.previous
        verb = line.split()[0] if len(line) else line
        if verb not in commands:
            if len(verb):
                self.previous = line
            line = 'gdb ' + line
        return line
