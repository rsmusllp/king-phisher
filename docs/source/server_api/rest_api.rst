REST API
========

Overview
--------

The King Phisher server provides an optional REST API *that is disabled by
default*. It can be enabled by setting the server configuration value
"rest_api.enabled" to true. An API token is required for all REST methods and
must be present in the "token" parameter. If a static token is not specified in
the server "rest_api.token" configuration, a new token will be randomly
generated every time the server starts. The REST API methods are provided for
access to convienence methods only. As such, campaign information can not be
accessed via the REST API.

REST Methods
------------

.. http:get:: /_/api/geoip/lookup

   Lookup an IP address in the GeoIP database.

   **Example request**:

   .. sourcecode:: http

      GET /_/api/geoip/lookup?token=SECRET_TOKEN&ip=4.2.2.2 HTTP/1.1
      User-Agent: curl/7.40.0
      Host: example.com
      Accept: */*

   **Example response**:

   .. sourcecode:: http

      HTTP/1.0 200 OK
      Server: Apache/2.4.12 (Unix)
      Date: Thu, 04 Jun 2015 14:15:57 GMT
      Content-Type: application/json
      Content-Length: 204

      {
        "result": {
         "city": null,
         "continent": "North America",
         "coordinates": [
           38.0,
           -97.0
         ],
         "country": "United States",
         "postal_code": null,
         "time_zone": null
        }
      }

   :query token: The server's REST API token.
   :query ip: The IP address to query geo location information for.
   :statuscode 200: The operation completed successfully.
   :statuscode 401: The REST API service is disabled or the token is invalid.
   :statuscode 500: The operation encountered an exception.

.. http:get:: /_/api/sms/send

   Send an SMS message by emailing the carriers SMS gateway.

   **Example request**:

   .. sourcecode:: http

      GET /_/api/geoip/lookup?token=SECRET_TOKEN&message=hello+world!&phone_number=1234567890&carrier=Sprint HTTP/1.1 HTTP/1.1
      User-Agent: curl/7.40.0
      Host: example.com
      Accept: */*

   **Example response**:

   .. sourcecode:: http

      HTTP/1.0 200 OK
      Server: Apache/2.4.12 (Unix)
      Date: Thu, 04 Jun 2015 14:30:40 GMT
      Content-Type: application/json
      Content-Length: 22

      {
        "result": "sent"
      }

   :query token: The server's REST API token.
   :query message: The message to send.
   :query phone_number: The phone number to send the SMS to.
   :query carrier: The cellular carrier that the phone number belongs to.
   :query from_address: The optional address to display in the 'from' field of the SMS.
   :statuscode 200: The operation completed successfully.
   :statuscode 401: The REST API service is disabled or the token is invalid.
   :statuscode 500: The operation encountered an exception.
