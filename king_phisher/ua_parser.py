#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/ua_parser.py
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
import re

from king_phisher.constants import OSArch
from king_phisher.constants import OSFamily

__all__ = ['UserAgent', 'parse_user_agent']
__version__ = '0.2'

USER_AGENT_REGEX_ARCH_PPC = re.compile(r'\sPPC\s', flags=re.IGNORECASE)
USER_AGENT_REGEX_ARCH_X86 = re.compile(r'(x|(i[3456]))86[^-_]', flags=re.IGNORECASE)
USER_AGENT_REGEX_ARCH_X86_64 = re.compile(r'(amd|wow|x(86[-_])?)?64', flags=re.IGNORECASE)
USER_AGENT_REGEX_OS = re.compile(r'(android|(bb|blackberry)(\d{4})?|(ipad|iphone)?; cpu (ipad |iphone )?os|linux|mac os x|windows nt|windows phone os)(( |/)([\d\._\-]+)(;|\)| ))?', flags=re.IGNORECASE)
USER_AGENT_REGEX_VERSION = re.compile(r'Version/(([\d\._\-]+)(;|\)| ))')

RE_POS_OS_NAME = 0
RE_POS_OS_VERSION = 7

class UserAgent(collections.namedtuple('UserAgent', ['os_name', 'os_version', 'os_arch'])):
	"""
	A parsed representation of the information available from a browsers user agent
	string. Only the :py:attr:`.os_name` attribute is guaranteed to not be None.

	.. py:attribute:: os_name

		The :py:class:`~.OSFamily` constant of the name of the operating system.

	.. py:attribute:: os_version

		The version of the operating system.

	.. py:attribute:: os_arch

		The :py:class:`~.OSArch` constant of the architecture of the operating system.
	"""
	pass

def parse_user_agent(user_agent):
	"""
	Parse a user agent string and return normalized information regarding the
	operating system.

	:param str user_agent: The user agent to parse.
	:return: A parsed user agent, None is returned if the data can not be processed.
	:rtype: :py:class:`.UserAgent`
	"""
	os_parts = USER_AGENT_REGEX_OS.findall(user_agent)
	if not os_parts:
		return None
	if len(os_parts) > 1:
		os_parts = sorted(os_parts, key=lambda a: len(a[RE_POS_OS_NAME]) + len(a[RE_POS_OS_VERSION]), reverse=True)[0]
	else:
		os_parts = os_parts[0]

	os_version = None
	# os name
	os_name = os_parts[RE_POS_OS_NAME].lower()
	if os_name == 'android':
		os_name = OSFamily.ANDROID
	elif os_name == 'bb' or os_name.startswith('blackberry'):
		os_name = OSFamily.BLACKBERRY
		version_tag = USER_AGENT_REGEX_VERSION.findall(user_agent)
		if version_tag:
			os_version = version_tag[0][1]
	elif 'ipad' in os_name or 'iphone' in os_name:
		os_name = OSFamily.IOS
	elif os_name == 'linux':
		os_name = OSFamily.LINUX
	elif os_name == 'mac os x':
		os_name = OSFamily.OSX
	elif os_name == 'windows nt':
		os_name = OSFamily.WINDOWS
	elif os_name == 'windows phone os':
		os_name = OSFamily.WINDOWS_PHONE
	else:
		return None

	# os version
	os_version = (os_version or '').strip()
	os_version = (os_version or os_parts[RE_POS_OS_VERSION])
	os_version = re.sub(r'[_-]', r'.', os_version) if os_version else None

	# os arch
	os_arch = None
	if USER_AGENT_REGEX_ARCH_X86_64.search(user_agent):
		os_arch = OSArch.X86_64
	elif USER_AGENT_REGEX_ARCH_X86.search(user_agent):
		os_arch = OSArch.X86
	elif USER_AGENT_REGEX_ARCH_PPC.search(user_agent):
		os_arch = OSArch.PPC
	return UserAgent(os_name, os_version, os_arch)
