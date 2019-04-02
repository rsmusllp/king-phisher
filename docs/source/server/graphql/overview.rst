.. _graphql-label:

Overview
========

The RPC API provides a function for executing GraphQL_ queries against the
server. The schema the server supports allows accessing the database models
through the ``db`` type as well as some additional information such as the
server plugins.

.. note::
   For consistencies within the GraphQL API and with GraphQL best practices, it
   is important to note that names are ``camelCase`` and not ``snake_case``.

Interface Extensions
--------------------

The GraphQL schema supported by King Phisher implements the Relay_ connection
interface allowing easier pagination using a cursor. As an extension to this
interface, the King Phisher schema also includes a ``total`` attribute to the
connection object. This attribute allows a query to access the number of
nodes available for a specific connection.

Schema
------

The following table represents the top-level objects available in the GraphQL
schema and their various sub-object types as applicable. For more information,
see the :ref:`graphql-schema-label` documentation.

+--------------------------+-------------------------+-------------------------------------------------------------+
| Object Name              | Object Type             | Description                                                 |
+==========================+=========================+=============================================================+
| ``db``                   | Object                  | Database models. See :ref:`db-table-relationships-label`    |
|                          |                         | for information on available sub-objects.                   |
+--------------------------+-------------------------+-------------------------------------------------------------+
| :gql:fld:`geoloc`        | :gql:obj:`GeoLocation`  | Geolocation information.                                    |
+--------------------------+-------------------------+-------------------------------------------------------------+
| :gql:fld:`hostnames`     | [String]                | The hostnames that are configured for use with this server. |
+--------------------------+-------------------------+-------------------------------------------------------------+
| :gql:fld:`plugin`        | :gql:obj:`Plugin`       | Specific information for a loaded plugin.                   |
+--------------------------+-------------------------+-------------------------------------------------------------+
| :gql:fld:`plugins`       | Connection              | Information on all loaded plugins.                          |
+--------------------------+-------------------------+-------------------------------------------------------------+
| :gql:fld:`siteTemplate`  | :gql:obj:`SiteTemplate` | Information for an available site template.                 |
+--------------------------+-------------------------+-------------------------------------------------------------+
| :gql:fld:`siteTemplates` | Connection              | Information on all available site templates.                |
+--------------------------+-------------------------+-------------------------------------------------------------+
| :gql:fld:`ssl`           | :gql:obj:`SSL`          | Information regarding the SSL configuration and status.     |
+--------------------------+-------------------------+-------------------------------------------------------------+
| :gql:fld:`version`       | String                  | The :py:data:`~king_phisher.version.version` of the King    |
|                          |                         | Phisher server.                                             |
+--------------------------+-------------------------+-------------------------------------------------------------+

:Connection:
  A connection sub-object is a special object providing a defined interface used
  to refer to an array of objects. The connection sub-object has a ``total``
  attribute which is an integer as well as an ``edges`` attribute. See
  `Connection Types`_ for more information.

:Object:
  Objects can in turn have their own attributes which can be a combination
  of additional sub-objects or scalars.


Additional Database Model Attributes
------------------------------------

Database objects which have an IP address string attribute associated with
their model have an additional attribute containing the corresponding geo
location information. This geo location attribute uses the same naming prefix,
for example the geo location information for a ``ip`` attribute can be accessed
from the ``ipGeoloc`` attribute.

.. _graphql-db-connection-args-label:

Additional Database Connection Arguments
----------------------------------------

Database connections can include additional arguments which allow manipulation
of the queried data.

The filter Argument
~~~~~~~~~~~~~~~~~~~

The ``filter`` argument is a ``FilterInput`` GraphQL object and can be passed
to database connection to filter what data is returned by the query. This
argument is an object containing one or more of the following key words.

+----------------+--------------------+----------+------------------------------------------------+
| Keyword        | Type               | Default  | Description                                    |
+================+====================+==========+================================================+
| and :sup:`1`   | List               | N/A      | A list of additional filter objects, where all |
|                |                    |          | must evaluate to true.                         |
+----------------+--------------------+----------+------------------------------------------------+
| or :sup:`1`    | List               | N/A      | A list of additional filter objects, where one |
|                |                    |          | or more must evaluate to true.                 |
+----------------+--------------------+----------+------------------------------------------------+
| field :sup:`1` | String             | N/A      | The name of a database field to filter by.     |
+----------------+--------------------+----------+------------------------------------------------+
| operator       | FilterOperatorEnum | ``EQ``   | The operator to use with value, one of ``EQ``, |
|                |                    |          | ``GE``, ``GT``, ``LE``, ``LT``, or ``NE``.     |
+----------------+--------------------+----------+------------------------------------------------+
| value          | AnyScalar          | ``Null`` | The value of the field to use with the         |
|                |                    | :sup:`2` | specified comparison operator.                 |
+----------------+--------------------+----------+------------------------------------------------+

:sup:`1` Exactly one of these keywords must be specified.

:sup:`2` ``null`` can not be passed as a literal for input. To compare a value to
``null``, the ``value`` keyword must be omitted.

The sort Argument
~~~~~~~~~~~~~~~~~

The ``sort`` argument is a list of ``SortInput`` GraphQL objects (described
below) which can be passed to a database connection to sort the query data by
one or more fields.

+-----------+-------------------+----------+--------------------------------------------------+
| Keyword   | Type              | Default  | Description                                      |
+===========+===================+==========+==================================================+
| field*    | String            | N/A      | The name of a database field to sort by.         |
+-----------+-------------------+----------+--------------------------------------------------+
| direction | SortDirectionEnum | ``AESC`` | The direction in which to sort the data, either  |
|           |                   |          | ``AESC`` or ``DESC``.                            |
+-----------+-------------------+----------+--------------------------------------------------+

\* This keyword must be specified.

Executing Raw Queries
---------------------

Raw GraphQL queries can be executed using the ``tools/database_console.py``
utility. This console provides a ``graphql_query`` function which takes a query
string parameter and optional query variables. This can be used for easily
testing queries. It should be noted however that using this utility directly on
the server does not restrict access to data as the RPC interface does.

The client's RPC terminal (only available on Linux due to the dependency on VTE)
can also be used to easily execute raw GraphQL queries. The RPC method can be
called directly, or when IPython is available, either the ``%graphql`` or
``%graphql_file`` commands can be used. The former of which takes a GraphQL
query as an argument, while the second takes the path to a file on disk to
execute. Both of these are useful for debugging and inspecting GraphQL queries
and their resulting data structures.

.. _Connection Types: https://facebook.github.io/relay/graphql/connections.htm#sec-Connection-Types
.. _GraphQL: http://graphql.org/
.. _Relay: https://facebook.github.io/relay/graphql/connections.htm
