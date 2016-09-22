#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/version.py
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
import os
import subprocess

import smoke_zephyr.utilities

def get_revision():
	"""
	Retrieve the current git revision identifier. If the git binary can not be
	found or the repository information is unavailable, None will be returned.

	:return: The git revision tag if it's available.
	:rtype: str
	"""
	git_bin = smoke_zephyr.utilities.which('git')
	if not git_bin:
		return None
	proc_h = subprocess.Popen(
		[git_bin, 'rev-parse', 'HEAD'],
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		close_fds=True,
		cwd=os.path.dirname(os.path.abspath(__file__))
	)
	rev = proc_h.stdout.read().strip()
	proc_h.wait()
	if not len(rev):
		return None
	return rev.decode('utf-8')

revision = get_revision()
"""The git revision identifying the latest commit if available."""

version_info = collections.namedtuple('version_info', ['major', 'minor', 'micro'])(1, 5, 1)
"""A tuple representing the version information in the format ('major', 'minor', 'micro')"""

version_label = 'beta'
"""A version label such as alpha or beta."""
version = "{0}.{1}.{2}".format(version_info.major, version_info.minor, version_info.micro)
"""A string representing the full version information."""

# distutils_version is compatible with distutils.version classes
distutils_version = version
"""A string suitable for being parsed by :py:mod:`distutils.version` classes."""

if version_label:
	version += '-' + version_label
	if revision:
		version += " (rev: {0})".format(revision[:8])
	distutils_version += version_label[0]
	if version_label[-1].isdigit():
		distutils_version += version_label[-1]
	else:
		distutils_version += '0'

rpc_api_version = collections.namedtuple('rpc_api_version', ['major', 'minor'])(5, 1)
"""
A tuple representing the local version of the RPC API for use with compatibility
checks. The major version is incremented when backwards incompatible changes are
made and the minor version is incremented when backwards compatible changes are
made.
"""
