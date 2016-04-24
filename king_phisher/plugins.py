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

from king_phisher import errors
from king_phisher import its

import pluginbase

if its.py_v2:
	_reload = reload
else:
	import importlib
	_reload = importlib.reload

class PluginBase(object):
	"""
	A base class to be inherited by all plugins. Overriding or extending the
	standard __init__ method should be avoided to be compatible with future API
	changes. Instead the :py:meth:`.initialize` and :py:meth:`.finalize` methods
	should be overridden to provide plugin functionality.
	"""
	authors = []
	"""The list of authors who have provided this plugin."""
	title = None
	"""The title of the plugin."""
	description = None
	"""A description of the plugin and what it does."""
	homepage = None
	"""An optional homepage for the plugin."""
	version = '1.0'
	"""The version identifier of this plugin."""
	_logging_prefix = 'KingPhisher.Plugins.'
	def __init__(self):
		self.logger = logging.getLogger(self._logging_prefix + self.__class__.__name__)

	def _cleanup(self):
		pass

	def finalize(self):
		"""
		This method can be overridden to perform any clean up action that the
		plugin needs such as closing files. It is called automatically by the
		manager when the plugin is disabled.
		"""
		pass

	def initialize(self):
		"""
		This method should be overridden to provide the primary functionality of
		the plugin. It is called automatically by the manager when the plugin is
		enabled.
		"""
		pass

class PluginManagerBase(object):
	"""
	A managing object to control loading and enabling individual plugin objects.
	"""
	_plugin_klass = PluginBase
	def __init__(self, path, args=None):
		"""
		:param tuple path: A tuple of directories from which to load plugins.
		:param tuple args: Arguments which should be passed to plugins when their class is initialized.
		"""
		self._lock = threading.RLock()
		self.plugin_init_args = (args or ())
		self.plugin_base = pluginbase.PluginBase(package='king_phisher.plugins.loaded')
		self.plugin_source = self.plugin_base.make_plugin_source(searchpath=path)
		self.loaded_plugins = {}
		"""A dictionary of the loaded plugins and their respective modules."""
		self.enabled_plugins = {}
		"""A dictionary of the enabled plugins and their respective instances."""
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
		"""Return a tuple of all available plugins that can be loaded."""
		return tuple(self.plugin_source.list_plugins())

	def shutdown(self):
		"""
		Unload all plugins and perform additional clean up operations.
		"""
		self.unload_all()
		self.plugin_source.cleanup()

	# methods to deal with plugin enable operations
	def enable(self, name):
		"""
		Enable a plugin by it's name. This will create a new instance of the
		plugin modules "Plugin" class, passing it the arguments defined in
		:py:attr:`.plugin_init_args`. A reference to the plugin instance is kept
		in :py:attr:`.enabled_plugins`. After the instance is created, the
		plugins :py:meth:`~.PluginBase.initialize` method is called.

		:param str name: The name of the plugin to enable.
		:return: The newly created instance.
		:rtype: :py:class:`.PluginBase`
		"""
		self._lock.acquire()
		klass = self.loaded_plugins[name]
		inst = klass(*self.plugin_init_args)
		self.enabled_plugins[name] = inst
		self._lock.release()
		inst.initialize()
		return inst

	def disable(self, name):
		"""
		Disable a plugin by it's name. This call the plugins
		:py:meth:`.PluginBase.finalize` method to allow it to perform any
		clean up operations.

		:param str name: The name of the plugin to disable.
		"""
		self._lock.acquire()
		inst = self.enabled_plugins[name]
		inst.finalize()
		inst._cleanup()
		del self.enabled_plugins[name]
		self._lock.release()

	# methods to deal with plugin load operations
	def load(self, name, reload_module=False):
		"""
		Load a plugin into memory, this is effectively the Python equivalent of
		importing it. A reference to the plugin class is kept in
		:py:attr:`.loaded_plugins`. If the plugin is already loaded, no changes
		are made.

		:param str name: The name of the plugin to load.
		:param bool reload_module: Reload the module to allow changes to take affect.
		:return:
		"""
		self._lock.acquire()
		if name in self.loaded_plugins:
			self._lock.release()
			return
		try:
			module = self.plugin_source.load_plugin(name)
		except Exception as error:
			self._lock.release()
			raise error
		if reload_module:
			_reload(module)
		klass = getattr(module, 'Plugin', None)
		if klass is None:
			self._lock.release()
			self.logger.warning("failed to load plugin '{0}', Plugin class not found".format(name))
			raise errors.KingPhisherResourceError('the Plugin class is missing')
		if not issubclass(klass, self._plugin_klass):
			self._lock.release()
			self.logger.warning("failed to load plugin '{0}', Plugin class is invalid".format(name))
			raise errors.KingPhisherResourceError('the Plugin class is invalid')
		klass.name = name
		self.loaded_plugins[name] = klass
		self.logger.debug("plugin '{0}' has been loaded".format(name))
		self._lock.release()
		return klass

	def load_all(self):
		"""
		Load all available plugins. Exceptions while loading specific plugins
		are ignored.
		"""
		self._lock.acquire()
		plugins = self.plugin_source.list_plugins()
		self.logger.info("loading {0:,} plugins".format(len(plugins)))
		for name in plugins:
			try:
				self.load(name)
			except Exception:
				pass
		self._lock.release()

	def unload(self, name):
		"""
		Unload a plugin from memory. If the specified plugin is currently
		enabled, it will first be disabled before being unloaded. If the plugin
		is not already loaded, no changes are made.

		:param str name: The name of the plugin to unload.
		"""
		self._lock.acquire()
		if not name in self.loaded_plugins:
			self._lock.release()
			return
		if name in self.enabled_plugins:
			self.disable(name)
		del self.loaded_plugins[name]
		self.logger.debug("plugin '{0}' has been unloaded".format(name))
		self._lock.release()

	def unload_all(self):
		"""
		Unload all available plugins. Exceptions while unloading specific
		plugins are ignored.
		"""
		self._lock.acquire()
		self.logger.info("unloading {0:,} plugins".format(len(self.loaded_plugins)))
		for name in tuple(self.loaded_plugins.keys()):
			try:
				self.unload(name)
			except Exception:
				pass
		self._lock.release()
