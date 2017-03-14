.. _server-published-events-label:

Published Events
================

Overview
--------

Certain signals used by the server can be forwarded to clients via event
subscriptions. In order to take advantage of this functionality the client
opens a web socket to the server, and configures it's subscriptions using
the available :ref:`rpc-api-event-api-label` functions. When a server signal is
emitted the corresponding information is then forwarded to the subscribed
clients over their open websocket.

.. _server-published-events-database-label:

Database Events
---------------

Database events can be subscribed to using the *event_id* of ``db-TABLE_NAME``.
Each of these events have the following sub-event types for each of the
database operations.

 * ``deleted``
 * ``inserted``
 * ``updated``

These events are emitted by the respective ``db_session_*``
:ref:`server-signals-database-label`. These signals are converted to events and
organized by table (e.g. messages) instead of operation (e.g. inserted) because
events are configured to send specific attributes. Not all attributes are
available on all tables, however for one table the available attributes will
always be available for all operations.
