#!/usr/bin/env python
# encoding: utf-8

import sys
import argparse
import yaml

_ignore_symbols = ['\n']


def check(nfae, string, state=None, chain=''):
    if state is None:
        state = nfae['initial']

    nchain = chain + state

    try:
        if None in nfae['transitions'][state]:
            nnchain = '%s [] ' % nchain
            for nstate in nfae['transitions'][state][None]:
                if check(nfae, string, nstate, nnchain):
                    return True
    except KeyError:
        pass

    if string == '':
        if state in nfae['finals']:
            print nchain
            return True
        else:
            return False

    symbol = string[0]
    nstring = string[1:]
    nchain = '%s [%s] ' % (nchain, symbol)

    if symbol in _ignore_symbols:
        return check(nfae, nstring, state, chain)

    elif symbol not in nfae['symbols']:
        return False

    try:
        for nstate in nfae['transitions'][state][symbol]:
            if check(nfae, nstring, nstate, nchain):
                return True
        return False

    except KeyError:
        return False


def main():
    parser = argparse.ArgumentParser(prog='nfae_check', add_help=True)
    parser.add_argument('-f', '--lang-file', required=True, help='file describing the language formatted in YAML', type=file)
    args = parser.parse_args()

    string = sys.stdin.read()
    for entry in yaml.load_all(args.lang_file):
        nfae = entry['nfae']
        print '%s:' % nfae['name']
        print 'OK!' if check(nfae, string) else 'FAIL!'


if __name__ == '__main__':
    main()
