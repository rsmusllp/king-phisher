.. _server-signals-label:

Server Signals
==============

Overview
--------

Server signals are used by the server to dispatch events to subscribed handlers.
This allows plugins to subscribe specific functions to be executed when a
particular event occurs. These signals are defined in the
:py:mod:`~server.signals` module.

.. _server-signals-database-label:

Database Signals
----------------

.. autodata:: king_phisher.server.signals.db_initialized
   :annotation:
   :noindex:

.. autodata:: king_phisher.server.signals.db_session_deleted
   :annotation:
   :noindex:

.. autodata:: king_phisher.server.signals.db_session_inserted
   :annotation:
   :noindex:

.. autodata:: king_phisher.server.signals.db_session_updated
   :annotation:
   :noindex:

.. autodata:: king_phisher.server.signals.db_table_delete
   :annotation:
   :noindex:

.. autodata:: king_phisher.server.signals.db_table_insert
   :annotation:
   :noindex:

.. autodata:: king_phisher.server.signals.db_table_update
   :annotation:
   :noindex:

.. _server-signals-request-handler-label:

Request Handler Signals
-----------------------

Signals which are emitted for events specific to individual HTTP requests. These
signals use the respective instance of
:py:class:`~king_phisher.server.server.KingPhisherRequestHandler` as the sender.

.. autodata:: king_phisher.server.signals.credentials_received
   :annotation:
   :noindex:

.. autodata:: king_phisher.server.signals.email_opened
   :annotation:
   :noindex:

.. autodata:: king_phisher.server.signals.request_handle
   :annotation:
   :noindex:

.. autodata:: king_phisher.server.signals.request_received
   :annotation:
   :noindex:

.. autodata:: king_phisher.server.signals.response_sent
   :annotation:
   :noindex:

.. autodata:: king_phisher.server.signals.rpc_method_call
   :annotation:
   :noindex:

.. autodata:: king_phisher.server.signals.rpc_method_called
   :annotation:
   :noindex:

.. autodata:: king_phisher.server.signals.rpc_user_logged_in
   :annotation:
   :noindex:

.. autodata:: king_phisher.server.signals.rpc_user_logged_out
   :annotation:
   :noindex:

.. autodata:: king_phisher.server.signals.visit_received
   :annotation:
   :noindex:

.. _server-signals-server-label:

Server Signals
--------------

Signals which are emitted for a
:py:class:`~king_phisher.server.server.KingPhisherServer` instance.

.. autodata:: king_phisher.server.signals.server_initialized
   :annotation:
   :noindex:
