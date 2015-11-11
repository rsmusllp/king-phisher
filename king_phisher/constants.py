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

from king_phisher import its

if its.py_v3:
	_intern = sys.intern
else:
	_intern = intern

__all__ = ['OSArch', 'OSFamily', 'SPFResult']

class ConstantGroupMeta(type):
	def __len__(cls):
		return len(list(cls.names()))

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
	"""Constants which describe possible errors for the client connection process."""
	ERROR_AUTHENTICATION_FAILED = _intern('authentication failed')
	ERROR_CONNECTION = _intern('connection error')
	ERROR_INCOMPATIBLE_VERSIONS = _intern('incompatible versions')
	ERROR_INVALID_CREDENTIALS = _intern('invalid credentials')
	ERROR_INVALID_OTP = _intern('invalid otp')
	ERROR_PORT_FORWARD = _intern('port forward error')
	ERROR_UNKNOWN = _intern('unknown error')
	SUCCESS = _intern('success')

class ColorHexCode(ConstantGroup):
	"""Constants for the hex code representations of different colors."""
	BLACK = _intern('#000000')
	GRAY = _intern('#888888')
	LIGHT_YELLOW = _intern('#ffffb2')
	WHITE = _intern('#ffffff')

class OSArch(ConstantGroup):
	"""Constants for different operating system architectures."""
	PPC = _intern('PPC')
	X86 = _intern('x86')
	X86_64 = _intern('x86-64')

class OSFamily(ConstantGroup):
	"""Constants for families of different operating systems."""
	ANDROID = _intern('Android')
	BLACKBERRY = _intern('BlackBerry')
	IOS = _intern('iOS')
	LINUX = _intern('Linux')
	OSX = _intern('OS X')
	WINDOWS = _intern('Windows NT')
	WINDOWS_PHONE = _intern('Windows Phone')

class SPFResult(ConstantGroup):
	"""Constants for the different result identifiers returned from SPF checks."""
	PASS = _intern('pass')
	NEUTRAL = _intern('neutral')
	FAIL = _intern('fail')
	SOFT_FAIL = _intern('softfail')
