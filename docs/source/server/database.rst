Database
========

.. _db-table-relationships-label:

Table Relationships
-------------------

The following diagram outlines the relationships of the various tables in the
database. Nodes are connected by foreign key constraints. The arrow head
references the object which has the constraint.

.. graphviz:: database_relationships.dot

Schema Versioning
-----------------

The King Phisher database uses an internal version number defined as
:py:data:`~king_phisher.server.database.models.SCHEMA_VERSION` which is used by
the initialization code to determine whether or not the stored database schema
(the one existing in the database) matches the running schema (the one defined
in the source code). When the schemas are not the same, the database is
considered to be incompatible. The King Phisher process will then attempt to
upgrade the stored database schema.


If the stored database schema is newer than the running schema, the King Phisher
process can not downgrade it. This would happen for example if a developer were
to use version control to revert the project code to an older version. In this
case the older version would have no knowledge of the newer schema and would
therefor be unable to "downgrade" it to a compatible version. In this case the
developer must use the included database schema migration utilities to update
the stored database schema to a compatible version before checkout out the older
project revision.

Alembic
~~~~~~~

King Phisher uses `Alembic`_ to manage it's database schema versions. This can
be used to explicitly upgrade and downgrade the schema version from the command
line. The Alembic environment files are stored with the server data files at
``data/server/king_phisher/alembic``.

The King Phisher version of the Alembic ``env`` file is modified to support two
ways for the database connection string to be passed from the command line. This
removes the need to store the credentials the ``alembic.ini`` file. The two
supported options are "config" and "database". Both are supplied as settings to
the ``-x`` option in the form ``-x SETTING=VALUE`` with no spaces between the
settings and their values.

config
  The ``config=`` option takes a path to the King Phisher server configuration
  file where the database connection string will be used.

database
  The ``database=`` option takes an explicit database connection string on the
  command line. The syntax is the same as how it would be stored in the server
  configuration file.

Example running Alembic's ``current`` subcommand with the database connection
string taken from the server's configuration file.

.. code-block:: shell

   alembic -x config=../../../server_config.yml current

Schema Version Identifiers
^^^^^^^^^^^^^^^^^^^^^^^^^^

Alembic and King Phisher must keep separate version identifiers. This is because
Alembic uses revision strings in it's internal, linked format while King Phisher
uses simple numeric versioning to easily identify newer schemas. When creating
a new Alembic migration file, it's important to set the King Phisher schema
version as well which must be explicitly done by the developer. The King Phisher
stored database schema version exists in the ``storage_data`` in the
``metadata`` namespace with the key ``schema_version``. See
:py:func:`~king_phisher.server.database.manager.set_metadata` for a convenient
way to set this value. The Alembic revision identifier is stored as a single
record in the ``alembic_version`` table under the ``version_num`` column.

.. _Alembic: http://alembic.zzzcomputing.com/en/latest/
