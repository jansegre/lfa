#!/usr/bin/env python
# encoding: utf-8
#
# Copyright (C) 2014 Jan Segre <jan@segre.in>
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.
#
import sys
import signal
import argparse
import yaml

VERSION = '1.0.0'
_ignore_symbols = ['\n']


def symb(s):
    return unicode(s) if s is not None else None


def pretty_symb(s):
    return symb(s) or u'ɛ'


class MalformedDesc(Exception):
    pass


class MalformedInput(Exception):
    pass


class TimeoutError(Exception):
    pass


class TM(object):

    def __init__(self, dikt):
        self.name = dikt['name']

        self.input_alphabet = map(symb, dikt['input_alphabet'])

        self.states = dikt['states']
        self.start_state = dikt['start_state']
        self.accepting_states = dikt['accepting_states']

        self.stack_alphabet = map(symb, dikt['stack_alphabet'])
        self.start_stack = symb(dikt['start_stack'])
        self._check_stack_symbol(self.start_stack)

        #TODO[jansegre]: load definitions from dict

    def _check_state(self, state):
        if state not in self.states:
            raise MalformedDesc('{} is not a valid state ({} are valid)'.format(state, self.states))

    def _check_symbol(self, symbol):
        if symbol is None:
            return
        if symbol not in self.input_alphabet:
            raise MalformedDesc('{} is not a valid symbol ({} are valid)'.format(symbol, self.input_alphabet))

    def _check_stack_symbol(self, symbol):
        if symbol is None:
            return
        if symbol not in self.stack_alphabet:
            raise MalformedDesc('{} is not a valid stack symbol ({} are valid)'.format(symbol, self.stack_alphabet))

    def _check_input(self, state, input, stack, chain, visited=[]):

        #TODO[jansegre]: implement input validation

        # stub
        return False, []

    def check(self, input_string):
        """This is a depth algorithm to find a match on a string for a given pushdown automaton (PDA)."""
        return self._check_input(self.start_state, input_string, [self.start_stack], [])


# from: http://stackoverflow.com/questions/2281850/timeout-function-if-it-takes-too-long-to-finish
class timeout(object):
    def __init__(self, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message
    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)
    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)
    def __exit__(self, type, value, traceback):
        signal.alarm(0)


def pretty_chain(chain):
    chain = [(unicode(s), pretty_symb(i), pretty_symb(''.join(z))) for s, i, z in chain]
    li = max(len(i) for _, i, _ in chain)
    lz = max(len(z) for _, _, z in chain)
    return u' ⊢\n'.join(u'({}, {:>{}s}, {:>{}s})'.format(s, i, li, z, lz) for s, i, z in chain)


def pretty_check(langs, maxtime):
    try:
        print
        input = raw_input('> ')
        if input == '':
            return False
    except EOFError:
        print
        return False
    except KeyboardInterrupt:
        print
        return False

    for lang in langs:
        print '%s:' % lang.name
        try:
            with timeout(seconds=maxtime):
                ok, ch = lang.check(input)
                print 'ACCEPTED:\n%s' % pretty_chain(ch) if ok else 'REJECTED!'
        except MalformedInput as e:
            print 'SYMBOL {} REJECTED'.format(e.message)
        except TimeoutError:
            print 'TIMEDOUT!'
        print

    return True


def main():
    parser = argparse.ArgumentParser(prog='tm_check', add_help=True)
    parser.add_argument('--timeout', '-t', default=1, help='max time in seconds of a single check', type=int)
    parser.add_argument('lang_file', nargs=1, help='file describing the language formatted in YAML', type=file)
    args = parser.parse_args()
    langs = list(yaml.load_all(args.lang_file[0]))
    maxtime = args.timeout

    print 'tm_check v%s -- (c) 2014 Jan Segre <jan@segre.in>' % VERSION
    print 'Give the input you want to check, you can do it multiple times:'

    langs = [TM(lang['pda']) for lang in langs]
    while True:
        if not pretty_check(langs, maxtime):
            break
    print 'Bye!'


if __name__ == '__main__':
    main()
