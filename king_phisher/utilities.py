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

import collections
import datetime
import distutils.version
import os
import random
import re
import shlex
import string
import subprocess
import sys
import time

import pkg_resources

EMAIL_REGEX = re.compile(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,6}$', flags=re.IGNORECASE)

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

class Cache(object):
	"""
	This class provides a simple to use cache object which can be applied
	as a decorator.
	"""
	def __init__(self, timeout):
		"""
		:param timeout: The amount of time in seconds that a cached
			result will be considered valid for.
		:type timeout: int, str
		"""
		if isinstance(timeout, (str, unicode)):
			timeout = timedef_to_seconds(timeout)
		self.cache_timeout = timeout
		self.__cache = {}

	def __call__(self, *args):
		if not hasattr(self, '_target_function'):
			self._target_function = args[0]
			return self
		self.cache_clean()
		if not isinstance(args, collections.Hashable):
			return self._target_function(*args)
		result, expiration = self.__cache.get(args, (None, 0))
		if expiration > time.time():
			return result
		result = self._target_function(*args)
		self.__cache[args] = (result, time.time() + self.cache_timeout)
		return result

	def __repr__(self):
		return "<cached function {0}>".format(self._target_function.__name__)

	def cache_clean(self):
		"""
		Remove expired items from the cache.
		"""
		now = time.time()
		keys_for_removal = []
		for key, (value, expiration) in self.__cache.items():
			if expiration < now:
				keys_for_removal.append(key)
		for key in keys_for_removal:
			del self.__cache[key]

	def cache_clear(self):
		"""
		Remove all items from the cache.
		"""
		self.__cache = {}

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

def check_requirements(requirements, ignore=None):
	"""
	Parse requirements for package information to determine if all requirements
	are met. The *requirements* argument can be a string to a requirements file,
	a file like object to be read, or a list of strings representing the package
	requirements.

	:param requirements: The file to parse.
	:type requirements: file obj, list, str, tuple
	:param ignore: A sequence of packages to ignore.
	:type ignore: list, tuple
	:return: A list of missing or incompatible packages.
	:rtype: list
	"""
	ignore = (ignore or [])
	not_satisfied = []
	working_set = pkg_resources.working_set
	installed_packages = dict(map(lambda p: (p.project_name, p), working_set))

	if isinstance(requirements, str):
		with open(requirements, 'r') as file_h:
			requirements = file_h.readlines()
	elif hasattr(requirements, 'readlines'):
		requirements = requirements.readlines()
	elif not isinstance(requirements, (list, tuple)):
		raise TypeError('invalid type for argument requirements')
	requirements = map(lambda req: req.strip(), requirements)

	for req_line in requirements:
		parts = re.match('^([\w\-]+)(([<>=]=)(\d+(\.\d+)*))?$', req_line)
		if not parts:
			continue
		req_pkg = parts.group(1)
		if req_pkg in ignore:
			continue
		if req_pkg not in installed_packages:
			try:
				find_result = working_set.find(pkg_resources.Requirement.parse(req_line))
			except pkg_resources.ResolutionError:
				find_result = False
			if not find_result:
				not_satisfied.append(req_pkg)
			continue
		if not parts.group(2):
			continue
		req_version = distutils.version.StrictVersion(parts.group(4))
		installed_pkg = installed_packages[req_pkg]
		installed_version = distutils.version.StrictVersion(installed_pkg.version)
		if parts.group(3) == '==' and not (installed_version == req_version):
			not_satisfied.append(req_pkg)
		elif parts.group(3) == '>=' and not (installed_version >= req_version):
			not_satisfied.append(req_pkg)
		elif parts.group(3) == '<=' and not (installed_version <= req_version):
			not_satisfied.append(req_pkg)
	return not_satisfied

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

def is_valid_email(email_address):
	"""
	Check that the string specified appears to be a valid email address.

	:param str email_address: The email address to validate.
	:return: Whether the email address appears to be valid or not.
	:rtype: bool
	"""
	return EMAIL_REGEX.match(email_address) != None

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
	server = server.split(':')
	host = server[0]
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
