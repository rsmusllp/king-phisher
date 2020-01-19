:mod:`geoip`
============

.. module:: king_phisher.geoip
   :synopsis:

This module uses GeoLite2 data created by MaxMind, available from
`http://www.maxmind.com <http://www.maxmind.com>`_.

Data
----

.. autodata:: DB_RESULT_FIELDS
   :annotation:

Functions
---------

.. autofunction:: download_geolite2_city_db

.. autofunction:: init_database

.. autofunction:: lookup

Classes
-------

.. autoclass:: Coordinates
   :members:

.. autoclass:: GeoLocation
   :members:
   :special-members: __init__, __geo_interface__
   :undoc-members:
