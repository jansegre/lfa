#!/usr/bin/env python
# encoding: utf-8

import sys
import argparse
import yaml

_ignore_symbols = ['\n']


def check(nfae, string, state=None, chain='', visited=set()):
    """This is a depth algorithm to find a match on a string for a given nfae language."""

    # start with the initial state if not already started
    if state is None:
        state = nfae['initial']

    nchain = chain + state

    try:
        # walk through all ε-moves first
        if None in nfae['transitions'][state]:
            nnchain = '%s [] ' % nchain

            # and recurse into every states it moves to
            for nstate in nfae['transitions'][state][None]:

                # unless that state was visited before consuming a symbol
                # that way we have no infinite loops
                if nstate not in visited:

                    # remember to add the just visited state to the list
                    if check(nfae, string, nstate, nnchain, visited | {nstate}):
                        return True
    except KeyError:
        pass

    # when reaching the end of the input
    if string == '':

        # check if the current state is final
        if state in nfae['finals']:
            print nchain
            return True

        # otherwise it's a known fail
        else:
            #print nchain, 'reached end of input'
            return False

    # if everything reached this point there is a symbol to be processed
    # and there isn't a ε-move available
    symbol = string[0]
    nstring = string[1:]
    nchain = '%s [%s] ' % (nchain, symbol)

    # so we skip the ignored symbols
    if symbol in _ignore_symbols:
        return check(nfae, nstring, state, chain)

    # and fail when there is an unkown symbol
    elif symbol not in nfae['symbols']:
        print nchain, 'found symbol {} not in symbols {}'.format(symbol, nfae['symbols'])
        return False

    try:
        # otherwise test every state reachable from the current symbol
        for nstate in nfae['transitions'][state][symbol]:
            if check(nfae, nstring, nstate, nchain):
                return True

        # and if no match was found it's a dead end
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
