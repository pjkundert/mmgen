#!/usr/bin/env python
#
# mmgen = Multi-Mode GENerator, command-line Bitcoin cold storage solution
# Copyright (C)2013-2017 Philemon <mmgen-py@yandex.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
tx.py:  Transaction routines for the MMGen suite
"""

import sys,os
from stat import *
from binascii import unhexlify
from mmgen.common import *
from mmgen.obj import *

def segwit_is_active(exit_on_error=False):
	d = g.rpch.getblockchaininfo()
	if d['chain'] == 'regtest':
		return True
	if 'segwit' in d['bip9_softforks'] and d['bip9_softforks']['segwit']['status'] == 'active':
		return True
	if g.skip_segwit_active_check:
		return True
	if exit_on_error:
		die(2,'Segwit not active on this chain.  Exiting')
	else:
		return False

def bytes2int(hex_bytes):
	r = hexlify(unhexlify(hex_bytes)[::-1])
	if r[0] in '89abcdef':
		die(3,"{}: Negative values not permitted in transaction!".format(hex_bytes))
	return int(r,16)

def bytes2coin_amt(hex_bytes):
	return g.proto.coin_amt(bytes2int(hex_bytes) * g.proto.coin_amt.min_coin_unit)

def scriptPubKey2addr(s):
	if len(s) == 50 and s[:6] == '76a914' and s[-4:] == '88ac': addr_hex,p2sh = s[6:-4],False
	elif len(s) == 46 and s[:4] == 'a914' and s[-2:] == '87':   addr_hex,p2sh = s[4:-2],True
	else: raise NotImplementedError,'Unknown scriptPubKey'
	return g.proto.hexaddr2addr(addr_hex,p2sh)

from collections import OrderedDict
class DeserializedTX(OrderedDict,MMGenObject): # need to add MMGen types
	def __init__(self,txhex):
		tx = list(unhexlify(txhex))
		tx_copy = tx[:]
		d = { 'raw_tx':'' }

		def hshift(l,n,reverse=False,skip=False):
			ret = l[:n]
			if not skip: d['raw_tx'] += ''.join(ret)
			del l[:n]
			return hexlify(''.join(ret[::-1] if reverse else ret))

		# https://bitcoin.org/en/developer-reference#compactsize-unsigned-integers
		# For example, the number 515 is encoded as 0xfd0302.
		def readVInt(l,skip=False,sub_null=False):
			s = int(hexlify(l[0]),16)
			bytes_len = 1 if s < 0xfd else 2 if s == 0xfd else 4 if s == 0xfe else 8
			if bytes_len != 1: del l[0]
			ret = int(hexlify(''.join(l[:bytes_len][::-1])),16)
			if sub_null: d['raw_tx'] += '\0'
			elif not skip: d['raw_tx'] += ''.join(l[:bytes_len])
			del l[:bytes_len]
			return ret

		d['version'] = bytes2int(hshift(tx,4))
		has_witness = (False,True)[hexlify(tx[0])=='00']
		if has_witness:
			u = hshift(tx,2,skip=True)[2:]
			if u != '01':
				die(2,"'{}': Illegal value for flag in transaction!".format(u))
			del tx_copy[-len(tx)-2:-len(tx)]

		d['num_txins'] = readVInt(tx)
		d['txins'] = MMGenList([OrderedDict((
			('txid',      hshift(tx,32,reverse=True)),
			('vout',      bytes2int(hshift(tx,4))),
			('scriptSig', hshift(tx,readVInt(tx,sub_null=True),skip=True)),
			('nSeq',      hshift(tx,4,reverse=True))
		)) for i in range(d['num_txins'])])

		d['num_txouts'] = readVInt(tx)
		d['txouts'] = MMGenList([OrderedDict((
			('amount',       bytes2coin_amt(hshift(tx,8))),
			('scriptPubKey', hshift(tx,readVInt(tx)))
		)) for i in range(d['num_txouts'])])

		for o in d['txouts']:
			o['address'] = scriptPubKey2addr(o['scriptPubKey'])

		d['witness_size'] = 0
		if has_witness:
			# https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki
			# A non-witness program (defined hereinafter) txin MUST be associated with an empty
			# witness field, represented by a 0x00.
			del tx_copy[-len(tx):-4]
			wd,tx = tx[:-4],tx[-4:]
			d['witness_size'] = len(wd) + 2 # add marker and flag
			for i in range(len(d['txins'])):
				if hexlify(wd[0]) == '00':
					hshift(wd,1,skip=True)
					continue
				d['txins'][i]['witness'] = [
					hshift(wd,readVInt(wd,skip=True),skip=True) for item in range(readVInt(wd,skip=True))
				]
			if wd:
				die(3,'More witness data than inputs with witnesses!')

		d['lock_time'] = bytes2int(hshift(tx,4))
		d['txid'] = hexlify(sha256(sha256(''.join(tx_copy)).digest()).digest()[::-1])
		d['unsigned_hex'] = hexlify(d['raw_tx'])
		del d['raw_tx']

		keys = 'txid','version','lock_time','witness_size','num_txins','txins','num_txouts','txouts','unsigned_hex'
		return OrderedDict.__init__(self, ((k,d[k]) for k in keys))

txio_attrs = {
	'vout':  MMGenListItemAttr('vout',int,typeconv=False),
	'amt':   MMGenImmutableAttr('amt',g.proto.coin_amt,typeconv=False), # require amt to be of proper type
	'label': MMGenListItemAttr('label','TwComment',reassign_ok=True),
	'mmid':  MMGenListItemAttr('mmid','MMGenID'),
	'addr':  MMGenImmutableAttr('addr','CoinAddr'),
	'confs': MMGenListItemAttr('confs',int,typeconv=True), # long confs exist in the wild, so convert
	'txid':  MMGenListItemAttr('txid','CoinTxID'),
	'have_wif': MMGenListItemAttr('have_wif',bool,typeconv=False,delete_ok=True)
}

class MMGenTX(MMGenObject):
	ext      = 'rawtx'
	raw_ext  = 'rawtx'
	sig_ext  = 'sigtx'
	txid_ext = 'txid'
	desc     = 'transaction'

	class MMGenTxInput(MMGenListItem):
		for k in txio_attrs: locals()[k] = txio_attrs[k] # in lieu of inheritance
		scriptPubKey = MMGenListItemAttr('scriptPubKey','HexStr')
		sequence = MMGenListItemAttr('sequence',(int,long)[g.platform=='win'],typeconv=False)

	class MMGenTxOutput(MMGenListItem):
		for k in txio_attrs: locals()[k] = txio_attrs[k]
		is_chg = MMGenListItemAttr('is_chg',bool,typeconv=False)

	class MMGenTxInputList(list,MMGenObject): pass
	class MMGenTxOutputList(list,MMGenObject): pass

	def __init__(self,filename=None,md_only=False):
		self.inputs      = self.MMGenTxInputList()
		self.outputs     = self.MMGenTxOutputList()
		self.send_amt    = g.proto.coin_amt('0')  # total amt minus change
		self.hex         = ''           # raw serialized hex transaction
		self.label       = MMGenTXLabel('')
		self.txid        = ''
		self.coin_txid    = ''
		self.timestamp   = ''
		self.chksum      = ''
		self.fmt_data    = ''
		self.blockcount  = 0
		self.chain       = None
		self.coin        = None

		if filename:
			self.parse_tx_file(filename,md_only=md_only)
			if md_only: return
			self.check_sigs() # marks the tx as signed

		# repeat with sign and send, because coin daemon could be restarted
		self.die_if_incorrect_chain()

	def die_if_incorrect_chain(self):
		if self.chain and g.chain and self.chain != g.chain:
			die(2,'Transaction is for {}, but current chain is {}!'.format(self.chain,g.chain))

	def add_output(self,coinaddr,amt,is_chg=None):
		self.outputs.append(self.MMGenTxOutput(addr=coinaddr,amt=amt,is_chg=is_chg))

	def get_chg_output_idx(self):
		for i in range(len(self.outputs)):
			if self.outputs[i].is_chg == True:
				return i
		return None

	def update_output_amt(self,idx,amt):
		o = self.outputs[idx].__dict__
		o['amt'] = amt
		self.outputs[idx] = self.MMGenTxOutput(**o)

	def del_output(self,idx):
		self.outputs.pop(idx)

	def sum_outputs(self,exclude=None):
		olist = self.outputs if exclude == None else \
			self.outputs[:exclude] + self.outputs[exclude+1:]
		return g.proto.coin_amt(sum(e.amt for e in olist))

	def add_mmaddrs_to_outputs(self,ad_w,ad_f):
		a = [e.addr for e in self.outputs]
		d = ad_w.make_reverse_dict(a)
		d.update(ad_f.make_reverse_dict(a))
		for e in self.outputs:
			if e.addr and e.addr in d:
				e.mmid,f = d[e.addr]
				if f: e.label = f

	def check_dup_addrs(self,io_str):
		assert io_str in ('inputs','outputs')
		io = getattr(self,io_str)
		for k in ('mmid','addr'):
			old_attr = None
			for attr in sorted(getattr(e,k) for e in io):
				if attr != None and attr == old_attr:
					die(2,'{}: duplicate address in transaction {}'.format(attr,io_str))
				old_attr = attr

	def create_raw(self):
		i = [{'txid':e.txid,'vout':e.vout} for e in self.inputs]
		if self.inputs[0].sequence:
			i[0]['sequence'] = self.inputs[0].sequence
		o = dict([(e.addr,e.amt) for e in self.outputs])
		self.hex = g.rpch.createrawtransaction(i,o)
		self.txid = MMGenTxID(make_chksum_6(unhexlify(self.hex)).upper())

	# returns true if comment added or changed
	def add_comment(self,infile=None):
		if infile:
			self.label = MMGenTXLabel(get_data_from_file(infile,'transaction comment'))
		else: # get comment from user, or edit existing comment
			m = ('Add a comment to transaction?','Edit transaction comment?')[bool(self.label)]
			if keypress_confirm(m,default_yes=False):
				while True:
					s = MMGenTXLabel(my_raw_input('Comment: ',insert_txt=self.label))
					if s:
						lbl_save = self.label
						self.label = s
						return (True,False)[lbl_save == self.label]
					else:
						msg('Invalid comment')
			return False

	def edit_comment(self):
		return self.add_comment(self)

	def has_segwit_inputs(self):
		return any(i.mmid and i.mmid.mmtype == 'S' for i in self.inputs)

	# https://bitcoin.stackexchange.com/questions/1195/how-to-calculate-transaction-size-before-sending
	# 180: uncompressed, 148: compressed
	def estimate_size_old(self):
		if not self.inputs or not self.outputs: return None
		return len(self.inputs)*180 + len(self.outputs)*34 + 10

	# https://bitcoincore.org/en/segwit_wallet_dev/
	# vsize: 3 times of the size with original serialization, plus the size with new
	# serialization, divide the result by 4 and round up to the next integer.

	# TODO: results differ slightly from actual transaction size
	def estimate_vsize(self):
		if not self.inputs or not self.outputs: return None

		sig_size = 72 # sig in DER format
		pubkey_size = { 'compressed':33, 'uncompressed':65 }
		outpoint_size = 36 # txid + vout

		def get_inputs_size():
			segwit_isize = outpoint_size + 1 + 23 + 4 # (txid,vout) [scriptSig size] scriptSig nSeq # = 64
			# txid vout [scriptSig size] scriptSig (<sig> <pubkey>) nSeq
			legacy_isize = outpoint_size + 1 + 2 + sig_size + pubkey_size['uncompressed'] + 4 # = 180
			compressed_isize = outpoint_size + 1 + 2 + sig_size + pubkey_size['compressed'] + 4 # = 148
			ret = sum((legacy_isize,segwit_isize)[i.mmid.mmtype=='S'] for i in self.inputs if i.mmid)
			# assume all non-MMGen pubkeys are compressed (we have no way of knowing
			# until we see the key).  TODO: add user option to specify this?
			return ret + sum(compressed_isize for i in self.inputs if not i.mmid)

		def get_outputs_size():
			return sum((34,32)[o.addr.addr_fmt=='p2sh'] for o in self.outputs)

		# https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki
		# The witness is a serialization of all witness data of the transaction. Each txin is
		# associated with a witness field. A witness field starts with a var_int to indicate the
		# number of stack items for the txin. It is followed by stack items, with each item starts
		# with a var_int to indicate the length. Witness data is NOT script.

		# A non-witness program txin MUST be associated with an empty witness field, represented
		# by a 0x00. If all txins are not witness program, a transaction's wtxid is equal to its txid.
		def get_witness_size():
			if not self.has_segwit_inputs(): return 0
			wf_size = 1 + 1 + sig_size + 1 + pubkey_size['compressed'] # vInt vInt sig vInt pubkey = 108
			return sum((1,wf_size)[bool(i.mmid) and i.mmid.mmtype=='S'] for i in self.inputs)

		isize = get_inputs_size()
		osize = get_outputs_size()
		wsize = get_witness_size()
#  		pmsg([i.mmid and i.mmid.mmtype == 'S' for i in self.inputs])
#  		pmsg([i.mmid for i in self.inputs])
#  		pmsg([i.mmid for i in self.outputs])
#  		pmsg('isize',isize)
#  		pmsg('osize',osize)
#  		pmsg('wsize',wsize)

		# TODO: compute real varInt sizes instead of assuming 1 byte
		# old serialization: [nVersion]              [vInt][txins][vInt][txouts]         [nLockTime]
		old_size =           4                     + 1   + isize + 1  + osize          + 4
		# new serialization: [nVersion][marker][flag][vInt][txins][vInt][txouts][witness][nLockTime]
		new_size =           4       + 1     + 1   + 1   + isize + 1  + osize + wsize  + 4 \
				if wsize else old_size

		ret = (old_size * 3 + new_size) / 4
# 		pmsg('old_size',old_size) # This should be equal to the size of serialized signed tx
# 		pmsg('ret',ret)
# 		pmsg('estimate_size_old',self.estimate_size_old())
		return ret

	estimate_size = estimate_vsize

	def get_fee(self):
		return self.sum_inputs() - self.sum_outputs()

	def btc2spb(self,coin_fee):
		return int(coin_fee/g.proto.coin_amt.min_coin_unit/self.estimate_size())

	def get_relay_fee(self):
		assert self.estimate_size()
		kb_fee = g.proto.coin_amt(g.rpch.getnetworkinfo()['relayfee'])
		vmsg('Relay fee: {} {}/kB'.format(kb_fee,g.coin))
		return kb_fee * self.estimate_size() / 1024

	def convert_fee_spec(self,tx_fee,tx_size,on_fail='throw'):
		if g.proto.coin_amt(tx_fee,on_fail='silent'):
			return g.proto.coin_amt(tx_fee)
		elif len(tx_fee) >= 2 and tx_fee[-1] == 's' and is_int(tx_fee[:-1]) and int(tx_fee[:-1]) >= 1:
			if tx_size:
				return g.proto.coin_amt(int(tx_fee[:-1]) * tx_size * g.proto.coin_amt.min_coin_unit)
			else:
				return None
		else:
			if on_fail == 'return':
				return False
			elif on_fail == 'throw':
				assert False, "'{}': invalid tx-fee argument".format(tx_fee)

	def get_usr_fee(self,tx_fee,desc='Missing description'):
		coin_fee = self.convert_fee_spec(tx_fee,self.estimate_size(),on_fail='return')
		if coin_fee == None:
			# we shouldn't be calling this if tx size is unknown
			m = "'{}': cannot convert satoshis-per-byte to {} because transaction size is unknown"
			assert False, m.format(tx_fee,g.coin)
		elif coin_fee == False:
			m = "'{}': invalid TX fee (not a {} amount or satoshis-per-byte specification)"
			msg(m.format(tx_fee,g.coin))
			return False
		elif coin_fee > g.proto.max_tx_fee:
			m = '{} {c}: {} fee too large (maximum fee: {} {c})'
			msg(m.format(coin_fee,desc,g.proto.max_tx_fee,c=g.coin))
			return False
		elif coin_fee < self.get_relay_fee():
			m = '{} {c}: {} fee too small (below relay fee of {} {c})'
			msg(m.format(str(coin_fee),desc,str(self.get_relay_fee()),c=g.coin))
			return False
		else:
			return coin_fee

	def get_usr_fee_interactive(self,tx_fee=None,desc='Starting'):
		coin_fee = None
		while True:
			if tx_fee:
				coin_fee = self.get_usr_fee(tx_fee,desc)
			if coin_fee:
				m = ('',' (after {}x adjustment)'.format(opt.tx_fee_adj))[opt.tx_fee_adj != 1]
				p = '{} TX fee{}: {} {} ({} satoshis per byte)'.format(desc,m,
					coin_fee.hl(),g.coin,pink(str(self.btc2spb(coin_fee))))
				if opt.yes or keypress_confirm(p+'.  OK?',default_yes=True):
					if opt.yes: msg(p)
					return coin_fee
			tx_fee = my_raw_input('Enter transaction fee: ')
			desc = 'User-selected'

	def delete_attrs(self,desc,attr):
		for e in getattr(self,desc):
			if hasattr(e,attr): delattr(e,attr)

	def decode_io(self,desc,data):
		io,il = (
			(self.MMGenTxOutput,self.MMGenTxOutputList),
			(self.MMGenTxInput,self.MMGenTxInputList)
		)[desc=='inputs']
		return il([io(**dict([(k,d[k]) for k in io.__dict__
					if k in d and d[k] not in ('',None)])) for d in data])

	def decode_io_oldfmt(self,data):
		tr = {'amount':'amt', 'address':'addr', 'confirmations':'confs','comment':'label'}
		tr_rev = dict([(v,k) for k,v in tr.items()])
		copy_keys = [tr_rev[k] if k in tr_rev else k for k in self.MMGenTxInput.__dict__]
		ret = MMGenList(self.MMGenTxInput(**dict([(tr[k] if k in tr else k,d[k])
					for k in copy_keys if k in d and d[k] != ''])) for d in data)
		for i in ret: i.sequence = int('0xffffffff',16)
		return ret

	# inputs methods
	def copy_inputs_from_tw(self,tw_unspent_data):
		txi,self.inputs = self.MMGenTxInput,self.MMGenTxInputList()
		for d in tw_unspent_data:
			t = txi(**dict([(attr,getattr(d,attr)) for attr in d.__dict__ if attr in txi.__dict__]))
			if d.twmmid.type == 'mmgen': t.mmid = d.twmmid # twmmid -> mmid
			self.inputs.append(t)

	def get_input_sids(self):
		return set(e.mmid.sid for e in self.inputs if e.mmid)

	def get_output_sids(self):
		return set(e.mmid.sid for e in self.outputs if e.mmid)

	def sum_inputs(self):
		return sum(e.amt for e in self.inputs)

	def add_timestamp(self):
		self.timestamp = make_timestamp()

	def add_blockcount(self):
		self.blockcount = int(g.rpch.getblockcount())

	def format(self):
		lines = [
			'{}{} {} {} {} {}'.format(
				(g.coin+' ','')[g.coin=='BTC'],
				self.chain.upper() if self.chain else 'Unknown',
				self.txid,
				self.send_amt,
				self.timestamp,
				self.blockcount
			),
			self.hex,
			repr([e.__dict__ for e in self.inputs]),
			repr([e.__dict__ for e in self.outputs])
		]
		if self.label:
			lines.append(baseconv.b58encode(self.label.encode('utf8')))
		if self.coin_txid:
			if not self.label: lines.append('-') # keep old tx files backwards compatible
			lines.append(self.coin_txid)
		self.chksum = make_chksum_6(' '.join(lines))
		self.fmt_data = '\n'.join([self.chksum] + lines)+'\n'

	def get_non_mmaddrs(self,desc):
		return list(set(i.addr for i in getattr(self,desc) if not i.mmid))

	# return true or false; don't exit
	def sign(self,tx_num_str,keys):

		if self.marked_signed():
			die(1,'Transaction is already signed!')

		self.die_if_incorrect_chain()

		if (self.has_segwit_inputs() or self.has_segwit_outputs()) and not g.proto.cap('segwit'):
			die(2,yellow("TX has Segwit inputs or outputs, but {} doesn't support Segwit!".format(g.coin)))

		qmsg('Passing {} key{} to {}'.format(len(keys),suf(keys,'s'),g.proto.daemon_name))

		if self.has_segwit_inputs():
			from mmgen.addr import KeyGenerator,AddrGenerator
			kg = KeyGenerator()
			ag = AddrGenerator('segwit')
			keydict = MMGenDict([(d.addr,d.sec) for d in keys])

		sig_data = []
		for d in self.inputs:
			e = dict([(k,getattr(d,k)) for k in ('txid','vout','scriptPubKey','amt')])
			e['amount'] = e['amt']
			del e['amt']
			if d.mmid and d.mmid.mmtype == 'S':
				e['redeemScript'] = ag.to_segwit_redeem_script(kg.to_pubhex(keydict[d.addr]))
			sig_data.append(e)

		msg_r('Signing transaction{}...'.format(tx_num_str))
		wifs = [d.sec.wif for d in keys]
#		keys.pmsg()
#		pmsg(wifs)
		ret = g.rpch.signrawtransaction(self.hex,sig_data,wifs,g.proto.sighash_type,on_fail='return')

		from mmgen.rpc import rpc_error,rpc_errmsg
		if rpc_error(ret):
			errmsg = rpc_errmsg(ret)
			if 'Invalid sighash param' in errmsg:
				m  = 'This is not the BCH chain.'
				m += "\nRe-run the script without the --coin=bch option."
			else:
				m = errmsg
			msg(yellow(m))
			return False
		else:
			if ret['complete']:
#				Msg(pretty_hexdump(unhexlify(self.hex),cols=16)) # DEBUG
#				pmsg(make_chksum_6(unhexlify(self.hex)).upper())
				self.hex = ret['hex']
				vmsg('Signed transaction size: {}'.format(len(self.hex)/2))
				dt = DeserializedTX(self.hex)
				self.check_hex_tx_matches_mmgen_tx(dt)
				self.coin_txid = CoinTxID(dt['txid'],on_fail='return')
				self.check_sigs(dt)
				assert self.coin_txid == g.rpch.decoderawtransaction(self.hex)['txid'],(
											'txid mismatch (after signing)')
				msg('OK')
				return True
			else:
				msg('failed\n{} returned the following errors:'.format(g.proto.daemon_name.capitalize()))
				msg(repr(ret['errors']))
				return False

	def mark_raw(self):
		self.desc = 'transaction'
		self.ext = self.raw_ext

	def mark_signed(self): # called ONLY by check_sigs()
		self.desc = 'signed transaction'
		self.ext = self.sig_ext

	def marked_signed(self,color=False):
		ret = self.desc == 'signed transaction'
		return (red,green)[ret](str(ret)) if color else ret

	# protect against an attack where a malicious, compromised or malfunctioning coin daemon could switch
	# hex transaction data.
	def check_hex_tx_matches_mmgen_tx(self,deserial_tx):
		m = 'Fatal error: a malicious or malfunctioning coin daemon or other program has altered your data!'

		if deserial_tx['lock_time'] != 0:
			rdie(3,'\nLock time is not zero!\n' + m)

		def check_equal(desc,mmio,hexio):
			if mmio != hexio:
				msg('\nMMGen {}:\n{}'.format(desc,pformat(mmio)))
				msg('Hex {}:\n{}'.format(desc,pformat(hexio)))
				m2 = '{} in hex transaction data from coin daemon do not match those in MMGen transaction!\n' + m
				rdie(3,m2.format(desc.capitalize()))

		d_hex   = sorted((i['txid'],i['vout']) for i in deserial_tx['txins'])
		d_mmgen = sorted((i.txid,i.vout) for i in self.inputs)
		check_equal('inputs',d_hex,d_mmgen)

		d_hex   = sorted((o['address'],g.proto.coin_amt(o['amount'])) for o in deserial_tx['txouts'])
		d_mmgen = sorted((o.addr,o.amt) for o in self.outputs)
		check_equal('outputs',d_hex,d_mmgen)

		uh = deserial_tx['unsigned_hex']
		if str(self.txid) != make_chksum_6(unhexlify(uh)).upper():
			die(3,'MMGen TxID ({}) does not match hex transaction data!'.format(self.txid))

	def check_sigs(self,deserial_tx=None): # return False if no sigs, die on error
		txins = (deserial_tx or DeserializedTX(self.hex))['txins']
		has_ss = any(ti['scriptSig'] for ti in txins)
		has_witness = any('witness' in ti and ti['witness'] for ti in txins)
		if not (has_ss or has_witness):
			return False
		for ti in txins:
			if ti['scriptSig'][:6] == '160014' and len(ti['scriptSig']) == 46: # P2SH-P2WPKH
				assert 'witness' in ti, 'missing witness'
				assert type(ti['witness']) == list and len(ti['witness']) == 2, 'malformed witness'
				assert len(ti['witness'][1]) == 66, 'incorrect witness pubkey length'
			elif ti['scriptSig'] == '': # native P2WPKH
				die(3,('TX has missing signature','Native P2WPKH not implemented')['witness' in ti])
			else: # non-witness
				assert not 'witness' in ti, 'non-witness input has witness'
				# sig_size 72 (DER format), pubkey_size 'compressed':33, 'uncompressed':65
				assert (200 < len(ti['scriptSig']) < 300), 'malformed scriptSig' # VERY rough check
		self.mark_signed()
		return True

	def has_segwit_outputs(self):
		return any(o.mmid and o.mmid.mmtype == 'S' for o in self.outputs)

	def is_in_mempool(self):
		return 'size' in g.rpch.getmempoolentry(self.coin_txid,on_fail='silent')

	def is_in_wallet(self):
		ret = g.rpch.gettransaction(self.coin_txid,on_fail='silent')
		if 'confirmations' in ret and ret['confirmations'] > 0:
			return ret['confirmations']
		else:
			return False

	def is_replaced(self):
		if self.is_in_mempool(): return False
		ret = g.rpch.gettransaction(self.coin_txid,on_fail='silent')
		if not 'bip125-replaceable' in ret or not 'confirmations' in ret or ret['confirmations'] > 0:
			return False
		return -ret['confirmations'] + 1 # 1: replacement in mempool, 2: replacement confirmed

	def is_in_utxos(self):
		return 'txid' in g.rpch.getrawtransaction(self.coin_txid,True,on_fail='silent')

	def get_status(self,status=False):
		if self.is_in_mempool():
			msg(('Warning: transaction is in mempool!','Transaction is in mempool')[status])
		elif self.is_in_wallet():
			confs = self.is_in_wallet()
			die(0,'Transaction has {} confirmation{}'.format(confs,suf(confs,'s')))
		elif self.is_in_utxos():
			die(2,red('ERROR: transaction is in the blockchain (but not in the tracking wallet)!'))
		ret = self.is_replaced() # 1: replacement in mempool, 2: replacement confirmed
		if ret:
			die(1,'Transaction has been replaced'+('',', and the replacement TX is confirmed')[ret==2]+'!')

	def send(self,prompt_user=True):

		if not self.marked_signed():
			die(1,'Transaction is not signed!')

		self.die_if_incorrect_chain()

		self.check_hex_tx_matches_mmgen_tx(DeserializedTX(self.hex))

		bogus_send = os.getenv('MMGEN_BOGUS_SEND')

		if self.has_segwit_outputs() and not segwit_is_active() and not bogus_send:
			m = 'Transaction has MMGen Segwit outputs, but this blockchain does not support Segwit'
			die(2,m+' at the current height')

		if self.get_fee() > g.proto.max_tx_fee:
			die(2,'Transaction fee ({}) greater than {} max_tx_fee ({} {})!'.format(
				self.get_fee(),g.proto.name.capitalize(),g.proto.max_tx_fee,g.coin.upper()))

		self.get_status()

		if prompt_user:
			m1 = ("Once this transaction is sent, there's no taking it back!",'')[bool(opt.quiet)]
			m2 = 'broadcast this transaction to the {} network'.format(g.chain.upper())
			m3 = ('YES, I REALLY WANT TO DO THIS','YES')[bool(opt.quiet or opt.yes)]
			confirm_or_exit(m1,m2,m3)

		msg('Sending transaction')
		ret = None if bogus_send else g.rpch.sendrawtransaction(self.hex,on_fail='return')

		from mmgen.rpc import rpc_error,rpc_errmsg
		if rpc_error(ret):
			errmsg = rpc_errmsg(ret)
			if 'Signature must use SIGHASH_FORKID' in errmsg:
				m  = 'The Aug. 1 2017 UAHF has activated on this chain.'
				m += "\nRe-run the script with the --coin=bch option."
			elif 'Illegal use of SIGHASH_FORKID' in errmsg:
				m  = 'The Aug. 1 2017 UAHF is not yet active on this chain.'
				m += "\nRe-run the script without the --coin=bch option."
			else:
				m = errmsg
			msg(yellow(m))
			msg(red('Send of MMGen transaction {} failed'.format(self.txid)))
			return False
		else:
			if bogus_send:
				m = 'BOGUS transaction NOT sent: {}'
			else:
				assert ret == self.coin_txid, 'txid mismatch (after sending)'
				m = 'Transaction sent: {}'
			self.desc = 'sent transaction'
			msg(m.format(self.coin_txid.hl()))
			self.add_timestamp()
			self.add_blockcount()
			return True

	def write_txid_to_file(self,ask_write=False,ask_write_default_yes=True):
		fn = '%s[%s].%s' % (self.txid,self.send_amt,self.txid_ext)
		write_data_to_file(fn,self.coin_txid+'\n','transaction ID',
			ask_write=ask_write,
			ask_write_default_yes=ask_write_default_yes)

	def write_to_file(self,add_desc='',ask_write=True,ask_write_default_yes=False,ask_tty=True,ask_overwrite=True):
		if ask_write == False:
			ask_write_default_yes=True
		self.format()
		fn = '{}{}[{}{}].{}'.format(
			self.txid,
			('-'+g.coin,'')[g.coin=='BTC'],
			self.send_amt,
			('',',{}'.format(self.btc2spb(self.get_fee())))[self.is_rbf()],
			self.ext)
		write_data_to_file(fn,self.fmt_data,self.desc+add_desc,
			ask_overwrite=ask_overwrite,
			ask_write=ask_write,
			ask_tty=ask_tty,
			ask_write_default_yes=ask_write_default_yes)

	def view_with_prompt(self,prompt=''):
		prompt += ' (y)es, (N)o, pager (v)iew, (t)erse view'
		reply = prompt_and_get_char(prompt,'YyNnVvTt',enter_ok=True)
		if reply and reply in 'YyVvTt':
			self.view(pager=reply in 'Vv',terse=reply in 'Tt')

	def view(self,pager=False,pause=True,terse=False):
		o = self.format_view(terse=terse)
		if pager: do_pager(o)
		else:
			msg_r(o)
			from mmgen.term import get_char
			if pause:
				get_char('Press any key to continue: ')
				msg('')

# 	def is_rbf_from_rpc(self):
# 		dec_tx = g.rpch.decoderawtransaction(self.hex)
# 		return None < dec_tx['vin'][0]['sequence'] <= g.max_int - 2

	def is_rbf(self):
		return self.inputs[0].sequence == g.max_int - 2

	def signal_for_rbf(self):
		self.inputs[0].sequence = g.max_int - 2

	def format_view(self,terse=False):
		try:
			rpc_init()
			blockcount = g.rpch.getblockcount()
		except:
			blockcount = None

		hdr_fs = (
			'TRANSACTION DATA\n\n[ID:{}] [{} {}] [{} UTC] [RBF:{}] [Signed:{}]\n',
			'Transaction {} {} {} ({} UTC) RBF={} Signed={}\n'
		)[bool(terse)]
		nonmm_str = '(non-{pnm} address)'.format(pnm=g.proj_name)

		def get_max_mmwid(io):
			if io == self.inputs:
				sel_f = lambda o: len(o.mmid) + 2 # len('()')
			else:
				sel_f = lambda o: len(o.mmid) + (2,8)[bool(o.is_chg)] # + len(' (chg)')
			return  max(max([sel_f(o) for o in io if o.mmid] or [0]),len(nonmm_str))

		max_mmwid = max(get_max_mmwid(self.inputs),get_max_mmwid(self.outputs))

		def format_io(io):
			ip = io == self.inputs
			io_out = ''
			confs_per_day = 60*60*24 / g.proto.secs_per_block
			for n,e in enumerate(sorted(io,key=lambda o: o.mmid.sort_key if o.mmid else o.addr)):
				if ip and blockcount != None:
					confs = e.confs + blockcount - self.blockcount
					days = int(confs / confs_per_day)
				if e.mmid:
					app=('',' (chg)')[bool(not ip and e.is_chg and terse)]
					mmid_fmt = e.mmid.fmt(width=max_mmwid,encl='()',color=True,app=app,appcolor='green')
				else:
					mmid_fmt = MMGenID.fmtc(nonmm_str,width=max_mmwid)
				if terse:
					io_out += '{:3} {} {} {} {}\n'.format(n+1,e.addr.fmt(color=True),mmid_fmt,e.amt.hl(),g.coin)
				else:
					icommon = [
						((n+1,'')[ip],'address:',e.addr.fmt(color=True) + ' '+mmid_fmt),
						('','comment:',e.label.hl() if e.label else ''),
						('','amount:','{} {}'.format(e.amt.hl(),g.coin))]
					items = [(n+1, 'tx,vout:','{},{}'.format(e.txid,e.vout))] + icommon + [
						('','confirmations:','{} (around {} days)'.format(confs,days) if blockcount!=None else '')
					] if ip else icommon + [
						('','change:',green('True') if e.is_chg else '')]
					io_out += '\n'.join([('{:>3} {:<8} {}'.format(*d)) for d in items if d[2]]) + '\n\n'
			return io_out

		out = hdr_fs.format(self.txid.hl(),self.send_amt.hl(),g.coin,self.timestamp,
				(red('False'),green('True'))[self.is_rbf()],self.marked_signed(color=True))
		if self.chain in ('testnet','regtest'):
			out += green('Chain: {}\n'.format(self.chain.upper()))
		if self.coin_txid:
			out += '{} TxID: {}\n'.format(g.coin,self.coin_txid.hl())
		enl = ('\n','')[bool(terse)]
		out += enl
		if self.label:
			out += 'Comment: %s\n%s' % (self.label.hl(),enl)
		out += 'Inputs:\n' + enl + format_io(self.inputs)
		out += 'Outputs:\n' + enl + format_io(self.outputs)

		fs = (
			'Total input:  {} {c}\nTotal output: {} {c}\nTX fee:       {} {c} ({} satoshis per byte)\n',
			'In {} {c} - Out {} {c} - Fee {} {c} ({} satoshis/byte)\n'
		)[bool(terse)]

		t_in,t_out = self.sum_inputs(),self.sum_outputs()
		fee = t_in-t_out
		out += fs.format(t_in.hl(),t_out.hl(),fee.hl(),pink(str(self.btc2spb(fee))),c=g.coin)

		if opt.verbose:
			ts = len(self.hex)/2 if self.hex else 'unknown'
			out += 'Transaction size: Vsize={} Actual={}'.format(self.estimate_size(),ts)
			if self.marked_signed():
				ws = DeserializedTX(self.hex)['witness_size']
				out += ' Base={} Witness={}'.format(ts-ws,ws)
			out += '\n'

		return out # TX label might contain non-ascii chars

	def parse_tx_file(self,infile,md_only=False):

		tx_data = get_lines_from_file(infile,self.desc+' data')

		try:
			desc = 'data'
			assert len(tx_data) >= 5,'number of lines less than 5'
			self.chksum = HexStr(tx_data.pop(0),on_fail='raise')
			assert self.chksum == make_chksum_6(' '.join(tx_data)),'file data does not match checksum'

			if len(tx_data) == 6:
				desc = '{} TxID'.format(g.proto.name.capitalize())
				self.coin_txid = CoinTxID(tx_data.pop(-1),on_fail='raise')

			if len(tx_data) == 5:
				c = tx_data.pop(-1)
				if c != '-':
					desc = 'encoded comment (not base58)'
					comment = baseconv.b58decode(c).decode('utf8')
					assert comment != False,'invalid comment'
					desc = 'comment'
					self.label = MMGenTXLabel(comment,on_fail='raise')

			desc = 'number of lines' # four required lines
			metadata,self.hex,inputs_data,outputs_data = tx_data
			metadata = metadata.split()

			self.coin = metadata.pop(0) if len(metadata) == 6 else 'BTC'

			if len(metadata) == 5:
				t = metadata.pop(0)
				self.chain = (t.lower(),None)[t=='Unknown']

			desc = 'metadata (4 items minimum required)'
			self.txid,send_amt,self.timestamp,blockcount = metadata
			desc = 'metadata'
			self.txid = MMGenTxID(self.txid,on_fail='raise')
			self.send_amt = g.proto.coin_amt(send_amt,on_fail='raise')
			desc = 'block count in metadata'
			self.blockcount = int(blockcount)
			desc = 'transaction hex data'
			self.hex = HexStr(self.hex,on_fail='raise')
			if md_only: return # the following ops will all fail if g.coin doesn't match tx.coin
			desc = 'coin type in metadata'
			assert self.coin == g.coin,'invalid coin type'
			desc = 'inputs data'
			self.inputs = self.decode_io('inputs',eval(inputs_data))
			assert len(self.inputs),'no inputs!'
			desc = '{}-to-MMGen address map data'.format(g.coin)
			self.outputs = self.decode_io('outputs',eval(outputs_data))
			assert len(self.outputs),'no outputs!'
		except Exception as e:
			die(2,'Invalid {} in transaction file: {}'.format(desc,e[0]))

		if not self.chain and not self.inputs[0].addr.is_for_chain('testnet'):
			self.chain = 'mainnet'

class MMGenBumpTX(MMGenTX):

	min_fee = None
	bump_output_idx = None

	def __init__(self,filename,send=False):

		super(type(self),self).__init__(filename)

		if not self.is_rbf():
			die(1,"Transaction '{}' is not replaceable (RBF)".format(self.txid))

		# If sending, require tx to have been signed
		if send:
			if not self.marked_signed():
				die(1,"File '{}' is not a signed {} transaction file".format(filename,g.proj_name))
			if not self.coin_txid:
				die(1,"Transaction '{}' was not broadcast to the network".format(self.txid,g.proj_name))

		self.coin_txid = ''
		self.mark_raw()

	def choose_output(self):
		chg_idx = self.get_chg_output_idx()
		init_reply = opt.output_to_reduce
		while True:
			if init_reply == None:
				m = 'Choose an output to deduct the fee from (Hit ENTER for the change output): '
				reply = my_raw_input(m) or 'c'
			else:
				reply,init_reply = init_reply,None
			if chg_idx == None and not is_int(reply):
				msg("Output must be an integer")
			elif chg_idx != None and not is_int(reply) and reply != 'c':
				msg("Output must be an integer, or 'c' for the change output")
			else:
				idx = chg_idx if reply == 'c' else (int(reply) - 1)
				if idx < 0 or idx >= len(self.outputs):
					msg('Output must be in the range 1-{}'.format(len(self.outputs)))
				else:
					o_amt = self.outputs[idx].amt
					cs = ('',' (change output)')[chg_idx == idx]
					p = 'Fee will be deducted from output {}{} ({} {})'.format(idx+1,cs,o_amt,g.coin)
					if o_amt < self.min_fee:
						msg('Minimum fee ({} {c}) is greater than output amount ({} {c})'.format(
							self.min_fee,o_amt,c=g.coin))
					elif opt.yes or keypress_confirm(p+'.  OK?',default_yes=True):
						if opt.yes: msg(p)
						self.bump_output_idx = idx
						return idx

	def set_min_fee(self):
		self.min_fee = self.sum_inputs() - self.sum_outputs() + self.get_relay_fee()

	def get_usr_fee(self,tx_fee,desc):
		ret = super(type(self),self).get_usr_fee(tx_fee,desc)
		if ret < self.min_fee:
			msg('{} {c}: {} fee too small. Minimum fee: {} {c} ({} satoshis per byte)'.format(
				ret,desc,self.min_fee,self.btc2spb(self.min_fee),c=g.coin))
			return False
		output_amt = self.outputs[self.bump_output_idx].amt
		if ret >= output_amt:
			msg('{} {c}: {} fee too large. Maximum fee: <{} {c}'.format(ret,desc,output_amt,c=g.coin))
			return False
		return ret
