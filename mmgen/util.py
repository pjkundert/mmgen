#!/usr/bin/env python
#
# mmgen = Multi-Mode GENerator, command-line Bitcoin cold storage solution
# Copyright (C) 2013-2014 by philemon <mmgen-py@yandex.com>
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
util.py:  Low-level routines imported by other modules for the MMGen suite
"""

import sys
from hashlib import sha256
from binascii import hexlify,unhexlify

import mmgen.config as g

def msg(s):    sys.stderr.write(s + "\n")
def msg_r(s):  sys.stderr.write(s)
def qmsg(s,alt=""):
	if g.quiet:
		if alt: sys.stderr.write(alt + "\n")
	else: sys.stderr.write(s + "\n")
def qmsg_r(s,alt=""):
	if g.quiet:
		if alt: sys.stderr.write(alt)
	else: sys.stderr.write(s)
def vmsg(s):
	if g.verbose: sys.stderr.write(s + "\n")
def vmsg_r(s):
	if g.verbose: sys.stderr.write(s)

cmessages = {
	'null': "",
	'incog_iv_id': """
   If you know your Incog ID, check it against the value above.  If it's
   incorrect, then your incognito data is invalid.
""",
	'incog_iv_id_hidden': """
   If you know your Incog ID, check it against the value above.  If it's
   incorrect, then your incognito data is invalid or you've supplied
   an incorrect offset.
""",
	'incog_key_id': """
   Check that the generated seed ID is correct.  If it's not, then your
   password or hash preset is incorrect or incognito data is corrupted.
""",
	'incog_key_id_hidden': """
   Check that the generated seed ID is correct.  If it's not, then your
   password or hash preset is incorrect or incognito data is corrupted.
   If the key ID is correct but the seed ID is not, then you might have
   chosen an incorrect seed length.
""",
	'unencrypted_secret_keys': """
This program generates secret keys from your {} seed, outputting them in
UNENCRYPTED form.  Generate only the key(s) you need and guard them carefully.
""".format(g.proj_name),
	'brain_warning': """
############################## EXPERTS ONLY! ##############################

A brainwallet will be secure only if you really know what you're doing and
have put much care into its creation.  {} assumes no responsibility for
coins stolen as a result of a poorly crafted brainwallet passphrase.

A key will be generated from your passphrase using the parameters requested
by you: seed length {}, hash preset '{}'.  For brainwallets it's highly
recommended to use one of the higher-numbered presets

Remember the seed length and hash preset parameters you've specified.  To
generate the correct keys/addresses associated with this passphrase in the
future, you must continue using these same parameters
""",
	'usr_rand_notice': """
You've chosen to not fully trust your OS's random number generator and provide
some additional entropy of your own.  Please type %s symbols on your keyboard.
Type slowly and choose your symbols carefully for maximum randomness.  Try to
use both upper and lowercase as well as punctuation and numerals.  What you
type will not be displayed on the screen.  Note that the timings between your
keystrokes will also be used as a source of randomness.
""",
	'choose_wallet_passphrase': """
Now you must choose a passphrase to encrypt the wallet with.  A key will be
generated from your passphrase using a hash preset of '%s'.  Please note that
no strength checking of passphrases is performed.  For an empty passphrase,
just hit ENTER twice.
""".strip()
}

def get_extension(f):
	import os
	return os.path.splitext(f)[1][1:]

def make_chksum_N(s,n,sep=False):
	if n%4 or not (4 <= n <= 64): return False
	s = sha256(sha256(s).digest()).hexdigest().upper()
	sep = " " if sep else ""
	return sep.join([s[i*4:i*4+4] for i in range(n/4)])
def make_chksum_8(s,sep=False):
	s = sha256(sha256(s).digest()).hexdigest()[:8].upper()
	return "{} {}".format(s[:4],s[4:]) if sep else s
def make_chksum_6(s): return sha256(s).hexdigest()[:6]
def make_iv_chksum(s): return sha256(s).hexdigest()[:8].upper()

def splitN(s,n,sep=None):                      # always return an n-element list
	ret = s.split(sep,n-1)
	return ret + ["" for i in range(n-len(ret))]
def split2(s,sep=None): return splitN(s,2,sep) # always return a 2-element list
def split3(s,sep=None): return splitN(s,3,sep) # always return a 3-element list

def col4(s):
	nondiv = 1 if len(s) % 4 else 0
	return " ".join([s[4*i:4*i+4] for i in range(len(s)/4 + nondiv)])

def make_timestamp():
	import time
	tv = time.gmtime(time.time())[:6]
	return "{:04d}{:02d}{:02d}_{:02d}{:02d}{:02d}".format(*tv)
def make_timestr():
	import time
	tv = time.gmtime(time.time())[:6]
	return "{:04d}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(*tv)
def secs_to_hms(secs):
	return "{:02d}:{:02d}:{:02d}".format(secs/3600, (secs/60) % 60, secs % 60)

def _is_hex(s):
	try: int(s,16)
	except: return False
	else: return True

def match_ext(addr,ext):
	return addr.split(".")[-1] == ext

def get_from_brain_opt_params(opts):
	l,p = opts['from_brain'].split(",")
	return(int(l),p)

def pretty_hexdump(data,gw=2,cols=8,line_nums=False):
	r = 1 if len(data) % gw else 0
	return "".join(
		[
			("" if (line_nums == False or i % cols) else "%03i: " % (i/cols)) +
			hexlify(data[i*gw:i*gw+gw]) +
			(" " if (i+1) % cols else "\n")
				for i in range(len(data)/gw + r)
		]
	).rstrip()

def decode_pretty_hexdump(data):
	import re
	lines = [re.sub('^\d+:\s+','',l) for l in data.split("\n")]
	return unhexlify("".join(("".join(lines).split())))

def get_hash_params(hash_preset):
	if hash_preset in g.hash_presets:
		return g.hash_presets[hash_preset] # N,p,r,buflen
	else: # Shouldn't be here
		msg("%s: invalid 'hash_preset' value" % hash_preset)
		sys.exit(3)

def show_hash_presets():
	fs = "  {:<7} {:<6} {:<3}  {}"
	msg("Available parameters for scrypt.hash():")
	msg(fs.format("Preset","N","r","p"))
	for i in sorted(g.hash_presets.keys()):
		msg(fs.format("'%s'" % i, *g.hash_presets[i]))
	msg("N = memory usage (power of two), p = iterations (rounds)")
	sys.exit(0)

def compare_checksums(chksum1, desc1, chksum2, desc2):

	if chksum1.lower() == chksum2.lower():
		vmsg("OK (%s)" % chksum1.upper())
		return True
	else:
		if g.debug:
			print \
	"ERROR!\nComputed checksum %s (%s) doesn't match checksum %s (%s)" \
			% (desc1,chksum1,desc2,chksum2)
		return False

def get_default_wordlist():

	wl_id = g.default_wl
	if wl_id == "electrum": from mmgen.mn_electrum import electrum_words as wl
	elif wl_id == "tirosh": from mmgen.mn_tirosh   import tirosh_words as wl
	return wl.strip().split("\n")

def open_file_or_exit(filename,mode):
	try:
		f = open(filename, mode)
	except:
		what = "reading" if mode == 'r' else "writing"
		msg("Unable to open file '%s' for %s" % (filename,what))
		sys.exit(2)
	return f


def check_file_type_and_access(fname,ftype):

	import os, stat

	typ2,tdesc2,access,action  = (stat.S_ISLNK,"symbolic link",os.R_OK,"read")\
	if ftype == "input file" else (stat.S_ISBLK,"block device",os.W_OK,"writ")

	if ftype == "directory":
		typ1,typ2,tdesc = stat.S_ISDIR,stat.S_ISDIR,"directory"
	else:
		typ1,tdesc = stat.S_ISREG,"regular file or "+tdesc2

	try: mode = os.stat(fname).st_mode
	except:
		msg("Unable to stat requested %s '%s'" % (ftype,fname))
		sys.exit(1)

	if not (typ1(mode) or typ2(mode)):
		msg("Requested %s '%s' is not a %s" % (ftype,fname,tdesc))
		sys.exit(1)

	if not os.access(fname, access):
		msg("Requested %s '%s' is un%sable by you" % (ftype,fname,action))
		sys.exit(1)

	return True

def check_infile(f):  return check_file_type_and_access(f,"input file")
def check_outfile(f): return check_file_type_and_access(f,"output file")
def check_outdir(f):  return check_file_type_and_access(f,"directory")


def _validate_addr_num(n):

	try: n = int(n)
	except:
		msg("'%s': address must be an integer" % n)
		return False

	if n < 1:
		msg("'%s': address must be greater than zero" % n)
		return False

	return n


def make_full_path(outdir,outfile):
	import os
	return os.path.normpath(os.sep.join([outdir, os.path.basename(outfile)]))
#	os.path.join() doesn't work?


def parse_address_list(arg,sep=","):

	ret = []

	for i in (arg.split(sep)):

		j = i.split("-")

		if len(j) == 1:
			i = _validate_addr_num(i)
			if not i: return False
			ret.append(i)
		elif len(j) == 2:
			beg = _validate_addr_num(j[0])
			if not beg: return False
			end = _validate_addr_num(j[1])
			if not end: return False
			if end < beg:
				msg("'%s-%s': end of range less than beginning" % (beg,end))
				return False
			for k in range(beg,end+1): ret.append(k)
		else:
			msg("'%s': invalid argument for address range" % i)
			return False

	return sorted(set(ret))


def get_new_passphrase(what, opts):

	if 'passwd_file' in opts:
		pw = " ".join(_get_words_from_file(opts['passwd_file'],what))
	elif 'echo_passphrase' in opts:
		pw = " ".join(_get_words_from_user(("Enter %s: " % what), opts))
	else:
		for i in range(g.passwd_max_tries):
			pw = " ".join(_get_words_from_user(("Enter %s: " % what),opts))
			pw2 = " ".join(_get_words_from_user(("Repeat %s: " % what),opts))
			if g.debug: print "Passphrases: [%s] [%s]" % (pw,pw2)
			if pw == pw2:
				vmsg("%ss match" % what.capitalize())
				break
			else:
				msg("%ss do not match" % what.capitalize())
		else:
			msg("User failed to duplicate passphrase in %s attempts" %
					g.passwd_max_tries)
			sys.exit(2)

	if pw == "": qmsg("WARNING: Empty passphrase")
	return pw


def confirm_or_exit(message, question, expect="YES"):

	vmsg("")

	m = message.strip()
	if m: msg(m)

	conf_msg = "Type uppercase '%s' to confirm: " % expect

	p = question+"  "+conf_msg if question[0].isupper() else \
		"Are you sure you want to %s?\n%s" % (question,conf_msg)

	if my_raw_input(p).strip() != expect:
		msg("Exiting at user request")
		sys.exit(2)

	vmsg("")


def write_to_stdout(data, what, confirm=True):
	if sys.stdout.isatty() and confirm:
		confirm_or_exit("",'output {} to screen'.format(what))
	elif not sys.stdout.isatty():
		try:
			import os
			of = os.readlink("/proc/%d/fd/1" % os.getpid())
			msg("Redirecting output to file '%s'" % os.path.relpath(of))
		except:
			msg("Redirecting output to file")
	sys.stdout.write(data)


def write_to_file(outfile,data,opts,what="data",confirm=False,verbose=False):

	if 'outdir' in opts: outfile = make_full_path(opts['outdir'],outfile)

	if confirm:
		from os import stat
		try:
			stat(outfile)
		except:
			pass
		else:
			confirm_or_exit("","File '%s' already exists\nOverwrite?" % outfile)

	f = open_file_or_exit(outfile,'w')
	try:
		f.write(data)
	except:
		msg("Failed to write %s to file '%s'" % (what,outfile))
		sys.exit(2)
	f.close

	if verbose: msg("%s written to file '%s'" % (what.capitalize(),outfile))


def export_to_file(outfile, data, opts, what="data"):

	if 'stdout' in opts:
		write_to_stdout(data, what, confirm=True)
	elif not sys.stdout.isatty():
		write_to_stdout(data, what, confirm=False)
	else:
		c = False if g.quiet else True
		write_to_file(outfile,data,opts,what,c,True)


from mmgen.bitcoin import b58decode_pad,b58encode_pad

def display_control_data(label,metadata,hash_preset,salt,enc_seed):
	msg("WALLET DATA")
	fs = "  {:18} {}"
	pw_empty = "yes" if metadata[3] == "E" else "no"
	for i in (
		("Label:",               label),
		("Seed ID:",             metadata[0].upper()),
		("Key  ID:",             metadata[1].upper()),
		("Seed length:",         "%s bits (%s bytes)" %
				(metadata[2],int(metadata[2])/8)),
		("Scrypt params:",  "Preset '%s' (%s)" % (hash_preset,
				" ".join([str(i) for i in get_hash_params(hash_preset)]))),
		("Passphrase empty?", pw_empty.capitalize()),
		("Timestamp:",           "%s UTC" % metadata[4]),
	): msg(fs.format(*i))

	fs = "  {:6} {}"
	for i in (
		("Salt:",    ""),
		("  b58:",      b58encode_pad(salt)),
		("  hex:",      hexlify(salt)),
		("Encrypted seed:", ""),
		("  b58:",      b58encode_pad(enc_seed)),
		("  hex:",      hexlify(enc_seed))
	): msg(fs.format(*i))


def write_wallet_to_file(seed, passwd, key_id, salt, enc_seed, opts):

	seed_id = make_chksum_8(seed)
	seed_len = str(len(seed)*8)
	pw_status = "NE" if len(passwd) else "E"
	hash_preset = opts['hash_preset']
	label = opts['label'] if 'label' in opts else "No Label"
	metadata = seed_id.lower(),key_id.lower(),seed_len,\
		pw_status,make_timestamp()
	sf  = b58encode_pad(salt)
	esf = b58encode_pad(enc_seed)

	lines = (
		label,
		"{} {} {} {} {}".format(*metadata),
		"{}: {} {} {}".format(hash_preset,*get_hash_params(hash_preset)),
		"{} {}".format(make_chksum_6(sf),  col4(sf)),
		"{} {}".format(make_chksum_6(esf), col4(esf))
	)

	chk = make_chksum_6(" ".join(lines))
	outfile="{}-{}[{},{}].{}".format(
		seed_id,key_id,seed_len,hash_preset,g.wallet_ext)

	c = False if g.quiet else True
	d = "\n".join((chk,)+lines)+"\n"
	write_to_file(outfile,d,opts,"wallet",c,True)

	if g.verbose:
		display_control_data(label,metadata,hash_preset,salt,enc_seed)


def _check_mmseed_format(words):

	valid = False
	what = "%s data" % g.seed_ext
	try:
		chklen = len(words[0])
	except:
		return False

	if len(words) < 3 or len(words) > 12:
		msg("Invalid data length (%s) in %s" % (len(words),what))
	elif not _is_hex(words[0]):
		msg("Invalid format of checksum '%s' in %s"%(words[0], what))
	elif chklen != 6:
		msg("Incorrect length of checksum (%s) in %s" % (chklen,what))
	else: valid = True

	return valid


def _check_wallet_format(infile, lines):

	what = "wallet file '%s'" % infile
	valid = False
	chklen = len(lines[0])
	if len(lines) != 6:
		vmsg("Invalid number of lines (%s) in %s" % (len(lines),what))
	elif chklen != 6:
		vmsg("Incorrect length of Master checksum (%s) in %s" % (chklen,what))
	elif not _is_hex(lines[0]):
		vmsg("Invalid format of Master checksum '%s' in %s"%(lines[0], what))
	else: valid = True

	if valid == False:
		msg("Invalid %s" % what)
		sys.exit(2)


def _check_chksum_6(chk,val,desc,infile):
	comp_chk = make_chksum_6(val)
	if chk != comp_chk:
		msg("%s checksum incorrect in file '%s'!" % (desc,infile))
		msg("Checksum: %s. Computed value: %s" % (chk,comp_chk))
		sys.exit(2)
	elif g.debug:
		print "%s checksum passed: %s" % (desc.capitalize(),chk)


def get_data_from_wallet(infile,silent=False):

	# Don't make this a qmsg: User will be prompted for passphrase and must see
	# the filename.
	if not silent and not g.quiet:
		msg("Getting {} wallet data from file '{}'".format(g.proj_name,infile))

	f = open_file_or_exit(infile, 'r')

	lines = [i.strip() for i in f.readlines()]
	f.close()

	_check_wallet_format(infile, lines)

	label = lines[1]

	metadata = lines[2].split()

	for i in 0,1: metadata[i] = metadata[i].upper()

	hd = lines[3].split()
	hash_preset = hd[0][:-1]
	hash_params = [int(i) for i in hd[1:]]

	if hash_params != get_hash_params(hash_preset):
		msg("Hash parameters '%s' don't match hash preset '%s'" %
				(" ".join(hash_params), hash_preset))
		sys.exit(9)

	res = {}
	for i,key in (4,"salt"),(5,"enc_seed"):
		l = lines[i].split()
		val = "".join(l[1:])
		_check_chksum_6(l[0], val, key, infile)
		res[key] = b58decode_pad(val)
		if res[key] == False:
			msg("Invalid b58 number: %s" % val)
			sys.exit(9)

	_check_chksum_6(lines[0], " ".join(lines[1:]), "Master", infile)

	return label,metadata,hash_preset,res['salt'],res['enc_seed']


def _get_words_from_user(prompt, opts):
	# split() also strips
	words = my_raw_input(prompt,
				echo=True if 'echo_passphrase' in opts else False).split()
	if g.debug: print "Sanitized input: [%s]" % " ".join(words)
	return words


def _get_words_from_file(infile,what):
	qmsg("Getting %s from file '%s'" % (what,infile))
	f = open_file_or_exit(infile, 'r')
	# split() also strips
	words = f.read().split()
	f.close()
	if g.debug: print "Sanitized input: [%s]" % " ".join(words)
	return words


def get_words(infile,what,prompt,opts):
	if infile:
		return _get_words_from_file(infile,what)
	else:
		return _get_words_from_user(prompt,opts)

def remove_comments(lines):
	import re
	# re.sub(pattern, repl, string, count=0, flags=0)
	ret = []
	for i in lines:
		i = re.sub('#.*','',i,1)
		i = re.sub('\s+$','',i)
		if i: ret.append(i)
	return ret

def get_lines_from_file(infile,what="",trim_comments=False):
	if what != "":
		qmsg("Getting %s from file '%s'" % (what,infile))
	f = open_file_or_exit(infile,'r')
	lines = f.read().splitlines()
	f.close()
	return remove_comments(lines) if trim_comments else lines


def get_data_from_file(infile,what="data",dash=False):
	if dash and infile == "-": return sys.stdin.read()
	qmsg("Getting %s from file '%s'" % (what,infile))
	f = open_file_or_exit(infile,'r')
	data = f.read()
	f.close()
	return data


def get_seed_from_seed_data(words):

	if not _check_mmseed_format(words):
		msg("Invalid %s data" % g.seed_ext)
		return False

	stored_chk = words[0]
	seed_b58 = "".join(words[1:])

	chk = make_chksum_6(seed_b58)
	vmsg_r("Validating %s checksum..." % g.seed_ext)

	if compare_checksums(chk, "from seed", stored_chk, "from input"):
		seed = b58decode_pad(seed_b58)
		if seed == False:
			msg("Invalid b58 number: %s" % val)
			return False

		vmsg("%s data produces seed ID: %s" % (g.seed_ext,make_chksum_8(seed)))
		return seed
	else:
		msg("Invalid checksum for {} seed".format(g.proj_name))
		return False


passwd_file_used = False

def mark_passwd_file_as_used(opts):
	global passwd_file_used
	if passwd_file_used:
		msg_r("WARNING: Reusing passphrase from file '%s'." % opts['passwd_file'])
		msg(" This may not be what you want!")
	passwd_file_used = True


def get_mmgen_passphrase(prompt,opts):
	if 'passwd_file' in opts:
		mark_passwd_file_as_used(opts)
		return " ".join(_get_words_from_file(opts['passwd_file'],"passphrase"))
	else:
		return " ".join(_get_words_from_user(prompt,opts))


def get_bitcoind_passphrase(prompt,opts):
	if 'passwd_file' in opts:
		mark_passwd_file_as_used(opts)
		return get_data_from_file(opts['passwd_file'],
				"passphrase").strip("\r\n")
	else:
		return my_raw_input(prompt,
					echo=True if 'echo_passphrase' in opts else False)


def check_data_fits_file_at_offset(fname,offset,dlen,action):
	# TODO: Check for Windows
	import os, stat
	if stat.S_ISBLK(os.stat(fname).st_mode):
		fd = os.open(fname, os.O_RDONLY)
		fsize = os.lseek(fd, 0, os.SEEK_END)
		os.close(fd)
	else:
		fsize = os.stat(fname).st_size

	if fsize < offset + dlen:
		msg(
"Destination file has length %s, too short to %s %s bytes of data at offset %s"
			% (fsize,action,dlen,offset))
		sys.exit(1)


def get_hidden_incog_data(opts):
		# Already sanity-checked:
		fname,offset,seed_len = opts['from_incog_hidden'].split(",")
		qmsg("Getting hidden incog data from file '%s'" % fname)

		dlen = g.aesctr_iv_len + g.salt_len + (int(seed_len)/8)

		fsize = check_data_fits_file_at_offset(fname,int(offset),dlen,"read")

		f = os.open(fname,os.O_RDONLY)
		os.lseek(f, int(offset), os.SEEK_SET)
		data = os.read(f, dlen)
		os.close(f)
		qmsg("Data read from file '%s' at offset %s" % (fname,offset),
				"Data read from file")
		return data


def export_to_hidden_incog(incog_enc,opts):
	outfile,offset = opts['export_incog_hidden'].split(",") #Already sanity-checked
	if 'outdir' in opts: outfile = make_full_path(opts['outdir'],outfile)

	check_data_fits_file_at_offset(outfile,int(offset),len(incog_enc),"write")

	if not g.quiet: confirm_or_exit("","alter file '%s'" % outfile)
	f = os.open(outfile,os.O_RDWR)
	os.lseek(f, int(offset), os.SEEK_SET)
	os.write(f, incog_enc)
	os.close(f)
	msg("Data written to file '%s' at offset %s" %
			(os.path.relpath(outfile),offset))


from mmgen.term import kb_hold_protect,get_char

def my_raw_input(prompt,echo=True):
	msg_r(prompt)
	kb_hold_protect()
	try:
		if echo:
			reply = raw_input("")
		else:
			from getpass import getpass
			reply = getpass("")
	except KeyboardInterrupt:
		msg("\nUser interrupt")
		sys.exit(1)

	kb_hold_protect()
	return reply


def user_confirm(prompt,default_yes=False,verbose=False):

	q = "(Y/n)" if default_yes else "(y/N)"

	while True:
		reply = get_char("%s %s: " % (prompt, q)).strip("\n\r")

		if not reply:
			if default_yes: msg(""); return True
			else:           msg(""); return False
		elif reply in 'yY': msg(""); return True
		elif reply in 'nN': msg(""); return False
		else:
			if verbose: msg("\nInvalid reply")
			else: msg_r("\r")


def prompt_and_get_char(prompt,chars,enter_ok=False,verbose=False):

	while True:
		reply = get_char("%s: " % prompt).strip("\n\r")

		if reply in chars or (enter_ok and not reply):
			msg("")
			return reply

		if verbose: msg("\nInvalid reply")
		else: msg_r("\r")

