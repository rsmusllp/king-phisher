:mod:`server.graphql`
=====================

.. module:: server.graphql
   :synopsis:

This module provides the `GraphQL <http://graphql.org/>`_ interface for
querying information from the King Phisher server. This allows flexibility in
how the client would like for the returned data to be formatted. This interface
can be accessed directly by the server or through the RPC end point at
:py:func:`~king_phisher.server.server_rpc.rpc_graphql`.

Classes
-------

.. autoclass:: king_phisher.server.graphql.AuthorizationMiddleware
   :show-inheritance:

.. autoclass:: king_phisher.server.graphql.Query
   :show-inheritance:

.. autoclass:: king_phisher.server.graphql.Schema
   :show-inheritance:
