import logging
import os
import sys
import time

from pprint import pprint
from slackclient import SlackClient

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# TODO:
# ignore users in a channel (conf)
# multiple standups



# bot.users = { user_id : user_object }
#
# bot.channel = { dm_channel : user_id } 
#
#


messages = {
    'help' : """Standup management (from a channel or pvt group):
`@{name} start`       Start a standup. I will message everyone in the channel
`@{name} cancel`      Cancel a standup that has been started
`@{name} publish`     Publish a standup that has been started
 
Status entry (via direct message):
`d: [...]`            Something you have done since the last standup
`b: [...]`            A blocker that prevented you from getting something done
`g: [...]`            A goal for today
`skip`                Nothing for today, diposes of anything you've entered
`end`                 When you've no more to say
`reset [...]`         Reset a status category, or all
 
Example:
 Group:
 <boss> @{name} start
 <{name}> group standup started.
 
 DM:
 <{name}>  @{name} Standup time for group!
 <you> d: finished documenting all the things
 <{name}> done: 1, blocked: 0, goals: 0
 <you> g: find more thing to document
 <{name}> done: 1, blocked: 0, goals: 1
 <you> end
 <{name}> Thanks; done: 1, blocked: 0, goals: 1
 
 Group:
 <{name}> @you sat down.
 <boss> @{name} publish
 <{name}> ...
""",

    'started' : """Standup time for {standup.channel.name}!
 
Remember to enter:
 1) Things you did since the last standup (`d: ...`)
 2) What blockers you ran into (`b: ...`)
 3) Your goals for today (`g: ...`)
 
Type `end` when you're finished, or `help` if you need.
""",

    'no_standup' : 'No active standup.',

    'pong' : 'pong',

    'standup_started' : '{standup.channel.name} standup started.',
    'standup_ended' : '*{standup.channel.name} standup ended!',
    'standup_cancelled' : '{standup.channel.name} standup cancelled.',
    'standup_already' : '{standup.channel.name} standup already started.',

    'sat_down': '{user.tag} sat down.',

    'unknown_cmd' : 'Bad command. Did you mean `start` or `publish`?',
    }


commands = {
    'blocked': ('b:', 'blocked', 'block', 'stuck'),
    'done': ('d:', 'did', 'finished', 'completed'),
    'end': ('end'),
    'goals': ('g:', 'goal', 'will', 'shall'),
    'reset': ('reset'),
    'skip': ('skip', 'no'),
    }


def _(key, **kwds):
    return str(messages[key]).format(**kwds)


class Standup(object):
    def __init__(self, channel):
        log.debug('Standup initialized in {}'.format(channel.name))
        #self.slack_client = slack_client
        self.channel = channel
        #self.channel = self.get_channel_info(channel)
        self.updates = {}
        self.users = []

        # maybe this is in a separate function after
        # the users are loaded?
        # so we know who to skip and how?
        for member in self.channel.members:
            user = self.get_user_info(member)
            if user:
                self.users.append(user)
                self.updates.update({user.tag: {
                    'blocked': [],
                    'done': [],
                    'goals': [],
                    }})

        self.outstanding = len(self.users)


#    def get_channel_info(self, channel_name):
#        channel_object = self.slack_client.api_call("channels.info", channel=channel_name)
#        if channel_object['ok'] is True:
#            return Channel(channel_object["channel"], self.slack_client)
#
#        group_object = self.slack_client.api_call("groups.info", channel=channel_name)
#        if group_object['ok'] is True:
#            return Channel(group_object['group'], self.slack_client)
#
#        assert False


    def get_user_info(self, user_name):
        #user_object = self.slack_client.api_call('users.info', user=user_name)
        user_object = self.channel.slack_client.api_call('users.info', user=user_name)
        if not user_object['user']['is_bot']:
            #return User(user_object['user'], self.slack_client)
            return User(user_object['user'], self.channel.slack_client)


    def publish(self):
        log.info('Publishing standup in {}'.format(self.channel.name))
        res = 'Standup for {}:\n \n'.format(self.channel.name)
        for tag, ups in self.updates.items():
            i = len(ups['done']) + len(ups['blocked']) + len(ups['goals'])
            if i < 1:
                res += '{} - *None*\n \n'.format(tag)
            else:
                res += '{}:'.format(tag)
                if len(ups['done']):
                    res += '\n  Done:\n'
                    res += '\n'.join(['    * {}'.format(m) for m in ups['done']])

                if len(ups['blocked']):
                    res += '\n  Blocked:\n'
                    res += '\n'.join(['    * {}'.format(m) for m in ups['blocked']])

                if len(ups['goals']):
                    res += '\n  Goals:\n'
                    res += '\n'.join(['    * {}'.format(m) for m in ups['goals']])
        self.channel.send_message(res + '\n')



class Channel(object):
    def __init__(self, channel_info, slack_client):
        self.slack_client = slack_client
        self.id = channel_info["id"]
        self.name = channel_info["name"]
        self.members = channel_info["members"]

        log.debug('Channel Initialized, ID: {} Name: {} Members: {}'.format(self.id, self.name, self.members))


    def send_message(self, message):
        self.slack_client.rtm_send_message(self.id, message)


class User(object):
    def __init__(self, user_info, slack_client):
        self.slack_client = slack_client
        self.id = user_info["id"]
        self.name = user_info["name"]
        self.tag = '<@{}>'.format(self.id)
        self.dm_channel = None


    def connect(self):
        res = self.slack_client.api_call('im.open', user=self.id)
        self.dm_channel = res['channel']['id']

        log.debug('User Initialized, ID: {} Name {} DM {}'.format(self.id, self.name, self.dm_channel))


    def send_message(self, message):
        assert self.dm_channel
        self.slack_client.rtm_send_message(self.dm_channel, message)



class StandupBot(object):
    def __init__(self, token):
        self.token = token
        self.bot = None
        self.mention_prefix = None

        self.channels = {}
        self.users = {}

        self.slack_client = None

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
        channel_object = self.slack_client.api_call("channels.info", channel=channel_name)
        if channel_object['ok'] is True:
            return Channel(channel_object["channel"], self.slack_client)

        group_object = self.slack_client.api_call("groups.info", channel=channel_name)
        if group_object['ok'] is True:
            return Channel(group_object['group'], self.slack_client)

        assert False

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
                time.sleep(0.5)


    def parse_cmd(self, text):
        tokens = text.strip().split(' ', 1)
        cmd = tokens[0]
        msg = tokens[1] if len(tokens) > 1 else None
        return (cmd, msg)


    def handle_message(self, channel_name, message):
        if not type(message) is str and len(message) > 1:
            log.info('Bad message in {}'.format(channel_name))
            return

        cmd, msg = self.parse_cmd(message)
        active = True if channel_name in self.channels else False
        direct = True if channel_name[0] == 'D' else False
        mention = False

        if cmd == self.mention_prefix:
            mention = True
            cmd, msg = self.parse_cmd(msg)

        # simple query/response commands
        if direct or mention:
            if cmd == 'help':
                self.slack_client.rtm_send_message(channel_name,
                    _('help', name=self.bot.name)
                    )
                return
            elif cmd == 'ping':
                self.slack_client.rtm_send_message(channel_name, _('pong'))
                return

        if active:
            # TODO - this has to come from the user object
            standup = self.channels[channel_name]

        if direct and active:
            user = self.users[channel_name]

            end = False
            done = standup.updates[user.tag]['done']
            blocked = standup.updates[user.tag]['blocked']
            goals = standup.updates[user.tag]['goals']
            stat = 'Ok'

            if msg and cmd in commands['done']:
                done.append(msg)

            elif msg and cmd in commands['blocked']:
                blocked.append(msg)

            elif msg and cmd in commands['goals']:
                goals.append(msg)

            elif cmd in commands['reset'] and msg == 'done':
                done = []

            elif cmd in commands['reset'] and msg == 'blocked':
                blocked = []

            elif cmd in commands['reset'] and msg == 'goals':
                goals = []

            elif cmd in commands['reset'] and msg is None:
                done = []
                blocked = []
                goals = []

            elif cmd in commands['reset']:
                stat = 'Huh?'

            elif cmd in commands['skip']:
                done = []
                blocked = []
                goals = []
                stat = 'Skipping'
                end = True

            elif cmd in commands['end']:
                stat = 'Thanks'
                end = True

            if end:
                log.info('{} is done'.format(user.name))
                standup.channel.send_message(_('sat_down', user=user))
                standup.outstanding -= 1
                self.users.pop(channel_name)
                self.channels.pop(channel_name)

                if standup.outstanding < 1:
                    standup.publish()
                    self.unlink(standup)

            else:
                stat = 'Bad command'

            user.send_message('{}; done: {}, blocked: {}, goals: {}'.format(stat, len(done), len(blocked), len(goals)))

        elif direct:
            self.slack_client.rtm_send_message(channel_name, _('no_standup'))

        elif mention:
            if not active:
                if cmd == 'start':
                    log.info('Beginning standup in {}'.format(channel_name))
                    channel = self.get_channel(channel_name)
                    #standup = Standup(channel_name, self.slack_client)
                    standup = Standup(channel)
                    self.channels.update({channel_name: standup})
                    for user in standup.users:
                        user.connect()
                        user.send_message(_('started', standup=standup))
                        self.channels.update({user.dm_channel: standup})
                        self.users.update({user.dm_channel: user})
                    standup.channel.send_message(_('standup_started', standup=standup))

                else:
                    log.debug('bad cmd, inactive state: "{}"'.format(cmd))

            else:
                if cmd == 'start':
                    standup.channel.send_message(_('standup_already', standup=standup))

                elif cmd == 'cancel':
                    log.info('Cancelling standup in {}'.format(channel_name))
                    standup.channel.send_message(_('standup_cancelled', standup=standup))
                    self.unlink(standup)

                elif cmd == 'publish':
                    standup.publish()
                    self.unlink(standup)

                else:
                    standup.channel.send_message(_('unknown_cmd'))
                    log.debug('bad cmd, active state: "{}"'.format(cmd))


    def handle_response(self, response):
        if "type" in response and "subtype" not in response:
            if "message" in response["type"]:
                try:
                    log.debug(response)
                    self.handle_message(response["channel"], response["text"])
                except Exception as e:
                    logging.exception('Message handling failure.')


    def unlink(self, standup):
        for user in standup.users:
            if user.id in self.users:
                self.users.pop(user.id)
            if user.dm_channel in self.channels:
                user.send_message(_('standup_ended', standup=standup))
                self.channels.pop(user.dm_channel)
        self.channels.pop(standup.channel.id)


# Startup
if __name__ == '__main__':
    import argparse

    # here = os.path.dirname(__file__)
    # conf = os.path.abspath("{}/{}".format(here, 'conf.yml'))
    # config = yaml.load(open(conf, 'r'))
    # bot = StandupBot(config["SLACK_TOKEN"])

    
    token = 'xoxb-11985753573-dm8f0dxq6wHsYC3qNG39w6IN'
    bot = StandupBot(token)

    while True:
        try:
            bot.start()
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            logging.exception('Bot failed')
