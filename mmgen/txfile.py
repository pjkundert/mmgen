#!/usr/bin/env python3
#
# mmgen = Multi-Mode GENerator, command-line Bitcoin cold storage solution
# Copyright (C)2013-2021 The MMGen Project <mmgen@tuta.io>
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
txfile.py:  Transaction file operations for the MMGen suite
"""

from .common import *
from .obj import HexStr,MMGenTxID,UnknownCoinAmt,CoinTxID,MMGenTxLabel
from .tx import MMGenTxOutput,MMGenTxOutputList,MMGenTxInput,MMGenTxInputList
from .exception import MaxFileSizeExceeded

class MMGenTxFile:

	def __init__(self,tx):
		self.tx       = tx
		self.chksum   = None
		self.fmt_data = None
		self.filename = None

	def parse(self,infile,metadata_only=False,quiet_open=False):
		tx = self.tx

		def eval_io_data(raw_data,desc):
			from ast import literal_eval
			try:
				d = literal_eval(raw_data)
			except:
				if desc == 'inputs' and not quiet_open:
					ymsg('Warning: transaction data appears to be in old format')
				import re
				d = literal_eval(re.sub(r"[A-Za-z]+?\(('.+?')\)",r'\1',raw_data))
			assert type(d) == list, f'{desc} data not a list!'
			if not (desc == 'outputs' and tx.proto.base_coin == 'ETH'): # ETH txs can have no outputs
				assert len(d), f'no {desc}!'
			for e in d:
				e['amt'] = tx.proto.coin_amt(e['amt'])
			io,io_list = (
				(MMGenTxOutput,MMGenTxOutputList),
				(MMGenTxInput,MMGenTxInputList)
			)[desc=='inputs']
			return io_list(tx,[io(tx.proto,**e) for e in d])

		tx_data = get_data_from_file(infile,tx.desc+' data',quiet=quiet_open)

		try:
			desc = 'data'
			if len(tx_data) > g.max_tx_file_size:
				raise MaxFileSizeExceeded(f'Transaction file size exceeds limit ({g.max_tx_file_size} bytes)')
			tx_data = tx_data.splitlines()
			assert len(tx_data) >= 5,'number of lines less than 5'
			assert len(tx_data[0]) == 6,'invalid length of first line'
			self.chksum = HexStr(tx_data.pop(0))
			assert self.chksum == make_chksum_6(' '.join(tx_data)),'file data does not match checksum'

			if len(tx_data) == 6:
				assert len(tx_data[-1]) == 64,'invalid coin TxID length'
				desc = f'coin TxID'
				tx.coin_txid = CoinTxID(tx_data.pop(-1))

			if len(tx_data) == 5:
				# rough check: allow for 4-byte utf8 characters + base58 (4 * 11 / 8 = 6 (rounded up))
				assert len(tx_data[-1]) < MMGenTxLabel.max_len*6,'invalid comment length'
				c = tx_data.pop(-1)
				if c != '-':
					desc = 'encoded comment (not base58)'
					from .baseconv import baseconv
					comment = baseconv.tobytes(c,'b58').decode()
					assert comment != False,'invalid comment'
					desc = 'comment'
					tx.label = MMGenTxLabel(comment)

			desc = 'number of lines' # four required lines
			metadata,tx.hex,inputs_data,outputs_data = tx_data
			assert len(metadata) < 100,'invalid metadata length' # rough check
			metadata = metadata.split()

			if metadata[-1].startswith('LT='):
				desc = 'locktime'
				tx.locktime = int(metadata.pop()[3:])

			desc = 'coin token in metadata'
			coin = metadata.pop(0) if len(metadata) == 6 else 'BTC'
			coin,tokensym = coin.split(':') if ':' in coin else (coin,None)

			desc = 'chain token in metadata'
			tx.chain = metadata.pop(0).lower() if len(metadata) == 5 else 'mainnet'

			from .protocol import CoinProtocol,init_proto
			network = CoinProtocol.Base.chain_name_to_network(coin,tx.chain)

			desc = 'initialization of protocol'
			tx.proto = init_proto(coin,network=network)
			if tokensym:
				tx.proto.tokensym = tokensym

			desc = 'metadata (4 items)'
			txid,send_amt,tx.timestamp,blockcount = metadata

			desc = 'TxID in metadata'
			tx.txid = MMGenTxID(txid)
			desc = 'block count in metadata'
			tx.blockcount = int(blockcount)

			if metadata_only:
				return

			desc = 'transaction file hex data'
			tx.check_txfile_hex_data()
			desc = 'Ethereum transaction file hex or json data'
			tx.parse_txfile_hex_data()
			desc = 'inputs data'
			tx.inputs  = eval_io_data(inputs_data,'inputs')
			desc = 'outputs data'
			tx.outputs = eval_io_data(outputs_data,'outputs')
			desc = 'send amount in metadata'
			assert Decimal(send_amt) == tx.send_amt, f'{send_amt} != {tx.send_amt}'
		except Exception as e:
			die(2,f'Invalid {desc} in transaction file: {e!s}')

	def make_filename(self):
		tx = self.tx
		def gen_filename():
			yield tx.txid
			if tx.coin != 'BTC':
				yield '-' + tx.dcoin
			yield f'[{tx.send_amt!s}'
			if tx.is_replaceable():
				yield ',{}'.format(tx.fee_abs2rel(tx.fee,to_unit=tx.fn_fee_unit))
			if tx.get_hex_locktime():
				yield ',tl={}'.format(tx.get_hex_locktime())
			yield ']'
			if g.debug_utf8:
				yield '-α'
			if tx.proto.testnet:
				yield '.' + tx.proto.network
			yield '.' + tx.ext
		return ''.join(gen_filename())

	def format(self):
		tx = self.tx

		def amt_to_str(d):
			return {k: (str(d[k]) if k == 'amt' else d[k]) for k in d}

		coin_id = '' if tx.coin == 'BTC' else tx.coin + ('' if tx.coin == tx.dcoin else ':'+tx.dcoin)
		lines = [
			'{}{} {} {} {} {}{}'.format(
				(coin_id+' ' if coin_id else ''),
				tx.chain.upper(),
				tx.txid,
				tx.send_amt,
				tx.timestamp,
				tx.blockcount,
				(f' LT={tx.locktime}' if tx.locktime else ''),
			),
			tx.hex,
			ascii([amt_to_str(e._asdict()) for e in tx.inputs]),
			ascii([amt_to_str(e._asdict()) for e in tx.outputs])
		]

		if tx.label:
			from .baseconv import baseconv
			lines.append(baseconv.frombytes(tx.label.encode(),'b58',tostr=True))

		if tx.coin_txid:
			if not tx.label:
				lines.append('-') # keep old tx files backwards compatible
			lines.append(tx.coin_txid)

		self.chksum = make_chksum_6(' '.join(lines))
		fmt_data = '\n'.join([self.chksum] + lines) + '\n'
		if len(fmt_data) > g.max_tx_file_size:
			raise MaxFileSizeExceeded(f'Transaction file size exceeds limit ({g.max_tx_file_size} bytes)')
		return fmt_data

	def write(self,
		add_desc              = '',
		ask_write             = True,
		ask_write_default_yes = False,
		ask_tty               = True,
		ask_overwrite         = True ):

		if ask_write == False:
			ask_write_default_yes = True

		if not self.filename:
			self.filename = self.make_filename()

		if not self.fmt_data:
			self.fmt_data = self.format()

		write_data_to_file(
			outfile               = self.filename,
			data                  = self.fmt_data,
			desc                  = self.tx.desc + add_desc,
			ask_overwrite         = ask_overwrite,
			ask_write             = ask_write,
			ask_tty               = ask_tty,
			ask_write_default_yes = ask_write_default_yes )

	@classmethod
	def get_proto(cls,filename,quiet_open=False):
		from .tx import MMGenTX
		tmp_tx = MMGenTX.Base()
		cls(tmp_tx).parse(filename,metadata_only=True,quiet_open=quiet_open)
		return tmp_tx.proto
