:mod:`ipaddress`
================

.. module:: ipaddress
   :synopsis:

This module provides functionality for dealing with an external "ipaddress"
module in a Python 2 backwards compatible way. In Python 2 all string address
arguments are converted to unicode which removes the ability to specify
addresses as packed binary strings.

Functions
---------

.. autofunction:: king_phisher.ipaddress.ip_address

.. autofunction:: king_phisher.ipaddress.ip_network

.. autofunction:: king_phisher.ipaddress.ip_interface

.. autofunction:: king_phisher.ipaddress.is_loopback

.. autofunction:: king_phisher.ipaddress.is_valid

Classes
-------

.. autoclass:: king_phisher.ipaddress.IPv4Address
   :members:

.. autoclass:: king_phisher.ipaddress.IPv4Network
   :members:

.. autoclass:: king_phisher.ipaddress.IPv6Address
   :members:

.. autoclass:: king_phisher.ipaddress.IPv6Network
   :members:
