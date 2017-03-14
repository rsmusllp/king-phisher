Style Guide
===========

It's important for a project to have a standardized style for it's code. The
King Phisher project, being a Python project follows the PEP-8_ style guide.
With the following notable exceptions:

* Do use hard tabs instead of spaces
* Do not use more than one consecutive blank line
* Do limit lines to 120 characters long instead of 79

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

.. _PEP-8: https://www.python.org/dev/peps/pep-0008/
