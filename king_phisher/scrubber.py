#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/scrubber.py
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
import tempfile
import xml.etree.ElementTree as ElementTree
import zipfile

def remove_office_metadata(file_name):
	"""
	Remove all metadata from Microsoft Office 2007+ file types such as docx,
	pptx, and xlsx.

	:param str file_name: The path to the file whose metadata is to be removed.
	"""
	ns = {
		'cp': 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
		'dc': 'http://purl.org/dc/elements/1.1/',
		'dcterms': 'http://purl.org/dc/terms/',
		'dcmitype': 'http://purl.org/dc/dcmitype/',
		'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
	}
	for prefix, uri in ns.items():
		ElementTree.register_namespace(prefix, uri)

	_, file_ext = os.path.splitext(file_name)
	tmpfd, tmpname = tempfile.mkstemp(dir=os.path.dirname(file_name), suffix=file_ext)
	os.close(tmpfd)
	with zipfile.ZipFile(file_name, 'r') as zin:
		with zipfile.ZipFile(tmpname, 'w') as zout:
			zout.comment = zin.comment
			for item in zin.infolist():
				data = zin.read(item.filename)
				if item.filename == 'docProps/core.xml':
					root = ElementTree.fromstring(data)
					root.clear()
					data = ElementTree.tostring(root, 'UTF-8')
				zout.writestr(item, data)
	os.remove(file_name)
	os.rename(tmpname, file_name)
