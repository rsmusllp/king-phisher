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
import stat

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


def access(path, mode, user=constants.AUTOMATIC, group=constants.AUTOMATIC):
	"""
	This is a high-level wrapper around :py:func:`os.access` to provide
	additional functionality. Similar to `os.access` this high-level wrapper
	will test the given path for a variety of access modes. Additionally however,
	*user* or *group* can be specified to test against a specific of user or group.
	.. versionadded:: 1.14.0
	:param str path: The path to test access for.
	:param mode: The mode to test access for. Set to `os.W_OK` to test for readability,
		`os.W_OK` for writability and
		`os.W_OK` to determine if path can be executed.
	:type mode: :py:class`os.*_OK`
	:param user: The user to test permissions for. If set to
		:py:class:`~king_phisher.constants.AUTOMATIC`, the processes current uid
		will be used.
	:type user: int, str, ``None``, :py:class:`~king_phisher.constants.AUTOMATIC`
	:param group: The group to test permissions for. If set to
		:py:class:`~king_phisher.constants.AUTOMATIC`, the group that *user*
		belongs too will be used.
	:type group: int, str, ``None``, :py:class:`~king_phisher.constants.AUTOMATIC`
	:return: Returns ``True`` only if the user or group has the mode of permission specified else returns ``False``.
	:rtype: bool
	"""
	uid, gid = _resolve_target_ids(user, group)
	file_info = os.stat(path)

	# If there are no permissions to check for then yes the user has no more than no permissions.
	if not mode:
		return True

	# Other checks
	# start with no test flags
	test_mode = 0
	# then check if R_OK is to be checked for
	if mode & os.R_OK:
		# and if so, add the proper flag to be tested
		test_mode |= stat.S_IROTH
	if mode & os.W_OK:
		test_mode |= stat.S_IWOTH
	if mode & os.X_OK:
		test_mode |= stat.S_IXOTH
	if file_info.st_mode & test_mode:
		return True

	# User Checks
	if file_info.st_uid == uid:
		# start with no test flags
		test_mode = 0
		# then check if R_OK is to be checked for
		if mode & os.R_OK:
			# and if so, add the proper flag to be tested
			test_mode |= stat.S_IRUSR
		if mode & os.W_OK:
			test_mode |= stat.S_IWUSR
		if mode & os.X_OK:
			test_mode |= stat.S_IXUSR
		if file_info.st_mode & test_mode:
			return True

	# Group checks
	if file_info.st_gid == gid:
		test_mode = 0
		# then check if R_OK is to be checked for
		if mode & os.R_OK:
			# and if so, add the proper flag to be tested
			test_mode |= stat.S_IRUSR
		if mode & os.W_OK:
			test_mode |= stat.S_IWUSR
		if mode & os.X_OK:
			test_mode |= stat.S_IXUSR
		if file_info.st_mode & test_mode:
			return True

	# If there were no groups specified then enumerate all of the users gids and test them all.
	if group == constants.AUTOMATIC:
		if not isinstance(user, str):
			user = pylibc.getpwuid(user).pw_name
		# check all the groups
		if any(file_info.st_gid == gid for gid in pylibc.getgrouplist(user)):
			test_mode = 0
			if mode & os.R_OK:
				test_mode |= stat.S_IRGRP
			if mode & os.W_OK:
				test_mode |= stat.S_IWGRP
			if mode & os.X_OK:
				test_mode |= stat.S_IXGRP
			if file_info.st_mode & test_mode:
				return True

	return False
