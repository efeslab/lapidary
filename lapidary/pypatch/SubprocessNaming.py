from subprocess import Popen, TimeoutExpired

def join(self, timeout):
    try:
        self.wait(timeout)
    except TimeoutExpired:
        pass

def is_alive(self):
    return self.returncode is None

Popen.join     = join
Popen.is_alive = is_alive