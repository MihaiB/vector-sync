#! /usr/bin/env python3

import argparse
import commands
import sys


def parse_args(args):
    p = argparse.ArgumentParser(description='''Synchronize file trees
            using version vectors.''')
    subparsers = p.add_subparsers(dest='command', required=True)

    init_p = subparsers.add_parser('init', help='''Initialize metadata
            in the current directory.''')
    init_p.add_argument('id', help='The unique ID (name) of this file tree.')
    init_p.set_defaults(func=commands.init)

    sync_p = subparsers.add_parser('sync', help='''Synchronize
            the current directory with another file tree.''')
    sync_p.add_argument('path', help='Path to the other file tree.')
    sync_p.set_defaults(func=commands.sync)

    return p.parse_args(args)


def main():
    args = parse_args(sys.argv[1:])
    args.func(args)


if __name__ == '__main__':
    main()
