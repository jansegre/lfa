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
            print nchain, 'reached end of input'
            return False

    symbol = string[0]
    nstring = string[1:]
    nchain = '%s [%s] ' % (nchain, symbol)

    if symbol in _ignore_symbols:
        return check(nfae, nstring, state, chain)

    elif symbol not in nfae['symbols']:
        print nchain, 'found symbol {} not in symbols {}'.format(symbol, nfae['symbols'])
        return False

    try:
        for nstate in nfae['transitions'][state][symbol]:
            if check(nfae, nstring, nstate, nchain):
                return True
        return False

    except KeyError:
        return False


def pretty_check(langs):
    try:
        string = raw_input('> ')
        if string == '':
            return False
    except EOFError:
        print
        return False
    except KeyboardInterrupt:
        print
        return False

    for lang in langs:
        nfae = lang['nfae']
        print
        print '%s:' % nfae['name']
        print 'OK!' if check(nfae, string) else 'FAIL!'
        print

    return True


def main():
    parser = argparse.ArgumentParser(prog='nfae_check', add_help=True)
    parser.add_argument('lang_file', nargs=1, help='file describing the language formatted in YAML', type=file)
    args = parser.parse_args()
    langs = list(yaml.load_all(args.lang_file[0]))

    while True:
        if not pretty_check(langs):
            break
    print 'Bye!'


if __name__ == '__main__':
    main()
