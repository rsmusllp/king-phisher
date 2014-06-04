#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tools/cx_freeze.py
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
import site
import sys

if sys.path[0] != os.getcwd():
	sys.path.insert(0, os.getcwd())

from king_phisher import version

import matplotlib
from cx_Freeze import setup, Executable

is_debugging_build = bool(os.environ.get('DEBUG'))

include_dll_path = os.path.join(site.getsitepackages()[1], 'gnome')

missing_dlls = [
	'libaspell-15.dll',
	'libatk-1.0-0.dll',
	'libcairo-gobject-2.dll',
	'libdbus-1-3.dll',
	'libdbus-glib-1-2.dll',
	'libenchant.dll',
	'lib\enchant\libenchant_aspell.dll',
	'lib\enchant\libenchant_hspell.dll',
	'lib\enchant\libenchant_ispell.dll',
	'lib\enchant\libenchant_myspell.dll',
	'lib\enchant\libenchant_voikko.dll',
	'libffi-6.dll',
	'libfontconfig-1.dll',
	'libfreetype-6.dll',
	'libgailutil-3-0.dll',
	'libgdk-3-0.dll',
	'libgdk_pixbuf-2.0-0.dll',
	'libgeoclue-0.dll',
	'libgio-2.0-0.dll',
	'lib\gio\modules\libgiolibproxy.dll',
	'libgirepository-1.0-1.dll',
	'libglib-2.0-0.dll',
	'libgmodule-2.0-0.dll',
	'libgobject-2.0-0.dll',
	'libgstapp-1.0-0.dll',
	'libgstaudio-1.0-0.dll',
	'libgstbase-1.0-0.dll',
	'libgstpbutils-1.0-0.dll',
	'libgstreamer-1.0-0.dll',
	'libgsttag-1.0-0.dll',
	'libgstvideo-1.0-0.dll',
	'libgtk-3-0.dll',
	'libharfbuzz-gobject-0.dll',
	'libintl-8.dll',
	'libjavascriptcoregtk-3.0-0.dll',
	'libjpeg-8.dll',
	'liborc-0.4-0.dll',
	'libpango-1.0-0.dll',
	'libpangocairo-1.0-0.dll',
	'libpangoft2-1.0-0.dll',
	'libpangowin32-1.0-0.dll',
	'libpng16-16.dll',
	'libproxy.dll',
	'libpyglib-gi-2.0-python27-0.dll',
	'librsvg-2-2.dll',
	'libsoup-2.4-1.dll',
	'libsqlite3-0.dll',
	'libwebkitgtk-3.0-0.dll',
	'libwebp-4.dll',
	'libwinpthread-1.dll',
	'libxml2-2.dll',
	'libzzz.dll',
]

include_files = []
for dll in missing_dlls:
	include_files.append((os.path.join(include_dll_path, dll), dll))

gtk_libs = ['etc', 'lib', 'share']
for lib in gtk_libs:
	include_files.append((os.path.join(include_dll_path, lib), lib))

include_files.append((matplotlib.get_data_path(), 'mpl-data'))
include_files.append(('data/client/king_phisher', 'king_phisher'))

exe_base = 'Win32GUI'
if is_debugging_build:
	exe_base = 'Console'

executables = [
	Executable(
		'KingPhisher',
		base=exe_base,
		shortcutName='KingPhisher',
		shortcutDir='ProgramMenuFolder'
	)
]

build_exe_options = dict(
	compressed=False,
	packages=['email', 'gi', 'jinja2', 'matplotlib', 'msgpack', 'paramiko'],
	include_files=include_files
)

setup(
	name='KingPhisher',
	author='Spencer McIntyre',
	version=version.distutils_version,
	description='King Phisher Client',
	options=dict(build_exe=build_exe_options),
	executables=executables
)
