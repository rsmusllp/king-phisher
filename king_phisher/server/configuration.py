#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/configuration.py
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

import copy
import json
import os
import sys

import king_phisher.color as color
import king_phisher.find as find

import smoke_zephyr.configuration as configuration
import jsonschema
import yaml

YamlLoader = getattr(yaml, 'CLoader', yaml.Loader)

def _load_file(file_path, yaml_include=True):
	_, extension = os.path.splitext(file_path)
	with open(file_path, 'r') as file_h:
		if extension in ('.jsn', '.json'):
			file_data = json.load(file_h)
		elif extension in ('.yml', '.yaml'):
			file_data = yaml.load(file_h, Loader=(YamlIncludeLoader if yaml_include else YamlLoader))
		else:
			raise ValueError('unknown configuration file extension: ' + extension)
	return file_data

class YamlIncludeLoader(YamlLoader):
	yaml_constructors = copy.copy(YamlLoader.yaml_constructors)
	def __init__(self, stream, *args, **kwargs):
		self.file_path = os.path.abspath(stream.name)
		super(YamlIncludeLoader, self).__init__(stream, *args, **kwargs)
		self.add_constructor('!include', self.constructor_include)

	@staticmethod
	def constructor_include(self, node):
		directory = os.path.dirname(self.file_path)
		return _load_file(os.path.join(directory, self.construct_scalar(node)))

class Configuration(configuration.MemoryConfiguration):
	"""
	The server configuration object. This can load from files in both the JSON
	and YAML formats. Files in the YAML format can use the ``!include``
	directive to include data from other files of supported formats.
	"""
	@classmethod
	def from_file(cls, file_path):
		"""
		Load the configuration from the specified file.

		:param str file_path: The path to the configuration file to load.
		:return: The loaded server configuration.
		:rtype: :py:class:`.Configuration`
		"""
		return cls(_load_file(file_path))

	def iter_schema_errors(self, schema_file):
		"""
		Iterate over the :py:class:`~jsonschema.exceptions.ValidationError`
		instances for all errors found within the specified schema.

		:param str schema_file: The path to the schema file to use for validation.
		:return: Each of the validation errors.
		:rtype: :py:class:`~jsonschema.exceptions.ValidationError`
		"""
		with open(schema_file, 'r') as file_h:
			schema = json.load(file_h)
		validator = jsonschema.Draft4Validator(schema)
		for error in validator.iter_errors(self.get_storage()):
			yield error

	def schema_errors(self, schema_file):
		"""
		Get a tuple of :py:class:`~jsonschema.exceptions.ValidationError`
		instances for all errors found within the specified schema.

		:param str schema_file: The path to the schema file to use for validation.
		:return: The validation errors.
		:rtype: tuple
		"""
		return tuple(self.iter_schema_errors(schema_file))

def ex_load_config(config_file, validate_schema=True):
	"""
	Load the server configuration from the specified file. This function is
	meant to be called early on during a scripts execution and if any error
	occurs, details will be printed and the process will exit.

	:param str config_file: The path to the configuration file to load.
	:param bool validate_schema: Whether or not to validate the schema of the configuration.
	:return: The loaded server configuration.
	:rtype: :py:class:`.Configuration`
	"""
	try:
		config = Configuration.from_file(config_file)
	except Exception as error:
		color.print_error('an error occurred while parsing the server configuration file')
		if isinstance(error, yaml.error.YAMLError):
			problem = getattr(error, 'problem', 'unknown yaml error')
			if hasattr(error, 'problem_mark'):
				prob_lineno = error.problem_mark.line + 1
				color.print_error("{0} - {1}:{2} {3}".format(error.__class__.__name__, config_file, prob_lineno, problem))
				lines = open(config_file, 'rU').readlines()
				for lineno, line in enumerate(lines[max(prob_lineno - 3, 0):(prob_lineno + 2)], max(prob_lineno - 3, 0) + 1):
					color.print_error("  {0} {1: <3}: {2}".format(('=>' if lineno == prob_lineno else '  '), lineno, line.rstrip()))
			else:
				color.print_error("{0} - {1}: {2}".format(error.__class__.__name__, config_file, problem))
		color.print_error('fix the errors in the configuration file and restart the server')
		sys.exit(os.EX_CONFIG)

	# check the configuration for missing and incompatible options
	if validate_schema:
		find.init_data_path('server')
		config_schema = find.data_file(os.path.join('schemas', 'json', 'king-phisher.server.config.json'))
		if not config_schema:
			color.print_error('could not load server configuration schema data')
			sys.exit(os.EX_NOINPUT)

		schema_errors = config.schema_errors(config_schema)
		if schema_errors:
			color.print_error('the server configuration validation encountered the following errors:')
			for schema_error in schema_errors:
				color.print_error("  - {0} error: {1} ({2})".format(schema_error.validator, '.'.join(map(str, schema_error.path)), schema_error.message))
			sys.exit(os.EX_CONFIG)
	return config
