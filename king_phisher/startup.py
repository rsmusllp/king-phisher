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

import os
import gc
import subprocess

from king_phisher import version

def run_process(process_args, cwd=os.getcwd()):
	process_handle = subprocess.Popen(process_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
	process_handle.wait()
	return process_handle.stdout.read().decode('utf-8'), process_handle.returncode

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

def argb_add_default_args(parser, default_root=''):
	"""
	Add standard arguments to a new :py:class:`argparse.ArgumentParser` instance
	Used to add the utilities argparse options to the wrapper for display

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
	kpc_group = parser.add_argument_group('King Phisher Client')
	kpc_group.add_argument('-c', '--config', dest='config_file', required=False, help='specify a configuration file to use')
	kpc_group.add_argument('--no-plugins', dest='use_plugins', default=True, action='store_false', help='disable all plugins')
	kpc_group.add_argument('--no-style', dest='use_style', default=True, action='store_false', help='disable interface styling')
	return parser

def argp_add_server(parser):
	kps_group = parser.add_argument_group('King Phisher Server')
	kps_group.add_argument('-f', '--foreground', dest='foreground', action='store_true', default=False, help='run in the foreground (do not fork)')
	kps_group.add_argument('--update-geoip-db', dest='update_geoip_db', action='store_true', default=False, help='update the geoip database and exit')
	kps_group.add_argument('--verify-config', dest='verify_config', action='store_true', default=False, help='verify the configuration and exit')
	kps_group.add_argument('config_file', action='store', help='configuration file to use')
	return parser

def argp_add_wrapper(parser):
	kpw_group = parser.add_argument_group('King Phisher pipenv wrapper')
	kpw_group.add_argument('--env-update', dest='pipenv_update', default=False, action='store_true', help='update pipenv requirments and exit')
	kpw_group.add_argument('--env-install', dest='pipenv_install', default=False, action='store_true', help='install pipenv environment and exit')
	return parser
