.. _architecture-overview:

Architecture Overview
=====================

The following diagram outlines the generic architecture of how the major
components both contained in and used by King Phisher interact.

.. graphviz:: architecture.dot

In the diagram above, all major components (shown in oval shapes) can
technically coexist on the same host system. In this case the term "host" refers
to a single OS installation whether that be a Virtual Machine or not. It is
however recommended to at a minimum install the King Phisher client and server
components on separate hosts for production deployments.

The King Phisher project consists of the client and server components. The major
responsibilities of each are noted as follows:

Client Responsibilities
-----------------------

- **Creating Campaigns** -- The client facilitates creating new campaigns
  through its user interface. Once the campaign user is done adjusting the
  settings for the new campaign, the client uses RPC to transfer the information
  to the King Phisher server.

- **Sending Email** -- The client is responsible for editing, rendering and
  ultimately sending phishing messages through an external SMTP server. Once a
  message is sent, the client notifies the King Phisher server via an RPC call
  with the applicable details such as who the message was sent to.

- **Processing Campaign Data** -- Once data has been collected on the King
  Phisher server for a particular campaign, the client retrieves it using
  GraphQL queries over RPC. Once the data has been transferred it is displayed
  through the user interface.

Server Responsibilities
-----------------------

- **Handling HTTP(S) Requests** -- The server handles all HTTP and HTTPS
  requests either from phishing targets or the King Phisher client (which uses
  a form of RPC over HTTP).

- **Tracking Campaigns** -- The server tracks the status of campaigns through
  the configured database backend. This allows the King Phisher client to
  disconnect and shutdown once it is done making changes.

- **Dispatching Campaign Notifications** -- While tracking campaign data, the
  server publishes event notifications to various pieces of subscriber code.
  Plugins utilizes this model to subscribe to events and execute arbitrary
  routines (such as sending alerts to end users) when they are received. The
  King Phisher client can also subscribe to a subset of events which are
  forwarded over websockets.

.. _login-process:

Login Process
-------------

The following steps outline the procedure taken by the client to open a
a connection to, and authenticate with the server for communication.

1. The client communicates to the server through an SSH tunnel which it
   establishes first. This requires the client to authenticate to the host on
   which the server is running.

2. The client issues an RPC request through the established SSH tunnel to the
   :rpc:func:`version` endpoint to determine compatibility.

3. The client issues an additional RPC request through the established SSH
   tunnel, this time to the :rpc:func:`login` endpoint to authenticate and
   create a new session.

4. The client opens a websocket connection through the SSH tunnel to subscribe
   to and receive events published by the server in real time.

At this point the client is fully connected to the server.

Signal Architecture
-------------------

Both the client and server utilize and provide functionality for signal-driven
callbacks. The two use different backends, but in both cases, there is a core
interface through which King Phisher signals are published to registered
callback functions as events. The signal subsystem is particularly useful for
plugins to modify system behavior.

Client Signals
^^^^^^^^^^^^^^

Due to the nature of the client application using GTK, the GObject Signal
functionality is used to provide the core of client events. These events are
defined in the :ref:`gobject-signals-label` documentation. These signals are
published by particular object instances, with the most notable being the
:py:class:`~king_phisher.client.application.KingPhisherClientApplication`.

Server Signals
^^^^^^^^^^^^^^

The server utilizes the :py:mod:`blinker` module to support application events.
This interface is defined and documented in :ref:`_server-signals-label`
documentation. Server signals are centrally located within the
:py:mod:`~king_phisher.server.signals` module from which that can be both
connected to and emitted.

Signal Forwarders
^^^^^^^^^^^^^^^^^

Due to the both the client and server having a centralized signal mechanism,
there are notable components which both forward signals to and from other
components to make the interface consistent.

+------------------+-----------------------------+---------------------------------------------------------------------+
| Name             | Direction                   | Description                                                         |
+==================+=============================+=====================================================================+
| SQLAlchemy       | **From:** SQLAlchemy        | Forwards events from SQLAlchemy into the server's core signal       |
|                  +-----------------------------+ dispatcher. This allows server components to connect to SQLAlchemy  |
|                  | **To:** Server Core         | signals for database events through the central interface.          |
+------------------+-----------------------------+---------------------------------------------------------------------+
| WebSocket Server | **From:** Server Core       | Forwards events from the server's core signal dispatcher to         |
|                  +-----------------------------+ connected and subscribed client web sockets. This effectively       |
|                  | **To:** WebSocket Clients   | enables subscribers to receive a subset of server signals.          |
+------------------+-----------------------------+---------------------------------------------------------------------+
| WebSocket Client | **From:** WebSocket Client  | Forwards events received from the web sockets to the client's core  |
|                  +-----------------------------+ signal dispatcher. This effectively enables client components to    |
|                  | **To:** Client Core         | receive a subset of server signals.                                 |
+------------------+-----------------------------+---------------------------------------------------------------------+

.. graphviz:: signals.dot