# slander

_SLack Agile Not Dangerously Evil Robot_

What makes it "not dangerously evil?"

* No database
* No data sharing
* NLP-esque (no funky command syntax)

Slander (yeah, I know, "libel" would have made more sense, but it was hard enough to make "slander" work as a name) is a dirt-simple Slack bot for running Agile style standups. It tries not to over-complicate anything because there's simply no need for much complexity in what it tries to do.

It was written because I wanted to do standups in Slack, but I didn't like any of the existing options. Hosted tools exfiltrate data by design, and I don't trust 'em. The various self-hosted bots I found didn't behave the way I wanted them to, and required too much setup. Slander can be stood up on a server or cloud node with monitoring and a watchdog, or you can just run it from a workstation when you need to.

#### It's Python, so install it with `pip`

    $ pip install slander

Create a simple [configparser](https://docs.python.org/3/library/configparser.html#configparser.ConfigParser "ConfigParser") compatible config file like so:

    [slack]
    token = xoxo-abcdefghijk-123456789876543212345678
    [channel:general]
    ignore = john.doe, jane.doe

And then just point the `slanderbot` CLI tool at it:

    $ slanderbot ./config.init

#### Interaction with the bot is fairly natural.

First, someone tells the bot it's go-time in some group chat:

    <scrum_master> @slander start
    <slander> Okay, group standup started.

Then the bot looks up all of the users in the group and messages them to start sending status:

    <slander>  Standup started for group.
    <you> d: finished documenting all the things
    <slander> done: 1, blocked: 0, goals: 0
    <you> g: find more thing to document
    <slander> done: 1, blocked: 0, goals: 1
    <you> end
    <slander> Thanks; done: 1, blocked: 0, goals: 1

Back in the group chat, you can either tell the bot to publish or cancel the standup at any point. Or, it will publish automatically after everyone involved has "sat down." 

    <slander> @you sat down.
    <scrum_master> @bot publish
    <slander> ...

You can write more naturally when interacting with the bot if you want. It will recognize certain different prefix words instead of `d:` and the like. For example:

    <slander>  Standup started for group.
    <you> completed documentation for all the things
    <slander> done: 1, blocked: 0, goals: 0
    <you> will review more things to document
    <slander> done: 1, blocked: 0, goals: 1

The full listing of valid prefix words is in the lang.py file, which serves as a primitive stub for what could eventually be proper I18N/L10N support if you want to have a bot that speaks a language other than English.
