#!/usr/bin/env python
# encoding: utf-8
#
# Copyright (C) 2014 Jan Segre <jan@segre.in>
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.
#
import signal
import argparse
import yaml
from abc import ABCMeta, abstractmethod

VERSION = '1.0.0'
_ignore_symbols = ['\n']


# UTILS


def symb(s):
    return unicode(s) if s is not None else None


def pretty_symb(s):
    return symb(s) or u'ɛ'


def pretty_list(l):
    return u'[{}]'.format(u', '.join(u'%s' % i for i in l))


class Malformed(Exception):
    pass


class MalformedDesc(Malformed):
    pass


class MalformedInput(Malformed):
    pass


class TimeoutError(Exception):
    pass


def machine(dikt):
    if 'dtm' in dikt:
        return DTM(dikt['dtm'])
    elif 'ntm' in dikt:
        return NTM(dikt['ntm'])
    elif 'pda' in dikt:
        return PDA(dikt['pda'])


class growing_list(list):
    # based on http://stackoverflow.com/a/4544699/947511
    def __init__(self, *args, **kwargs):
        self.none = kwargs.pop('none', None)
        self.double = kwargs.pop('double', False)
        super(growing_list, self).__init__(*args, **kwargs)
        if self.double:
            self._dark_side = growing_list(none=self.none, double=False)

    def __setitem__(self, index, value):
        if self.double and index < 0:
            return self._dark_side.__setitem__(-index - 1, value)
        if index >= len(self):
            self.extend([self.none]*(index + 1 - len(self)))
        list.__setitem__(self, index, value)

    def __getitem__(self, index):
        if self.double and index < 0:
            return self._dark_side.__getitem__(-index - 1)
        if index >= len(self):
            return self.none
        return list.__getitem__(self, index)


class PDA(object):

    def __init__(self, dikt):
        self.input_alphabet = map(symb, dikt['input_alphabet'])

        self.states = dikt['states']
        self.start_state = dikt['start_state']
        self.final_states = dikt['final_states']

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

        if input == '' and state in self.final_states:
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

    def pretty_chain(self, chain):
        chain = [(unicode(s), pretty_symb(i), pretty_symb(''.join(z))) for s, i, z in chain]
        li = max(len(i) for _, i, _ in chain)
        lz = max(len(z) for _, _, z in chain)
        return u' ⊢\n'.join(u'({}, {:>{}s}, {:>{}s})'.format(s, i, li, z, lz) for s, i, z in chain)


class TM:
    __metaclass__ = ABCMeta

    left_markers = u'LEle<←'
    right_markers = u'RDrd>→'

    def __init__(self, dikt):
        # Q is a finite, non-empty set of states
        self.states = dikt['states']

        # Γ is a finite, non-empty set of tape alphabet symbols
        self.tape_alphabet = map(symb, dikt['tape_alphabet'])

        # b ∈ Γ is the blank symbol (the only symbol allowed to occur on the tape
        # infinitely often at any step during the computation)
        self.blank_symbol = symb(dikt['blank_symbol'])

        # ∑ ⊆ Γ ∖ {b} is the set of input symbols
        self.input_alphabet = map(symb, dikt['input_alphabet'])

        # q₀ ∈ Q is the initial state
        self.start_state = dikt['start_state']
        self._check_state(self.start_state)

        # F ⊆ Q is the set of final or accepting states.
        self.final_states = dikt['final_states']
        map(self._check_state, self.final_states)

        # wether the tape is infinite on both sides [optional, defaults to false]
        self.double_sided = dikt.get('double_sided', False)

        # ◘ start marker [optional: None or supress to disable it]
        self.start_marker = symb(dikt.get('start_marker'))
        self._check_tape_symbol(self.start_marker)
        self.has_start_marker = self.start_marker is not None

    def _init_tape(self, input):
        if self.has_start_marker:
            tape_list = [self.start_marker] + list(unicode(input))
            return growing_list(tape_list, none=self.blank_symbol, double=self.double_sided)
        return growing_list(unicode(input), none=self.blank_symbol, double=self.double_sided)

    def _check_state(self, state):
        if state not in self.states:
            raise MalformedDesc(u'{} is not a valid state ({} are valid)'.format(state, pretty_list(self.states)))

    def _check_symbol(self, symbol):
        if symbol is None:
            return
        if symbol not in self.input_alphabet:
            raise MalformedDesc(u'{} is not a valid symbol ({} are valid)'.format(symbol, pretty_list(self.input_alphabet)))

    def _check_tape_symbol(self, symbol):
        if symbol is None:
            return
        if symbol not in self.tape_alphabet:
            raise MalformedDesc(u'{} is not a valid tape symbol ({} are valid)'.format(symbol, pretty_list(self.tape_alphabet)))

    def _check_shift(self, shift):
        if shift not in self.left_markers + self.right_markers:
            raise MalformedDesc('{} is not a valid shift (\'L\' and \'R\' are valid)'.format(shift))

    def _conv_shift(self, shift):
        if shift in self.left_markers:
            return -1
        elif shift in self.right_markers:
            return 1

    @abstractmethod
    def check(self, input_string):
        return False, []

    def pretty_chain(self, chain):
        chain = [(unicode(s), str(i), pretty_symb(''.join(z))) for s, i, z in chain]
        li = max(len(i) for _, i, _ in chain)
        lz = max(len(z) for _, _, z in chain)
        return u'\n'.join(u'{} | {:<{}s} | {:<{}s}'.format(s, i, li, z, lz) for s, i, z in chain)


class DTM(TM):
    def __init__(self, dikt):
        super(DTM, self).__init__(dikt)
        trans_map = dikt['transition_function']
        t = self.transition_function = {}
        for state, input_map in trans_map.iteritems():
            self._check_state(state)
            for symbol, output in input_map.iteritems():
                symbol = symb(symbol)
                self._check_tape_symbol(symbol)
                nsymbol, shift, nstate = tuple(output)
                nsymbol = symb(nsymbol)
                self._check_tape_symbol(nsymbol)
                self._check_shift(shift)
                self._check_state(nstate)
                t[(state, symbol)] = nsymbol, self._conv_shift(shift), nstate

    def _transition(self, state, symbol):
        return self.transition_function.get((state, symbol))

    def check(self, input_string):
        state = self.start_state
        tape = self._init_tape(input_string)
        pos = 0

        chain = []
        while True:
            chain.append((state, pos, tape[:]))
            if state in self.final_states:
                return True, chain
            symbol = tape[pos]
            if symbol not in self.tape_alphabet:
                break
            trans = self._transition(state, symbol)
            if trans is None:
                break
            wsymbol, shift, state = trans
            tape[pos] = wsymbol
            pos += shift
            if pos < 0:
                break

        return False, chain


class NTM(TM):
    #TODO[jansegre]: implement non-deterministic turing machine
    pass


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


def pretty_check(langs, maxtime):
    try:
        print
        input = raw_input('> ')
        #if input == '':
        #    return False
    except EOFError:
        print
        return False
    except KeyboardInterrupt:
        print
        return False

    for name, lang in langs.iteritems():
        print '%s' % name,
        try:
            with timeout(seconds=maxtime):
                ok, ch = lang.check(input)
                chain = lang.pretty_chain(ch)
                print u'ACCEPTED:\n%s ✓' % chain if ok else u'REJECTED!\n%s ✗' % chain
        except MalformedInput as e:
            print 'SYMBOL {} REJECTED'.format(e.message)
        except TimeoutError:
            print 'TIMEDOUT!'
        #print

    return True


def main():
    parser = argparse.ArgumentParser(prog='tm_check', add_help=True)
    parser.add_argument('--timeout', '-t', default=3, help='max time in seconds of a single check', type=int)
    parser.add_argument('lang_file', nargs=1, help='file describing the language formatted in YAML', type=file)
    parser.add_argument('lang', nargs=1, help='name of the lang inside lang_file to load')
    args = parser.parse_args()
    langs = list(yaml.load_all(args.lang_file[0]))
    langk = args.lang[0]
    maxtime = args.timeout

    print 'tm_check v%s -- (c) 2014 Jan Segre <jan@segre.in>' % VERSION
    print 'Give the input you want to check, you can do it multiple times:'

    try:
        langs = dict((lang['name'], machine(lang)) for lang in langs if lang)
    except Malformed as e:
        print unicode(e)
        return

    if langk not in langs:
        print 'lang not found'
        return
    langs = {langk: langs[langk]}

    while True:
        if not pretty_check(langs, maxtime):
            break
    print 'Bye!'


if __name__ == '__main__':
    main()
