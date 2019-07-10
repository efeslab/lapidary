from lapidary.tools import LapidaryTools

from argparse import ArgumentParser

def main():
    parser = ArgumentParser(prog='lapidary')
    tools = LapidaryTools(parser)

    args = tools.parse_args()

    args.fn(args)

if __name__ == '__main__':
    main()