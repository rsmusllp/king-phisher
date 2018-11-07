Additional Configuration
========================

The following configuration settings will be honored but can not be set from
within the client's user interface. The client configuration file is usually
located in the following locations depending on the host operating system:

:Linux:
  ``~/.config/king-phisher/config.json``

:Windows:
  ``%LOCALAPPDATA%\king-phisher\config.json``

.. note::
   The King Phisher client will overwrite its configuration file when it exits
   to store the latest values. This means that the client should not be running
   when the configuration file is being manually edited so the changes are not
   overwritten.

+------------------------------------+--------------------------------------------------------+
| Setting Name                       | Default Value                                          |
+====================================+========================================================+
| gui.refresh_frequency              | ``5m`` (5 minutes)                                     |
+------------------------------------+--------------------------------------------------------+
| gui.show_deaddrop                  | ``false``                                              |
+------------------------------------+--------------------------------------------------------+
| mailer.max_messages_per_connection | ``5``                                                  |
+------------------------------------+--------------------------------------------------------+
| plugins.path                       | ``[]`` (No additional plugin paths)                    |
+------------------------------------+--------------------------------------------------------+
| rpc.serializer                     | ``null`` (Automatically determined)                    |
+------------------------------------+--------------------------------------------------------+
| ssh_preferred_key                  | ``null`` (Automatically determined)                    |
+------------------------------------+--------------------------------------------------------+
| text_font                          | ``"monospace 10"``                                     |
+------------------------------------+--------------------------------------------------------+
| text_source.hardtabs               | ``false``                                              |
+------------------------------------+--------------------------------------------------------+
| text_source.highlight_line         | ``true``                                               |
+------------------------------------+--------------------------------------------------------+
| text_source.tab_width              | ``2``                                                  |
+------------------------------------+--------------------------------------------------------+
| text_source.theme                  | ``"cobalt"`` (One of the GtkSourceView StyleSchemes_)  |
+------------------------------------+--------------------------------------------------------+
| text_source.wrap_mode              | ``"NONE"`` (One of ``"CHAR"``, ``"NONE"``, ``"WORD"``, |
|                                    | ``"WORD_CHAR"``) :sup:`1`                              |
+------------------------------------+--------------------------------------------------------+

:sup:`1` See GtkWrapMode_ for more details.

.. _GtkWrapMode: https://developer.gnome.org/gtk3/stable/GtkTextView.html#GtkWrapMode
.. _StyleSchemes: https://wiki.gnome.org/Projects/GtkSourceView/StyleSchemes
