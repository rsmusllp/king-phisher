.. _rpc-api-label:

RPC API
=======

Overview
--------

The RPC API is used by the King Phisher client to communicate with the server.
It uses the RPC capabilities provided by the :py:mod:`AdvancedHTTPServer` module
for the underlying communications. The RPC API provides a way for the client to
retrieve and set information regarding campaigns as well as the server's
configuration. RPC requests must be authenticated and are only permitted from
the loopback interface. The client is responsible for using SSH to set up a port
forward for requests. See the :ref:`Login Process <login-process>` documentation
for more information.

RPC API Versioning
------------------

It's important for the client and server components to have a compatible RPC
version. The version each understands is described in the
:py:data:`~king_phisher.version.rpc_api_version` object. This object contains
both a major and minor version identifier. The major version is incremented when
backwards-incompatible changes are made such as an argument or method is
removed. The minor version is incremented when backwards-compatible changes are
made such as when a new method is added or when a keyword argument is added
whose default value maintains the original behavior.

In this way, it is possible for the server to support a newer RPC version than
the client. This would be the case when the server is newer and provides more
functionality than the older client requires. It is not possible for the client
to support a newer RPC version than the server. This would imply that the client
requires functionality that the server is unable to provide.

Since version :release:`1.10.0`, the GraphQL API loosens the interdependency
between the RPC API version and the database's
:ref:`schema version <schema-versioning>`. Since GraphQL allows the client to
specify only the fields it requires, new fields can be added to the database
without incrementing the major RPC API version. **It is still important to
increment the minor RPC API version** so the client knows that those fields are
available to be requested through the :rpc:func:`graphql` endpoint. If database
fields are removed, columns are renamed, columns types are changed, or columns
have additional restrictions placed on them (such as being nullable), the major
RPC API version must be incremented.

The Table Fetch API
^^^^^^^^^^^^^^^^^^^

The RPC functions responsible for fetching table data through the ``db/table/*``
API endpoints (:rpc:func:`db/table/get` and :rpc:func:`db/table/view`) use a
hard coded data set located in ``data/server/king_phisher/table-api.json`` to
maintain backwards compatibility. This is required since the RPC client can not
specify the columns and order of the columns that it is requesting as it can do
with the :rpc:func:`graphql` API endpoint. This data set effectively allows the
table fetch RPC API endpoints to be artificially  pinned to a specific database
schema version. The other table API endpoints do not need to be pinned in such a
fashion due to them taking the columns to work with as parameters. This means
that an older but still compatible client (same major version but a lesser minor
version as the server) would not be specifying columns which do not exist since
renaming and removing columns require incrementing the major RPC API version.

.. _rpc-api-general-api-label:

General API
-----------

.. rpc:function:: graphql(query, query_vars=None)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_graphql`

.. rpc:function:: login()

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_login`

.. rpc:function:: logout()

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_logout`

.. rpc:function:: ping()

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_ping`

.. rpc:function:: plugins/list()

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_plugins_list`

.. rpc:function:: shutdown()

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_shutdown`

.. rpc:function:: version()

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_version`

.. _rpc-api-campaign-api-label:

Campaign API
------------

.. rpc:function:: campaign/alerts/is_subscribed(campaign_id)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_campaign_alerts_is_subscribed`

.. rpc:function:: campaign/alerts/subscribe(campaign_id)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_campaign_alerts_subscribe`

.. rpc:function:: campaign/alerts/unsubscribe(campaign_id)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_campaign_alerts_unsubscribe`

.. rpc:function:: campaign/landing_page/new(campaign_id, hostname, page)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_campaign_landing_page_new`

.. rpc:function:: campaign/message/new(campaign_id, email_id, email_target, company_name, first_name, last_name)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_campaign_message_new`

.. rpc:function:: campaign/new(name, description=None)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_campaign_new`

.. rpc:function:: campaign/stats(campaign_id)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_campaign_stats`

.. _rpc-api-configuration-api-label:

Configuration API
-----------------

.. rpc:function:: config/get(option_name)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_config_get`

.. rpc:function:: config/set(options)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_config_set`

.. _rpc-api-event-api-label:

Event API
---------

.. rpc:function:: events/is_subscribed(event_id, event_type)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_events_is_subscribed`

.. rpc:function:: events/subscribe(event_id, event_types, attributes)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_events_subscribe`

.. rpc:function:: events/unsubscribe(event_id, event_types, attributes)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_events_unsubscribe`

.. _rpc-api-geoip-api-label:

GeoIP API
---------

.. rpc:function:: geoip/lookup(ip, lang=None)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_geoip_lookup`

.. rpc:function:: geoip/lookup/multi(ips, lang=None)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_geoip_lookup_multi`

.. _rpc-api-hostnames-api-label:

Hostnames API
-------------

.. rpc:function:: hostnames/add(hostname)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_hostnames_add`

   .. versionadded:: 1.13.0

.. rpc:function:: hostnames/get()

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_hostnames_get`

   .. versionadded:: 1.13.0

.. _rpc-api-table-api-label:

Table API
---------

.. rpc:function:: db/table/count(table_name, query_filter=None)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_database_count_rows`

.. rpc:function:: db/table/delete(table_name, row_id)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_database_delete_row_by_id`

.. rpc:function:: db/table/delete/multi(table_name, row_ids)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_database_delete_rows_by_id`

.. rpc:function:: db/table/get(table_name, row_id)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_database_get_row_by_id`

.. rpc:function:: db/table/insert(table_name, keys, values)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_database_insert_row`

.. rpc:function:: db/table/set(table_name, row_id, keys, values)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_database_set_row_value`

.. rpc:function:: db/table/view(table_name, page=0, query_filter=None)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_database_view_rows`
