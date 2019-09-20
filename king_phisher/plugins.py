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

import collections
import copy
import distutils.version
import functools
import importlib
import inspect
import logging
import os
import platform
import re
import shutil
import sys
import textwrap
import threading

import smoke_zephyr.requirements

from king_phisher import constants
from king_phisher import errors
from king_phisher import its
from king_phisher import startup
from king_phisher import utilities
from king_phisher import version

import pluginbase

StrictVersion = distutils.version.StrictVersion

def _recursive_reload(package, package_name, completed):
	importlib.reload(package)
	completed.append(package)
	for module in dir(package):
		module = getattr(package, module)
		if not inspect.ismodule(module):
			continue
		if not getattr(module, '__package__', '').startswith(package_name):
			continue
		if module in completed:
			continue
		_recursive_reload(module, package_name, completed)

def recursive_reload(module):
	"""
	Reload *module* and if it is a package, recursively find and reload it's
	imported sub-modules.

	:param module: The module to reload.
	:type module: module
	:return: The reloaded module.
	"""
	_recursive_reload(module, module.__package__, [])
	return module

def _resolve_lib_path(lib_path=None):
	if not lib_path:
		if its.on_windows:
			lib_path = os.path.join('%LOCALAPPDATA%', 'king-phisher', 'lib')
		else:
			lib_path = os.path.join('$HOME', '.local', 'lib', 'king-phisher')
	lib_path = os.path.abspath(os.path.expandvars(lib_path))
	lib_path = os.path.join(lib_path, "python{}.{}".format(sys.version_info.major, sys.version_info.minor), 'site-packages')
	if not os.path.isdir(lib_path):
		os.makedirs(lib_path)
	return lib_path

class OptionBase(object):
	"""
	A base class for options which can be configured for plugins.
	"""
	_type = str
	def __init__(self, name, description, default=None):
		"""
		:param str name: The name of this option.
		:param str description: The description of this option.
		:param default: The default value of this option.
		"""
		self.name = name
		self.description = description
		self.default = default

class OptionBoolean(OptionBase):
	"""A plugin option which is represented with a boolean value."""
	_type = bool

class OptionEnum(OptionBase):
	"""A plugin option which is represented with an enumerable value."""
	_type = str
	def __init__(self, name, description, choices, default=None):
		"""
		:param str name: The name of this option.
		:param str description: The description of this option.
		:param tuple choices: The supported values for this option.
		:param default: The default value of this option.
		"""
		self.choices = choices
		super(OptionEnum, self).__init__(name, description, default=default)

class OptionInteger(OptionBase):
	"""A plugin option which is represented with an integer value."""
	_type = int

class OptionString(OptionBase):
	"""A plugin option which is represented with a string value."""
	pass

class Requirements(collections.abc.Mapping):
	"""
	This object servers to map requirements specified as strings to their
	respective values. Once the requirements are defined, this class can then be
	used to evaluate them in an effort to determine which requirements are met
	and which are not.
	"""
	_package_regex = re.compile(r'^(?P<name>[\w\-]+)(([<>=]=)(\d+(\.\d+)*))?$')
	def __init__(self, items):
		"""
		:param dict items: A dictionary or two-dimensional array mapping requirement names to their respective values.
		"""
		# call dict here to allow items to be a two dimensional array suitable for passing to dict
		items = dict(items)
		packages = items.get('packages')
		if isinstance(packages, (list, set, tuple)):
			missing_packages = self._check_for_missing_packages(packages)
			packages_dict = {}
			for package_version in packages:
				match = self._package_regex.match(package_version)
				package_name = match.group('name') if match else package_version
				packages_dict[package_version] = package_name not in missing_packages
			items['packages'] = packages_dict
		self._storage = items

	def __repr__(self):
		return "<{0} is_compatible={1!r} >".format(self.__class__.__name__, self.is_compatible)

	def __getitem__(self, key):
		return self._storage[key]

	def __iter__(self):
		return iter(self._storage)

	def __len__(self):
		return len(self._storage)

	@property
	def is_compatible(self):
		"""Whether or not all requirements are met."""
		for req_type, req_details, req_met in self.compatibility_iter():
			if not req_met:
				return False
		return True

	def compatibility_iter(self):
		"""
		Iterate over each of the requirements, evaluate them and yield a tuple
		regarding them.
		"""
		StrictVersion = distutils.version.StrictVersion
		if self._storage.get('minimum-python-version'):
			# platform.python_version() cannot be used with StrictVersion because it returns letters in the version number.
			available = StrictVersion(self._storage['minimum-python-version']) <= StrictVersion('.'.join(map(str, sys.version_info[:3])))
			yield ('Minimum Python Version', self._storage['minimum-python-version'], available)

		if self._storage.get('minimum-version'):
			available = StrictVersion(self._storage['minimum-version']) <= StrictVersion(version.distutils_version)
			yield ('Minimum King Phisher Version', self._storage['minimum-version'], available)

		if self._storage.get('packages'):
			for name, available in self._storage['packages'].items():
				yield ('Required Package', name, available)

		if self._storage.get('platforms'):
			platforms = tuple(p.title() for p in self._storage['platforms'])
			system = platform.system()
			yield ('Supported Platforms', ', '.join(platforms), system.title() in platforms)

	def _check_for_missing_packages(self, packages):
		missing_packages = []
		for package in packages:
			if package.startswith('gi.'):
				try:
					if not importlib.util.find_spec(package):
						missing_packages.append(package)
				except ImportError:
					missing_packages.append(package)
				continue
			package_check = smoke_zephyr.requirements.check_requirements([package])
			if package_check:
				missing_packages.append(package_check[0])
		return missing_packages

	@property
	def compatibility(self):
		return tuple(self.compatibility_iter())

	def to_dict(self):
		"""
		Return a dictionary representing the requirements.
		"""
		# this method always returns 'packages' as an iterable
		storage = copy.deepcopy(self._storage)
		if 'packages' in storage:
			storage['packages'] = tuple(storage['packages'].keys())
		return storage

class PluginBaseMeta(type):
	"""
	The meta class for :py:class:`.PluginBase` which provides additional class
	properties based on defined attributes.
	"""
	req_min_version = None
	req_packages = None
	def __new__(mcs, name, bases, dct):
		description = dct.get('description', '')
		if description:
			if description[0] == '\n':
				description = description[1:]
			description = textwrap.dedent(description)
			description = description.split('\n\n')
			description = [chunk.replace('\n', ' ').strip() for chunk in description]
			dct['description'] = '\n\n'.join(description)
		raw_reqs = {}
		update_requirements = functools.partial(mcs._update_requirements, bases, dct, raw_reqs)
		update_requirements('req_min_py_version', 'minimum-python-version')
		update_requirements('req_min_version', 'minimum-version')
		update_requirements('req_packages', 'packages')
		update_requirements('req_platforms', 'platforms')
		dct['requirements'] = Requirements(raw_reqs)
		return super(PluginBaseMeta, mcs).__new__(mcs, name, bases, dct)

	@staticmethod
	def _update_requirements(bases, dct, requirements, property, requirement):
		value = None
		if property in dct:
			value = dct[property]
		else:
			base = next((base for base in bases if hasattr(base, property)), None)
			if base is not None:
				value = getattr(base, property)
		if value is None:
			return
		if hasattr(value, '__len__') and not len(value):
			return
		requirements[requirement] = value

	@property
	def compatibility(cls):
		"""
		A generator which yields tuples of compatibility information based on
		the classes defined attributes. Each tuple contains three elements, a
		string describing the requirement, the requirements value, and a boolean
		indicating whether or not the requirement is met.

		:return: Tuples of compatibility information.
		"""
		return cls.requirements.compatibility

	@property
	def is_compatible(cls):
		"""
		Whether or not this plugin is compatible with this version of King
		Phisher. This can only be checked after the module is imported, so any
		references to non-existent classes in older versions outside of the
		class methods will still cause a load error.

		:return: Whether or not this plugin class is compatible.
		:rtype: bool
		"""
		return cls.requirements.is_compatible

	@property
	def name(cls):
		return cls.__module__.split('.')[-1]

	@property
	def metadata(cls):
		metadata = {
			'authors': cls.authors,
			'description': cls.description,
			'homepage': cls.homepage,
			'is_compatible': cls.is_compatible,
			'name': cls.name,
			'requirements': cls.requirements.to_dict(),
			'title': cls.title,
			'version': cls.version,
		}
		if cls.classifiers:
			metadata['classifiers'] = cls.classifiers
		if cls.reference_urls:
			metadata['reference_urls'] = cls.reference_urls
		return metadata

# stylized metaclass definition to be Python 2.7 and 3.x compatible
class PluginBase(PluginBaseMeta('PluginBaseMeta', (object,), {})):
	"""
	A base class to be inherited by all plugins. Overriding or extending the
	standard __init__ method should be avoided to be compatible with future API
	changes. Instead the :py:meth:`.initialize` and :py:meth:`.finalize` methods
	should be overridden to provide plugin functionality.
	"""
	authors = ()
	"""The tuple of authors who have provided this plugin."""
	classifiers = ()
	"""An array containing optional classifier strings. These are free-formatted strings used to identify functionality."""
	title = None
	"""The title of the plugin."""
	description = None
	"""A description of the plugin and what it does."""
	homepage = None
	"""An optional homepage for the plugin."""
	options = []
	"""A list of configurable option definitions for the plugin."""
	reference_urls = ()
	"""An array containing optional reference URL strings."""
	req_min_py_version = None
	"""The required minimum Python version for compatibility."""
	req_min_version = '1.3.0b0'
	"""The required minimum version for compatibility."""
	req_packages = {}
	"""A dictionary of required packages, keyed by the package name and a boolean value of it's availability."""
	req_platforms = ()
	"""A tuple of case-insensitive supported platform names."""
	version = '1.0'
	"""The version identifier of this plugin."""
	_logging_prefix = 'KingPhisher.Plugins.'
	def __init__(self):
		logger = logging.getLogger(self._logging_prefix + self.name + '.' + self.__class__.__name__)
		self.logger = utilities.PrefixLoggerAdapter("[plugin: {0}]".format(self.name), logger, {})
		if getattr(self, 'config') is None:  # hasattr will return False with subclass properties
			self.config = {}
			"""The plugins configuration dictionary for storing the values of it's options."""
		for option in self.options:
			if option.name in self.config:
				continue
			self.config[option.name] = option.default

	@property
	def name(self):
		"""The name of this plugin."""
		return self.__class__.name

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

		:return: Whether or not the plugin successfully initialized itself.
		:rtype: bool
		"""
		return True

class PluginManagerBase(object):
	"""
	A managing object to control loading and enabling individual plugin objects.
	"""
	_plugin_klass = PluginBase
	def __init__(self, path, args=None, library_path=constants.AUTOMATIC):
		"""
		:param tuple path: A tuple of directories from which to load plugins.
		:param tuple args: Arguments which should be passed to plugins when
			their class is initialized.
		:param str library_path: A path to use for plugins library dependencies.
			This value will be added to :py:attr:`sys.path` if it is not already
			included.
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

		if library_path is not None:
			library_path = _resolve_lib_path(library_path)
		if library_path:
			if library_path not in sys.path:
				sys.path.append(library_path)
			library_path = os.path.abspath(library_path)
			self.logger.debug('using plugin-specific library path: ' + library_path)
		else:
			self.logger.debug('no plugin-specific library path has been specified')
		self.library_path = library_path
		"""
		The path to a directory which is included for additional libraries. This
		path must be writable by the current user.

		The default value is platform and Python-version (where X.Y is the major
		and minor versions of Python) dependant:

		:Linux:
			``~/.local/lib/king-phisher/pythonX.Y/site-packages``

		:Windows:
			``%LOCALAPPDATA%\\king-phisher\\lib\\pythonX.Y\\site-packages``
		"""

	def __contains__(self, key):
		return key in self.loaded_plugins

	def __getitem__(self, key):
		return self.loaded_plugins[key]

	def __delitem__(self, key):
		self.unload(key)

	def __iter__(self):
		for name, klass in self.loaded_plugins.items():
			yield name, klass

	def __len__(self):
		return len(self.loaded_plugins)

	@property
	def available(self):
		"""Return a tuple of all available plugins that can be loaded."""
		return tuple(self.plugin_source.list_plugins())

	def get_plugin_path(self, name):
		"""
		Get the path at which the plugin data resides. This is either the path
		to the single plugin file or a folder in the case that the plugin is a
		module. In either case, the path is an absolute path.

		:param str name: The name of the plugin to get the path for.
		:return: The path of the plugin data.
		:rtype: str
		"""
		module = self.load_module(name)
		path = getattr(module, '__file__', None)
		if path is None:
			return
		if path.endswith(('.pyc', '.pyo')):
			path = path[:-1]
		if path.endswith(os.path.sep + '__init__.py'):
			path = path[:-11]
		return path

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
		if not klass.is_compatible:
			self._lock.release()
			raise errors.KingPhisherPluginError(name, 'the plugin is incompatible')
		inst = klass(*self.plugin_init_args)
		try:
			initialized = inst.initialize()
		except Exception:
			self.logger.error("failed to enable plugin '{0}', initialize threw an exception".format(name), exc_info=True)
			try:
				inst._cleanup()
			except Exception:
				self.logger.error("failed to clean up resources for plugin '{0}'".format(name), exc_info=True)
			self._lock.release()
			raise
		if not initialized:
			self.logger.warning("failed to enable plugin '{0}', initialize check failed".format(name))
			self._lock.release()
			return
		self.enabled_plugins[name] = inst
		self._lock.release()
		self.logger.info("plugin '{0}' has been enabled".format(name))
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
		self.logger.info("plugin '{0}' has been disabled".format(name))

	# methods to deal with plugin load operations
	def load(self, name, reload_module=False):
		"""
		Load a plugin into memory, this is effectively the Python equivalent of
		importing it. A reference to the plugin class is kept in
		:py:attr:`.loaded_plugins`. If the plugin is already loaded, no changes
		are made.

		:param str name: The name of the plugin to load.
		:param bool reload_module: Reload the module to allow changes to take affect.
		:return: The plugin class.
		"""
		self._lock.acquire()
		if not reload_module and name in self.loaded_plugins:
			self._lock.release()
			return
		module = self.load_module(name, reload_module=reload_module)
		klass = getattr(module, 'Plugin', None)
		if klass is None:
			self._lock.release()
			self.logger.warning("failed to load plugin '{0}', Plugin class not found".format(name))
			raise errors.KingPhisherPluginError(name, 'the Plugin class is missing')
		if not issubclass(klass, self._plugin_klass):
			self._lock.release()
			self.logger.warning("failed to load plugin '{0}', Plugin class is invalid".format(name))
			raise errors.KingPhisherPluginError(name, 'the Plugin class is invalid')
		self.loaded_plugins[name] = klass
		self.logger.debug("plugin '{0}' has been {1}loaded".format(name, 're' if reload_module else ''))
		self._lock.release()
		return klass

	def load_all(self, on_error=None):
		"""
		Load all available plugins. Exceptions while loading specific plugins
		are ignored. If *on_error* is specified, it will be called from within
		the exception handler when a plugin fails to load correctly. It will be
		called with two parameters, the name of the plugin and the exception
		instance.

		:param on_error: A call back function to call when an error occurs while loading a plugin.
		:type on_error: function
		"""
		self._lock.acquire()
		plugins = self.plugin_source.list_plugins()
		self.logger.info("loading {0:,} plugins".format(len(plugins)))
		for name in plugins:
			try:
				self.load(name)
			except Exception as error:
				if on_error:
					on_error(name, error)
		self._lock.release()

	def load_module(self, name, reload_module=False):
		"""
		Load the module which contains a plugin into memory and return the
		entire module object.

		:param str name: The name of the plugin module to load.
		:param bool reload_module: Reload the module to allow changes to take affect.
		:return: The plugin module.
		"""
		try:
			module = self.plugin_source.load_plugin(name)
		except Exception as error:
			self._lock.release()
			raise error
		if reload_module:
			recursive_reload(module)
		return module

	def install_packages(self, packages):
		"""
		This function will take a list of Python packages and attempt to install
		them through pip to the :py:attr:`.library_path`.

		.. versionadded:: 1.14.0

		:param list packages: list of python packages to install using pip.
		:return: The process results from the command execution.
		:rtype: :py:class:`~.ProcessResults`
		"""
		pip_options = []
		if self.library_path is None:
			raise errors.KingPhisherResourceError('missing plugin-specific library path')
		pip_options.extend(['--target', self.library_path])
		if its.frozen:
			args = [os.path.join(os.path.dirname(sys.executable), 'python.exe')]
		else:
			args = [sys.executable] + pip_options + packages
		args += ['-m', 'pip', 'install'] + pip_options + packages
		if len(packages) > 1:
			info_string = "installing packages: {}"
		else:
			info_string = "installing package: {}"
		self.logger.info(info_string.format(', '.join(packages)))
		return startup.run_process(args)

	def uninstall(self, name):
		"""
		Uninstall a plugin by first unloading it and then delete it's data on
		disk. The plugin data on disk is found with the
		:py:meth:`.get_plugin_path` method.

		:param str name: The name of the plugin to uninstall.
		:return: Whether or not the plugin was successfully uninstalled.
		:rtype: bool
		"""
		plugin_path = self.get_plugin_path(name)
		if os.path.isfile(plugin_path) or os.path.islink(plugin_path):
			os.remove(plugin_path)
		elif os.path.isdir(plugin_path):
			shutil.rmtree(plugin_path)
		else:
			self.logger.warning('failed to identify the data path for plugin: ' + name)
			return False
		self.unload(name)
		return True

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
