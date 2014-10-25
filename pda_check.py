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


class PDA(object):

    def __init__(self, dikt):
        self.name = dikt['name']

        self.input_alphabet = map(symb, dikt['input_alphabet'])

        self.states = dikt['states']
        self.start_state = dikt['start_state']
        self.accepting_states = dikt['accepting_states']

        self.stack_alphabet = map(symb, dikt['stack_alphabet'])
        self.start_stack = symb(dikt['start_stack'])
        self._check_stack_symbol(self.start_stack)

        trans = self.transition_relation = {}
        for state in self.states:
            trans[state] = {}
            for nstate in self.states:
                trans[state][nstate] = []

        transition_relation = dikt['transition_relation']
        for state, symbols in transition_relation.iteritems():
            self._check_state(state)

            for symbol, stack_symbols in symbols.iteritems():
                symbol = symb(symbol)
                self._check_symbol(symbol)

                for stack_symbol, state_stack_output in stack_symbols.iteritems():
                    stack_symbol = symb(stack_symbol)
                    self._check_stack_symbol(stack_symbol)

                    if len(state_stack_output) != 2:
                        raise MalformedDesc('{} is not a pair'.format(state_stack_output))
                    state_output, stack_output = state_stack_output
                    self._check_state(state_output)
                    stack_output = symb(stack_output)
                    if stack_output is not None:
                        stack_output = list(stack_output)
                        map(self._check_stack_symbol, stack_output)

                    trans[state][state_output].append((symbol, stack_symbol, stack_output))


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
        nchain = chain + [(state, input, stack)]

        if input == '' and state in self.accepting_states:
            return True, nchain


        nsymbol_map = self.transition_relation[state]
        for nstate, ntrans in nsymbol_map.iteritems():
            for nsymbol, ntop, nstack_top in ntrans:

                if nsymbol is None:
                    ninput = input[:]
                    if (state, stack) in visited:
                        continue
                    nvisited = visited + [(state, stack)]

                else:
                    if input == '':
                        continue

                    symbol = input[0]
                    if symbol not in self.input_alphabet:
                        raise MalformedInput(symbol)
                    ninput = input[1:]
                    nvisited = []

                    if symbol != nsymbol:
                        continue

                top = stack[0]
                nstack = (nstack_top or []) + stack[1:]

                if top != ntop:
                    continue

                ok, fchain = self._check_input(nstate, ninput, nstack, nchain, nvisited)
                if ok:
                    return ok, fchain

        return False, nchain

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
    parser = argparse.ArgumentParser(prog='pda_check', add_help=True)
    parser.add_argument('--timeout', '-t', default=1, help='max time in seconds of a single check', type=int)
    parser.add_argument('lang_file', nargs=1, help='file describing the language formatted in YAML', type=file)
    args = parser.parse_args()
    langs = list(yaml.load_all(args.lang_file[0]))
    maxtime = args.timeout

    print 'pda_check v%s -- (c) 2014 Jan Segre <jan@segre.in>' % VERSION
    print 'Give the input you want to check, you can do it multiple times:'

    langs = [PDA(lang['pda']) for lang in langs]
    while True:
        if not pretty_check(langs, maxtime):
            break
    print 'Bye!'


if __name__ == '__main__':
    main()
