#!/usr/bin/env python3
#
# mmgen = Multi-Mode GENerator, command-line Bitcoin cold storage solution
# Copyright (C)2013-2020 The MMGen Project <mmgen@tuta.io>
#
# Project source code repository: https://github.com/mmgen/mmgen
# Licensed according to the terms of GPL Version 3.  See LICENSE for details.

"""
input.py: Shared input routines for the test.py test suite
"""

import os,time
from .common import randbool

def stealth_mnemonic_entry(t,mne,mn,entry_mode,pad_entry=False):

	def pad_mnemonic(mn,ss_len):
		def get_pad_chars(n):
			ret = ''
			for i in range(n):
				m = int.from_bytes(os.urandom(1),'big') % 32
				ret += r'123579!@#$%^&*()_+-=[]{}"?/,.<>|'[m]
			return ret
		ret = []
		for w in mn:
			if entry_mode == 'short':
				w = w[:ss_len]
				if len(w) < ss_len:
					npc = 3
					w = w[0] + get_pad_chars(npc) + w[1:]
					if pad_entry:
						w += '%' * (1 + mne.em.pad_max - npc)
					else:
						w += '\n'
				else:
					w = get_pad_chars(1) + w[0] + get_pad_chars(1) + w[1:]
			elif len(w) > (3,5)[ss_len==12]:
				w = w + '\n'
			else:
				w = (
					get_pad_chars(2 if randbool() and entry_mode != 'short' else 0)
					+ w[0] + get_pad_chars(2) + w[1:]
					+ get_pad_chars(9) )
				w = w[:ss_len+1]
			ret.append(w)
		return ret

	if entry_mode == 'fixed':
		mn = ['bkr'] + mn[:5] + ['nfb'] + mn[5:]
		ssl = mne.uniq_ss_len
		mn = [w[:ssl] if len(w) >= ssl else (w[0] + 'z\b{}'.format('#'*(ssl-len(w))) + w[1:]) for w in mn]
	elif entry_mode in ('full','short'):
		mn = ['fzr'] + mn[:5] + ['grd','grdbxm'] + mn[5:]
		mn = pad_mnemonic(mn,mne.em.ss_len)
		mn[10] = '@#$%*##' + mn[10]

	wnum = 1
	p_ok,p_err = mne.word_prompt
	for w in mn:
		ret = t.expect((p_ok.format(wnum),p_err.format(wnum-1)))
		if ret == 0:
			wnum += 1
		for j in range(len(w)):
			t.send(w[j])
			time.sleep(0.005)

def user_dieroll_entry(t,data):
	for s in data:
		t.expect(r'Enter die roll #.+: ',s,regex=True)
		time.sleep(0.005)
