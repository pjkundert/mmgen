#!/usr/bin/env python3
#
# mmgen = Multi-Mode GENerator, command-line Bitcoin cold storage solution
# Copyright (C)2013-2021 The MMGen Project <mmgen@tuta.io>
#
# Project source code repository: https://github.com/mmgen/mmgen
# Licensed according to the terms of GPL Version 3.  See LICENSE for details.

"""
ts_opts.py: options processing tests for the MMGen test.py test suite
"""

from ..include.common import *
from .ts_base import *

class TestSuiteOpts(TestSuiteBase):
	'options processing'
	networks = ('btc',)
	tmpdir_nums = [41]
	cmd_group = (
		('opt_helpscreen',       (41,"helpscreen output", [])),
		('opt_noargs',           (41,"invocation with no user options or arguments", [])),
		('opt_good',             (41,"good opts", [])),
		('opt_bad_infile',       (41,"bad infile parameter", [])),
		('opt_bad_outdir',       (41,"bad outdir parameter", [])),
		('opt_bad_incompatible', (41,"incompatible opts", [])),
		('opt_bad_autoset',      (41,"invalid autoset value", [])),
		('opt_show_diff',        (41,"show_common_opts_diff()", [])),
	)

	def spawn_prog(self,args):
		return self.spawn('test/misc/opts.py',args,cmd_dir='.')

	def check_vals(self,args,vals):
		t = self.spawn_prog(args)
		for k,v in vals:
			t.expect(rf'{k}:\s+{v}',regex=True)
		t.read()
		return t

	def do_run(self,args,expect,exit_val,regex=False):
		t = self.spawn_prog(args)
		t.expect(expect,regex=regex)
		t.read()
		t.req_exit_val = exit_val
		return t

	def opt_helpscreen(self):
		return self.do_run(
			['--help'],
			r'OPTS.PY: Opts test.*USAGE:\s+opts.py.*1:python-ecdsa 2:libsecp256k1 \(default: 2\).*'
			+ r'NOTES FOR THIS.*a note',
			0,
			regex=True )

	def opt_noargs(self):
		return self.check_vals(
				[],
				(
					('opt.foo',               'None'),         # added opt
					('opt.print_checksum',    'None'),         # sets 'quiet'
					('opt.quiet',             'False'),        # required_opts, incompatible_opts
					('opt.verbose',           'None'),         # required_opts, incompatible_opts
					('opt.fee_estimate_mode', 'conservative'), # autoset_opts
					('opt.passwd_file',       'None'),         # infile_opts - check_infile()
					('opt.outdir',            'None'),         # check_outdir()
					('opt.subseeds',          'None'),         # opt_sets_global
					('opt.key_generator',     '2'),            # global_sets_opt
					('g.subseeds',            'None'),
					('g.key_generator',       '2'),
				)
			)

	def opt_good(self):
		pf_base = 'testfile'
		pf = os.path.join(self.tmpdir,pf_base)
		self.write_to_tmpfile(pf_base,'')
		return self.check_vals(
				[
					'--print-checksum',
					'--fee-estimate-mode=E',
					'--passwd-file='+pf,
					'--outdir='+self.tmpdir,
					'--subseeds=200',
					f'--hidden-incog-input-params={pf},123',
				],
				(
					('opt.print_checksum',    'True'),
					('opt.quiet',             'True'), # set by print_checksum
					('opt.fee_estimate_mode', 'economical'),
					('opt.passwd_file',       pf),
					('opt.outdir',            self.tmpdir),
					('opt.subseeds',          '200'),
					('opt.hidden_incog_input_params', pf+',123'),
					('g.subseeds',            '200'),
				)
			)

	def opt_bad_infile(self):
		pf = os.path.join(self.tmpdir,'fubar')
		return self.do_run(['--passwd-file='+pf],'not found',1)

	def opt_bad_outdir(self):
		bo = self.tmpdir+'_fubar'
		return self.do_run(['--outdir='+bo],'not found',1)

	def opt_bad_incompatible(self):
		return self.do_run(['--label=Label','--keep-label'],'Conflicting options',1)

	def opt_bad_autoset(self):
		return self.do_run(['--fee-estimate-mode=Fubar'],'not unique substring',1)

	def opt_show_diff(self):
		return self.do_run(['show_common_opts_diff'],'common_opts_data',0)
