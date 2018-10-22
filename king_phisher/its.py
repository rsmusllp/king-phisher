#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/its.py
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

################################################################################
#
# CLEAN ROOM MODULE
#
# This module is classified as a "Clean Room" module and is subject to
# restrictions on what it may import.
#
# See: https://king-phisher.readthedocs.io/en/latest/development/modules.html#clean-room-modules
#
################################################################################

import os
import sys

frozen = getattr(sys, 'frozen', False)
"""Whether or not the current environment is a frozen Windows build."""

on_linux = sys.platform.startswith('linux')
"""Whether or not the current platform is Linux."""
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
"""Whether or not the current platform is ReadTheDocs."""
on_windows = sys.platform.startswith('win')
"""Whether or not the current platform is Windows."""

py_v2 = sys.version_info[0] == 2
"""Whether or not the current Python version is 2.x."""
py_v3 = sys.version_info[0] == 3
"""Whether or not the current Python version is 3.x."""

mocked = False
"""
Whether or not certain objects are non-functional mock implementations. These
are used for the purpose of generating documentation.
"""
