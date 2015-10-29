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

if sys.version_info[0] == 3:
	intern = sys.intern

__all__ = ['OSArch', 'OSFamily', 'SPFResult']

class ConstantGroup:
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
	ERROR_AUTHENTICATION_FAILED = intern('authentication failed')
	ERROR_CONNECTION = intern('connection error')
	ERROR_INCOMPATIBLE_VERSIONS = intern('incompatible versions')
	ERROR_INVALID_CREDENTIALS = intern('invalid credentials')
	ERROR_INVALID_OTP = intern('invalid otp')
	ERROR_PORT_FORWARD = intern('port forward error')
	ERROR_UNKNOWN = intern('unknown error')
	SUCCESS = intern('success')

class ColorHexCode(ConstantGroup):
	"""Constants for the hex code representations of different colors."""
	BLACK = intern('#000000')
	GRAY = intern('#888888')
	LIGHT_YELLOW = intern('#ffffb2')
	WHITE = intern('#ffffff')

class OSArch(ConstantGroup):
	"""Constants for different operating system architectures."""
	PPC = intern('PPC')
	X86 = intern('x86')
	X86_64 = intern('x86-64')

class OSFamily(ConstantGroup):
	"""Constants for families of different operating systems."""
	ANDROID = intern('Android')
	BLACKBERRY = intern('BlackBerry')
	IOS = intern('iOS')
	LINUX = intern('Linux')
	OSX = intern('OS X')
	WINDOWS = intern('Windows NT')
	WINDOWS_PHONE = intern('Windows Phone')

class SPFResult(ConstantGroup):
	"""Constants for the different result identifiers returned from SPF checks."""
	PASS = intern('pass')
	NEUTRAL = intern('neutral')
	FAIL = intern('fail')
	SOFT_FAIL = intern('softfail')
