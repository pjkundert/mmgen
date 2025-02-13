# MMGen = Multi-Mode GENerator

##### An online/offline cryptocurrency wallet for the command line

### Description

MMGen is a wallet and cold storage solution for Bitcoin (and selected altcoins)
implemented as a suite of lightweight Python scripts.  The scripts work in
tandem with a reference Bitcoin or altcoin daemon running on both online and
offline computers to provide a robust solution for securely storing, tracking,
sending and receiving your crypto assets.

The online computer is used for tracking balances and creating and sending
transactions, while the offline machine (typically an air-gapped, low-power
device such as a Raspberry Pi) takes care of wallet creation, address generation
and transaction signing.  All operations involving secret data are handled
offline: **your seed and private keys never come into contact with a
network-connected device.**

MMGen is designed for reliability by having the reference Bitcoin or altcoin
daemon, rather than less-tested third-party software, do all the “heavy lifting”
of tracking and signing transactions.  It’s also designed with privacy in mind:
unlike some other online/offline wallets, MMGen is a completely self-contained
system that makes **no connections to the Internet** apart from the coin network
itself: no information about which addresses you’re tracking is ever leaked to
the outside world.

Like all deterministic wallets, MMGen can generate a virtually unlimited number
of address/key pairs from a single seed.  Your wallet never changes, so you need
back it up only once.

At the heart of the MMGen system is the seed, the “master key” providing access
to all your crypto assets.  The seed can be stored in many different formats:
as a password-encrypted wallet (the default), as a one-line base58 or
hexadecimal seed file, as formatted “dieroll base6” data, as an Electrum-based
or BIP39 mnemonic seed phrase, as a brainwallet passphrase, or as “incognito
data” hideable within random data in a file or block device.  Conversion among
all formats is supported.

***mmgen-txcreate running in a terminal window***
![mmgen-txcreate running in a terminal window][9]

#### Simplified key derivation and seed-phrase generation

To deterministically derive its keys, MMGen uses a non-hierarchical scheme
differing from the BIP32 protocol on which most of today’s popular wallets are
based.  One advantage of this simple, hash-based scheme is that you can easily
[recover your private keys from your seed without the MMGen program itself][K]
using standard command-line utilities.

MMGen also differs from most cryptocurrency wallets today in its use of the
original 1626-word [Electrum wordlist][ew] for mnemonic seed phrases.  Seed
phrases are derived using ordinary base conversion, similarly allowing you to
regenerate your seed from your seed phrase without MMGen program itself, should
the need arise.  An example of how to do this at the Python prompt is provided
[here.][S]

The original Electrum wordlist was derived from a [frequency list][fl] of words
found in contemporary English poetry.  The high emotional impact of these words
makes seed phrases easy to memorize.  Curiously, only 861 of them are shared by
the more prosaic 2048-word [BIP39 wordlist][bw] used in most wallets today.

Beginning with version 0.12.0, the BIP39 mnemonic format is also supported,
allowing you to use MMGen as a master wallet for other wallets supporting that
widespread standard.

#### A brief overview of MMGen’s unique feature set:

- **[Full transaction and address tracking support][T]** for Bitcoin, [Bcash][bx],
  [Litecoin][bx], [Ethereum][E], Ethereum Classic and [ERC20 tokens][E].
- **Monero transacting and wallet management** via the interactive
  [`mmgen-xmrwallet`][xm] command.  Offline transaction signing is possible
  using a shared blockchain between online and offline machines.
- **[Address generation support][ag]** for the above coins, plus [Zcash][zx]
  (t and z addresses) and [144 Bitcoin-derived altcoins][ax].
- **Support for all Bitcoin address types** including Segwit-P2SH and Bech32.
- **Independent key derivation for each address type:** No two addresses ever
  share the same private key.  Certain wallets in wide use today regrettably
  fail to guarantee this property, leading to the danger of inadvertent key
  reuse.
- **Coin control:** You select the outputs your transaction will spend.  An
  essential requirement for maintaining anonymity.
- **[BIP69 transaction input and output ordering][69]** helps anonymize the
  “signature” of your transactions.
- **[Full control over transaction fees][M]:** Fees are specified as absolute or
  satoshi/byte amounts and can be adjusted interactively, letting you round fees
  to improve anonymity.  Network fee estimation (with selectable estimation
  mode), [RBF][R] and [fee bumping][B] are supported.
- **Support for nine wallet formats:** three encrypted (native wallet,
  brainwallet, incognito wallet) and six unencrypted (native mnemonic,
  **BIP39,** mmseed, hexseed, plain hex, dieroll).
- Interactive **dieroll wallet** generation via `mmgen-walletconv -i dieroll`.
- Support for new-style **Monero mnemonics** in `mmgen-tool` and `mmgen-passgen`.
- **[Subwallets][U]:** Subwallets have many applications, the most notable being
  online hot wallets, decoy wallets and travel wallets.  MMGen subwallets are
  functionally and externally identical to ordinary wallets, which provides a
  key security benefit: only the user who generated the subwallet knows that it
  is indeed a subwallet.  Subwallets don’t need to be backed up, as they can
  always be regenerated from their parent.
- **[XOR (N-of-N) seed splitting][O]** with shares exportable to all MMGen
  wallet formats.  The [master share][ms] feature allows you to create multiple
  splits with a single master share.
- **[Transaction autosigning][X]:** This feature puts your offline signing
  machine into “hands-off” mode, allowing you to transact directly from cold
  storage securely and conveniently.  Additional LED signaling support is
  provided for Raspbian and Armbian platforms.
- **[Password generation][G]:** MMGen can be used to generate and manage your
  online passwords.  Password lists are identified by arbitrarily chosen strings
  like “alice@github” or “bob@reddit”.  Passwords of different lengths and
  formats, including BIP39, are supported.
- **Selectable seed lengths** of 128, 192 or 256 bits.  Subwallets may have
  shorter seeds than their parent.
- **User-enhanced entropy:** All operations requiring random data will prompt
  you for additional entropy from the keyboard.  Keystroke timings are used in
  addition to the characters typed.
- **Wallet-free operation:** All wallet operations can be performed directly
  from your seed phrase at the prompt, allowing you to dispense with a
  physically stored wallet entirely if you wish.
- Word-completing **mnemonic entry modes** customized for each of MMGen’s
  supported wordlists minimize keystrokes during seed phrase entry.
- **Stealth mnemonic entry:** This feature allows you to obfuscate your seed
  phrase with “dead” keystrokes to guard against acoustic side-channel attacks.
- **Network privacy:** MMGen never “calls home” or checks for upgrades over the
  network.  No information about your wallet installation or crypto assets is
  ever leaked to third parties.
- **Human-readable wallet files:** All of MMGen’s wallet formats, with the
  exception of incognito wallets, can be printed or copied by hand.
- **Terminal-based:** MMGen can be run in a screen or tmux session on your local
  network.
- **Scriptability:** Most MMGen commands can be made non-interactive, allowing
  you to automate repetitive tasks using shell scripts.
- The project also includes the [`mmgen-tool`][L] utility, a handy “pocket
  knife” for cryptocurrency developers, along with an easy-to-use [**tool API
  interface**][ta] providing access to a subset of its commands from within
  Python.

#### Supported platforms:

Linux, Armbian, Raspbian, Windows/MSYS2

### Download/Install

> #### [Install from source on Microsoft Windows][1]

> #### [Install from source on Debian, Ubuntu, Raspbian, Armbian or Arch Linux][2]


### Using MMGen

> #### [Getting Started with MMGen][3]

> #### [MMGen Quick Start with Regtest Mode][Q]

> #### [MMGen command help][6]

> #### [Recovering your keys without the MMGen software][K]

> #### [Altcoin and Forkcoin support (ETH,ETC,XMR,ZEC,LTC,BCH and 144 Bitcoin-derived alts)][F]

> #### [Subwallets][U]

> #### [XOR Seed Splitting][O]

> #### [Test Suite][ts]

> #### [Tool API][ta]

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

[**Forum**][4] |
[Reddit][0] |
[PGP Public Keys][5] |
Donate (BTC,BCH): 15TLdmi5NYLdqmtCqczUs5pBPkJDXRs83w

[0]: https://www.reddit.com/user/mmgen-py
[1]: https://github.com/mmgen/mmgen/wiki/Install-MMGen-on-Microsoft-Windows
[2]: https://github.com/mmgen/mmgen/wiki/Install-MMGen-on-Linux
[3]: https://github.com/mmgen/mmgen/wiki/Getting-Started-with-MMGen
[4]: https://bitcointalk.org/index.php?topic=567069.0
[5]: https://github.com/mmgen/mmgen/wiki/MMGen-Signing-Keys
[6]: https://github.com/mmgen/mmgen/wiki/MMGen-command-help
[7]: http://bitcoinmagazine.com/8396/deterministic-wallets-advantages-flaw/
[8]: https://github.com/mmgen/MMGenLive
[9]: https://cloud.githubusercontent.com/assets/6071028/20677261/6ccab1bc-b58a-11e6-8ab6-094f88befef2.jpg
[Q]: https://github.com/mmgen/mmgen/wiki/MMGen-Quick-Start-with-Regtest-Mode
[K]: https://github.com/mmgen/mmgen/wiki/Recovering-Your-Keys-Without-the-MMGen-Software
[S]: https://github.com/mmgen/mmgen/wiki/Recovering-Your-Keys-Without-the-MMGen-Software#a_mh
[F]: https://github.com/mmgen/mmgen/wiki/Altcoin-and-Forkcoin-Support
[W]: https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki
[ew]: https://github.com/spesmilo/electrum/blob/1.9.5/lib/mnemonic.py
[bw]: https://github.com/bitcoin/bips/blob/master/bip-0039/english.txt
[fl]: https://en.wiktionary.org/wiki/Wiktionary:Frequency_lists/Contemporary_poetry
[U]: https://github.com/mmgen/mmgen/wiki/Subwallets
[X]: https://github.com/mmgen/mmgen/wiki/autosign-[MMGen-command-help]
[xm]: https://github.com/mmgen/mmgen/wiki/xmrwallet-[MMGen-command-help]
[G]: https://github.com/mmgen/mmgen/wiki/passgen-[MMGen-command-help]
[T]: https://github.com/mmgen/mmgen/wiki/Getting-Started-with-MMGen#a_ct
[E]: https://github.com/mmgen/mmgen/wiki/Altcoin-and-Forkcoin-Support#a_tx
[ag]: https://github.com/mmgen/mmgen/wiki/addrgen-[MMGen-command-help]
[bx]: https://github.com/mmgen/mmgen/wiki/Altcoin-and-Forkcoin-Support#a_bch
[mx]: https://github.com/mmgen/mmgen/wiki/Altcoin-and-Forkcoin-Support#a_xmr
[zx]: https://github.com/mmgen/mmgen/wiki/Altcoin-and-Forkcoin-Support#a_zec
[ax]: https://github.com/mmgen/mmgen/wiki/Altcoin-and-Forkcoin-Support#a_kg
[M]: https://github.com/mmgen/mmgen/wiki/Getting-Started-with-MMGen#a_fee
[R]: https://github.com/mmgen/mmgen/wiki/Getting-Started-with-MMGen#a_rbf
[B]: https://github.com/mmgen/mmgen/wiki/txbump-[MMGen-command-help]
[69]: https://github.com/bitcoin/bips/blob/master/bip-0069.mediawiki
[O]: https://github.com/mmgen/mmgen/wiki/XOR-Seed-Splitting:-Theory-and-Practice
[ms]: https://github.com/mmgen/mmgen/wiki/seedsplit-[MMGen-command-help]
[ta]: https://github.com/mmgen/mmgen/wiki/Tool-API
[ts]: https://github.com/mmgen/mmgen/wiki/Test-Suite
[L]: https://github.com/mmgen/mmgen/wiki/tool-[MMGen-command-help].md
