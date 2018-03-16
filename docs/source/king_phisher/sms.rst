:mod:`sms`
==========

.. module:: king_phisher.sms
   :synopsis:

This module provides functionality for sending free SMS messages by emailing a
carriers SMS gateway.

Data
----

.. autodata:: CARRIERS
   :annotation:

.. autodata:: DEFAULT_FROM_ADDRESS
   :annotation:

Functions
---------

.. autofunction:: get_smtp_servers(domain)

.. autofunction:: lookup_carrier_gateway

.. autofunction:: send_sms
