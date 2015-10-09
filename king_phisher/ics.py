#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/ics.py
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
import datetime
import os
import re
import uuid

from king_phisher import its

import dateutil.tz
import icalendar
import pytz.tzfile
import tzlocal
import smoke_zephyr.utilities

DAY_ABBREVIATIONS = ('SU', 'MO', 'TU', 'WE', 'TH', 'FR', 'SA')
SECONDS_IN_ONE_DAY = (24 * 60 * 60)
SECONDS_IN_ONE_HOUR = (60 * 60)

POSIX_VAR_OFFSET = r'[A-Z]{3,5}(?P<offset>([\+\-])?[0-9:]{1,5})([A-Z]{3,5}(?P<offset_dst>([\+\-])?([0-9:]{1,5})?))?'
POSIX_VAR_DST0 = POSIX_VAR_OFFSET + r',(?P<start>M\d{1,2}\.[1-5]\.[0-6](/([\+\-])?[0-9:]{1,5})?),(?P<end>M\d{1,2}\.[1-5]\.[0-6](/([\+\-])?[0-9:]{1,5})?)'
POSIX_VAR_DST_RRULE = 'M(?P<month>\d{1,2}).(?P<week>[1-5]).(?P<day>[0-6])(/\d{1,2})?'

zoneinfo_path = os.path.join(os.path.dirname(pytz.tzfile.__file__), 'zoneinfo')

TimezoneOffsetDetails = collections.namedtuple(
	'TimezoneOffsetDetails',
	(
		'offset',
		'offset_dst',
		'dst_start',
		'dst_end'
	)
)

def get_timedelta_for_offset(offset):
	"""
	Take a POSIX environment variable style offset from UTC and convert it into
	a :py:class:`datetime.timedelta` instance.

	:param str offset: The offset from UTC such as '-5:00'
	:return: The parsed offset.
	:rtype: :py:class:`datetime.timedelta`
	"""
	sign = '+'
	if offset[0] in ('+', '-'):
		sign = offset[0]
		offset = offset[1:]
	if ':' in offset:
		hours, minutes = offset.split(':')
	else:
		hours, minutes = offset, 0
	hours = int(hours)
	minutes = int(minutes)
	seconds = ((hours * 60 * 60) + (minutes * 60))
	if sign == '-':
		delta = datetime.timedelta(0, seconds)
	else:
		delta = datetime.timedelta(-1, SECONDS_IN_ONE_DAY - seconds)
	return delta

def get_tz_posix_env_var(tz_name):
	buffer_size = 2048
	assert os.path.isdir(zoneinfo_path)
	file_path = os.path.join(zoneinfo_path, *tz_name.split('/'))
	with open(file_path, 'rb') as file_h:
		magic = file_h.read(4)
		assert magic == b'TZif'
		version = file_h.read(1)
		if version != b'2':
			return ''
		file_h.seek(max(os.path.getsize(file_path) - buffer_size, 0), os.SEEK_SET)
		data = file_h.read(buffer_size)
	end_pos = -2
	if its.py_v3:
		newline = 0x0a
	else:
		newline = '\n'
	while data[end_pos] != newline:
		end_pos -= 1
	end_pos += 1
	env_var = data[end_pos:-1]
	if its.py_v3:
		env_var = env_var.decode('utf-8')
	return env_var

def get_tz_offset_details(tz_name):
	posix_env_var = get_tz_posix_env_var(tz_name)
	if not posix_env_var:
		return
	match = re.match(POSIX_VAR_OFFSET, posix_env_var)
	if not match:
		return
	match = match.groupdict()
	offset = get_timedelta_for_offset(match['offset'])
	if match['offset_dst']:
		offset_dst = get_timedelta_for_offset(match['offset_dst'])
	else:
		# default to an hour difference if it's not specified
		offset_dst = offset - datetime.timedelta(0, SECONDS_IN_ONE_HOUR)
	dst_start = None
	dst_end = None
	match = re.match(POSIX_VAR_DST0, posix_env_var)
	if match:
		match = match.groupdict()
		dst_start = match['start']
		dst_end = match['end']

		match = re.match(POSIX_VAR_DST_RRULE, dst_start)
		details = match.groupdict()
		byday = details['week'] + DAY_ABBREVIATIONS[int(details['day'])]
		dst_start = icalendar.vRecur({'BYMONTH': details['month'], 'FREQ': 'YEARLY', 'INTERVAL': 1, 'BYDAY': byday})

		match = re.match(POSIX_VAR_DST_RRULE, dst_end)
		details = match.groupdict()
		byday = details['week'] + DAY_ABBREVIATIONS[int(details['day'])]
		dst_end = icalendar.vRecur({'BYMONTH': details['month'], 'FREQ': 'YEARLY', 'INTERVAL': 1, 'BYDAY': byday})
	else:
		# remove the dst offset if not rrule is present on when it's active
		offset_dst = None
	details = TimezoneOffsetDetails(offset, offset_dst, dst_start, dst_end)
	return details

class Timezone(icalendar.Timezone):
	def __init__(self, zonename=None):
		super(Timezone, self).__init__()
		if zonename is None:
			zonename = tzlocal.get_localzone().zone
		self.add('tzid', zonename)

		tz_details = get_tz_offset_details(zonename)
		timezone_standard = icalendar.TimezoneStandard()
		timezone_standard.add('dtstart', datetime.datetime(1601, 1, 1, 2, 0, tzinfo=dateutil.tz.tzutc()))
		timezone_standard.add('tzoffsetfrom', tz_details.offset + datetime.timedelta(0, SECONDS_IN_ONE_HOUR))
		timezone_standard.add('tzoffsetto', tz_details.offset)

		if tz_details.offset_dst:
			timezone_standard.add('rrule', tz_details.dst_end)
			timezone_daylight = icalendar.TimezoneDaylight()
			timezone_daylight.add('dtstart', datetime.datetime(1601, 1, 1, 2, 0, tzinfo=dateutil.tz.tzutc()))
			timezone_daylight.add('tzoffsetfrom', tz_details.offset)
			timezone_daylight.add('tzoffsetto', tz_details.offset + datetime.timedelta(0, SECONDS_IN_ONE_HOUR))
			timezone_daylight.add('rrule', tz_details.dst_start)
			self.add_component(timezone_daylight)
		self.add_component(timezone_standard)

class Calendar(icalendar.Calendar):
	def __init__(self, organizer_email, start, organizer_cn=None, duration='1h', location=None):
		super(Calendar, self).__init__()
		if start.tzinfo is None:
			start = start.replace(tzinfo=dateutil.tz.tzlocal())
		start = start.astimezone(dateutil.tz.tzutc())

		if isinstance(duration, str):
			duration = smoke_zephyr.utilities.parse_timespan(duration)
		if not isinstance(duration, datetime.timedelta):
			duration = datetime.timedelta(seconds=duration)

		self.add('method', 'REQUEST')
		self.add('prodid', 'Microsoft Exchange Server 2010')
		self.add('version', '2.0')

		self._event = icalendar.Event()
		event = self._event
		self.add_component(event)
		self.add_component(Timezone())

		organizer = icalendar.vCalAddress('MAILTO:' + organizer_email)
		organizer.params['cn'] = icalendar.vText(organizer_cn or organizer_email)
		event['organizer'] = organizer

		event.add('description', 'This is the event description.')
		event.add('uid', str(uuid.uuid4()))
		event.add('summary', 'This is the event summary.')
		event.add('dtstart', start)
		event.add('dtend', start + duration)
		event.add('class', 'PUBLIC')
		event.add('priority', 5)
		event.add('dtstamp', datetime.datetime.now(dateutil.tz.tzutc()))
		event.add('transp', 'OPAQUE')
		event.add('status', 'CONFIRMED')
		event.add('sequence', 0)
		if location:
			event.add('location', icalendar.vText(location))

		alarm = icalendar.Alarm()
		alarm.add('description', 'REMINDER')
		alarm.add('trigger;related=start', '-PT1H')
		alarm.add('action', 'DISPLAY')
		event.add_component(alarm)

	def __str__(self):
		return self.to_ical()

	def add_attendee(self, email, cn=None, rsvp=True):
		attendee = icalendar.vCalAddress('MAILTO:' + email)
		attendee.params['ROLE'] = icalendar.vText('REQ-PARTICIPANT')
		attendee.params['PARTSTAT'] = icalendar.vText('NEEDS-ACTION')
		attendee.params['RSVP'] = icalendar.vText(str(bool(rsvp)).upper())
		attendee.params['CN'] = icalendar.vText(cn or email)
		self._event.add('attendee', attendee)
