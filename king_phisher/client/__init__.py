#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/__init__.py
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

from king_phisher import its

import gi

repo = gi.Repository.get_default()
repo.get_loaded_namespaces()

_gi_versions = [
	('Gdk', '3.0'),
	('Gtk', '3.0'),
	('GtkSource', '3.0'),
	('JavaScriptCore', ('3.0', '4.0')),
	('Pango', '1.0'),
	('WebKit2', ('3.0', '4.0'))
]

if its.on_linux:
	_gi_versions.append(('Vte', ('2.90', '2.91')))

if not its.on_rtd:
	for namespace, versions in _gi_versions:
		if not isinstance(versions, (list, tuple)):
			versions = (versions,)
		versions = reversed(sorted(versions, key=float))
		available_versions = repo.enumerate_versions(namespace)
		for version in versions:
			if version in available_versions:
				gi.require_version(namespace, version)
				break
		else:
			raise RuntimeError("Missing required version for gi namespace '{0}'".format(namespace))
