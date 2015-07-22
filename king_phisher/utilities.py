#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/utilities.py
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
#

import datetime
import ipaddress
import logging
import os
import random
import re
import shlex
import string
import subprocess
import sys

from king_phisher import color
from king_phisher import its
from king_phisher import version

from dateutil import tz
from smoke_zephyr.utilities import which

EMAIL_REGEX = re.compile(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,6}$', flags=re.IGNORECASE)

class Mock(object):
	"""
	A fake object used to replace missing imports when generating documentation.
	"""
	__all__ = []
	def __init__(self, *args, **kwargs):
		pass

	def __call__(self, *args, **kwargs):
		return Mock()

	@classmethod
	def __getattr__(cls, name):
		if name in ('__file__', '__path__'):
			return os.devnull
		else:
			return Mock()

	@classmethod
	def __setattr__(cls, name):
		pass

	def __getitem__(self, name):
		return Mock()

	def __setitem__(self, name, value):
		pass

def argp_add_args(parser, default_root=''):
	"""
	Add standard arguments to a new :py:class:`argparse.ArgumentParser` instance
	for configuring logging options from the command line and displaying the
	version information.

	:param parser: The parser to add arguments to.
	:type parser: :py:class:`argparse.ArgumentParser`
	:param str default_root: The default root logger to specify.
	"""
	parser.add_argument('-v', '--version', action='version', version=parser.prog + ' Version: ' + version.version)
	parser.add_argument('-L', '--log', dest='loglvl', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='WARNING', help='set the logging level')
	parser.add_argument('--logger', default=default_root, help='specify the root logger')

def configure_stream_logger(level, logger):
	"""
	Configure the default stream handler for logging messages to the console.
	This also configures the basic logging environment for the application.

	:param level: The level to set the logger to.
	:type level: int, str
	:param str logger: The logger to add the stream handler for.
	:return: The new configured stream handler.
	:rtype: :py:class:`logging.StreamHandler`
	"""
	if isinstance(level, str):
		level = getattr(logging, level)
	root_logger = logging.getLogger('')
	for handler in root_logger.handlers:
		root_logger.removeHandler(handler)

	logging.getLogger(logger).setLevel(logging.DEBUG)
	console_log_handler = logging.StreamHandler()
	console_log_handler.setLevel(level)
	if its.on_linux:
		console_log_handler.setFormatter(color.ColoredLogFormatter("%(levelname)s %(message)s"))
	else:
		console_log_handler.setFormatter(logging.Formatter("%(levelname)-8s %(message)s"))
	logging.getLogger(logger).addHandler(console_log_handler)
	logging.captureWarnings(True)
	return console_log_handler

def datetime_local_to_utc(dt):
	"""
	Convert a :py:class:`datetime.datetime` instance from the local time to UTC
	time.

	:param dt: The time to convert from local to UTC.
	:type dt: :py:class:`datetime.datetime`
	:return: The time converted to the UTC timezone.
	:rtype: :py:class:`datetime.datetime`
	"""
	dt = dt.replace(tzinfo=tz.tzlocal())
	dt = dt.astimezone(tz.tzutc())
	return dt.replace(tzinfo=None)

def datetime_utc_to_local(dt):
	"""
	Convert a :py:class:`datetime.datetime` instance from UTC time to the local
	time.

	:param dt: The time to convert from UTC to local.
	:type dt: :py:class:`datetime.datetime`
	:return: The time converted to the local timezone.
	:rtype: :py:class:`datetime.datetime`
	"""
	dt = dt.replace(tzinfo=tz.tzutc())
	dt = dt.astimezone(tz.tzlocal())
	return dt.replace(tzinfo=None)

def format_datetime(dt):
	"""
	Format a date time object into a string. If the object *dt* is not an
	instance of :py:class:`datetime.datetime` then an empty string will be
	returned.

	:param dt: The object to format.
	:type dt: :py:class:`datetime.datetime`
	:return: The string representing the formatted time.
	:rtype: str
	"""
	if not isinstance(dt, datetime.datetime):
		return ''
	return dt.strftime('%Y-%m-%d %H:%M:%S')

def is_valid_email_address(email_address):
	"""
	Check that the string specified appears to be a valid email address.

	:param str email_address: The email address to validate.
	:return: Whether the email address appears to be valid or not.
	:rtype: bool
	"""
	if email_address == None:
		return False
	return EMAIL_REGEX.match(email_address) != None

def is_valid_ip_address(ip_address):
	"""
	Check that the string specified appears to be either a valid IPv4 or IPv6
	address.

	:param str ip_address: The IP address to validate.
	:return: Whether the IP address appears to be valid or not.
	:rtype: bool
	"""
	try:
		ipaddress.ip_address(ip_address)
	except ValueError:
		return False
	return True

def open_uri(uri):
	"""
	Open a URI in a platform intelligent way. On Windows this will use
	'cmd.exe /c start' and on Linux this will use gvfs-open or xdg-open
	depending on which is available. If no suitable application can be
	found to open the URI, a RuntimeError will be raised.

	:param str uri: The URI to open.
	"""
	proc_args = []
	if sys.platform.startswith('win'):
		proc_args.append(which('cmd.exe'))
		proc_args.append('/c')
		proc_args.append('start')
	elif which('gvfs-open'):
		proc_args.append(which('gvfs-open'))
	elif which('xdg-open'):
		proc_args.append(which('xdg-open'))
	else:
		raise RuntimeError('could not find suitable application to open uri')
	proc_args.append(uri)
	return start_process(proc_args)

def random_string(size):
	"""
	Generate a random string consisting of uppercase letters, lowercase letters
	and numbers of the specified size.

	:param int size: The size of the string to make.
	:return: The string containing the random characters.
	:rtype: str
	"""
	return ''.join(random.choice(string.ascii_letters + string.digits) for x in range(size))

def random_string_lower_numeric(size):
	"""
	Generate a random string consisting of lowercase letters and numbers of the
	specified size.

	:param int size: The size of the string to make.
	:return: The string containing the random characters.
	:rtype: str
	"""
	return ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(size))

def start_process(proc_args, wait=True):
	"""
	Start an external process.

	:param proc_args: The arguments of the process to start.
	:type proc_args: list, str
	:param bool wait: Wait for the process to exit before returning.
	"""
	if isinstance(proc_args, str):
		proc_args = shlex.split(proc_args)
	close_fds = True
	startupinfo = None
	preexec_fn = None if wait else getattr(os, 'setsid', None)
	if sys.platform.startswith('win'):
		close_fds = False
		startupinfo = subprocess.STARTUPINFO()
		startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
		startupinfo.wShowWindow = subprocess.SW_HIDE

	proc_h = subprocess.Popen(proc_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=preexec_fn, close_fds=close_fds, startupinfo=startupinfo)
	if not wait:
		return proc_h
	return proc_h.wait() == 0
