Example Queries
===============

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

This query returns a summary of all of the campaigns, including basic
information such has when it was created, who by and the number of messages
sent and visits received.

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

This query demonstrates how whitespace is not necessary in GraphQL and the
entire query can be on a single line.

.. code-block:: none

   # This query does not define the operation type or an operation name
   # and is condensed to a single line
   { plugins { total edges { node { name title authors } } } }

Queries With Variables
----------------------

The following two queries show how variables and arguments can be used in
GraphQL.

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

Database Connections
--------------------

This query uses the ``filter`` and ``sort`` arguments to process the queried
data. See :ref:`graphql-db-connection-args-label` for more details.

.. code-block:: none

   query getFilteredCampaigns {
      db {
         campaigns(
            # define a filter for the campaigns
            filter: {
               # the following conditions must be met
               and: [
                  # created on or after January 1st, 2017 (created GE "2017-01-01")
                  {field: "created", operator: GE, value: "2017-01-01"},
                  # and with either...
                  {
                     or: [
                        # no expiration set (expiration EQ Null)
                        {field: "expiration"},
                        # or expiring before April 1st, 2018 (expiration LT "2018-04-01")
                        {field: "expiration", operator: LT, value: "2018-04-01"}
                     ]
                  }
               ]
            },
            # sort the campaigns by the created timestamp
            sort: [{field: "created", direction: AESC}]
         ) {
            total
            edges {
               node {
                  id
                  name
                  # count the number of messages that were opened (opened NE Null)
                  messages(filter: {field: "opened", operator: NE}) {
                     total
                  }
               }
            }
         }
      }
   }
