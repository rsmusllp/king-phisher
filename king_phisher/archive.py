#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/archive.py
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
#  * Neither the name of the  nor the names of its
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
import copy
import datetime
import io
import os
import shutil
import tarfile
import tempfile
import zipfile

from king_phisher import its
from king_phisher import serializers
from king_phisher import version

def is_archive(file_path):
	"""
	Check if the specified file appears to be a valid archive file that can be
	opened with :py:class:`.ArchiveFile`.

	:param str file_path: The path to the file to check.
	:return: Whether or not the file looks like a compatible archive.
	:rtype: bool
	"""
	return tarfile.is_tarfile(file_path)

def patch_zipfile(input_file, patches, output_file=None):
	"""
	Patch content into the specified input Zip file. The *input_file* must be
	either an input path string to the file to patch or a
	:py:class:`zipfile.ZipFile` instance. Patch data is supplied in the *patch*
	argument which is a dictionary keyed by the paths to modify, values are
	then used in place of the specified path. If the value of a path is
	``None``, then that file is removed from the archive. The *output_file* is
	either a string to the path of where to place the patched archive, a
	:py:class:`~zipfile.ZipFile` instance or ``None``. If ``None`` is specified
	then *input_file* is modified in place.

	.. note::
		If a :py:class:`~zipfile.ZipFile` instance is specified as *input_file*
		then *output_file* can not be ``None``.

	:param input_file: The Zip file archive to modify.
	:type input_file: str, :py:class:`~zipfile.ZipFile`
	:param dict patches: The data to modify from the original archive.
	:param output_file: The destination of the modified archive
	:type output_file: None, str, :py:class:`~zipfile.ZipFile`
	"""
	ZipMeta = collections.namedtuple('ZipMeta', ('close', 'delete', 'obj', 'path'))
	copy_out_to_in = False
	if isinstance(input_file, str):
		zin_meta = ZipMeta(close=True, delete=False, obj=zipfile.ZipFile(input_file, 'r'), path=os.path.abspath(input_file))
	elif isinstance(input_file, zipfile.ZipFile):
		zin_meta = ZipMeta(close=False, delete=False, obj=input_file, path=os.path.abspath(input_file.filename))
	else:
		raise TypeError('arg 1 (input_file) must either be a path or zipfile.ZipFile instance')

	if output_file is None:
		if not zin_meta.close:
			raise ValueError('input_file must be a path when output_file is None')
		tmp_fd, output_file = tempfile.mkstemp(suffix=os.path.splitext(input_file)[1])
		os.close(tmp_fd)
		zout_meta = ZipMeta(close=True, delete=True, obj=zipfile.ZipFile(output_file, 'w'), path=os.path.abspath(output_file))
		copy_out_to_in = True
	elif isinstance(output_file, str):
		zout_meta = ZipMeta(close=True, delete=False, obj=zipfile.ZipFile(output_file, 'w'), path=os.path.abspath(output_file))
	elif isinstance(output_file, zipfile.ZipFile):
		zout_meta = ZipMeta(close=False, delete=False, obj=output_file, path=os.path.abspath(output_file.filename))
	else:
		raise TypeError('arg 3 (output_file) must either be None, a path or zipfile.ZipFile instance')

	patches = copy.copy(patches)
	zout_meta.obj.comment = zin_meta.obj.comment
	for item in zin_meta.obj.infolist():
		data = zin_meta.obj.read(item.filename)
		if item.filename in patches:
			data = patches.pop(item.filename)
			if data is None:
				continue
		zout_meta.obj.writestr(item, data)
	for filename, data in patches.items():
		zout_meta.obj.writestr(filename, data)

	if zin_meta.close:
		zin_meta.obj.close()
	if zout_meta.close:
		zout_meta.obj.close()

	if copy_out_to_in:
		shutil.copyfile(zout_meta.path, zin_meta.path)

	# zin_meta.delete will never be True
	if zout_meta.delete:
		os.unlink(zout_meta.path)

class ArchiveFile(object):
	"""
	An object representing a generic archive for storing information. The
	resulting archive file is a tarfile that can easily be opened and
	manipulated with external tools. This class also facilitates storing
	metadata with the archive. This metadata contains basic information such as
	the version of King Phisher that generated it, and a UTC timestamp of when
	it was created.
	"""
	metadata_file_name = 'metadata.json'
	def __init__(self, file_name, mode, encoding='utf-8'):
		"""
		:param str file_name: The path to the file to open as an archive.
		:param str mode: The mode to open the file such as 'r' or 'w'.
		:param str encoding: The encoding to use for strings.
		"""
		self._mode = mode + ':bz2'
		self.encoding = encoding
		self.file_name = file_name
		epoch = datetime.datetime.utcfromtimestamp(0)
		self.mtime = (datetime.datetime.utcnow() - epoch).total_seconds()
		self._tar_h = tarfile.open(file_name, self._mode)
		if 'r' in mode and self.has_file(self.metadata_file_name):
			self.metadata = serializers.JSON.loads(self.get_data(self.metadata_file_name).decode(self.encoding))
		else:
			self.metadata = {}
		if 'w' in mode:
			self.metadata['timestamp'] = datetime.datetime.utcnow().isoformat()
			self.metadata['version'] = version.version

	def add_data(self, name, data):
		"""
		Add arbitrary data directly to the archive under the specified name.
		This allows data to be directly inserted into the archive without first
		writing it to a file or file like object.

		:param str name: The name of the destination file in the archive.
		:param data: The data to place into the archive.
		:type data: bytes, str
		"""
		if its.py_v2 and isinstance(data, unicode):
			data = data.encode(self.encoding)
		elif its.py_v3 and isinstance(data, str):
			data = data.encode(self.encoding)
		pseudo_file = io.BytesIO()
		pseudo_file.write(data)

		tarinfo = tarfile.TarInfo(name=name)
		tarinfo.mtime = self.mtime
		tarinfo.size = pseudo_file.tell()
		pseudo_file.seek(os.SEEK_SET)
		self._tar_h.addfile(tarinfo=tarinfo, fileobj=pseudo_file)

	def add_file(self, name, file_path, recursive=True):
		"""
		Place a file or directory into the archive. If *file_path* is a
		directory, it's contents will be added recursively if *recursive* is
		True.

		:param str name: The name of the destination file in the archive.
		:param str file_path: The path to the file to add to the archive.
		:param bool recursive: Whether or not to add directory contents.
		"""
		self._tar_h.add(file_path, arcname=name, recursive=recursive)

	def close(self):
		"""Close the handle to the archive."""
		if 'w' in self.mode:
			self.add_data(self.metadata_file_name, serializers.JSON.dumps(self.metadata, pretty=True))
		self._tar_h.close()

	@property
	def files(self):
		"""
		This property is a generator which yields tuples of two objects each
		where the first is the file name and the second is the file object. The
		metadata file is skipped.

		:return: A generator which yields all the contained file name and file objects.
		:rtype: tuple
		"""
		for name in self._tar_h.getnames():
			if name == self.metadata_file_name:
				continue
			yield name, self.get_file(name)

	@property
	def file_names(self):
		"""
		This property is a generator which yields the names of all of the
		contained files. The metadata file is skipped.

		:return: A generator which yields all the contained file names.
		:rtype: str
		"""
		for name in self._tar_h.getnames():
			if name == self.metadata_file_name:
				continue
			yield name

	def get_data(self, name):
		"""
		Return the data contained within the specified archive file.

		:param str name: The name of the source file in the archive.
		:return: The contents of the specified file.
		:rtype: bytes
		"""
		return self.get_file(name).read()

	def get_file(self, name):
		"""
		Return the specified file object from the archive.

		:param str name: The name of the source file in the archive.
		:return: The specified file.
		:rtype: file
		"""
		member = self._tar_h.getmember(name)
		return self._tar_h.extractfile(member)

	def has_file(self, name):
		"""
		Check if a file exists within archive.

		:param str name:
		:return: Whether or not the file exists.
		:rtype: bool
		"""
		return name in self._tar_h.getnames()

	@property
	def mode(self):
		"""
		A read-only attribute representing the mode that the archive file was
		opened in.
		"""
		return self._mode
