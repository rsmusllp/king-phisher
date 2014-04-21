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

DATA_DIRECTORY_NAME = 'king_phisher'
ENV_VAR = 'KING_PHISHER_DATA_PATH'
os.environ[ENV_VAR] = os.pathsep.join((os.getenv(ENV_VAR, ''), '/usr/share:/usr/local/share:.'))

def data_path_append(path):
	if not path in os.environ[ENV_VAR].split(os.pathsep):
		os.environ[ENV_VAR] = os.pathsep.join((os.environ[ENV_VAR], path))

def find_data_file(data_file, access_mode = os.R_OK):
	search_path = os.environ[ENV_VAR]
	for directory in search_path.split(os.pathsep):
		test_file_path = os.path.join(directory, DATA_DIRECTORY_NAME, data_file)
		if not os.path.isfile(test_file_path):
			continue
		if not os.access(test_file_path, access_mode):
			continue
		return test_file_path
	return None

def find_data_directory(data_directory):
	search_path = os.environ[ENV_VAR]
	for directory in search_path.split(os.pathsep):
		test_path = os.path.join(directory, DATA_DIRECTORY_NAME, data_directory)
		if not os.path.isdir(test_path):
			continue
		return test_path
	return None
