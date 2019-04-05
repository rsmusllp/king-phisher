#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/pylibc.py
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
import ctypes
import ctypes.util

_c_gid_t = ctypes.c_int
_c_uid_t = ctypes.c_int

def _cstr(c_string, encoding='utf-8'):
	if c_string is None:
		return None
	if isinstance(c_string, bytes):
		return c_string.decode(encoding)
	if isinstance(c_string, str):
		return c_string
	raise TypeError('c_string must be None or bytes or instance')

def _cbytes(c_bytes, encoding='utf-8'):
	if isinstance(c_bytes, bytes):
		return c_bytes
	if isinstance(c_bytes, str):
		return c_bytes.encode(encoding)
	raise TypeError('c_bytes must be None, bytes or str instance')

_GroupTuple = collections.namedtuple(
	'_GroupTuple',
	('gr_name', 'gr_passwd', 'gr_gid', 'gr_mem')
)
class _GROUP(ctypes.Structure):
	_fields_ = (('gr_name', ctypes.c_char_p),
				('gr_passwd', ctypes.c_char_p),
				('gr_gid', _c_gid_t),
				('gr_mem', ctypes.POINTER(ctypes.c_char_p)))

	def to_tuple(self, encoding='utf-8'):
		members = collections.deque()
		for mem in self.gr_mem:
			if mem is None:
				break
			members.append(_cstr(mem, encoding=encoding))
		astuple = _GroupTuple(
			gr_name=_cstr(self.gr_name, encoding=encoding),
			gr_passwd=_cstr(self.gr_passwd, encoding=encoding),
			gr_gid=self.gr_gid,
			gr_mem=members
		)
		return astuple

_PasswdTuple = collections.namedtuple(
	'_PasswdTuple',
	('pw_name', 'pw_passwd', 'pw_uid', 'pw_gid', 'pw_gecos', 'pw_dir', 'pw_shell')
)
class _PASSWD(ctypes.Structure):
	_fields_ = (('pw_name', ctypes.c_char_p),
				('pw_passwd', ctypes.c_char_p),
				('pw_uid', _c_uid_t),
				('pw_gid', _c_gid_t),
				('pw_gecos', ctypes.c_char_p),
				('pw_dir', ctypes.c_char_p),
				('pw_shell', ctypes.c_char_p))

	def to_tuple(self, encoding='utf-8'):
		astuple = _PasswdTuple(
			pw_name=_cstr(self.pw_name, encoding=encoding),
			pw_passwd=_cstr(self.pw_passwd, encoding=encoding),
			pw_uid=self.pw_uid,
			pw_gid=self.pw_gid,
			pw_gecos=_cstr(self.pw_gecos, encoding=encoding),
			pw_dir=_cstr(self.pw_dir, encoding=encoding),
			pw_shell=_cstr(self.pw_shell, encoding=encoding)
		)
		return astuple

_libc = ctypes.cdll.LoadLibrary(ctypes.util.find_library('libc'))

_libc_getgrnam = _libc.getgrnam
_libc_getgrnam.argtypes = [ctypes.c_char_p]
_libc_getgrnam.restype = ctypes.POINTER(_GROUP)

_libc_getgrouplist = _libc.getgrouplist
_libc_getgrouplist.argtypes = [ctypes.c_char_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_int)]
_libc_getgrouplist.restype = ctypes.c_int32

_libc_getpwnam = _libc.getpwnam
_libc_getpwnam.argtypes = [ctypes.c_char_p]
_libc_getpwnam.restype = ctypes.POINTER(_PASSWD)

def getgrnam(name, encoding='utf-8'):
	name = _cbytes(name, encoding=encoding)
	c_pgroup = _libc_getgrnam(name)
	if not c_pgroup:
		return None
	return c_pgroup.contents.to_tuple()

def getgrouplist(user, group=None, encoding='utf-8'):
	user = _cbytes(user, encoding=encoding)
	ngroups = 10
	ngrouplist = ctypes.c_int(ngroups)
	if group is None:
		group = getpwnam(user).pw_gid

	grouplist = (ctypes.c_uint * ngroups)()
	ct = _libc_getgrouplist(user, group, ctypes.cast(ctypes.byref(grouplist), ctypes.POINTER(ctypes.c_uint)), ctypes.byref(ngrouplist))
	if ct == -1:
		grouplist = (ctypes.c_uint * int(ngrouplist.value))()
		ct = _libc_getgrouplist(user, group, ctypes.cast(ctypes.byref(grouplist), ctypes.POINTER(ctypes.c_uint)), ctypes.byref(ngrouplist))
	return tuple(grouplist[:ct])

def getpwnam(name, encoding='utf-8'):
	name = _cbytes(name, encoding=encoding)
	c_ppasswd = _libc_getpwnam(name)
	if not c_ppasswd:
		return None
	return c_ppasswd.contents.to_tuple()
