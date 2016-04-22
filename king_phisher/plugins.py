#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/plugins.py
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

import logging
import threading

import pluginbase

class PluginBase(object):
	authors = []
	title = None
	description = None
	_logging_prefix = 'KingPhisher.Plugins.'
	def __init__(self):
		self.logger = logging.getLogger(self._logging_prefix + self.__class__.__name__)

	def _cleanup(self):
		pass

	def finalize(self):
		pass

	def initialize(self):
		pass

class PluginManagerBase(object):
	_plugin_klass = PluginBase
	def __init__(self, path, args=None):
		self._lock = threading.RLock()
		self.plugin_init_args = (args or ())
		self.plugin_base = pluginbase.PluginBase(package='king_phisher.plugins.loaded')
		self.plugin_source = self.plugin_base.make_plugin_source(searchpath=path)
		self.loaded_plugins = {}
		self.enabled_plugins = {}
		self.logger = logging.getLogger('KingPhisher.Plugins.Manager')
		self.load_all()

	def __contains__(self, key):
		return key in self.loaded_plugins

	def __getitem__(self, key):
		return self.loaded_plugins[key]

	def __delitem__(self, key):
		self.unload(key)

	def __iter__(self):
		for name, inst in self.loaded_plugins.items():
			yield name, inst

	def __len__(self):
		return len(self.loaded_plugins)

	@property
	def available(self):
		return self.plugin_source.list_plugins()

	def shutdown(self):
		self.unload_all()
		self.plugin_source.cleanup()

	# methods to deal with plugin enable operations
	def enable(self, name):
		self._lock.acquire()
		klass = self.loaded_plugins.get(name, None)
		if klass is None:
			klass = self.load(name)
		inst = klass(*self.plugin_init_args)
		self.enabled_plugins[name] = inst
		self._lock.release()
		inst.initialize()
		return inst

	def disable(self, name):
		self._lock.acquire()
		inst = self.enabled_plugins[name]
		inst.finalize()
		inst._cleanup()
		del self.enabled_plugins[name]
		self._lock.release()

	# methods to deal with plugin load operations
	def load(self, name):
		self._lock.acquire()
		module = self.plugin_source.load_plugin(name)
		klass = getattr(module, 'Plugin', None)
		if klass is None:
			self._lock.release()
			raise Exception
		if not issubclass(klass, self._plugin_klass):
			self._lock.release()
			raise Exception
		klass.name = name
		self.loaded_plugins[name] = klass
		self.logger.debug("plugin '{0}' has been loaded".format(name))
		self._lock.release()
		return klass

	def load_all(self):
		self._lock.acquire()
		plugins = self.plugin_source.list_plugins()
		self.logger.info("loading {0:,} plugins".format(len(plugins)))
		for name in plugins:
			self.load(name)
		self._lock.release()

	def unload(self, name):
		self._lock.acquire()
		if name in self.enabled_plugins:
			self.disable(name)
		del self.loaded_plugins[name]
		self.logger.debug("plugin '{0}' has been unloaded".format(name))
		self._lock.release()

	def unload_all(self):
		self._lock.acquire()
		self.logger.info("unloading {0:,} plugins".format(len(self.loaded_plugins)))
		for name in tuple(self.loaded_plugins.keys()):
			self.unload(name)
		self._lock.release()
