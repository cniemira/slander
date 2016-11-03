messages = {
    'help' : """\
Standup management (from a channel or pvt group):
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
    <{name}> Okay, group standup started.
 
  direct-message with me:
    <{name}> Standup started for group.
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

    'cmd_error' : 'Uh oh. I wasn\'t able do to that.',

    'next' : 'Another standup, for {standup.channel.name}, also started.',

    'no_standup' : 'No active standup.',

    'pong' : 'pong',

    'preview': """\
Preview:
{update}
""",

    'reset_what': 'Reset what?',

    'sat_down': '{user.name} sat down.',

    'standup_already' : '{standup.channel.name} standup already started.',
    'standup_cancelled' : '{standup.channel.name} standup cancelled.',
    'standup_contains' : '{user.name} is already in {standup.channel.name}',
    'standup_ended' : '{standup.channel.name} standup ended!',
    'standup_empty' : '{standup.channel.name} has no un-ignored members.',
    'standup_for': '*Standup for {standup.channel.name}*',
    'standup_started' : 'Okay, {standup.channel.name} standup started.',

    'rejoined' : 'Your previous staus has been clobbered.',

    'started' : """\
Standup started for {standup.channel.name}.
Use `d: ...`, `b: ...`, `g: ...` to report tasks done, blockers, and goals.
Type `end` when you're finished, or `help` if you need.
""",

    'status_response': '{status}; channel:{standup.channel.name}, done:{n_done}, blocked:{n_blocked}, goals:{n_goals}',

    'unknown_cmd' : 'Bad command. Try `help` if you need it.',

    'uptime' : """\
Details for {bot.bot.name}:
  
current time: {now}
started at: {bot.initialized_at}
last connect: {bot.last_connected}
last ping: {bot.last_ping}
last pong: {bot.last_pong}
  
current error counter: {bot.error_count}
total connections: {bot.connect_count}
""",

    'Done': 'Done',
    'Blocked': 'Blocked',
    'Goals': 'Goals',
    'None': '*None*',
    'Ok': 'Ok',
    'Skipping': 'Skipping you',
    'Thanks': 'Thanks',
    }


commands = {
    'blocked': ('b', 'b:', 'blocked', 'block', 'stuck'),
    'cancel': ('cancel',),
    'done': ('d', 'd:', 'did', 'finished', 'completed'),
    'echo': ('echo',),
    'end': ('end',),
    'goals': ('g', 'g:', 'goal', 'will', 'shall'),
    'help': ('help',),
    'join': ('join', 'add'),
    'reset': ('reset',),
    'skip': ('skip', 'no'),
    'show': ('show', 'what'),
    'start': ('start', 'begin'),
    'ping': ('ping',),
    'publish': ('publish',),
    'uptime': ('uptime',),
    }


def _(key, **kwds):
    return str(messages[key]).format(**kwds)
