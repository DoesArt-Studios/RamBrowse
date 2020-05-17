import sys
import os
import socket

from optparse import make_option
from urlparse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand

from django_nose.management.commands.test import Command

from django_webdriver.message import Message

SETTINGS = getattr(settings, "DJANGO_WEBDRIVER_SETTINGS", {})

class Command(Command):

    extra_options = (
        make_option('--webdriver', action='store', dest='webdriver', default=None,
        ),
        make_option('--selenium_only', action='store_true', dest='isSelenium',
                    default=False,
        ),
        make_option('--with_selenium', action='store_true', dest='isAll', 
                    default=False,),
        make_option('--remote_selenium_provider', action='store', dest='remote_provider',
                    default=None)
    )

    Command.option_list = Command.option_list + extra_options
    BaseCommand.option_list = BaseCommand.option_list + extra_options

    def _exit_with_msg(self, msg):
        print(Message.build_error(msg))
        sys.exit(1)

    def _set_exclude(self, **options):
        regexp_exclude = '--exclude='
        if options.get('isSelenium') or options.get('remote_provider'):
            sys.argv.append('--exclude=tests(?!_selenium)')
        elif not options.get('isAll'):
            sys.argv.append('--exclude=tests_selenium*')

    def _set_live_server(self, **options):
        if options.get('liveserver'):
                port = urlparse(options['liveserver']).port
        else:
            port = '8081'
        ip = socket.gethostbyname(socket.gethostname())
        os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = '{ip}:{p}'.format(ip=ip,
            p=port)

    def _set_test_env(self, **options):
        if (options.get('isSelenium') or options.get('isAll') or
            options.get('remote_provider')):
            
            self._set_live_server(**options)

            if options.get('isSelenium') or options.get('isAll'):
                if options.get('webdriver'):
                    os.environ['DJANGO_NOSE_WEBDRIVER'] = options['webdriver']
                else:
                    self._exit_with_msg("You have to define the webdriver to use selenium in local")
                sys.argv.append('--nocapture')
            elif options.get('remote_provider'):
                sys.argv.append('--nocapture')
                if SETTINGS.get('remote_providers') and SETTINGS.get('remote_capabilities'):
                   os.environ['DJANGO_NOSE_REMOTE'] = options['remote_provider']
                else:
                    self._exit_with_msg("You have to define your remote providers in settings.py")
        else:
            if options.get('webdriver'):
                print(Message.build_warning("You haven't to define the"
                 " browser is you don't use selenium in local"))

    def handle(self, *test_labels, **options):
        self._set_test_env(**options)
        self._set_exclude(**options)
        super(Command, self).handle(*test_labels, **options)
