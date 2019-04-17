:mod:`gui_utilities`
====================

.. module:: king_phisher.client.gui_utilities
   :synopsis:

This module provides various utility functions specific to the graphical nature
of the client application.

Data
----

.. autodata:: GOBJECT_PROPERTY_MAP
   :annotation:

Functions
---------

.. autofunction:: glib_idle_add_once

.. autofunction:: glib_idle_add_wait

.. autofunction:: glib_idle_add_store_extend

.. autofunction:: gobject_get_value

.. autofunction:: gobject_set_value

.. autofunction:: gobject_signal_accumulator

.. autofunction:: gobject_signal_blocked

.. autofunction:: gtk_calendar_get_pydate

.. autofunction:: gtk_calendar_set_pydate

.. autofunction:: gtk_list_store_search

.. autofunction:: gtk_listbox_populate_labels

.. autofunction:: gtk_menu_get_item_by_label

.. autofunction:: gtk_menu_insert_by_path

.. autofunction:: gtk_menu_position

.. autofunction:: gtk_style_context_get_color

.. autofunction:: gtk_sync

.. autofunction:: gtk_treesortable_sort_func_numeric

.. autofunction:: gtk_treeview_get_column_titles

.. autofunction:: gtk_treeview_selection_to_clipboard

.. autofunction:: gtk_treeview_selection_iterate

.. autofunction:: gtk_treeview_set_column_titles

.. autofunction:: gtk_widget_destroy_children

.. autofunction:: show_dialog

.. autofunction:: show_dialog_exc_socket_error

.. autofunction:: show_dialog_error

.. autofunction:: show_dialog_info

.. autofunction:: show_dialog_warning

.. autofunction:: show_dialog_yes_no

.. autofunction:: which_glade

Classes
-------

.. autoclass:: FileMonitor
   :show-inheritance:
   :special-members: __init__

.. autoclass:: GladeDependencies
   :show-inheritance:
   :members:
   :special-members: __init__
   :undoc-members:

.. autoclass:: GladeGObjectMeta
   :show-inheritance:
   :members:
   :undoc-members:

.. autoclass:: GladeGObject
   :show-inheritance:
   :members:
   :special-members: __init__
   :undoc-members:

.. autoclass:: GladeProxy
   :show-inheritance:
   :members:
   :special-members: __init__
   :undoc-members:

.. autoclass:: GladeProxyDestination
   :show-inheritance:
   :members:
   :special-members: __init__
   :undoc-members:
