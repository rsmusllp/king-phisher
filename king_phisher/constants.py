#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/constants.py
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

import sys

import boltons.typeutils

__all__ = ('OSArch', 'OSFamily', 'SPFResult')

DEFAULT_LOG_LEVEL = 'WARNING'
"""The default log level to use for filtering messages by importance."""

AUTOMATIC = boltons.typeutils.make_sentinel('AUTOMATIC', var_name='AUTOMATIC')
DISABLED = boltons.typeutils.make_sentinel('DISABLED', var_name='DISABLED')

class ConstantGroupMeta(type):
	def __len__(cls):
		return len(list(cls.names()))

# stylized metaclass definition to be Python 2.7 and 3.x compatible
class ConstantGroup(ConstantGroupMeta('_ConstantGroup', (object,), {})):
	"""A class for grouping related constants together."""
	@classmethod
	def names(cls):
		"""Iterate over the names in a group of constants."""
		for name in dir(cls):
			if name.upper() != name:
				continue
			yield name

	@classmethod
	def items(cls):
		"""Iterate over the names and values in a group of constants."""
		for name in dir(cls):
			if name.upper() != name:
				continue
			yield (name, getattr(cls, name))

	@classmethod
	def values(cls):
		"""Iterate over the values in a group of constants."""
		for name in dir(cls):
			if name.upper() != name:
				continue
			yield getattr(cls, name)

class ConnectionErrorReason(ConstantGroup):
	"""Constants which describe possible errors for an arbitrary connection process."""
	ERROR_AUTHENTICATION_FAILED = sys.intern('authentication failed')
	ERROR_CONNECTION = sys.intern('connection error')
	ERROR_INCOMPATIBLE_VERSIONS = sys.intern('incompatible versions')
	ERROR_INVALID_CREDENTIALS = sys.intern('invalid credentials')
	ERROR_INVALID_OTP = sys.intern('invalid otp')
	ERROR_PORT_FORWARD = sys.intern('port forward error')
	ERROR_UNKNOWN = sys.intern('unknown error')
	SUCCESS = sys.intern('success')

class ColorHexCode(ConstantGroup):
	"""Constants for the hex code representations of different colors."""
	BLACK = sys.intern('#000000')
	BLUE = sys.intern('#0000ff')
	GRAY = sys.intern('#808080')
	GREEN = sys.intern('#00ff00')
	LIGHT_YELLOW = sys.intern('#ffffb2')
	ORANGE = sys.intern('#ffa500')
	RED = sys.intern('#ff0000')
	WHITE = sys.intern('#ffffff')
	YELLOW = sys.intern('#ffff00')

class OSArch(ConstantGroup):
	"""Constants for different operating system architectures."""
	PPC = sys.intern('PPC')
	X86 = sys.intern('x86')
	X86_64 = sys.intern('x86-64')

class OSFamily(ConstantGroup):
	"""Constants for families of different operating systems."""
	ANDROID = sys.intern('Android')
	BLACKBERRY = sys.intern('BlackBerry')
	IOS = sys.intern('iOS')
	LINUX = sys.intern('Linux')
	OSX = sys.intern('OS X')
	WINDOWS = sys.intern('Windows NT')
	WINDOWS_PHONE = sys.intern('Windows Phone')

class SPFResult(ConstantGroup):
	"""Constants for the different result identifiers returned from SPF checks."""
	PASS = sys.intern('pass')
	NEUTRAL = sys.intern('neutral')
	FAIL = sys.intern('fail')
	SOFT_FAIL = sys.intern('softfail')
