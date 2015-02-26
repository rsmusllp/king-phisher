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
import os
import random
import re
import shlex
import string
import subprocess
import sys
import time

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

def datetime_utc_to_local(dt):
	"""
	Convert a :py:class:`datetime.datetime` instance from UTC time to the local
	time.

	:param dt: The time to convert from UTC to local.
	:type dt: :py:class:`datetime.datetime`
	:return: The time converted to the local timezone.
	:rtype: :py:class:`datetime.datetime`
	"""
	return dt - datetime.timedelta(seconds=time.timezone)

def escape_single_quote(string):
	"""
	Escape a string containing single quotes and backslashes with backslashes.
	This is useful when a string is evaluated in some way.

	:param str string: The string to escape.
	:return: The escaped string.
	:rtype: str
	"""
	return re.sub('(\'|\\\)', r'\\\1', string)

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

def server_parse(server, default_port):
	"""
	Convert a server string to a tuple suitable for passing to connect, for
	example converting 'www.google.com:443' to ('www.google.com', 443).

	:param str server: The server string to convert.
	:param int default_port: The port to use in case one is not specified
		in the server string.
	:return: The parsed server information.
	:rtype: tuple
	"""
	server = server.rsplit(':', 1)
	host = server[0]
	if host.startswith('[') and host.endswith(']'):
		host = host[1:-1]
	if len(server) == 1:
		return (host, default_port)
	else:
		port = server[1]
		if not port:
			port = default_port
		else:
			port = int(port)
		return (host, port)

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

def timedef_to_seconds(timedef):
	"""
	Convert a string timespan definition to seconds, for example converting
	'1m30s' to 90.

	:param str timedef: The timespan definition to convert to seconds.
	:return: The converted value in seconds.
	:rtype: int
	"""
	converter_order = ['w', 'd', 'h', 'm', 's']
	converters = {
		'w': 604800,
		'd': 86400,
		'h': 3600,
		'm': 60,
		's': 1
	}
	timedef = timedef.lower()
	if timedef.isdigit():
		return int(timedef)
	elif len(timedef) == 0:
		return 0
	seconds = -1
	for spec in converter_order:
		timedef = timedef.split(spec)
		if len(timedef) == 1:
			timedef = timedef[0]
			continue
		elif len(timedef) > 2 or not timedef[0].isdigit():
			seconds = -1
			break
		adjustment = converters[spec]
		seconds = max(seconds, 0)
		seconds += (int(timedef[0]) * adjustment)
		timedef = timedef[1]
		if not len(timedef):
			break
	if seconds < 0:
		raise ValueError('invalid time format')
	return seconds

def unescape_single_quote(string):
	"""
	Unescape a string which uses backslashes to escape single quotes.

	:param str string: The string to unescape.
	:return: The unescaped string.
	:rtype: str
	"""
	string = string.replace('\\\\', '\\')
	string = string.replace('\\\'', '\'')
	return string

def unique(seq, key=None):
	"""
	Create a list or tuple consisting of the unique elements of *seq* and
	preserve their order.

	:param seq: The list or tuple to preserve unique items from.
	:type seq: list, tuple
	:param function key: If key is provided it will be called during the
		comparison process.
	:return: An object of the same type as *seq* and contaning its unique elements.
	"""
	if key is None:
		key = lambda x: x
	preserved_type = type(seq)
	seen = {}
	result = []
	for item in seq:
		marker = key(item)
		if marker in seen:
			continue
		seen[marker] = 1
		result.append(item)
	return preserved_type(result)

def which(program):
	"""
	Locate an executable binary's full path by its name.

	:param str program: The executable's name.
	:return: The full path to the executable.
	:rtype: str
	"""
	is_exe = lambda fpath: (os.path.isfile(fpath) and os.access(fpath, os.X_OK))
	for path in os.environ['PATH'].split(os.pathsep):
		path = path.strip('"')
		exe_file = os.path.join(path, program)
		if is_exe(exe_file):
			return exe_file
	if is_exe(program):
		return os.path.abspath(program)
	return None
