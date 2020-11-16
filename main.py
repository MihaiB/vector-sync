#! /usr/bin/env python3

import argparse
import commands
import sys
import traceback


def parseArgs(args=None):
    parser = argparse.ArgumentParser(description='''Synchronize directory
        replicas using version vectors.''')
    subparsers = parser.add_subparsers(dest='command')
    subparsers.required = True

    initP = subparsers.add_parser('init', help='''Initialize a new replica
        in the current directory''')
    initP.add_argument('ID', help='ID for the new Replica')
    initP.set_defaults(func=lambda args: commands.init(args.ID))

    syncP = subparsers.add_parser('sync', help='''Synchronize with another
        replica''')
    syncP.add_argument('path', help='path/to/another replica')
    syncP.set_defaults(func=lambda args: commands.sync(args.path))

    parsedArgs = parser.parse_args(args)
    parsedArgs.func(parsedArgs)


def main():
    try:
        parseArgs()
    except SystemExit:
        raise
    except:
        traceback.print_exception(*sys.exc_info()[:2], None)
        sys.exit(1)


if __name__ == '__main__':
    main()
