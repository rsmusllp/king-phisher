# Copyright (c) 2015, Brandan [coldfusion]
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are
#  met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following disclaimer
#    in the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of the  nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


require 'uri'

module Msf
  class Plugin::SessionSMS < Msf::Plugin
    include Msf::SessionEvent

    CARRIERS = ['AT&T', 'Boost', 'Sprint', 'T-Mobile', 'Verizon', 'Virgin Mobile']
    private_constant :CARRIERS

    def initialize(framework, opts)
      super
      add_console_dispatcher(SMSCommandDispatcher)
    end

    def cleanup
      self.framework.events.remove_session_subscriber(@inst)
      remove_console_dispatcher('sms')
    end

    def name
      "sms"
    end

    def desc
      "Sends a SMS message when recieving a new session through the use of the King Phisher's REST API."
    end

    def sms_yaml
      "#{Msf::Config.get_config_root}/sms.yaml"
    end

    class SMSCommandDispatcher < Plugin::SessionSMS
      include Msf::Ui::Console::CommandDispatcher

      def initialize(framework)
        super
        @king_phisher_server = nil
        @king_phisher_token = nil
        @sms_number = nil
        @sms_carrier = nil

        print_status('Loaded previously configured settings') if read_settings
      end

      def on_session_open(session)
        print_status('Session received, sending SMS...')
        send_sms("Session: #{session.sid} opened")
      end

      def name
        'sms'
      end

      def read_settings
        return false unless File.exist?(sms_yaml)

        ldconfig = YAML.load_file(sms_yaml)
        @king_phisher_server = ldconfig['king_phisher_server']
        @king_phisher_token = ldconfig['king_phisher_token']
        @sms_number = ldconfig['sms_number']
        @sms_carrier = ldconfig['sms_carrier']
        return true
      end

      def send_sms(message)
        message = Rex::Text.uri_encode(message)
        begin
          http_client = Rex::Proto::Http::Client.new(@king_phisher_server)
          http_client.connect
          request = http_client.request_cgi({
            'uri'    => '/_/api/sms/send',
            'query'  => "token=#{@king_phisher_token}&message=#{message}&phone_number=#{@sms_number}&carrier=#{@sms_carrier}"
          })
          res = http_client.send_recv(request)
        rescue Exception => e
          print_error("Error sending SMS: #{e.class} - #{e}")
          return false
        ensure
          http_client.close
        end

        res and res.code == 200
      end

      def commands
        {
          'sms_start'       => 'Start SMS alerts for new sessions',
          'sms_stop'        => 'Stop SMS alerts for new sessions',
          'sms_save'        => "Save SMS settings to #{sms_yaml}",
          'sms_set_server'  => 'Set domain name of the King Phisher server',
          'sms_set_token'   => 'Set King Phisher\'s API token',
          'sms_set_number'  => 'Set number to send SMS alerts to on new session',
          'sms_set_carrier' => 'Set carrier for sending SMS messages',
          'sms_show_params' => 'Shows currently set or saved parameters',
          'sms_test'        => 'Send a test SMS message to verify the parameters'
        }
      end

      def cmd_sms_start
        unless @king_phisher_server and @king_phisher_token and @sms_number and @sms_carrier
          print_error('You have not provided all the parameters!')
          return
        end

        self.framework.events.add_session_subscriber(self)
        print_good('Started SMS sessions session notifications')
      end

      def cmd_sms_stop
        self.framework.events.remove_session_subscriber(self)
        print_good('Stopped SMS sessions session notifications')
      end

      def cmd_sms_save
        unless @king_phisher_server and @king_phisher_token and @sms_number and @sms_carrier
          print_error('You have not provided all the parameters!')
          return
        end

        config = {
          'king_phisher_server' => @king_phisher_server,
          'king_phisher_token'  => @king_phisher_token,
          'sms_number'          => @sms_number,
          'sms_carrier'         => @sms_carrier
        }
        File.open(sms_yaml, 'w') do |out|
          YAML.dump(config, out)
        end
        print_good("All parameters saved to #{sms_yaml}")
      end

      def cmd_sms_test(*args)
        unless @king_phisher_server and @king_phisher_token and @sms_number and @sms_carrier
          print_error('You have not provided all the parameters!')
          return
        end

        message = args.shift
        message = 'Test SMS message' if message.nil?

        if send_sms(message)
          print_good('Sent the test SMS message')
        else
          print_error('Failed to send the test SMS message')
        end
      end

      def cmd_sms_set_server(*args)
        if args.length > 0
          print_status("Setting the King Phisher server to #{args[0]}")
          @king_phisher_server = args[0]
        else
          print_error('Please provide the domain name of your King Phisher server!')
        end
      end

      def cmd_sms_set_token(*args)
        if args.length > 0
          print_status("Setting King Phisher's REST API token to #{args[0]}")
          @king_phisher_token = args[0]
        else
          print_error('Please provide the REST API token of your King Phisher server!')
        end
      end

      def cmd_sms_set_number(*args)
        if args[0].length == 10
          print_status("Setting SMS number to #{args[0]}")
          @sms_number = args[0]
        else
          print_error('Please provide a valid SMS number!')
        end
      end

      def cmd_sms_set_carrier(*args)
        if args.length > 0 and CARRIERS.include?(args[0])
          print_status("Setting SMS carrier to #{args[0]}")
          @sms_carrier = args[0]
        else
          print_error("Please provide a valid SMS carrier (#{CARRIERS.join(', ')})!")
        end
      end

      def cmd_sms_show_params
        print_status('Parameters:')
        print_status("  King Phisher Server: #{@king_phisher_server}")
        print_status("  King Phisher Token: #{@king_phisher_token}")
        print_status("  SMS Number: #{@sms_number}")
        print_status("  SMS Carrier: #{@sms_carrier}")
      end
    end
  end
end
