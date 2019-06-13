#! /usr/bin/env python3

if __name__ == '__main__':
    from pathlib import Path
    import sys

    if len(sys.argv) < 2:
        raise Exception('Please provide a directory!')
    
    sim_res = Path(sys.argv[1])
    if not sim_res.exists():
        raise Exception('{} does not exists!'.format(sys.argv[1]))

    for d in sim_res.iterdir():
        if d.is_dir():
            stats = d / 'stats.txt'
            if stats.exists():
                print(str(stats))
                stats.unlink()
    
else:
    raise Exception('Not a module!')
