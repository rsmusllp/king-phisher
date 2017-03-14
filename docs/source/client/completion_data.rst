.. _completion-data:

Completion Data
===============

Some classes provided by the
:py:mod:`widget.completion_providers` module require large amounts of data to
function. This data is stored encoded in JSON to be loaded when these classes
are initialized. The formats of the data are specific to each completion
provider depending on the needs of their target syntax.

.. _completion-data-html:

HTML
----

The HTML data file is a dictionary whose keys are HTML 5 tags such as body,
input and script. Each of these keys values is either None if the tag does not
have any attributes or a list of the valid attribute names. Each of the defined
attributes are assumed to require a value, however ones which do not are
suffixed with ``!``. This suffix is used by the completion provider to determine
if the opening definition for an attribute (``="``) should be appended to the
token or not.

Example data containing completion information for the html and input tags:

.. code-block:: javascript

   {
     "html": null,
     "input": [
       "disabled!",
       "type"
      ]
   }

.. _completion-data-jinja:

Jinja
-----

The Jinja data file is a dictionary containing two sub keys of ``global`` and
``context`` for global, and context specific data respectively. The global key's
value is a dictionary containing three subkeys of ``filters``, ``tests`` and
``tokens`` for the different kinds of Jinja terms which should be auto
completed. The filters and tests keys have values of lists including all of the
defined Jinja filters and tests respectively.

The tokens key has a value of a dictionary which contains the tokens broken out
into a hierarchy of objects and attributes. Attributes which have
sub-attributes are represented as dictionaries while attributes which have no
attributes and are thus leaves have values of None. In the context of
completion, variables and functions are treated as tokens because neither one
are dependant on presence of a setup statement which is the case with filters
and tests.

Tokens, filters and tests which are callable and require at least one argument
to be specified are all suffixed with ``(``. This suffix is used by the
completion provider to signify that arguments are expected.

The top-level context key contains subkeys that define additional data to be
merged with the global filters, tests and tokens based on a defined context.
This allows the global Jinja environment data to be added to context specific
providers.

Example data containing global filters, tests and tokens along with a truncated
"email" context.

.. code-block:: javascript

   {
     "context": {
       "email": {
         "tokens": {
           ...
         }
       }
     },
     "global": {
       "filters": [
         "replace(",
         "title"
       ],
       "tests": [
         "defined",
         "equalto("
       ],
       "tokens": {
         "range(": null,
         "time": {
           "local": null,
           "utc": null
         },
         "version": null
       }
     }
   }
