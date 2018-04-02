Style Guide
===========

It's important for a project to have a standardized style for it's code. The
King Phisher project, being a Python project follows the PEP-8_ style guide
with the following notable exceptions:

* Do use hard tabs instead of spaces.
* Do not use more than one consecutive blank line, ever.
* Do limit lines of code to 120 characters long instead of 79.

   * Do limit documentation lines to 80 characters long.

* Do use single quotes for strings with the exception of template strings (such
  as those used by ``str.format``) and documentation strings which should use
  triple double-quotes.
* Optionally use additional spaces within a line for visual grouping. For
  example, when defining a long list of constants use additional spaces after
  the name and before the value to align all the values on the right.

Multi Line Indentation
----------------------

Use hanging indentation for parenthesized statements. This is to say, the last
non-whitespace character of the line should be the opening parenthesis with
each subsequent line being indented until the closing parenthesis. Furthermore,
in the case that this style is used, each expression should be on a separate
line.

Example:

.. code-block:: python

   # good (standard one-line invocation)
   this_function(takes_two, different_arguments)

   # good (multi-line invocation)
   this_other_function_has_a_longer_name(
       and_also_takes_two,
       different_arguments
   )

   # bad
   this_other_function_has_a_longer_name(and_one_argument_up_here,
       and_another_down_here
   )

This same style is applied to multi-line list, tuple and dictionary
definitions with the bracket, or curly-brace taking the place of the
opening and closing parenthesis as appropriate.

English Verbiage
----------------

Use full, complete and grammatically correct sentences for all documentation
purposes. This includes class, function, attribute, and parameter
documentation. Additionally, proper sentences should be used for any messages
that are displayed to end users with the notable exception of log messages. Log
messages are to be entirely lowercase with the exception of acronyms which are
currently inconsistently cased. Either all capital letters or all lower case
letters are acceptable for acronyms within log messages.

Documenation
------------

When documenting a function, use the grammar provided by Sphinx_. Documentation
strings should be surrounded by triple double quotes (``"""``). There should be
a single blank line between the body of the description and the parameter and
return definitions.

.. code-block:: python

   def add_two_numbers(x, y):
       """
       Add two values specified as *x* and *y* together returning their sum.

       :param int x: The value for the first number to return.
       :param int y: The value for the second number to return.
       :return: The sum of the two values.
       :rtype: int
       """
       return x + y

Native Python types are able to be specified on the ``:param`` line. More
complex types, such instances of classes defined by modules in the project must
be defined on a separate line using a dedicated ``:type`` annotation. See the
Sphinx documentation for the `Python Domain`_.

.. code-block:: rst

   :param foo: The widget this function uses.
   :type foo: :py:class:`~the_full.module_path_to.Foo`

.. _PEP-8: https://www.python.org/dev/peps/pep-0008/
.. _Python Domain: http://www.sphinx-doc.org/en/stable/domains.html#the-python-domain
.. _Sphinx: http://www.sphinx-doc.org/en/stable/domains.html
