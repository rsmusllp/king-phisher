#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/fs_utilities.py
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

import os
import smoke_zephyr.utilities

from king_phisher import constants
from king_phisher.server import pylibc

def _resolve_target_ids(user, group):
	if user is None and (group is constants.AUTOMATIC or group is None):
		raise ValueError('either user or group must be specified')

	uid = None
	gid = None
	if isinstance(user, str):
		struct_passwd = pylibc.getpwnam(user)
		uid = struct_passwd.pw_uid
		if group is constants.AUTOMATIC:
			gid = struct_passwd.pw_gid
	elif user is constants.AUTOMATIC:
		uid = os.getuid()
	elif user is None:
		uid = None
	elif isinstance(user, int):
		if user < 0:
			raise ValueError('owner must be a (zero inclusive) natural number or a user name')
		uid = user
	else:
		raise TypeError('the user argument type is unsupported')

	if isinstance(group, str):
		struct_group = pylibc.getgrnam(group)
		gid = struct_group.gr_gid
	elif group is constants.AUTOMATIC:
		if uid is None:
			raise ValueError('can not resolve a group without a uid')
		if gid is None:  # check if this was resolved already before calling into libc
			struct_passwd = pylibc.getpwuid(uid)
			gid = struct_passwd.pw_gid
	elif group is None:
		gid = None
	elif isinstance(group, int):
		if group < 0:
			raise ValueError('group must be a (zero inclusive) natural number or a group name')
		gid = group
	return uid, gid

def chown(path, user=None, group=constants.AUTOMATIC, recursive=True):
	"""
	This is a high-level wrapper around :py:func:`os.chown` to provide
	additional functionality. ``None`` can be specified as the *user* or *group*
	to leave the value unchanged. At least one of either *user* or *group* must
	be specified.
	.. versionadded:: 1.14.0
	:param str path: The path to change the owner information for.
	:param user: The new owner to set for the path. If set to
		:py:class:`~king_phisher.constants.AUTOMATIC`, the processes current uid
		will be used.
	:type user: int, str, ``None``, :py:class:`~king_phisher.constants.AUTOMATIC`
	:param group: The new group to set for the path. If set to
		:py:class:`~king_phisher.constants.AUTOMATIC`, the group that *user*
		belongs too will be used.
	:type group: int, str, ``None``, :py:class:`~king_phisher.constants.AUTOMATIC`
	:param bool recursive: Whether or not to recurse into directories.
	"""
	uid, gid = _resolve_target_ids(user, group)
	if uid is None:
		uid = -1
	if gid is None:
		gid = -1
	if recursive:
		iterator = smoke_zephyr.utilities.FileWalker(path)
	else:
		iterator = (path,)
	for path in iterator:
		os.chown(path, uid, gid)

