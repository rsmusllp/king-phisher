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
USER_AGENT_REGEX_OS = re.compile(r'(android|blackberry|(ipad|iphone)?; cpu (ipad |iphone )?os|linux|mac os x|windows nt) (([\d\._\-]+)(;|\)| ))?', flags=re.IGNORECASE)
USER_AGENT_REGEX_VERSION = re.compile(r'Version/(([\d\._\-]+)(;|\)| ))')

UserAgent = collections.namedtuple('UserAgent', ['os_name', 'os_version', 'os_arch'])
"""
A parsed representation of the information available from a browsers user agent
string. Only the :py:attr:`.os_name` attribute is guaranteed to not be None.
"""

def parse_user_agent(user_agent):
	"""
	Parse a user agent string and return normalized information regarding the
	operating system.

	:param str user_agent: The user agent to parse.
	:return: A parsed user agent, None is returned if the data can not be processed.
	:rtype: :py:class:`.UserAgent`
	"""
	os_parts = USER_AGENT_REGEX_OS.search(user_agent)
	if not os_parts:
		user_agent = re.sub(r'(BB)(\d+)', r'BlackBerry \2', user_agent)
		os_parts = USER_AGENT_REGEX_OS.search(user_agent)
		if not os_parts:
			return None
	os_arch = None
	os_version = None
	# os name
	os_name = os_parts.group(1).lower()
	if 'android' in os_name:
		os_name = OSFamily.ANDROID
	elif 'blackberry' in os_name:
		os_name = OSFamily.BLACKBERRY
		version_tag = USER_AGENT_REGEX_VERSION.search(user_agent)
		if version_tag:
			os_version = version_tag.group(2)
	elif 'ipad' in os_name or 'iphone' in os_name:
		os_name = OSFamily.IOS
	elif 'linux' in os_name:
		os_name = OSFamily.LINUX
	elif 'os x' in os_name:
		os_name = OSFamily.OSX
	elif 'windows nt' in os_name:
		os_name = OSFamily.WINDOWS
	else:
		return None
	# os version
	os_version = (os_version or os_parts.group(5))
	if os_version:
		os_version = re.sub(r'[_-]', r'.', os_version)
	# os arch
	os_arch = None
	if USER_AGENT_REGEX_ARCH_PPC.search(user_agent):
		os_arch = OSArch.PPC
	elif USER_AGENT_REGEX_ARCH_X86_64.search(user_agent):
		os_arch = OSArch.X86_64
	elif USER_AGENT_REGEX_ARCH_X86.search(user_agent):
		os_arch = OSArch.X86
	return UserAgent(os_name, os_version, os_arch)
