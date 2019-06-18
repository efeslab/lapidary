from enum import Enum

# https://stackoverflow.com/a/11781721
def gettype(name):
    from collections import deque
    # q is short for "queue", here
    q = deque([object])
    while q:
        t = q.popleft()
        if t.__name__ == name:
            return t

        try:
            # Keep looking!
            q.extend(t.__subclasses__())
        except TypeError:
            # type.__subclasses__ needs an argument, for whatever reason.
            if t is type:
                continue
            else:
                raise
    else:
        raise ValueError('No such type: %r' % name)