# -*- coding: utf-8 -*-
#
#  king_phisher/client/__main__.py
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

import argparse
import logging
import os
import sys
import threading
import time

if getattr(sys, 'frozen', False):
	# set the basemap data directory for frozen builds
	os.environ['BASEMAPDATA'] = os.path.join(os.path.dirname(sys.executable), 'mpl-basemap-data')

from king_phisher import startup
from king_phisher import color
from king_phisher import find
from king_phisher import utilities
from king_phisher import version
from king_phisher.client import application
from king_phisher.client import gui_utilities

from gi.repository import GObject
from gi.repository import Gtk

def main():
	parser = argparse.ArgumentParser(prog='KingPhisher', description='King Phisher Client GUI', conflict_handler='resolve')
	utilities.argp_add_args(parser, default_root='KingPhisher')
	startup.argp_add_client(parser)
	arguments = parser.parse_args()

	# basic runtime checks
	if sys.version_info < (3, 4):
		color.print_error('the Python version is too old (minimum required is 3.4)')
		return 0

	if Gtk.check_version(3, 14, 0):
		color.print_error('the GTK+ version is too old (minimum required is 3.14)')
		return 0

	if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'):
		color.print_error('no display was detected, this must be run with an interactive X session')
		return 0

	config_file = arguments.config_file
	use_plugins = arguments.use_plugins
	use_style = arguments.use_style
	del arguments, parser
	logger = logging.getLogger('KingPhisher.Client.CLI')

	if sys.platform.startswith('linux') and not os.getuid():
		logger.warning('it is not necessary to run the king phisher client as root')

	find.init_data_path('client')

	if not gui_utilities.which_glade():
		color.print_error('unable to locate the glade ui data file')
		return 0

	logger.debug("king phisher version: {0} python version: {1}.{2}.{3}".format(version.version, sys.version_info[0], sys.version_info[1], sys.version_info[2]))
	logger.debug("client running in process: {0} main tid: 0x{1:x}".format(os.getpid(), threading.current_thread().ident))

	start_time = time.time()
	logger.debug('using ui data from glade file: ' + gui_utilities.which_glade())
	try:
		app = application.KingPhisherClientApplication(config_file=config_file, use_plugins=use_plugins, use_style=use_style)
	except Exception as error:
		logger.critical("initialization error: {0} ({1})".format(error.__class__.__name__, getattr(error, 'message', 'n/a')))
		color.print_error('failed to initialize the King Phisher client')
		return 0
	logger.debug("client loaded in {0:.2f} seconds".format(time.time() - start_time))

	GObject.threads_init()
	return app.run([])

if __name__ == '__main__':
	sys.exit(main())
