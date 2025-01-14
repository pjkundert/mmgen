#!/usr/bin/env python3

from .tests_header import repo_root
from mmgen.common import *

action = g.prog_name.split('-')[0]

opts_data = {
	'sets': [('debug',True,'verbose',True)],
	'text': {
		'desc': f'{action.capitalize()} coin daemons for the MMGen test suite',
		'usage':'[opts] <network IDs>',
		'options': """
-h, --help           Print this help message
--, --longhelp       Print help message for long options (common options)
-D, --debug          Produce debugging output (implies --verbose)
-d, --datadir=       Override the default datadir
-n, --no-daemonize   Don't fork daemon to background
-p, --port-shift=    Shift the RPC port by this number
-s, --get-state      Get the state of the daemon(s) and exit
-t, --testing        Testing mode.  Print commands but don't execute them
-q, --quiet          Produce quieter output
-u, --usermode       Run the daemon in user (non test-suite) mode
-v, --verbose        Produce more verbose output
-W, --no-wait        Don't wait for daemons to change state before exiting
""",
	'notes': """
Valid network IDs: {nid}, all, or no_xmr
"""
	},
	'code': {
		'options': lambda s: s.format(a=action.capitalize(),pn=g.prog_name),
		'notes': lambda s,help_notes: s.format(nid=help_notes('coin_daemon_network_ids'))
	}
}

cmd_args = opts.init(opts_data)

from mmgen.daemon import *

def run(network_id=None,proto=None,daemon_id=None):
	d = CoinDaemon(
		network_id = network_id,
		proto      = proto,
		test_suite = not opt.usermode,
		opts       = ['no_daemonize'] if opt.no_daemonize else None,
		port_shift = int(opt.port_shift or 0),
		datadir    = opt.datadir,
		daemon_id  = daemon_id )
	d.debug = d.debug or opt.debug
	d.wait = not opt.no_wait
	if opt.get_state:
		print(d.state_msg())
	elif opt.testing:
		for cmd in d.start_cmds if action == 'start' else [d.stop_cmd]:
			print(' '.join(cmd))
	else:
		if action == 'stop' and hasattr(d,'rpc'):
			run_session(d.rpc.stop_daemon(quiet=opt.quiet))
		else:
			d.cmd(action,quiet=opt.quiet)

if 'all' in cmd_args or 'no_xmr' in cmd_args:
	if len(cmd_args) != 1:
		die(1,"'all' or 'no_xmr' must be the sole argument")
	from mmgen.protocol import init_proto
	for coin,data in CoinDaemon.coins.items():
		if coin == 'XMR' and cmd_args[0] == 'no_xmr':
			continue
		for daemon_id in data.daemon_ids:
			for network in globals()[daemon_id+'_daemon'].networks:
				run(proto=init_proto(coin=coin,network=network),daemon_id=daemon_id)
else:
	ids = cmd_args
	network_ids = CoinDaemon.get_network_ids()
	if not ids:
		opts.usage()
	for i in ids:
		if i not in network_ids:
			die(1,f'{i!r}: invalid network ID')
	for network_id in ids:
		run(network_id=network_id.lower())
