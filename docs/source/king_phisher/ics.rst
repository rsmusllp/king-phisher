:mod:`ics`
==========

.. module:: ics
   :synopsis:

This module provides functionality for creating :rfc:`5545` compliant iCalendar
invite files.

Data
----

.. autodata:: king_phisher.ics.DAY_ABBREVIATIONS
   :annotation:

.. autodata:: king_phisher.ics.zoneinfo_path
   :annotation:

Functions
---------

.. autofunction:: king_phisher.ics.get_timedelta_for_offset

.. autofunction:: king_phisher.ics.get_tz_posix_env_var(tz_name)

.. autofunction:: king_phisher.ics.parse_tz_posix_env_var(posix_env_var)

Classes
-------

.. autoclass:: king_phisher.ics.Calendar
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoclass:: king_phisher.ics.DurationAllDay
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoclass:: king_phisher.ics.Timezone
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoclass:: king_phisher.ics.TimezoneOffsetDetails
   :members:
   :show-inheritance:
   :special-members: __init__
