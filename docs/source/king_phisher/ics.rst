:mod:`ics`
==========

.. module:: king_phisher.ics
   :synopsis:

This module provides functionality for creating :rfc:`5545` compliant iCalendar
invite files.

Data
----

.. autodata:: DAY_ABBREVIATIONS
   :annotation:

.. autodata:: zoneinfo_path
   :annotation:

Functions
---------

.. autofunction:: get_timedelta_for_offset

.. autofunction:: get_tz_posix_env_var(tz_name)

.. autofunction:: parse_tz_posix_env_var(posix_env_var)

Classes
-------

.. autoclass:: Calendar
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoclass:: DurationAllDay
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoclass:: Timezone
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoclass:: TimezoneOffsetDetails
   :members:
   :show-inheritance:
   :special-members: __init__
