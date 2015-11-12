#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/color.py
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
# pylint: disable=superfluous-parens

import logging
import os
import re
import traceback

from king_phisher import its

import termcolor

print_colors = its.on_linux
LEVEL_COLORS = {
	logging.DEBUG: ('cyan',),
	logging.INFO: ('white',),
	logging.WARNING: ('yellow',),
	logging.ERROR: ('red',),
	logging.CRITICAL: ('white', 'on_red')
}

class ColoredLogFormatter(logging.Formatter):
	"""
	A formatting class suitable for use with the :py:mod:`logging` module which
	colorizes the names of log levels.
	"""
	def format(self, record):
		orig_levelname = None
		if record.levelno in LEVEL_COLORS:
			orig_levelname = record.levelname
			record.levelname = termcolor.colored("{0:<8}".format(record.levelname), *LEVEL_COLORS[record.levelno], attrs=['bold'])
		value = super(ColoredLogFormatter, self).format(record)
		if orig_levelname is not None:
			record.levelname = orig_levelname
		return value

	@staticmethod
	def formatException(exc_info):
		tb_lines = traceback.format_exception(*exc_info)
		for line_no, line in enumerate(tb_lines):
			search = re.search(r'File \"([^"]+)", line ([\d,]+), in', line)
			if search:
				new_line = line[:search.start(1)]
				new_line += termcolor.colored(search.group(1), 'yellow', attrs=['underline'])
				new_line += line[search.end(1):search.start(2)]
				new_line += termcolor.colored(search.group(2), 'white', attrs=['bold'])
				new_line += line[search.end(2):]
				tb_lines[line_no] = new_line
		line = tb_lines[-1]
		if line.find(':'):
			idx = line.find(':')
			line = termcolor.colored(line[:idx], 'red', attrs=['bold']) + line[idx:]
		if line.endswith(os.linesep):
			line = line[:-len(os.linesep)]
		tb_lines[-1] = line
		return ''.join(tb_lines)

def convert_hex_to_tuple(hex_color, raw=False):
	"""
	Converts an RGB hex triplet such as #ff0000 into an RGB tuple. If *raw* is
	True then each value is on a scale from 0 to 255 instead of 0.0 to 1.0.

	:param str hex_color: The hex code for the desired color.
	:param bool raw: Whether the values are raw or percentages.
	:return: The color as a red, green, blue tuple.
	:rtype: tuple
	"""
	if hex_color.startswith('#'):
		hex_color = hex_color[1:]
	if len(hex_color) != 6:
		raise ValueError('hex color code is in an invalid format')
	rgb = (int(x, 16) for x in (hex_color[i:i + 2] for i in range(0, 6, 2)))
	if not raw:
		rgb = (float(x) / 255.0 for x in rgb)
	return tuple(rgb)

def convert_tuple_to_hex(rgb, raw=False):
	"""
	Converts an RGB color tuple info a hex string such as #ff0000. If *raw* is
	True then each value is treated as if it were on a scale from 0 to 255
	instead of 0.0 to 1.0.

	:param tuple rgb: The RGB tuple to convert into a string.
	:param bool raw: Whether the values are raw or percentages.
	:return: The RGB color as a string.
	:rtype: str
	"""
	if raw:
		rgb = (int(x) for x in rgb)
	else:
		rgb = (int(round(float(x) * 255.0)) for x in rgb)
	return "#{0:02x}{1:02x}{2:02x}".format(*rgb)

def get_scale(color_low, color_high, count, ascending=True):
	"""
	Create a scale of colors gradually moving from the low color to the high
	color.

	:param tuple color_low: The darker color to start the scale with.
	:param tuple color_high: The lighter color to end the scale with.
	:param count: The total number of resulting colors.
	:param bool ascending: Whether the colors should be ascending from lighter to darker or the reverse.
	:return: An array of colors starting with the low and gradually transitioning to the high.
	:rtype: tuple
	"""
	if sum(color_low) > sum(color_high):
		# the colors are reversed so fix it and continue
		color_low, color_high = (color_high, color_low)
		ascending = not ascending
	for _ in range(1):
		if count < 1:
			scale = []
		elif count == 1:
			scale = [color_low]
		elif count == 2:
			scale = [color_low, color_high]
		else:
			scale = [color_low]
			for modifier in range(1, count - 1):
				modifier = float(modifier) / float(count - 1)
				scale.append(tuple(min(color_high[i], color_low[i]) + (abs(color_high[i] - color_low[i]) * modifier) for i in range(0, 3)))
			scale.append(color_high)
	if not ascending:
		scale.reverse()
	return tuple(scale)

def print_error(message):
	"""
	Print an error message to the console.

	:param str message: The message to print
	"""
	prefix = '[-] '
	if print_colors:
		prefix = termcolor.colored(prefix, 'red', attrs=['bold'])
	print(prefix + message)

def print_good(message):
	"""
	Print a good message to the console.

	:param str message: The message to print
	"""
	prefix = '[+] '
	if print_colors:
		prefix = termcolor.colored(prefix, 'green', attrs=['bold'])
	print(prefix + message)

def print_status(message):
	"""
	Print a status message to the console.

	:param str message: The message to print
	"""
	prefix = '[*] '
	if print_colors:
		prefix = termcolor.colored(prefix, 'blue', attrs=['bold'])
	print(prefix + message)
