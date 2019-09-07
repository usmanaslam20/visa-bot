#!/usr/bin/env python3
'''Copyright (c) 2019 Aleksandr Derbenev. All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

 1. Redistributions of source code must retain the above copyright notice, this
    list of conditions and the following disclaimer.

 2. Redistributions in binary form must reproduce the above copyright notice,
    this list of conditions and the following disclaimer in the documentation
    and/or other materials provided with the distribution.

 3. All advertising materials mentioning features or use of this software must
    display the following acknowledgement:

        This product includes software developed by Aleksandr Derbenev.

 4. Neither the name of the copyright holder nor the names of its contributors
    may be used to endorse or promote products derived from this software
    without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY COPYRIGHT HOLDER "AS IS" AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL COPYRIGHT HOLDER BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
'''

import logging
import argparse
import sys
import datetime
import contextlib
import textwrap
import functools
import threading
import time
from urllib.parse import urljoin

import inflect
import telegram
import sqlalchemy
import requests
from bs4 import BeautifulSoup
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, DateTime, Boolean

Base = declarative_base()
p = inflect.engine()


class LastUpdate(Base):
    __tablename__ = 'last_update'
    id = Column(Integer, primary_key=True)
    update_id = Column(Integer)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, unique=True)
    subscribed = Column(Boolean)


class AppointmentEvent(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    have_appointments = Column(Boolean)
    notification_sent = Column(Boolean)


BASE_URL = ('https://www.vfsvisaonline.com/'
            'Netherlands-Global-Online-Appointment_Zone2/AppScheduling/')
WELCOME_PAGE = (
    BASE_URL +
    'AppWelcome.aspx?P=yLSZQO8Ad673EXhKOPALC%2Fa6TdN5o6wQfJGZex2bh88%3D')
INTERVAL = 5


class TEXTS(object):
    GREETINGS = textwrap.dedent('''\
        Hi! I watch for appointments to the Netherlands embassy in Dublin.
        I'm checking [this page]({}) each *{}* seconds.

        You can subscribe to notifications with /subscribe command.
        Feel free to check /help and /terms.''').format(WELCOME_PAGE, INTERVAL)
    HELP = textwrap.dedent('''\
        I'm watching for appointments to the Netherlands embassy in Dublin.
        I'm checking [this page]({}) each *{}* seconds.

        *Available commands*

        /start - Just greetings. Just tells me that I can talk with you.
        /help - This message.
        /terms - Information about terms of use and collected information.
        /subscribe - Subscribe for notifications. I will send you a message \
when I see an appointment.
        /unsubscribe - Unsubscribe for notification.''').format(
            WELCOME_PAGE, INTERVAL)
    TERMS = textwrap.dedent('''\
        *Collected data*

        This bot *does not* use, collect or keep any personal data. It does not
        even uses your username. However it uses and keeps:

         - Telegram chat id (not user id) - It's required to send a message \
to you.
         - Your subscription state - It will not know that you need a \
notification without it. You should opt-in for it with /subscribe command.
         - Your messages to this bot - Bot keeps history for maintenance \
purposes.

        *Source & License*

        Please note, author does not control, support or maintain this bot.
        He just wrote the code for personal use and published it.
        You can freely contribute. You can launch our copy of this bot.

        Source code is hosted [here](https://github.com/alex-ac/netherappbot)

        {}
        ''').format(__doc__)
    SUBSCRIBED = textwrap.dedent('''\
        I will notify when find an appointment to the Netherlands embassy in \
Dublin.
        You can disable notifications with /unsubscribe command.''')
    UNSUBSCRIBED = textwrap.dedent('''\
        Ok, I will not send notifications to you anymore.
        Feel free to subscribe again with /subscribe command.''')
    UNKNOWN_COMMAND = textwrap.dedent('''\
        Sorry, I don't know this command: {}
        Use /help for the list of available commands.''')
    DONT_UNDERSTAND = textwrap.dedent('''\
        Sorry, I don't understand your message.
        Use /help for the list of available commands.''')
    APPOINTMENTS_AVAILABLE = (
        '*Psst! Looks like there are some appointments available:* '
        '[GO GET THEM]({})').format(WELCOME_PAGE)
    NO_MORE_APPOINTMENTS = textwrap.dedent('''\
        *I don\'t see appointments anymore.*
        Will notify when see them again.''')
    STATISTICS = textwrap.dedent('''\
        I've been watching for *{watching_for}*.
        I've seen appointments for *{seen_appointments}*.
        There {users_plural} watching for notifications.''')


def loop(interval, ignore=()):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(self):
            try:
                while not self.shutdown:
                    if ignore:
                        with contextlib.closing(self.Session()) as session:
                            try:
                                f(self, session)
                                session.commit()
                            except ignore:
                                self.logger.error(
                                    'Transient exception caught',
                                    exc_info=True)
                                continue
                    else:
                        with contextlib.closing(self.Session()) as session:
                            f(self, session)
                            session.commit()
                    time.sleep(interval)
            finally:
                self.shutdown = True
                self.logger.error('Exiting %s', f.__name__, exc_info=True)

        return wrapper

    return decorator


class Bot(object):
    def __init__(self, bot, database):
        super(Bot, self).__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.bot = bot
        self.engine = sqlalchemy.create_engine(database)
        Base.metadata.create_all(self.engine)
        self.Session = sqlalchemy.orm.sessionmaker(bind=self.engine)
        self.session = requests.Session()
        self.shutdown = False

    @loop(0)
    def interactive_loop(self, session):
        last_update = session.query(LastUpdate).first()
        if last_update is not None:
            offset = last_update.update_id + 1
        else:
            offset = None

        try:
            updates = self.bot.get_updates(offset, timeout=4)
        except telegram.error.TimedOut:
            return

        for update in updates:
            if not last_update:
                last_update = LastUpdate(
                    update_id=update.update_id)
                session.add(last_update)
                session.commit()
            else:
                last_update.update_id = update.update_id

            if update.message is None:
                continue

            self.on_message(session, update.message)

    @loop(1)
    def notification_loop(self, session):
        event = session.query(AppointmentEvent).filter(
            AppointmentEvent.notification_sent == False).first()  # noqa: E712
        if event is None:
            return

        text = (TEXTS.APPOINTMENTS_AVAILABLE
                if event.have_appointments else TEXTS.NO_MORE_APPOINTMENTS)

        for user in session.query(User).filter(
                User.subscribed == True).all():  # noqa: E712
            self.reply(session, user, text)

        event.notification_sent = True

    def load_page(self, stage, url, method='GET', data=None):
        logging.info('%s: %s %s -> %r', stage, method, url, data)
        response = self.session.request(method, url, data=data).text

        return BeautifulSoup(response, 'html.parser')

    def extract_form_data(self, soup):
        frm_web = soup.find(id='frmWeb')
        args = {
            input_tag.get('name'): input_tag.get('value')
            for input_tag in frm_web.find_all('input')
            if input_tag.get('name') not in {
                'ctl00$plhMain$btnCancel', 'ctl00$plhMain$btnBack'}
        }
        return urljoin(BASE_URL, frm_web.get('action')), args

    @loop(INTERVAL, ignore=(requests.exceptions.ConnectionError,))
    def watching_loop(self, session):
        soup = self.load_page('welcome', WELCOME_PAGE)
        action, args = self.extract_form_data(soup)
        args['__EVENTTARGET'] = 'ctl00$plhMain$lnkSchApp'
        args['__EVENTARGUMENT'] = ''

        soup = self.load_page(
            'appointment_type', action, method='POST', data=args)
        action, args = self.extract_form_data(soup)
        # Number of applicants: 1
        args['ctl00$plhMain$tbxNumOfApplicants'] = 1
        # Visa category: Touristic Schengen
        args['ctl00$plhMain$cboVisaCategory'] = 898

        soup = self.load_page('application', action, method='POST', data=args)

        response = (
            soup.find(id='plhMain_lblMsg').string or
            soup.find(id='plhMain_lblFillAppDetails').string)
        logging.info('Response: %s', response)

        last_event = session.query(AppointmentEvent).order_by(
            AppointmentEvent.timestamp.desc()).limit(1).first()
        if last_event is None:
            previous_result = False
        else:
            previous_result = last_event.have_appointments

        have_appointments = (
            response != 'No date(s) available for appointment.')
        if last_event is None or have_appointments != previous_result:
            event = AppointmentEvent(
                have_appointments=have_appointments,
                # Don't sent notification if it's first check and
                # we have no appointments.
                notification_sent=have_appointments == previous_result,
                timestamp=datetime.datetime.utcnow())
            session.add(event)

    def on_message(self, session, message):
        text = message.text
        chat_id = message.chat.id

        self.logger.info('<== %d: %s', chat_id, text)

        user = session.query(User).filter(User.chat_id == chat_id).first()
        if user is None:
            user = User(chat_id=chat_id, subscribed=False)
            session.add(user)

        if text.startswith('/'):
            self.on_command(session, user, text)
        else:
            self.on_plain_message(session, user, text)

    def on_command(self, session, user, message):
        command = message.split(' ', 1)[0]
        if '/start' == command:
            self.on_start(session, user, message)
        elif '/help' == command:
            self.on_help(session, user, message)
        elif '/terms' == command:
            self.on_terms(session, user, message)
        elif '/subscribe' == command:
            self.on_subscribe(session, user, message)
        elif '/unsubscribe' == command:
            self.on_unsubscribe(session, user, message)
        elif '/stats' == command:
            self.on_stats(session, user, message)
        else:
            self.on_unknown_command(session, user, message)

    def on_start(self, session, user, message):
        self.reply(session, user, TEXTS.GREETINGS)

    def on_help(self, session, user, message):
        self.reply(session, user, TEXTS.HELP)

    def on_terms(self, session, user, message):
        self.reply(session, user, TEXTS.TERMS)

    def on_subscribe(self, session, user, message):
        user.subscribed = True
        self.logger.info('Subscribing user with chat_id: %d', user.chat_id)
        self.reply(session, user, TEXTS.SUBSCRIBED)

    def on_unsubscribe(self, session, user, message):
        user.subscribed = False
        self.logger.info('Unsubscribing user with chat_id: %d', user.chat_id)
        self.reply(session, user, TEXTS.UNSUBSCRIBED)

    def on_stats(self, session, user, message):
        subscribed_users = session.query(User).filter(
            User.subscribed == True).count()  # noqa: E721
        first_event = None
        last_event = None
        seen_appointments = datetime.timedelta(seconds=0)
        for event in session.query(AppointmentEvent).order_by(
                AppointmentEvent.timestamp).all():
            if first_event is None:
                first_event = event
            if last_event is not None:
                if last_event.have_appointments:
                    delta = event.timestamp - last_event.timestamp
                    seen_appointments += delta
            last_event = event

        watching_for = datetime.datetime.utcnow() - first_event.timestamp
        watching_for = datetime.timedelta(seconds=watching_for // datetime.timedelta(seconds=1))
        seen_appointments = datetime.timedelta(seconds=seen_appointments // datetime.timedelta(seconds=1))

        self.reply(session, user, TEXTS.STATISTICS.format(
            users_plural=p.plural_verb('is', subscribed_users) + p.no(' person', subscribed_users),
            watching_for=watching_for,
            seen_appointments=seen_appointments))


    def on_unknown_command(self, session, user, message):
        self.reply(session, user, TEXTS.UNKNOWN_COMMAND)

    def on_plain_message(self, session, user, message):
        self.reply(session, user, TEXTS.DONT_UNDERSTAND)

    def reply(self, session, user, text):
        try:
            self.logger.info('==> %d: %s', user.chat_id, text)
            self.bot.send_message(
                user.chat_id, text, telegram.ParseMode.MARKDOWN)
        except telegram.error.Unauthorized:
            session.delete(user)


def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('token', help='Telegram bot token')
    parser.add_argument('database', help='SQLite3 database')
    args = parser.parse_args(argv)
    logging.basicConfig(level='DEBUG',
                        format='%(asctime)s\t%(levelname)s\t%(message)s')

    bot = Bot(telegram.Bot(args.token), args.database)
    interactive_loop = threading.Thread(
        target=bot.interactive_loop, name='ChatInteraction')
    notification_loop = threading.Thread(
        target=bot.notification_loop, name='ChatNotification')
    try:
        interactive_loop.start()
        notification_loop.start()
        bot.watching_loop()
    finally:
        bot.shutdown = True
        interactive_loop.join()
        notification_loop.join()


if __name__ == '__main__':
    sys.exit(run())
