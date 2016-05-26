:mod:`sms`
==========

.. module:: sms
   :synopsis:

This module provides functionality for sending free SMS messages by emailing a
carriers SMS gateway.

Data
----

.. autodata:: king_phisher.sms.CARRIERS
   :annotation:

.. autodata:: king_phisher.sms.DEFAULT_FROM_ADDRESS
   :annotation:

Functions
---------

.. autofunction:: king_phisher.sms.get_smtp_servers(domain)

.. autofunction:: king_phisher.sms.lookup_carrier_gateway

.. autofunction:: king_phisher.sms.send_sms
