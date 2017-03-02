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
import inspect
import logging
import operator
import os
import random
import re
import shlex
import string
import subprocess
import sys

from king_phisher import color
from king_phisher import constants
from king_phisher import its
from king_phisher import version

from dateutil import tz
from smoke_zephyr.utilities import which

EMAIL_REGEX = re.compile(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,7}$', flags=re.IGNORECASE)
TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'

class FreezableDict(collections.OrderedDict):
	"""
	A dictionary that can be frozen to prevent further editing. Useful for
	debugging. If any function tries to edit a frozen dictionary, a
	:py:exc:`RuntimeError` will be raised and a traceback will occur.
	"""
	__slots__ = ('_frozen',)
	def __init__(self, *args, **kwargs):
		super(FreezableDict, self).__init__(*args, **kwargs)
		self._frozen = False

	def __repr__(self):
		return "<{0} frozen={1} {2}>".format(self.__class__.__name__, self._frozen, super(FreezableDict, self).__repr__())

	def __setitem__(self, *args, **kwargs):
		if self._frozen:
			raise RuntimeError('Frozen dictionary cannot be modified')
		super(FreezableDict, self).__setitem__(*args, **kwargs)

	def __delitem__(self, *args, **kwargs):
		if self._frozen:
			raise RuntimeError('Frozen dictionary cannot be modified')
		super(FreezableDict, self).__delitem__(*args, **kwargs)

	def pop(self, *args, **kwargs):
		if self._frozen:
			raise RuntimeError('Frozen dictionary cannot be modified')
		super(FreezableDict, self).pop(*args, **kwargs)

	def update(self, *args, **kwargs):
		if self._frozen:
			raise RuntimeError('Frozen dictionary cannot be modified')
		super(FreezableDict, self).update(*args, **kwargs)

	def popitem(self, *args, **kwargs):
		if self._frozen:
			raise RuntimeError('Frozen dictionary cannot be modified')
		super(FreezableDict, self).popitem(*args, **kwargs)

	def clear(self, *args, **kwargs):
		if self._frozen:
			raise RuntimeError('Frozen dictionary cannot be modified')
		super(FreezableDict, self).clear(*args, **kwargs)

	def freeze(self):
		"""
		Freeze the dictionary to prevent further editing.
		"""
		self._frozen = True

	def thaw(self):
		"""
		Thaw the dictionary to once again enable editing.
		"""
		self._frozen = False

	@property
	def frozen(self):
		"""
		Whether or not the dictionary is frozen and can not be modified.

		:rtype: bool
		"""
		return self._frozen

class Mock(object):
	"""
	A fake object used to replace missing imports when generating documentation.
	"""
	__all__ = []
	def __init__(self, *args, **kwargs):
		pass

	def __add__(self, other):
		return other

	def __call__(self, *args, **kwargs):
		return Mock()

	@classmethod
	def __getattr__(cls, name):
		if name in ('__file__', '__path__'):
			return os.devnull
		else:
			return Mock()

	def __or__(self, other):
		return other

	@classmethod
	def __setattr__(cls, name, value):
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
	parser.add_argument('-L', '--log', dest='loglvl', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'FATAL'], help='set the logging level')
	parser.add_argument('--logger', default=default_root, help='specify the root logger')

def assert_arg_type(arg, arg_type, arg_pos=1, func_name=None):
	"""
	Check that an argument is an instance of the specified type and if not
	raise a :py:exc:`TypeError` exception with a meaningful message. If
	*func_name* is not specified, it will be determined by examining the stack.

	:param arg: The argument to check.
	:param arg_type: The type or sequence of types that *arg* can be.
	:type arg_type: list, tuple, type
	:param int arg_pos: The position of the argument in the function.
	:param str func_name: The name of the function the argument is for.
	"""
	if isinstance(arg, arg_type):
		return
	if func_name is None:
		parent_frame = inspect.stack()[1][0]
		func_name = parent_frame.f_code.co_name
	if isinstance(arg_type, (list, tuple)):
		if len(arg_type) == 1:
			arg_type = arg_type[0].__name__
		else:
			arg_type = tuple(at.__name__ for at in arg_type)
			arg_type = ', '.join(arg_type[:-1]) + ' or ' + arg_type[-1]
	else:
		arg_type = arg_type.__name__
	raise TypeError("{0}() argument {1} must be {2}, not {3}".format(func_name, arg_pos, arg_type, type(arg).__name__))

def configure_stream_logger(logger, level=None):
	"""
	Configure the default stream handler for logging messages to the console.
	This also configures the basic logging environment for the application.

	:param str logger: The logger to add the stream handler for.
	:param level: The level to set the logger to, will default to WARNING if no level is specified.
	:type level: None, int, str
	:return: The new configured stream handler.
	:rtype: :py:class:`logging.StreamHandler`
	"""
	if level is None:
		level = constants.DEFAULT_LOG_LEVEL
	if isinstance(level, str):
		level = getattr(logging, level)
	root_logger = logging.getLogger('')
	for handler in root_logger.handlers:
		root_logger.removeHandler(handler)

	logging.getLogger(logger).setLevel(logging.DEBUG)
	console_log_handler = logging.StreamHandler()
	console_log_handler.setLevel(level)
	if its.on_linux:
		console_log_handler.setFormatter(color.ColoredLogFormatter('%(levelname)s %(message)s'))
	else:
		console_log_handler.setFormatter(logging.Formatter('%(levelname)-8s %(message)s'))
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

def format_datetime(dt, encoding='utf-8'):
	"""
	Format a date time object into a string. If the object *dt* is not an
	instance of :py:class:`datetime.datetime` then an empty string will be
	returned.

	:param dt: The object to format.
	:type dt: :py:class:`datetime.datetime`
	:param str encoding: The encoding to use to coerce the return value into a unicode string.
	:return: The string representing the formatted time.
	:rtype: str
	"""
	if isinstance(dt, datetime.datetime):
		formatted = dt.strftime(TIMESTAMP_FORMAT)
	else:
		formatted = ''
	if isinstance(formatted, bytes):
		formatted = formatted.decode(encoding)
	return formatted

def is_valid_email_address(email_address):
	"""
	Check that the string specified appears to be a valid email address.

	:param str email_address: The email address to validate.
	:return: Whether the email address appears to be valid or not.
	:rtype: bool
	"""
	if email_address is None:
		return False
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

def parse_datetime(ts):
	"""
	Parse a time stamp into a :py:class:`datetime.datetime` instance. The time
	stamp must be in a compatible format, as would have been returned from the
	:py:func:`.format_datetime` function.

	:param str ts: The timestamp to parse.
	:return: The parsed timestamp.
	:rtype: :py:class:`datetime.datetime`
	"""
	assert_arg_type(ts, str)
	return datetime.datetime.strptime(ts, TIMESTAMP_FORMAT)

def password_is_complex(password, min_len=12):
	"""
	Check that the specified string meets standard password complexity
	requirements.
	:param str password: The password to validate.
	:param int min_len: The mininum length the password should be.
	:return: Whether the strings appears to be complex or not.
	:rtype: bool
	"""
	has_upper = False
	has_lower = False
	has_digit = False
	if len(password) < min_len:
		return False
	for char in password:
		if char.isupper():
			has_upper = True
		if char.islower():
			has_lower = True
		if char.isdigit():
			has_digit = True
		if has_upper and has_lower and has_digit:
			return True
	return False

def make_message_uid():
	"""
	Creates a random string of characters and numbers to be used as a message id.

	:return: String of characters from the random_string function.
	:rtype: str
	"""
	return random_string(16)

def make_visit_uid():
	"""
	Creates a random string of characters and numbers to be used as a visit id.

	:return: String of characters from the random_string function.
	:rtype: str
	"""
	return random_string(24)

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

def switch(value, comp=operator.eq, swapped=False):
	"""
	A pure Python implementation of a switch case statement. *comp* will be used
	as a comparison function and passed two arguments of *value* and the
	provided case respectively.

	Switch case example usage:

	.. code-block:: python

	  for case in switch(2):
	      if case(1):
	          print('case 1 matched!')
	          break
	      if case(2):
	          print('case 2 matched!')
	          break
	  else:
	      print('no cases were matched')

	:param value: The value to compare in each of the case statements.
	:param comp: The function to use for comparison in the case statements.
	:param swapped: Whether or not to swap the arguments to the *comp* function.
	:return: A function to be called for each case statement.
	"""
	if swapped:
		yield lambda case: comp(case, value)
	else:
		yield lambda case: comp(value, case)
