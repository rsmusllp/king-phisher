#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/startup.py
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are
#  met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following disclaimer
#    in the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of the project nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import collections
import gc
import logging
import os
import shutil
import subprocess
import sys

from king_phisher import its
from king_phisher import version

ProcessResults = collections.namedtuple('ProcessResults', ('stdout', 'stderr', 'status'))

def pipenv_entry(parser, entrypoint):
	if its.on_windows:
		# this is because of the os.exec call and os.EX_* status codes
		raise RuntimeError('pipenv_entry is incompatible with windows')
	argp_add_wrapper(parser)
	argp_add_default_args(parser)

	arguments, _ = parser.parse_known_args()
	sys_argv = sys.argv
	sys_argv.pop(0)

	if sys.version_info < (3, 4):
		print('[-] the Python version is too old (minimum required is 3.4)')
		return os.EX_SOFTWARE

	# initialize basic stream logging
	logger = logging.getLogger('KingPhisher.wrapper')
	logger.setLevel(arguments.loglvl if arguments.loglvl else 'WARNING')
	console_log_handler = logging.StreamHandler()
	console_log_handler.setLevel(arguments.loglvl if arguments.loglvl else 'WARNING')
	console_log_handler.setFormatter(logging.Formatter('%(levelname)-8s %(message)s'))
	logger.addHandler(console_log_handler)

	target_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
	logger.debug("target diretory: {}".format(target_directory))

	os.environ['PIPENV_VENV_IN_PROJECT'] = os.environ.get('PIPENV_VENV_IN_PROJECT', 'True')
	os.environ['PIPENV_PIPFILE'] = os.environ.get('PIPENV_PIPFILE', os.path.join(target_directory, 'Pipfile'))

	logger.info('checking for the pipenv environment')
	if which('pipenv') is None:
		logger.info('installing pipenv from PyPi using pip')
		results = run_process([sys.executable, '-m', 'pip', 'install', 'pipenv'], cwd=target_directory)
		if results.status:
			sys.stderr.write('the following issue occurred during installation of pipenv:\n')
			sys.stderr.write(results.stdout)
			return results.status

	pipenv_path = which('pipenv')
	logger.debug("pipenv path: {0!r}".format(pipenv_path))
	if not pipenv_path:
		logger.exception('failed to find pipenv')
		return os.EX_UNAVAILABLE

	if arguments.pipenv_install or not os.path.isdir(os.path.join(target_directory, '.venv')):
		if arguments.pipenv_install:
			logger.info('installing the pipenv environment')
		else:
			logger.warning('no pre-existing pipenv environment was found, installing it now')
		results = run_pipenv(('--site-packages', 'install'), cwd=target_directory)
		if results.status:
			logger.error('failed to install the pipenv environment')
			logger.info('removing the incomplete .venv directory')
			try:
				shutil.rmtree(os.path.join(target_directory, '.venv'))
			except OSError:
				logger.error('failed to remove the incomplete .venv directory', exc_info=True)
			return results.status
		if arguments.pipenv_install:
			return os.EX_OK

	if arguments.pipenv_update:
		logger.info('updating the pipenv environment')
		results = run_pipenv(('--site-packages', 'update'), cwd=target_directory)
		if results.status:
			logger.error('failed to update the pipenv environment')
			return results.status
		logger.info('the pipenv environment has been updated')
		return os.EX_OK

	logger.debug('pipenv Pipfile: {}'.format(os.environ['PIPENV_PIPFILE']))
	# the blank arg being passed is required for pipenv
	passing_argv = [' ', 'run', entrypoint] + sys_argv
	os.execve(pipenv_path, passing_argv, os.environ)

def run_pipenv(args, cwd=None):
	path = which('pipenv')
	if path is None:
		return RuntimeError('pipenv could not be found')
	args = (path,) + tuple(args)
	results = run_process(args, cwd=cwd)
	if results.status:
		sys.stderr.write('pipenv encountered the following error:\n')
		sys.stderr.write(results.stdout)
		sys.stderr.flush()
	return results

def run_process(process_args, cwd=None, encoding='utf-8'):
	"""
	Start a process, wait for it to complete and return a
	:py:class:`~.ProcessResults` object.

	:param process_args: The arguments for the processes including the binary.
	:param cwd: An optional current working directory to use for the process.
	:param str encoding: The encoding to use for strings.
	:return: The results of the process including the status code and any text printed to stdout or stderr.
	:rtype: :py:class:`~.ProcessResults`
	"""
	cwd = cwd or os.getcwd()
	process_handle = subprocess.Popen(process_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
	process_handle.wait()
	results = ProcessResults(
		process_handle.stdout.read().decode(encoding),
		process_handle.stderr.read().decode(encoding),
		process_handle.returncode
	)
	return results

def which(program):
	is_exe = lambda fpath: (os.path.isfile(fpath) and os.access(fpath, os.X_OK))
	for path in os.environ['PATH'].split(os.pathsep):
		path = path.strip('"')
		exe_file = os.path.join(path, program)
		if is_exe(exe_file):
			return exe_file
	if is_exe(program):
		return os.path.abspath(program)
	return None

def argp_add_default_args(parser, default_root=''):
	"""
	Add standard arguments to a new :py:class:`argparse.ArgumentParser`
	instance. Used to add the utilities argparse options to the wrapper for
	display.

	:param parser: The parser to add arguments to.
	:type parser: :py:class:`argparse.ArgumentParser`
	:param str default_root: The default root logger to specify.
	"""
	parser.add_argument('-v', '--version', action='version', version=parser.prog + ' Version: ' + version.version)
	parser.add_argument('-L', '--log', dest='loglvl', choices=('DEBUG', 'INFO', 'WARNING', 'ERROR', 'FATAL'), help='set the logging level')
	parser.add_argument('--logger', default=default_root, help='specify the root logger')
	gc_group = parser.add_argument_group('garbage collector options')
	gc_group.add_argument('--gc-debug-leak', action='store_const', const=gc.DEBUG_LEAK, default=0, help='set the DEBUG_LEAK flag')
	gc_group.add_argument('--gc-debug-stats', action='store_const', const=gc.DEBUG_STATS, default=0, help='set the DEBUG_STATS flag')
	return parser

def argp_add_client(parser):
	kpc_group = parser.add_argument_group('client specific options')
	kpc_group.add_argument('-c', '--config', dest='config_file', required=False, help='specify a configuration file to use')
	kpc_group.add_argument('--no-plugins', dest='use_plugins', default=True, action='store_false', help='disable all plugins')
	kpc_group.add_argument('--no-style', dest='use_style', default=True, action='store_false', help='disable interface styling')
	return parser

def argp_add_server(parser):
	kps_group = parser.add_argument_group('server specific options')
	kps_group.add_argument('-f', '--foreground', dest='foreground', action='store_true', default=False, help='run in the foreground (do not fork)')
	kps_group.add_argument('--update-geoip-db', dest='update_geoip_db', action='store_true', default=False, help='update the geoip database and exit')
	kps_group.add_argument('--verify-config', dest='verify_config', action='store_true', default=False, help='verify the configuration and exit')
	kps_group.add_argument('config_file', action='store', help='configuration file to use')
	return parser

def argp_add_wrapper(parser):
	kpw_group = parser.add_argument_group('environment wrapper options')
	kpw_group.add_argument('--env-install', dest='pipenv_install', default=False, action='store_true', help='install pipenv environment and exit')
	kpw_group.add_argument('--env-update', dest='pipenv_update', default=False, action='store_true', help='update pipenv requirements and exit')
	return parser
