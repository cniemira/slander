import logging
import os
import sys
import time

from configparser import ConfigParser
from textwrap import TextWrapper

from slackclient import SlackClient
from terminaltables import AsciiTable

log = logging.getLogger(__name__)

# TODO:
# ignore users in a channel (conf)


messages = {
    'help' : """Standup management (from a channel or pvt group):
  `@{name} start`       Start a standup. I will message everyone in the channel
  `@{name} cancel`      Cancel a standup that has been started
  `@{name} publish`     Publish a standup that has been started
 
Status entry (via direct message):
  `d: [...]`     Something you have done since the last standup
  `b: [...]`     A blocker that prevented you from getting something done
  `g: [...]`     A goal for today
  `end`     When you've no more to say
  `show`     If you're too lazy to scroll back
  `skip`     Nothing for today, diposes of anything you've entered
  `reset [...]`     Reset a status category, or all
 
Example:
  Your group chat:
    <boss> @{name} start
    <{name}> group standup started.
 
  direct-message with me:
    <{name}>  @{name} Standup started for group!
    <you> d: finished documenting all the things
    <{name}> done: 1, blocked: 0, goals: 0
    <you> g: find more thing to document
    <{name}> done: 1, blocked: 0, goals: 1
    <you> end
    <{name}> Thanks; done: 1, blocked: 0, goals: 1
 
  Back in your group chat:
    <{name}> @you sat down.
    <boss> @{name} publish
    <{name}> ...
""",

    'next' : 'Another standup, for {standup.channel.name}, also started.',

    'no_standup' : 'No active standup.',

    'pong' : 'pong',

    'preview': """Preview:
  
{update}
""",

    'reset_what': 'Reset what?',

    'sat_down': '{user.tag} sat down.',

    'standup_already': '{standup.channel.name} standup already started.',
    'standup_cancelled': '{standup.channel.name} standup cancelled.',
    'standup_empty': '*There are no users in the standup!*',
    'standup_ended': '*{standup.channel.name} standup ended!',
    'standup_for': '*Standup for {standup.channel.name}*',
    'standup_started': '{standup.channel.name} standup started.',

    'started' : """Standup started for {standup.channel.name}!
Use `d: ...`, `b: ...`, `g: ...` to report tasks done, blockers, and goals.
Type `end` when you're finished, or `help` if you need.
""",

    'unknown_cmd' : 'Bad command. Try `help` if you need it.',

    'Done': 'Done',
    'Blocked': 'Blocked',
    'Goals': 'Goals',
    'None': '*None*',
    'Ok': 'Ok',
    'Skipping': 'Skipping you',
    'Thanks': 'Thanks',
    }


commands = {
    'blocked': ('b:', 'blocked', 'block', 'stuck'),
    'cancel': ('cancel'),
    'done': ('d:', 'did', 'finished', 'completed'),
    'end': ('end'),
    'help': ('help'),
    'goals': ('g:', 'goal', 'will', 'shall'),
    'reset': ('reset'),
    'skip': ('skip', 'no'),
    'show': ('show', 'what'),
    'start': ('start', 'begin'),
    'ping': ('ping'),
    'publish': ('publish'),
    }


def _(key, **kwds):
    if not key in messages:
        log.error('Undefined message: "{}"'.format(key))
        return ''
    return str(messages[key]).format(**kwds)


class Standup(object):
    def __init__(self, channel):
        assert isinstance(channel, Channel)
        self.channel = channel
        self.outstanding = 0
        self.updates = {}
        self.users = []
        log.debug('Initialized {}'.format(self))


    def __repr__(self):
        return str('<{} channel="id:{}, name:{}">'.format(
            self.__class__.__name__,
            self.channel.id, self.channel.name))


    def add_user(self, user):
        assert isinstance(user, User)
        self.users.append(user)
        self.updates.update({user.tag: Updates()})
        self.outstanding += 1


    def publish(self):
        log.info('Publishing standup in {}'.format(self.channel.name))
        res = [_('standup_for', standup=self)]
        [res.append(ups.display(tag)) for tag, ups in self.updates.items()]
        self.channel.send_message('\n \n'.join(res))


class Updates(object):
    def __init__(self):
        self.done = []
        self.blocked = []
        self.goals = []
        log.debug('Initialized {}'.format(self))


    def __repr__(self):
        return str('<{} done={} blocked={} goals={}>'.format(
            self.__class__.__name__,
            len(self.done), len(self.blocked), len(self.goals)))


    def display(self, tag):
        i = len(self.done) + len(self.blocked) + len(self.goals)
        return self._as_none(tag) if i < 1 else self._as_table(tag)


    def _as_none(self, tag):
        return tag + ': ' + _('None')


    def _as_table(self, tag):
        w = TextWrapper(width=68, initial_indent='* ',
                subsequent_indent='  ')

        d = []
        if len(self.done):
            d.append((_('Done'), '\n'.join([w.fill(i) for i in self.done])))
        if len(self.blocked):
            d.append((_('Blocked'), '\n'.join([w.fill(i) for i in self.blocked])))
        if len(self.goals):
            d.append((_('Goals'), '\n'.join([w.fill(i) for i in self.goals])))

        t = AsciiTable(d)
        t.inner_row_border = True
        t.outer_border = False
        t.justify_columns = {0: 'right', 1: 'left'}
        return tag + ':```\n' + t.table + '```'



class Channel(object):
    def __init__(self, channel_info, slack_client):
        self.slack_client = slack_client
        self.id = channel_info["id"]
        self.name = channel_info["name"]
        self.members = channel_info["members"]
        log.debug('Initialized {}'.format(self))


    def __repr__(self):
        return str('<{} id="{}" name="{}" members="{}">'.format(
            self.__class__.__name__,
            self.id, self.name, self.members))


    def send_message(self, message):
        self.slack_client.rtm_send_message(self.id, message)


class User(object):
    def __init__(self, user_info, slack_client):
        self.slack_client = slack_client
        self.id = user_info["id"]
        self.name = user_info["name"]
        self.tag = '<@{}>'.format(self.id)
        self.connected = False
        self.dm_channel = None
        self.standups = []
        log.debug('Initialized {}'.format(self))


    def __repr__(self):
        return str('<{} id="{}" name="{}" channel="{}" c={}>'.format(
            self.__class__.__name__,
            self.id, self.name, self.dm_channel, len(self.standups)))


    def connect(self):
        res = self.slack_client.api_call('im.open', user=self.id)
        self.connected = True
        self.dm_channel = res['channel']['id']

        log.debug('Connected {}'.format(self))


    def send_message(self, message):
        assert self.dm_channel
        self.slack_client.rtm_send_message(self.dm_channel, message)



class StandupBot(object):
    def __init__(self, config):
        assert isinstance(config, ConfigParser)
        self.config = config
        self.token = self.config.get('slack', 'token')

        self.bot = None
        self.channels = {}
        self.users = {}

        self.slack_client = None
        self.mention_prefix = None

        self.last_ping = 0
        self.keepalive_timer = 3
        log.info('Bot initialized')


    def connect(self):
        log.debug('Connecting')
        self.slack_client = SlackClient(self.token)
        self.slack_client.rtm_connect()
        self.bot = self.slack_client.server.users.find(
            self.slack_client.server.username
            )
        self.mention_prefix = '<@{}>'.format(self.bot.id)
        log.info('Connected as {} [{}]'.format(self.bot.name, self.mention_prefix))


    def get_channel(self, channel_name):
        channel_object = self.slack_client.api_call('channels.info', channel=channel_name)
        if channel_object['ok'] is True:
            return Channel(channel_object['channel'], self.slack_client)

        # not a channel, probably a pvt group
        group_object = self.slack_client.api_call('groups.info', channel=channel_name)
        if group_object['ok'] is True:
            return Channel(group_object['group'], self.slack_client)

        assert False


    def get_user(self, user_name):
        user_object = self.slack_client.api_call('users.info', user=user_name)
        if not user_object['user']['is_bot']:
            return User(user_object['user'], self.slack_client)


    def keepalive(self):
        now = int(time.time())
        if now > self.last_ping + self.keepalive_timer:
            self.slack_client.server.ping()
            self.last_ping = now


    def start(self):
        self.connect()

        while True:
            self.keepalive()
            messages = self.slack_client.rtm_read()
            if len(messages):
                for response in messages:
                    self.handle_response(response)
            else:
                time.sleep(0.1)


    def parse_cmd(self, text):
        words = text.strip().split(' ', 1)
        cmd = words[0]
        msg = words[1] if len(words) > 1 else None
        return (cmd, msg)


    def handle_message(self, channel_name, message):
        if not type(message) is str and len(message) > 1:
            log.info('Bad message in {}'.format(channel_name))
            return

        cmd, msg = self.parse_cmd(message)
        active = True if channel_name in self.channels else False
        direct = True if channel_name[0] == 'D' else False
        mention = False

        # pay attention to '@bot COMMAND' messages
        if cmd == self.mention_prefix:
            mention = True
            cmd, msg = self.parse_cmd(msg)

        # simple query/response commands
        if direct or mention:
            if cmd in commands['help']:
                self.slack_client.rtm_send_message(channel_name,
                    _('help', name=self.bot.name)
                    )
                return
            elif cmd in commands['ping']:
                self.slack_client.rtm_send_message(channel_name, _('pong'))
                return

        if direct and active:
            # This is a user interacting with the bot directly.
            # Usually, this will be someone entering or editing
            # their status
            user = self.channels[channel_name]
            standup = user.standups[0]

            end = False
            ups = standup.updates[user.tag]
            done = ups.done
            blocked = ups.blocked
            goals = ups.goals
            stat = _('Ok')

            if msg and cmd in commands['done']:
                done.append(msg)

            elif msg and cmd in commands['blocked']:
                blocked.append(msg)

            elif msg and cmd in commands['goals']:
                goals.append(msg)

            elif cmd in commands['reset'] and msg in commands['done']:
                done.clear()

            elif cmd in commands['reset'] and msg in commands['blocked']:
                blocked.clear()

            elif cmd in commands['reset'] and msg in commands['goals']:
                goals.clear()

            elif cmd in commands['reset'] and msg is None:
                done.clear()
                blocked.clear()
                goals.clear()

            elif cmd in commands['reset']:
                stat = _('reset_what')

            elif cmd in commands['show']:
                user.send_message(_('preview', update=ups.display(user.tag)))

            elif cmd in commands['skip']:
                done = []
                blocked = []
                goals = []
                stat = _('Skipping')
                end = True

            elif cmd in commands['end']:
                stat = _('Thanks')
                end = True

            else:
                user.send_message(_('unknown_command'))
                return

            user.send_message(
                '{}; {}: _done:_ {}, _blocked:_ {}, _goals:_ {}'.format(
                    stat, standup.channel.name,
                    len(done), len(blocked), len(goals)))

            if end:
                log.debug('{} is done with {}'.format(user.name,
                    standup.channel.name))
                standup.channel.send_message(_('sat_down', user=user))
                standup.outstanding -= 1

                if standup.outstanding < 1:
                    standup.publish()
                    self.unlink(standup)

                self.sit_down(user, standup)

        elif direct:
            self.slack_client.rtm_send_message(channel_name, _('no_standup'))

        elif mention:
            if not active:
                if cmd in commands['start']:
                    log.info('Beginning standup in {}'.format(channel_name))
                    channel = self.get_channel(channel_name)

                    section = 'channel:{}'.format(channel.name)
                    ignore_users = []
                    if self.config.has_section(section):
                        if self.config.has_option(section, 'ignore'):
                            ignore_str = self.config.get(section, 'ignore')
                            ignore_users = [u.strip() for u in
                                    ignore_str.split(',')]
                            log.debug('Ignore: {}'.format(ignore_users))

                    standup = Standup(channel)
                    self.channels.update({channel_name: standup})
                    for uid in standup.channel.members:
                        if uid in self.users:
                            user = self.users[uid]

                        else:
                            user = self.get_user(uid)
                            if not user:
                                continue

                        if user.name in ignore_users:
                            log.info('Not adding {} to {}'.format(
                                user.name, standup.channel.name))
                            continue

                        if not user.connected:
                            user.connect()

                        if len(user.standups) < 1:
                            user.send_message(_('started', standup=standup))

                        if not user.dm_channel in self.channels:
                            self.channels.update({user.dm_channel: user})

                        if not uid in self.users:
                            self.users.update({uid: user})

                        user.standups.append(standup)
                        standup.add_user(user)

                    if standup.outstanding > 0:
                        standup.channel.send_message(_('standup_started', standup=standup))
                    else:
                        standup.channel.send_message(_('standup_empty', standup=standup))
                        log.error('Standup is empty!')
                        self.unlink(standup)

                else:
                    log.debug('bad cmd, inactive state: "{}"'.format(cmd))

            else:
                # In a channel with an active standup
                standup = self.channels[channel_name]

                if cmd in commands['start']:
                    standup.channel.send_message(_('standup_already', standup=standup))

                elif cmd in commands['cancel']:
                    log.info('Cancelling standup in {}'.format(channel_name))
                    standup.channel.send_message(_('standup_cancelled', standup=standup))
                    self.unlink(standup)

                elif cmd in commands['publish']:
                    standup.publish()
                    self.unlink(standup)

                else:
                    standup.channel.send_message(_('unknown_cmd'))
                    log.debug('bad cmd, active state: "{}"'.format(cmd))


    def handle_response(self, response):
        if "type" in response and "subtype" not in response:
            if "message" in response["type"]:
                try:
                    age = time.time() - float(response["ts"])
                    if age > 10.0:
                        log.warn('Skipping {}s old response: "{}"'.format(
                            age, str(response)))
                        return

                    log.debug(response)
                    self.handle_message(response["channel"], response["text"])
                except Exception as e:
                    logging.exception('Message handling failure.')


    def sit_down(self, user, standup):
        if standup in user.standups:
            log.debug('seating {}/{} in {}'.format(user.name,
                user.dm_channel, standup.channel.name))
            user.standups.pop(user.standups.index(standup))

            if len(user.standups) < 1:
                log.debug('done talking to {}'.format(user.name))
                self.channels.pop(user.dm_channel)
                self.users.pop(user.id)

            else:
                log.debug('alert {} about next standup'.format(user.name))
                next_standup = user.standups[0]
                user.send_message(_('next', standup=next_standup))


    def unlink(self, standup):
        log.debug('unlink {}'.format(standup.channel.name))
        for user in standup.users:
            if user.dm_channel in self.channels:
                user.send_message(_('standup_ended', standup=standup))
            self.sit_down(user, standup)
        self.channels.pop(standup.channel.id)



def main():
    import argparse

    here = os.path.dirname(__file__)
    default_file = os.path.abspath("{}/{}".format(here, 'conf.ini'))

    parser = argparse.ArgumentParser(description='SLack Agile Not Dangerously Evil Robot')

    log_group = parser.add_mutually_exclusive_group()
    log_group.add_argument('-v', '--verbose', action='count', default=0,
            dest='verbosity')
    log_group.add_argument('-q', '--quiet', action='count', default=0,
            dest='quiet')
    parser.add_argument('config_file', action='store', type=open,
            default=default_file)
    args = parser.parse_args()

    verbosity = min(2, args.verbosity)
    quiet = min(2, args.quiet)
    log_level = 30 - (verbosity*10) + (quiet*10) # yeah, I know
    logging.basicConfig(level=log_level)

    config = ConfigParser()
    config.read_file(args.config_file)
    bot = StandupBot(config)

    while True:
        try:
            bot.start()
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            logging.exception('Bot failed')
    sys.exit(1)



# Startup
if __name__ == '__main__':
    main()
