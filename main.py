#! /usr/bin/env python3

import argparse
import commands
import sys
import traceback


def parse_args(args=None):
    p = argparse.ArgumentParser(description='''Synchronize directory replicas
            using version vectors.''')
    subparsers = p.add_subparsers(dest='command', required=True)

    init_p = subparsers.add_parser('init', help='''Initialize an
            empty replica in the current directory''')
    init_p.add_argument('ID', help='unique ID of the new replica')
    init_p.set_defaults(func=lambda args: commands.init_replica(args.ID, '.'))

    sync_p = subparsers.add_parser('sync', help='''Synchronize the replica
            in the current directory with another replica''')
    sync_p.add_argument('path', help='path/to/another/replica')
    sync_p.set_defaults(func=lambda args: commands.sync('.', args.path))

    parsed_args = p.parse_args(args)
    parsed_args.func(parsed_args)


def main():
    parse_args()


if __name__ == '__main__':
    main()
