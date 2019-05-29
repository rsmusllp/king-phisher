#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/fs_utilities.py
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

import grp
import os
import pwd

import smoke_zephyr.utilities

from king_phisher import constants

def chown(path, user=None, group=constants.AUTOMATIC, recursive=True):
	"""
	This is a high-level wrapper around :py:func:`os.chown` to provide
	additional functionality. ``None`` can be specified as the *user* or *group*
	to leave the value unchanged. At least one of either *user* or *group* must
	be specified.

	.. versionadded:: 1.14.0

	:param str path: The path to change the owner information for.
	:param user: The new owner to set for the path.
	:type user: int, str, ``None``
	:param group: The new group to set for the path. If set to
		:py:class:`~king_phisher.constants.AUTOMATIC`, the group that *user*
		belongs too will be used.
	:type group: int, str, ``None``, :py:class:`~king_phisher.constants.AUTOMATIC`
	:param bool recursive: Whether or not to recurse into directories.
	"""
	if (user is constants.AUTOMATIC or user is None) and (group is constants.AUTOMATIC or group is None):
		raise ValueError('either user or group must be specified')
	if isinstance(user, str):
		struct_passwd = pwd.getpwnam(user)
		user = struct_passwd.pw_uid
		if group is constants.AUTOMATIC:
			group = struct_passwd.pw_gid
	elif user is None:
		user = -1
	elif not isinstance(user, int) and user >= 0:
		raise ValueError('owner must be a (zero inclusive) natural number or a user name')
	elif group is constants.AUTOMATIC:
		struct_passwd = pwd.getpwuid(user)
		group = struct_passwd.pw_gid
	if isinstance(group, str):
		struct_group = grp.getgrnam(group)
		group = struct_group.gr_gid
	elif group is None:
		group = -1
	elif not isinstance(group, int) and group >= 0:
		raise ValueError('group must be a (zero inclusive) natural number or a group name')
	if recursive:
		iterator = smoke_zephyr.utilities.FileWalker(path)
	else:
		iterator = (path,)
	for path in iterator:
		os.chown(path, user, group)
