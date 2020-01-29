#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/geoip.py
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
import logging
import os
import shutil
import sys
import tarfile
import tempfile
import threading

from king_phisher import errors
from king_phisher import find
from king_phisher import ipaddress

import geoip2.database
import geoip2.errors
import maxminddb.errors
import requests

__all__ = ('init_database', 'lookup', 'GeoLocation')

DB_DOWNLOAD_URL = 'https://zerosteiner.s3.amazonaws.com/data/GeoLite2-City.tar.gz'
DB_RESULT_FIELDS = ('city', 'continent', 'coordinates', 'country', 'postal_code', 'time_zone')
"""A tuple listing the fields that are required in database results."""

AddressNotFoundError = geoip2.errors.AddressNotFoundError
_geoip_db = None
_geoip_db_lock = threading.Lock()
logger = logging.getLogger('KingPhisher.GeoIP')

Coordinates = collections.namedtuple('Coordinates', ('latitude', 'longitude'))
"""A named tuple for representing GPS coordinates."""

def _normalize_encoding(word):
	if sys.version_info[0] == 2 and isinstance(word, unicode):
		word = word.encode('ascii', 'ignore')
	return word

def download_geolite2_city_db(dest, license=None, date=None):
	"""
	Download the GeoLite2 database and save it to disk.

	.. versionchanged:: 1.16.0
		Added the *license* and *date* parameters.

	:param str dest: The file path to save the database to.
	:param str license: The MaxMind license key to use to download the database.
	:param date: The date for which to download the database.
	:type date: :py:class:`datetime.date`
	"""
	params = {'edition_id': 'GeoLite2-City', 'license_key': license, 'suffix': 'tar.gz'}
	if date is not None:
		if license is None:
			raise errors.KingPhisherError('can not request a specific date when no license is specified')
		params['date'] = date.strftime('%Y%m%d')
	try:
		if license is None:
			logger.info('no license was specified, downloading the default GeoLite2 database')
			response = requests.get(DB_DOWNLOAD_URL, stream=True)
		else:
			response = requests.get('https://download.maxmind.com/app/geoip_download', params=params, stream=True)
	except requests.ConnectionError:
		logger.error('geoip database download failed (could not connect to the server)')
		raise errors.KingPhisherResourceError('could not download the geoip database') from None
	except requests.RequestException:
		logger.error('geoip database download failed', exc_info=True)
		raise errors.KingPhisherResourceError('could not download the geoip database') from None
	tmp_file = tempfile.mkstemp()
	os.close(tmp_file[0])
	tmp_file = tmp_file[1]
	try:
		with open(tmp_file, 'wb') as file_h:
			for chunk in response.iter_content(chunk_size=4096):
				file_h.write(chunk)
				file_h.flush()
		tar_file = tarfile.open(tmp_file, mode='r:gz')
		member = next((name for name in tar_file.getnames() if name.endswith('GeoLite2-City.mmdb')), None)
		if member is None:
			raise errors.KingPhisherResourceError('could not find the GeoLite2-City.mmdb file in the archive')
		with open(dest, 'wb') as file_h:
			shutil.copyfileobj(tar_file.extractfile(member), file_h)
	finally:
		os.remove(tmp_file)
	os.chmod(dest, 0o644)
	return os.stat(dest).st_size

def init_database(database_file):
	"""
	Create and initialize the GeoLite2 database engine. This must be done before
	classes and functions in this module attempt to look up results. If the
	specified database file does not exist, a new copy will be downloaded.

	:param str database_file: The GeoLite2 database file to use.
	:return: The initialized GeoLite2 database object.
	:rtype: :py:class:`geoip2.database.Reader`
	"""
	# pylint: disable=global-statement
	global _geoip_db
	if not os.path.isfile(database_file):
		db_path = find.data_file('GeoLite2-City.mmdb')
		if db_path is None:
			raise errors.KingPhisherResourceError('the default geoip database file is unavailable')
		logger.info('initializing the default geoip database')
		shutil.copyfile(db_path, database_file)
	try:
		_geoip_db = geoip2.database.Reader(database_file)
	except maxminddb.errors.InvalidDatabaseError:
		logger.warning('the geoip database file is invalid, downloading a new one')
		download_geolite2_city_db(database_file)
		_geoip_db = geoip2.database.Reader(database_file)
	metadata = _geoip_db.metadata()
	if not metadata.database_type == 'GeoLite2-City':
		raise ValueError('the connected database is not a GeoLite2-City database')
	build_date = datetime.datetime.fromtimestamp(metadata.build_epoch)
	if build_date < datetime.datetime.utcnow() - datetime.timedelta(days=90):
		logger.warning('the geoip database is older than 90 days')
	return _geoip_db

def lookup(ip, lang='en'):
	"""
	Lookup the geo location information for the specified IP from the configured
	GeoLite2 City database.

	:param str ip: The IP address to look up the information for.
	:param str lang: The language to prefer for regional names.
	:return: The geo location information as a dict. The keys are the values of
		:py:data:`.DB_RESULT_FIELDS`.
	:rtype: dict
	"""
	if not _geoip_db:
		raise RuntimeError('the geoip database has not been initialized yet')
	lang = (lang or 'en')
	if isinstance(ip, str):
		ip = ipaddress.ip_address(ip)
	if isinstance(ip, ipaddress.IPv6Address):
		raise TypeError('ipv6 addresses are not supported at this time')
	if ip.is_loopback or ip.is_private:
		raise RuntimeError('the specified IP address is not a public IP address')
	with _geoip_db_lock:
		city = _geoip_db.city(str(ip))
	result = {}
	result['city'] = city.city.names.get(lang)
	result['continent'] = city.continent.names.get(lang)
	result['coordinates'] = Coordinates(latitude=city.location.latitude, longitude=city.location.longitude)
	result['country'] = city.country.names.get(lang)
	result['postal_code'] = city.postal.code
	result['time_zone'] = city.location.time_zone
	return result

class GeoLocation(object):
	"""
	The geographic location information for a given IP address. If *result* is
	not specified, :py:func:`.lookup` will be used to obtain the information.
	"""
	__slots__ = ('city', 'continent', 'coordinates', 'country', 'ip_address', 'postal_code', 'time_zone')
	def __init__(self, ip, lang='en', result=None):
		"""
		:param str ip: The IP address to look up geographic location data for.
		:param str lang: The language to prefer for regional names.
		:param dict result: A raw query result from a previous call to :py:func:`.lookup`.
		"""
		if isinstance(ip, str):
			ip = ipaddress.ip_address(ip)
		if not result:
			result = lookup(ip, lang=lang)
		self.ip_address = ip
		"""The :py:class:`~ipaddress.IPv4Address` which this geographic location data describes."""
		for field in DB_RESULT_FIELDS:
			if field not in result:
				raise RuntimeError('the retrieved information is missing required data field: ' + field)
			if field in ('coordinates',):
				continue
			setattr(self, field, result[field])
		self.coordinates = Coordinates(latitude=result['coordinates'][0], longitude=result['coordinates'][1])

	@property
	def __geo_interface__(self):
		"""
		A simple implementation of the Python
		`__geo_interface__ <https://gist.github.com/sgillies/2217756>`_
		specification. This allows this object to be used with modules which
		also support this interface such as :py:mod:`geojson`.

		:return: A dictionary describing a this location as a GeoJSON Point.
		:rtype: dict
		"""
		return {'type': 'Point', 'coordinates': (self.coordinates.longitude, self.coordinates.latitude)}

	def __repr__(self):
		return "<{0} ip={1} >".format(self.__class__.__name__, self.ip_address)

	def __str__(self):
		country = _normalize_encoding(self.country)
		if self.city:
			return "{0}, {1}".format(_normalize_encoding(self.city), country)
		return country or ''

	@classmethod
	def from_graphql(cls, ip, result, lang='en'):
		# update these camel case fields from GQL
		result['postal_code'] = result.pop('postalCode')
		result['time_zone'] = result.pop('timeZone')
		return cls(ip, lang=lang, result=result)
