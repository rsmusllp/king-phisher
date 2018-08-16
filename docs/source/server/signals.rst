.. py:currentmodule:: king_phisher.server.signals
.. _server-signals-label:

Server Signals
==============

Overview
--------

Server signals are used by the server to dispatch events to subscribed handlers.
This allows plugins to subscribe specific functions to be executed when a
particular event occurs. These signals are defined in the
:py:mod:`~server.signals` module.


.. _server-signals-campaign-label:

Campaign Signals
----------------

.. autodata:: campaign_alert
   :annotation:
   :noindex:

.. autodata:: campaign_expired
   :annotation:
   :noindex:

.. _server-signals-database-label:

Database Signals
----------------

.. autodata:: db_initialized
   :annotation:
   :noindex:

.. autodata:: db_session_deleted
   :annotation:
   :noindex:

.. autodata:: db_session_inserted
   :annotation:
   :noindex:

.. autodata:: db_session_updated
   :annotation:
   :noindex:

.. autodata:: db_table_delete
   :annotation:
   :noindex:

.. autodata:: db_table_insert
   :annotation:
   :noindex:

.. autodata:: db_table_update
   :annotation:
   :noindex:

.. _server-signals-request-handler-label:

Request Handler Signals
-----------------------

Signals which are emitted for events specific to individual HTTP requests. These
signals use the respective instance of
:py:class:`~king_phisher.server.server.KingPhisherRequestHandler` as the sender.

.. autodata:: credentials_received
   :annotation:
   :noindex:

.. autodata:: email_opened
   :annotation:
   :noindex:

.. autodata:: request_handle
   :annotation:
   :noindex:

.. autodata:: request_received
   :annotation:
   :noindex:

.. autodata:: response_sent
   :annotation:
   :noindex:

.. autodata:: rpc_method_call
   :annotation:
   :noindex:

.. autodata:: rpc_method_called
   :annotation:
   :noindex:

.. autodata:: rpc_user_logged_in
   :annotation:
   :noindex:

.. autodata:: rpc_user_logged_out
   :annotation:
   :noindex:

.. autodata:: visit_received
   :annotation:
   :noindex:

.. _server-signals-server-label:

Server Signals
--------------

Signals which are emitted for a
:py:class:`~king_phisher.server.server.KingPhisherServer` instance.

.. autodata:: server_initialized
   :annotation:
   :noindex:
