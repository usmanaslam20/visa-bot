'''Copyright (c) 2019 Aleksandr Derbenev. All rights reserved.

Some basic tests for commands.
'''

import collections
import datetime
import time

from ..bot import Bot, TEXTS


class MockBot(Bot):
    @property
    def shutdown(self):
        return self.bot._fixture._next_event is None

    @shutdown.setter
    def shutdown(self, value):
        pass


class TelegramBotFixture(object):
    Chat = collections.namedtuple('Chat', ('id',))
    Message = collections.namedtuple('Message', ('chat', 'text'))
    Update = collections.namedtuple('Update', ('update_id', 'message'))
    MessageExpected = collections.namedtuple('MessageExpected',
                                             ('chat_id', 'text'))

    class Client(object):
        def __init__(self, fixture):
            super(TelegramBotFixture.Client, self).__init__()
            self._fixture = fixture
            self._update_id = 0
            self._updates = []
            self._last_offset = 0

        def get_updates(self, offset=None, timeout=None):
            if offset is None:
                offset = self._last_offset
            else:
                self._last_offset = offset

            while offset < len(self._updates):
                yield self._updates[offset]
                offset += 1

            event = self._fixture._next_event
            while (event is not None and
                    isinstance(event, TelegramBotFixture.Message)):
                self._updates.append(
                    TelegramBotFixture.Update(len(self._updates), event))
                self._fixture._advance()
                event = self._fixture._next_event

            while offset < len(self._updates):
                yield self._updates[offset]
                offset += 1

            time.sleep(0)

        def send_message(self, chat_id, text, formatting=None):
            event = self._fixture._next_event
            assert event is not None
            assert not isinstance(event, TelegramBotFixture.Message), \
                'Trying to send message while no messages expected.'
            if isinstance(event, TelegramBotFixture.MessageExpected):
                self._fixture._advance()
                assert event.chat_id == chat_id
                if event.text is not None:
                    assert event.text == text

    def __init__(self):
        self._events = []
        self._pos = 0

    @property
    def _next_event(self):
        if self._pos < len(self._events):
            return self._events[self._pos]

    def _advance(self):
        self._pos += 1

    def input_message(self, chat_id, text):
        self._events.append(
            self.Message(self.Chat(chat_id), text))
        return self

    def expect_message(self, chat_id, text=None):
        self._events.append(
            self.MessageExpected(chat_id, text))
        return self

    @property
    def client(self):
        return self.Client(self)


def test_start():
    fixture = (
        TelegramBotFixture()
        .input_message(1, '/start')
        .expect_message(1, TEXTS.GREETINGS)
    )
    bot = MockBot(fixture.client, 'sqlite:///:memory:')
    bot.interactive_loop()


def test_help():
    fixture = (
        TelegramBotFixture()
        .input_message(1, '/help')
        .expect_message(1, TEXTS.HELP)
    )
    bot = MockBot(fixture.client, 'sqlite:///:memory:')
    bot.interactive_loop()


def test_terms():
    fixture = (
        TelegramBotFixture()
        .input_message(1, '/terms')
        .expect_message(1, TEXTS.TERMS)
    )
    bot = MockBot(fixture.client, 'sqlite:///:memory:')
    bot.interactive_loop()


def test_subscribe():
    fixture = (
        TelegramBotFixture()
        .input_message(1, '/subscribe')
        .expect_message(1, TEXTS.SUBSCRIBED)
    )
    bot = MockBot(fixture.client, 'sqlite:///:memory:')
    bot.interactive_loop()


def test_unsubscribe():
    fixture = (
        TelegramBotFixture()
        .input_message(1, '/unsubscribe')
        .expect_message(1, TEXTS.UNSUBSCRIBED)
    )
    bot = MockBot(fixture.client, 'sqlite:///:memory:')
    bot.interactive_loop()


def test_stats():
    fixture = (
        TelegramBotFixture()
        .input_message(1, '/stats')
        .expect_message(1, TEXTS.STATISTICS.format(
            users_plural='are no people',
            watching_for=datetime.timedelta(0),
            seen_appointments=datetime.timedelta(0)))
    )
    bot = MockBot(fixture.client, 'sqlite:///:memory:')
    bot.interactive_loop()


def test_unknown_command():
    fixture = (
        TelegramBotFixture()
        .input_message(1, '/someunexistentcommand')
        .expect_message(1, TEXTS.UNKNOWN_COMMAND)
    )
    bot = MockBot(fixture.client, 'sqlite:///:memory:')
    bot.interactive_loop()


def test_message():
    fixture = (
        TelegramBotFixture()
        .input_message(1, 'Hello!')
        .expect_message(1, TEXTS.DONT_UNDERSTAND)
    )
    bot = MockBot(fixture.client, 'sqlite:///:memory:')
    bot.interactive_loop()
