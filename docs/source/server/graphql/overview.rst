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

The ``filter`` argument can be passed to database connection to filter what
data is returned by the query. This argument is an object containing one or
more of the following key words.

+----------+--------+-------------+------------------------------------------------+
| Keyword  | Type   | Default     | Description                                    |
+==========+========+=============+================================================+
| and*     | List   | N/A         | A list of additional filter objects, where all |
|          |        |             | must evaluate to true.                         |
+----------+--------+-------------+------------------------------------------------+
| or*      | List   | N/A         | A list of additional filter objects, where one |
|          |        |             | or more must evaluate to true.                 |
+----------+--------+-------------+------------------------------------------------+
| field*   | String | N/A         | The name of a database field to filter by.     |
+----------+--------+-------------+------------------------------------------------+
| operator | Enum   | ``EQ``      | The operator to use with value, one of ``EQ``, |
|          |        |             | ``GE``, ``GT``, ``LE``, ``LT``, ``NE``.        |
+----------+--------+-------------+------------------------------------------------+
| value    | N/A    | ``Null`` ** | The value of the field to use with the         |
|          |        |             | specified comparison operator.                 |
+----------+--------+-------------+------------------------------------------------+

\* Exactly one of these keywords must be specified.

\** ``Null`` can not be passed as a literal for input. To compare a value to
``Null``, the ``value`` keyword must be omitted.

The sort Argument
~~~~~~~~~~~~~~~~~

The ``sort`` argument is a list of objects (described below) which can be
passed to database connection to sort the query data by one or more fields.

+-----------+--------+----------+--------------------------------------------------+
| Keyword   | Type   | Default  | Description                                      |
+===========+========+==========+==================================================+
| field*    | String | N/A      | The name of a database field to sort by.         |
+-----------+--------+----------+--------------------------------------------------+
| direction | Enum   | ``AESC`` | The direction in which to sort the data, one of  |
|           |        |          | ``AESC``, ``DESC``.                              |
+-----------+--------+----------+--------------------------------------------------+

\* This keyword must be specified.

Executing Raw Queries
---------------------

Raw GraphQL queries can be executed using the ``tools/database_console.py``
utility. This console provides a ``graphql_query`` function which takes a query
string parameter and optional query variables. This can be used for easily
testing queries. It should be noted however that using this utility directly on
the server does not restrict access to data as the RPC interface does.

.. _GraphQL: http://graphql.org/
.. _Relay: https://facebook.github.io/relay/graphql/connections.htm
