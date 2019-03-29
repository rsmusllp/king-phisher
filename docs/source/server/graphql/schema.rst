Schema
======

.. gql:object:: GeoLocation

   :field String city:
   :field String continent:
   :field [Float] coordinates:
   :field String country:
   :field String postalCode:
   :field String timeZone:

.. gql:object:: Plugin

   :field [String] authors:
   :field [String] classifiers:
   :field String description:
   :field String homepage:
   :field String name:
   :field [String] reference_urls:
   :field String title:
   :field String version:

.. gql:object:: SiteTemplate

   :field DateTime created:
   :field String hostname:
   :field String path:
   :field metadata:
   :type metadata: :gql:obj:`SiteTemplateMetadata`

.. gql:object:: SiteTemplateMetadata

   :field [String] authors:
   :field [String] classifiers:
   :field String description:
   :field String homepage:
   :field [String] pages:
   :field [String] referenceUrls:
   :field String title:
   :field String version:

.. gql:object:: SSL

   :field sniHostname:
   :type sniHostname: :gql:obj:`SniHostname`
   :field Connection sniHostnames:
   :field status:
   :type status: :gql:obj:`SSLStatus`

.. gql:object:: SniHostname

   :field Boolean enabled: Whether or not the hostname is enabled.
   :field String hostname: The hostname for this configuration.

.. gql:object:: SSLStatus

   :field Boolean enabled:
   :field Boolean hasSni:
