#!/usr/bin/env python3

# Demonstrates use of the MMGen asyncio/aiohttp JSON-RPC interface
# https://github.com/mmgen/mmgen

import time
from decimal import Decimal
from mmgen.common import *

opts.init({
	'text': {
		'desc': 'Estimate date of next block subsidy halving',
		'usage':'[opts]',
		'options': """
-h, --help          Print this help message
--, --longhelp      Print help message for long options (common options)
-s, --sample-size=N Specify sample block range for block discovery time
                    estimate
""",
	'notes': """
Requires a running coin daemon
Specify coin with --coin=btc (default)/--coin=bch/--coin=ltc
If necessary, invoke with --rpc-host/--rpc-port/--rpc-user/--rpc-password
Specify aiohttp backend with --rpc-backend=aiohttp (Linux only)

A more full-featured version of this program can be found in the
mmgen-node-tools repository.
"""
	}
})

def date(t):
	return '{}-{:02}-{:02} {:02}:{:02}:{:02}'.format(*time.gmtime(t)[:6])

def dhms(t):
	t,neg = (-t,'-') if t < 0 else (t,' ')
	return f'{neg}{t//60//60//24} days, {t//60//60%24:02}:{t//60%60:02}:{t%60:02} h/m/s'

def time_diff_warning(t_diff):
	if abs(t_diff) > 60*60:
		print('Warning: block tip time is {} {} clock time!'.format(
			dhms(abs(t_diff)),
			('behind','ahead of')[t_diff<0]))

async def main():

	from mmgen.protocol import init_proto_from_opts
	proto = init_proto_from_opts()

	from mmgen.rpc import rpc_init
	c = await rpc_init(proto)

	tip = await c.call('getblockcount')
	assert tip > 1, 'block tip must be > 1'
	remaining = proto.halving_interval - tip % proto.halving_interval
	sample_size = int(opt.sample_size) if opt.sample_size else min(tip-1,max(remaining,144))

	# aiohttp backend will perform these two calls concurrently:
	cur,old = await c.gathered_call('getblockstats',((tip,),(tip - sample_size,)))

	clock_time = int(time.time())
	time_diff_warning(clock_time - cur['time'])

	bdr = (cur['time'] - old['time']) / sample_size
	t_rem = remaining * int(bdr)
	sub = cur['subsidy'] * proto.coin_amt.satoshi

	print(
		f'Current block:      {tip}\n'
		f'Next halving block: {tip + remaining}\n'
		f'Blocks until halving: {remaining}\n'
		f'Current block subsidy: {str(sub).rstrip("0")} {proto.coin}\n'
		f'Current block discovery rate (over last {sample_size} blocks): {bdr/60:0.1f} minutes\n'
		f'Current clock time (UTC): {date(clock_time)}\n'
		f'Est. halving date (UTC):  {date(cur["time"] + t_rem)}\n'
		f'Est. time until halving: {dhms(cur["time"] + t_rem - clock_time)}\n'
	)

run_session(main())
