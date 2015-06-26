:mod:`geoip`
============

.. module:: geoip
   :synopsis:

This module uses GeoLite2 data created by MaxMind, available from
`http://www.maxmind.com <http://www.maxmind.com>`_.

Data
----

.. autodata:: king_phisher.geoip.DB_DOWNLOAD_URL
   :annotation:

.. autodata:: king_phisher.geoip.DB_RESULT_FIELDS
   :annotation:

Functions
---------

.. autofunction:: king_phisher.geoip.download_geolite2_city_db

.. autofunction:: king_phisher.geoip.init_database

.. autofunction:: king_phisher.geoip.lookup

Classes
-------

.. autoclass:: king_phisher.geoip.Coordinates
   :members:

.. autoclass:: king_phisher.geoip.GeoLocation
   :members:
   :special-members: __init__, __geo_interface__
   :undoc-members:
