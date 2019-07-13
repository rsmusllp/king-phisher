.. _database-schema-label:

Schema
======

Tables
------

.. db:table:: alert_subscriptions

   .. db:field:: expiration

      :nullable: True
      :type: DateTime
      
   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: user_id

      :nullable: False
      :foreignkey: :db:fld:`users.id`
            
   .. db:field:: campaign_id

      :nullable: False
      :foreignkey: :db:fld:`campaigns.id`
            
.. db:table:: authenticated_sessions

   .. db:field:: id

      :primarykey: True
      :type: String
      
   .. db:field:: created

      :nullable: False
      :type: DateTime
      
   .. db:field:: last_seen

      :nullable: False
      :type: DateTime
      
   .. db:field:: user_id

      :nullable: False
      :foreignkey: :db:fld:`users.id`
            
.. db:table:: campaign_types

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: name

      :nullable: False
      :type: String
      
   .. db:field:: description

      :nullable: True
      :type: String
      
.. db:table:: campaigns

   .. db:field:: expiration

      :nullable: True
      :type: DateTime
      
   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: name

      :nullable: False
      :type: String
      
   .. db:field:: description

      :nullable: True
      :type: String
      
   .. db:field:: user_id

      :nullable: False
      :foreignkey: :db:fld:`users.id`
            
   .. db:field:: created

      :nullable: True
      :type: DateTime
      
   .. db:field:: max_credentials

      :nullable: True
      :type: Integer
      
   .. db:field:: campaign_type_id

      :nullable: True
      :foreignkey: :db:fld:`campaign_types.id`
            
   .. db:field:: company_id

      :nullable: True
      :foreignkey: :db:fld:`companies.id`
            
   .. db:field:: credential_regex_username

      :nullable: True
      :type: String
      
   .. db:field:: credential_regex_password

      :nullable: True
      :type: String
      
   .. db:field:: credential_regex_mfa_token

      :nullable: True
      :type: String
      
.. db:table:: companies

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: name

      :nullable: False
      :type: String
      
   .. db:field:: description

      :nullable: True
      :type: String
      
   .. db:field:: industry_id

      :nullable: True
      :foreignkey: :db:fld:`industries.id`
            
   .. db:field:: url_main

      :nullable: True
      :type: String
      
   .. db:field:: url_email

      :nullable: True
      :type: String
      
   .. db:field:: url_remote_access

      :nullable: True
      :type: String
      
.. db:table:: company_departments

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: name

      :nullable: False
      :type: String
      
   .. db:field:: description

      :nullable: True
      :type: String
      
.. db:table:: credentials

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: visit_id

      :nullable: False
      :foreignkey: :db:fld:`visits.id`
            
   .. db:field:: message_id

      :nullable: False
      :foreignkey: :db:fld:`messages.id`
            
   .. db:field:: campaign_id

      :nullable: False
      :foreignkey: :db:fld:`campaigns.id`
            
   .. db:field:: username

      :nullable: True
      :type: String
      
   .. db:field:: password

      :nullable: True
      :type: String
      
   .. db:field:: mfa_token

      :nullable: True
      :type: String
      
   .. db:field:: submitted

      :nullable: True
      :type: DateTime
      
   .. db:field:: regex_validated

      :nullable: True
      :type: Boolean
      
.. db:table:: deaddrop_connections

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: deployment_id

      :nullable: False
      :foreignkey: :db:fld:`deaddrop_deployments.id`
            
   .. db:field:: campaign_id

      :nullable: False
      :foreignkey: :db:fld:`campaigns.id`
            
   .. db:field:: count

      :nullable: True
      :type: Integer
      
   .. db:field:: ip

      :nullable: True
      :type: String
      
   .. db:field:: local_username

      :nullable: True
      :type: String
      
   .. db:field:: local_hostname

      :nullable: True
      :type: String
      
   .. db:field:: local_ip_addresses

      :nullable: True
      :type: String
      
   .. db:field:: first_seen

      :nullable: True
      :type: DateTime
      
   .. db:field:: last_seen

      :nullable: True
      :type: DateTime
      
.. db:table:: deaddrop_deployments

   .. db:field:: id

      :primarykey: True
      :type: String
      
   .. db:field:: campaign_id

      :nullable: False
      :foreignkey: :db:fld:`campaigns.id`
            
   .. db:field:: destination

      :nullable: True
      :type: String
      
.. db:table:: industries

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: name

      :nullable: False
      :type: String
      
   .. db:field:: description

      :nullable: True
      :type: String
      
.. db:table:: landing_pages

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: campaign_id

      :nullable: False
      :foreignkey: :db:fld:`campaigns.id`
            
   .. db:field:: hostname

      :nullable: False
      :type: String
      
   .. db:field:: page

      :nullable: False
      :type: String
      
.. db:table:: messages

   .. db:field:: id

      :primarykey: True
      :type: String
      
   .. db:field:: campaign_id

      :nullable: False
      :foreignkey: :db:fld:`campaigns.id`
            
   .. db:field:: target_email

      :nullable: True
      :type: String
      
   .. db:field:: first_name

      :nullable: True
      :type: String
      
   .. db:field:: last_name

      :nullable: True
      :type: String
      
   .. db:field:: opened

      :nullable: True
      :type: DateTime
      
   .. db:field:: opener_ip

      :nullable: True
      :type: String
      
   .. db:field:: opener_user_agent

      :nullable: True
      :type: String
      
   .. db:field:: sent

      :nullable: True
      :type: DateTime
      
   .. db:field:: reported

      :nullable: True
      :type: DateTime
      
   .. db:field:: trained

      :nullable: True
      :type: Boolean
      
   .. db:field:: delivery_status

      :nullable: True
      :type: String
      
   .. db:field:: delivery_details

      :nullable: True
      :type: String
      
   .. db:field:: testing

      :nullable: False
      :type: Boolean
      
   .. db:field:: company_department_id

      :nullable: True
      :foreignkey: :db:fld:`company_departments.id`
            
.. db:table:: storage_data

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: created

      :nullable: True
      :type: DateTime
      
   .. db:field:: modified

      :nullable: True
      :type: DateTime
      
   .. db:field:: namespace

      :nullable: True
      :type: String
      
   .. db:field:: key

      :nullable: False
      :type: String
      
   .. db:field:: value

      :nullable: True
      :type: Binary
      
.. db:table:: users

   .. db:field:: expiration

      :nullable: True
      :type: DateTime
      
   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: name

      :nullable: False
      :type: String
      
   .. db:field:: description

      :nullable: True
      :type: String
      
   .. db:field:: phone_carrier

      :nullable: True
      :type: String
      
   .. db:field:: phone_number

      :nullable: True
      :type: String
      
   .. db:field:: email_address

      :nullable: True
      :type: String
      
   .. db:field:: otp_secret

      :nullable: True
      :type: String
      
   .. db:field:: last_login

      :nullable: True
      :type: DateTime
      
   .. db:field:: access_level

      :nullable: False
      :type: Integer
      
.. db:table:: visits

   .. db:field:: id

      :primarykey: True
      :type: String
      
   .. db:field:: message_id

      :nullable: False
      :foreignkey: :db:fld:`messages.id`
            
   .. db:field:: campaign_id

      :nullable: False
      :foreignkey: :db:fld:`campaigns.id`
            
   .. db:field:: count

      :nullable: True
      :type: Integer
      
   .. db:field:: ip

      :nullable: True
      :type: String
      
   .. db:field:: details

      :nullable: True
      :type: String
      
   .. db:field:: user_agent

      :nullable: True
      :type: String
      
   .. db:field:: first_landing_page_id

      :nullable: True
      :foreignkey: :db:fld:`landing_pages.id`
            
   .. db:field:: first_seen

      :nullable: True
      :type: DateTime
      
   .. db:field:: last_seen

      :nullable: True
      :type: DateTime
      

