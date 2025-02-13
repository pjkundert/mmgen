#!/usr/bin/env python3

# Import as few modules and define as few names as possible at global level before exec'ing the
# file, as all names will be seen by the exec'ed code.  To prevent name collisions, all names
# defined here should begin with 'exec_wrapper_'

import sys,os,time

def exec_wrapper_get_colors():
	from collections import namedtuple
	return namedtuple('colors',['red','green','yellow','blue'])(*[
			(lambda s:s) if os.getenv('MMGEN_DISABLE_COLOR') else
			(lambda s,n=n:f'\033[{n};1m{s}\033[0m' )
		for n in (31,32,33,34) ])

def exec_wrapper_init(): # don't change: name is used to test if script is running under exec_wrapper

	if os.path.dirname(sys.argv[1]) == 'test': # scripts in ./test do overlay setup themselves
		sys.path[0] = 'test'
	else:
		from test.overlay import overlay_setup
		sys.path[0] = overlay_setup(repo_root=os.getcwd()) # assume we're in the repo root

	os.environ['MMGEN_TRACEBACK'] = '1'
	os.environ['PYTHONPATH'] = '.'
	if 'TMUX' in os.environ:
		del os.environ['TMUX']

	if not os.getenv('EXEC_WRAPPER_NO_TRACEBACK'):
		try:
			os.unlink('my.err')
		except:
			pass

def exec_wrapper_write_traceback():
	import traceback,re
	lines = traceback.format_exception(*sys.exc_info()) # returns a list

	pat = re.compile('File "<string>"')
	repl = f'File "{exec_wrapper_execed_file}"'
	lines = [pat.sub(repl,line,count=1) for line in lines]

	exc = lines.pop()
	if exc.startswith('SystemExit:'):
		lines.pop()

	c = exec_wrapper_get_colors()
	sys.stdout.write('{}{}'.format(c.yellow(''.join(lines)),c.red(exc)))

	open('my.err','w').write(''.join(lines+[exc]))

def exec_wrapper_end_msg():
	if os.getenv('EXEC_WRAPPER_SPAWN') and not os.getenv('MMGEN_TEST_SUITE_DETERMINISTIC'):
		c = exec_wrapper_get_colors()
		# write to stdout to ensure script output gets to terminal first
		sys.stdout.write(c.blue('Runtime: {:0.5f} secs\n'.format(time.time() - exec_wrapper_tstart)))

exec_wrapper_init() # sets sys.path[0]
exec_wrapper_tstart = time.time()

try:
	sys.argv.pop(0)
	exec_wrapper_execed_file = sys.argv[0]
	exec(open(sys.argv[0]).read())
except SystemExit as e:
	if e.code != 0 and not os.getenv('EXEC_WRAPPER_NO_TRACEBACK'):
		exec_wrapper_write_traceback()
	else:
		exec_wrapper_end_msg()
	sys.exit(e.code)
except Exception as e:
	exec_wrapper_write_traceback()
	retval = e.mmcode if hasattr(e,'mmcode') else e.code if hasattr(e,'code') else 1
	sys.exit(retval)

exec_wrapper_end_msg()
