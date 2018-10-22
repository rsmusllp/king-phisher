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
  through it's user interface. Once the campaign user is done adjusting the
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

4. The client opens a websocket connection through the RPC tunnel to subscribe
   to and receive events published by the server in real time.

At this point the client is fully connected to the server.
