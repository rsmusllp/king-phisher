#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/find.py
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
import sys

from king_phisher import its

DATA_DIRECTORY_NAME = 'king_phisher'
"""The name of the directory containing the King Phisher data."""

ENV_VAR = 'KING_PHISHER_DATA_PATH'
"""The name of the environment variable which contains the search path."""

os.environ[ENV_VAR] = os.getenv(ENV_VAR, ('/usr/share:/usr/local/share' if its.on_linux else ''))

def data_path_append(path):
	"""
	Add a directory to the data search path. The directory will be used
	by the :py:func:`.data_file` and :py:func:`.data_directory`
	functions.

	:param str path: The path to add for searching.
	"""
	path_var = os.environ[ENV_VAR].split(os.pathsep)
	if not path in path_var:
		path_var.append(path)
		os.environ[ENV_VAR] = os.pathsep.join(path_var)

def init_data_path(directory):
	"""
	Add a directory to the data search path for either client or server data
	files.

	:param str directory: The directory to add, either 'client' or 'server'.
	"""
	found = False
	possible_data_paths = set()
	if its.frozen:
		possible_data_paths.add(os.path.dirname(sys.executable))
	else:
		data_path = os.path.dirname(__file__)
		possible_data_paths.add(os.path.abspath(os.path.join(data_path, '..', 'data', directory)))
		possible_data_paths.add(os.path.join(os.getcwd(), 'data', directory))

	for data_path in possible_data_paths:
		if not os.path.isdir(data_path):
			continue
		found = True
		data_path_append(data_path)
	if not found:
		raise RuntimeError('failed to initialize the specified data directory')

def data_file(name, access_mode=os.R_OK):
	"""
	Locate a data file by searching the directories specified in
	:py:data:`.ENV_VAR`. If *access_mode* is specified, it needs to be a
	value suitable for use with :py:func:`os.access`.

	:param str name: The name of the file to locate.
	:param int access_mode: The access that is required for the file.
	:return: The path to the located file.
	:rtype: str
	"""
	search_path = os.environ[ENV_VAR]
	for directory in search_path.split(os.pathsep):
		test_file_path = os.path.join(directory, DATA_DIRECTORY_NAME, name)
		if not os.path.isfile(test_file_path):
			continue
		if not os.access(test_file_path, access_mode):
			continue
		return test_file_path
	return None

def data_directory(name):
	"""
	Locate a subdirectory in the data search path.

	:param str name: The directory name to locate.
	:return: The path to the located directory.
	:rtype: str
	"""
	search_path = os.environ[ENV_VAR]
	for directory in search_path.split(os.pathsep):
		test_path = os.path.join(directory, DATA_DIRECTORY_NAME, name)
		if not os.path.isdir(test_path):
			continue
		return test_path
	return None
