from argparse import ArgumentParser

def add_create_args(parser):
    from lapidary.tools import GDBProcess
    GDBProcess.add_args(parser)

    run = lambda args: GDBProcess.main(args)
    parser.set_defaults(fn=run)

def add_parser_args(parser):
    subparsers = parser.add_subparsers()

    create = subparsers.add_parser('create')
    add_create_args(create)

def main():
    parser = ArgumentParser()
    add_parser_args(parser)

    args = parser.parse_args()

    args.fn(args)

if __name__ == '__main__':
    main()