from lapidary.tools import LapidaryTools

def main():
    parser = ArgumentParser()
    tools = LapidaryTools(parser)

    args = tools.parse_args()

    args.fn(args)

if __name__ == '__main__':
    main()