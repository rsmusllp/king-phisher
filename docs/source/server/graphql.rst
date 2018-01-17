.. _graphql-label:

GraphQL
=======

Overview
--------

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
for example the geo location information for a ``visitorIp`` attribute can be
accessed from the ``visitorGeoloc`` attribute.

Executing Raw Queries
---------------------

Raw GraphQL queries can be executed using the ``tools/database_console.py``
utility. This console provides a ``graphql_query`` function which takes a query
string parameter and optional query variables. This can be used for easily
testing queries. It should be noted however that using this utility directly on
the server does not restrict access to data as the RPC interface does.

Example Queries
---------------

The following query is an example of retrieving the first 3 users from the
users table. The query includes the necessary information to perform subsequent
queries to iterate over all entries.

.. 'none' has to be used because at this type pygments does not support graphql

.. code-block:: none

   # GraphQL queries can have comments like this
   query getFirstUser {
      # database objects are accessible under the 'db' type
      db {
         # retrieve the first 3 user objects
         users(first: 3) {
            # 'total' is an extension to the standard GraphQL relay interface
            total
            edges {
               # 'cursor' is a string used for iteration
               cursor
               node {
                  # here the desired fields of the user object are specified
                  id
                  phoneNumber
               }
            }
            # request information regarding the chunk of users returned
            pageInfo {
               endCursor
               hasNextPage
            }
         }
      }
   }

.. code-block:: none

   # Get a summary of all of the campaigns
   query getCampaigns {
      db {
         campaigns {
            # get the total number of campaigns
            total
            edges {
               node {
                  id
                  created
                  name
                  # get the details about the user that created this campaign
                  user {
                     id
                     phoneNumber
                  }
                  # get the total number of messages in this campaign
                  messages {
                     total
                  }
                  # get the total number of visits in this campaign
                  visits {
                     total
                  }
               }
            }
         }
      }
   }

.. code-block:: none

   # This query does not define the operation type or an operation name
   # and is condensed to a single line
   { plugins { total edges { node { name title authors } } } }

.. code-block:: none

   # This query is an example of how a single database object can be referenced
   # by its ID (which is always a string in GraphQL)
   query getSpecificCampaign {
      db {
         # Campaign is specified here (instead of campaigns) as well as the ID
         campaign(id: "1") {
            name
            description
         }
      }
   }

.. code-block:: none

   # This query is the same as the previous one, except here the campaign ID
   # is defined as a variable
   query getSpecificCampaign($id: String) {
      db {
         # The variable, defined above is then used here
         campaign(id: $id) {
            name
            description
         }
      }
   }

.. _GraphQL: http://graphql.org/
.. _Relay: https://facebook.github.io/relay/graphql/connections.htm
