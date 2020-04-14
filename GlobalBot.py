#GlobalBot.py

import os
import discord
import sqlite3
import inspect
import sys
import random
import re
import time
from datetime import datetime
from datetime import date
from dotenv import load_dotenv
from github import Github
import base64
from urlextract import URLExtract
import asyncio
import threading

#command class
class command:
    trigger = ''
    description = ''
    function = ''
    userCommand = False
    arguments = None
    admin = False

    def __init__(self, trigger, description, function, userCommand = False, arguments = None, admin = False):
        self.trigger = trigger
        self.description = description
        self.function = function
        self.userCommand = userCommand
        self.arguments = arguments
        self.admin = admin

#returns and open connection to the database
def openConnection():
    con = sqlite3.connect(database)
    return con

#closes the given database connection
def closeConnection(con):
    con.close()

#prints a message in the shell and adds it to BOT_LOG
def addLog(message, function = None, command = None, arguments = None, targetUser = None, targetUserID = None, server = None, serverID = None, channel = None, channelID = None, invokedUser = None, invokedUserID = None, invokedUserDiscriminator = None, invokedUserDisplayName = None, targetUserDiscriminator = None, targetUserDisplayName = None, messageID = None):
    con = openConnection()
    cur = con.cursor()
    print(f'{datetime.now()}: {message}')
    data = [datetime.now(), message, server, serverID, channel, channelID, invokedUser, invokedUserID, command, arguments, function, targetUser, targetUserID, invokedUserDiscriminator, invokedUserDisplayName, targetUserDiscriminator, targetUserDisplayName, messageID]
    cur.execute('insert into BOT_LOG (LOG_TIME, MESSAGE, SERVER, SERVER_ID, CHANNEL, CHANNEL_ID, INVOKED_USER, INVOKED_USER_ID, COMMAND, ARGUMENTS, FUNCTION, TARGET_USER, TARGET_USER_ID, INVOKED_USER_DISCRIMINATOR, INVOKED_USER_DISPLAY_NAME, TARGET_USER_DISCRIMINATOR, TARGET_USER_DISPLAY_NAME, MESSAGE_ID) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', data)
    con.commit()
    closeConnection(con)

#save a user added command to USER_COMMANDS
def saveUserCommand(message, command, commandMessage, textToSpeech):
    con = openConnection()
    cur = con.cursor()
    data = [command, commandMessage, textToSpeech, message.guild.name, message.guild.id, message.author.name, message.author.id, message.channel.name, message.channel.id, datetime.now()]
    cur.execute('insert into USER_COMMANDS (TRIGGER, MESSAGE, TEXT_TO_SPEECH, SERVER, SERVER_ID, USER_ADDED, USER_ADDED_ID, CHANNEL_ADDED, CHANNEL_ADDED_ID, ADDED_TIMESTAMP) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', data)
    con.commit()
    closeConnection(con)

#executes a select statement from the database, returns the result
def select(SQL):
    addLog(f'Executing select SQL [{SQL}]', inspect.currentframe().f_code.co_name)
    con = openConnection()
    cur = con.cursor()
    cur.execute(SQL)
    x = cur.fetchall() 
    closeConnection(con)
    return x

#loads user commands from USER_COMMANDS
def loadUserCommands():
    addLog('Loading user commands...', inspect.currentframe().f_code.co_name)
    userMessages = select('select * from USER_COMMANDS')
    for x in userMessages:
        if x[3]:
            commands.append(command(x[1], f'Sends the text to speech message "{x[2]}"', 'sendMessage', True, [x[2], x[3]]))
        else:
            commands.append(command(x[1], f'Sends the message "{x[2]}"', 'sendMessage', True, [x[2], x[3]]))

#saves a message to MESSAGES
def saveMessage(message):
    addLog(f'Receiving {message.guild} message: {message.id}', inspect.currentframe().f_code.co_name, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)

    con = openConnection()
    cur = con.cursor()

    if message.type == 'call':
        call = message.call
    else:
        call = None

    data = [message.tts, str(message.type), str(message.author), str(message.content), message.nonce, str(message.embeds), str(message.channel), call, message.mention_everyone, str(message.mentions), str(message.channel_mentions), str(message.role_mentions), message.id, message.webhook_id, str(message.attachments), message.pinned, str(message.flags), str(message.reactions), str(message.activity), message.application, str(message.guild), str(message.raw_mentions), str(message.raw_channel_mentions), str(message.raw_role_mentions), message.clean_content, message.created_at, message.edited_at, message.jump_url, str(message.is_system()), message.system_content, str(message), message.guild.id, message.author.id, message.author.discriminator, message.author.display_name, message.channel.id]

    cur.execute('insert into MESSAGES (TTS, TYPE, AUTHOR, CONTENT, NONCE, EMBEDS, CHANNEL, CALL, MENTION_EVERYONE, MENTIONS, CHANNEL_MENTIONS, ROLE_MENTIONS, ID, WEBHOOK_ID, ATTACHMENTS, PINNED, FLAGS, REACTIONS, ACTIVITY, APPLICATION, GUILD, RAW_MENTIONS, RAW_CHANNEL_MENTIONS, RAW_ROLE_MENTIONS, CLEAN_CONTENT, CREATED_AT, EDITED_AT, JUMP_URL, IS_SYSTEM, SYSTEM_CONTENT, RAW, GUILD_ID, AUTHOR_ID, AUTHOR_DISCRIMINATOR, AUTHOR_DISPLAY_NAME, CHANNEL_ID) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', data)
    con.commit()
    closeConnection(con)

#chunks a string into pieces of size length
def chunkstring(string, length):
    return (string[0+i:length+i] for i in range(0, len(string), length))

#chunks a string into pieces of size length, but respects line breaks
def chunkStringNewLine(string, length):
    splitString = string.split('\n')
    returnStrings = []
    tempString = ''
    for i in splitString:
        if len(i) + len(tempString) > length:
            returnStrings.append(tempString)
            tempString = i
        else:
            tempString = tempString + '\n' +  i
    returnStrings.append(tempString)
    return returnStrings

#sends a message to the channel
async def sendMessage(triggerMessage, sendMessage, textToSpeech = False, deleteAfter = None, embedItem = None, embedItems = None, triggeredCommand = None):
    addLog(f'''Sending message "{sendMessage}" to channel {triggerMessage.channel} in server {triggerMessage.guild}, {triggerMessage.guild.id}.''', inspect.currentframe().f_code.co_name, server = triggerMessage.guild.name, serverID = triggerMessage.guild.id, channel = triggerMessage.channel.name, channelID = triggerMessage.channel.id, invokedUser = triggerMessage.author.name, invokedUserID = triggerMessage.author.id, invokedUserDiscriminator = triggerMessage.author.discriminator, invokedUserDisplayName = triggerMessage.author.nick, command = triggeredCommand)

    if len(sendMessage) > 2000:
        x = chunkStringNewLine(sendMessage, 2000)
        for i in x:
            await triggerMessage.channel.send(i, tts = textToSpeech, delete_after = deleteAfter, embed = embedItem)
    else:
        await triggerMessage.channel.send(sendMessage, tts = textToSpeech, delete_after = deleteAfter, embed = embedItem)

#sends a message to the channel
async def sendChannelMessage(message, channelID, textToSpeech = False, deleteAfter = None, embedItem = None, embedItems = None):
    x = client.get_channel(channelID)
    addLog(f'''Sending message "{message}" to channel {x.name} in server {x.guild}, {x.guild.id}.''', inspect.currentframe().f_code.co_name, server = x.guild.name, serverID = x.guild.id, channel = x.name, channelID = x.id)

    if len(message) > 2000:
        x = chunkstring(message, 2000)
        for i in x:
            await x.send(i, tts = textToSpeech, delete_after = deleteAfter, embed = embedItem)
    else:
        await x.send(message, tts = textToSpeech, delete_after = deleteAfter, embed = embedItem)

#lists available commands
async def help(message, trigger):
    addLog(f'Listing commands', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
    x = ''
    s = filter(filterStandardFunctions, commands)
    for i in s:
        x = x + f'''**!{i.trigger.ljust(20)}** - \t{i.description}\n'''
    await sendMessage(message, x, deleteAfter = 30, triggeredCommand = trigger)

#lists available user commands
async def listUserCommands(message, trigger):
    addLog(f'Listing user commands', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
    x = ''
    s = filter(filterUserFunctions, commands)
    extractor = URLExtract()
    for i in s:
        description = i.description
        urls = extractor.find_urls(i.description)
        for url in urls:
            description = description.replace(url, f'<{url}>')
        x = x + f'''**!{i.trigger.ljust(20)}** - \t{description}\n'''
    await sendMessage(message, x, deleteAfter = 30, triggeredCommand = trigger)

#restart the bot
async def restart(message, trigger):
    addLog(f'Restarting bot', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
    await sendMessage(message, 'Restarting bot...',  deleteAfter = 20, triggeredCommand = trigger)
    
    #wait for message cleanup
    os.execlp('python3', '-m', '/root/GlobalBot/GlobalBot.py')
    sys.stdout.flush()
    exit()

#add a new simple message command
async def addUserCommand(message, commandTrigger):
    x = removeCommand(message.content, f'!{commandTrigger}')
    x = x.split(',')
    if len(x) >= 2:
        trigger = x.pop(0).strip().lower()
        spaceTest = trigger.split(' ')
        if len(spaceTest) > 1:
            await sendMessage(message, 'Invalid command name. Command names cannot include spaces',  deleteAfter = 20, triggeredCommand = commandTrigger)
        else:
            messageToSend = ','
            messageToSend = messageToSend.join(x).strip()
            for i in commands:
                if trigger == i.trigger:
                    await sendMessage(message, 'This command already exists.',  deleteAfter = 20, triggeredCommand = commandTrigger)
                    return
            if messageToSend.startswith('/tts'):
                messageToSend = messageToSend.replace('/tts', '')
                tts = True
                z = 'text to speech '
            else:
                tts = False
                z = ''
            commands.append(command(trigger, f'''Sends the {z}message "{messageToSend}"''', 'sendMessage', True, [messageToSend, tts]))
            await sendMessage(message, f'Adding user command [{trigger}]',  deleteAfter = 20, triggeredCommand = trigger)
            saveUserCommand(message, trigger, messageToSend, tts)
            addLog(f'Adding user command [{trigger}]', inspect.currentframe().f_code.co_name, commandTrigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
    else:
        await sendMessage(message, 'Invalid parameters. Format is !addmessagecommand command, message',  deleteAfter = 20, triggeredCommand = commandTrigger)

#filters command list to only user functions
def filterUserFunctions(command):
    return command.userCommand

#filters command list to only admin functions
def filterAdminFunctions(command):
    return command.admin

#filters command list to only admin functions
def filterStandardFunctions(command):
    return (not command.userCommand and not command.admin)

#deletes a user command from the database
def deleteUserCommandFromDatabase(serverID, command):
    con = openConnection()
    cur = con.cursor()
    cur.execute('delete from USER_COMMANDS where SERVER_ID = ? and TRIGGER = ?', [serverID, command])
    con.commit()
    closeConnection(con)

#delete an existing user command
async def deleteUserCommand(message, commandTrigger):
    x = removeCommand(message.content, f'!{commandTrigger}')

    s = filter(filterUserFunctions, commands)
    for y in s:
        if y.trigger.lower() == x.lower():
            commands.remove(y)
            del y
            deleteUserCommandFromDatabase(message.guild.id, x.lower())
            addLog(f'Deleting user command [{x}] from server {message.guild.name}', inspect.currentframe().f_code.co_name, commandTrigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
            await sendMessage(message, f'Deleting user command [{x}]',  deleteAfter = 20, triggeredCommand = commandTrigger)
            return
    await sendMessage(message, f'Command [{x}] not found',  deleteAfter = 20, triggeredCommand = commandTrigger)

#send a random pinned message
async def sendRandomPinnedMessage(message, trigger):
    pin = await message.channel.pins()
    if len(pin) == 0:
        await sendMessage(message, 'This server has no pinned messages.', deleteAfter = 20, triggeredCommand = trigger)
    else:
        x = random.randrange(0, len(pin), 1)
        addLog(f'Sending random pinned message {pin[x]}', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
        await sendMessage(message, pin[x].jump_url, triggeredCommand = trigger)

#kicks a user out of voice chat
async def kickUser(message, trigger):
    users = message.mentions
    if users == []:
        await sendMessage(message, 'Invalid format. Correct format is !kick @user.', deleteAfter = 20, triggeredCommand = trigger)
    else:
        for x in users:
            if x.voice == None:
                await sendMessage(message, f'User {x.display_name} is not currently in a voice channel.', deleteAfter = 10, triggeredCommand = trigger)
            else:
                addLog(f'Kicking user {x.display_name} from voice', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, targetUser = x.name, targetUserID = x.id, targetUserDiscriminator = x.discriminator, targetUserDisplayName = x.display_name, messageID = message.id)
                await x.move_to(None)
                await sendMessage(message, f'Kicking user {x.display_name} from voice', deleteAfter = 10, triggeredCommand = trigger)

#kicks a random user out of voice chat
async def roulette(message, trigger):
    channels = message.guild.voice_channels
    x = []
    for i in channels:
        for j in i.members:
            x.append(j)
    if len(x) > 0:
        userIndex = random.randrange(0, len(x), 1)
        await sendMessage(message, f'Kicking user {x[userIndex].display_name} from voice', deleteAfter = 10, triggeredCommand = trigger)
        addLog(f'Kicking user {x[userIndex].display_name} from voice', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, targetUser = x[userIndex].name, targetUserID = x[userIndex].id, targetUserDiscriminator = x[userIndex].discriminator, targetUserDisplayName = x[userIndex].display_name, messageID = message.id)
        await x[userIndex].move_to(None)  
    else:
        await sendMessage(message, 'There are no users currently in voice chat', deleteAfter = 10, triggeredCommand = trigger)  

#remove the command from the message
def removeCommand(message, command):
    redata = re.compile(re.escape(command), re.IGNORECASE)
    return redata.sub('', message).strip()

#sets the bots status
async def setStatus(message, trigger):
    y = discord.Game(removeCommand(message.content, f'!{trigger}'))
    await sendMessage(message, f'Setting status to "{y}"', deleteAfter = 10, triggeredCommand = trigger)
    addLog(f'Setting status to "{y}"', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
    await client.change_presence(status = discord.Status.online, activity = y)

#sets the bots status
async def setName(message, trigger):
    y = removeCommand(message.content, f'!{trigger}')

    if len(y) > 32:
        await sendMessage(message, f'Display names must be 32 characters or less.', deleteAfter = 10, triggeredCommand = trigger)
    else:
        await sendMessage(message, f'Setting display name to "{y}"', deleteAfter = 10, triggeredCommand = trigger)
        addLog(f'Setting display name to "{y}"', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
        member = message.guild.get_member(client.user.id)
        await member.edit(nick = y)

#sends a user to the tier 1 voice chat
async def demote(message, trigger):
    users = message.mentions
    if users == []:
        await sendMessage(message, 'Invalid format. Correct format is !demote @user.', deleteAfter = 20, triggeredCommand = trigger)
    else:
        for x in users:
            if x.voice == None:
                await sendMessage(message, f'User {x.display_name} is not currently in a voice channel.', deleteAfter = 10, triggeredCommand = trigger)
            else:
                tier1 = getChannelByName(message.guild, 'Tier 1')
                if tier1 == None:
                    await sendMessage(message, 'There is currently no Tier 1 voice channel.', deleteAfter = 10, triggeredCommand = trigger)
                else:
                    addLog(f'Moving user {x.display_name} to Tier 1 voice channel.', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, targetUser = x.name, targetUserID = x.id, targetUserDiscriminator = x.discriminator, targetUserDisplayName = x.display_name, messageID = message.id)
                    await x.move_to(tier1)
                    await sendMessage(message, f'Demoting user {x.display_name} to Tier 1.', deleteAfter = 10, triggeredCommand = trigger)

#gets a channel by name
def getChannelByName(server, name):
    for i in server.voice_channels:
        if i.name == name:
            return i
    return None

#grabs the top stored message id
def grabTopStoredMesage(guild):
    x = select(f'select created_at from MESSAGE_HISTORY where GUILD_ID = {guild.id} order by created_at desc limit 1')
    if x == []:
        return None
    else:
        return x[0][0]

#launches a backup of the server
async def backup(message, trigger):
    recordLimit = 1000

    addLog(f'Backing up server {message.guild.name}...', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
    await sendMessage(message, f'Backing up server {message.guild.name}...', deleteAfter = 10, triggeredCommand = trigger)
    startTime = time.time()
    top = grabTopStoredMesage(message.guild)
    records = []
    attachments = []
    reactions = []

    for i in message.guild.text_channels:
        if top == None:
            history = await i.history(limit = None, oldest_first = True).flatten()
        else:
            history = await i.history(limit = None, oldest_first = True, after = datetime.strptime(top, '%Y-%m-%d %H:%M:%S.%f')).flatten()
        for j in history:
            if message.type == 'call':
                call = message.call
            else:
                call = None
            records.append([j.tts, str(j.type), str(j.author), str(j.content), j.nonce, str(j.embeds), str(j.channel), call, j.mention_everyone, str(j.mentions), str(j.channel_mentions), str(j.role_mentions), j.id, j.webhook_id, str(j.attachments), j.pinned, str(j.flags), str(j.reactions), str(j.activity), j.application, str(j.guild), str(j.raw_mentions), str(j.raw_channel_mentions), str(j.raw_role_mentions), j.clean_content, j.created_at, j.edited_at, j.jump_url, str(j.is_system()), j.system_content, str(j), j.guild.id, j.author.id, j.author.discriminator, j.author.display_name, j.channel.id])

            #add attachments
            for a in j.attachments:
                #rawData = await a.read()
                rawData = None
                attachments.append([a.id, a.size, a.height, a.width, a.filename, a.url, a.proxy_url, a.is_spoiler(), rawData, j.id, str(a), message.guild.id])

            #save reactions
            for r in j.reactions:
                for u in await r.users().flatten():
                    if r.custom_emoji:
                        name = r.emoji.name
                        id = r.emoji.id
                        require_colons = r.emoji.require_colons
                        animated = r.emoji.animated
                        managed = r.emoji.managed
                        guild_id = r.emoji.guild_id
                        available = r.emoji.available
                        if r.emoji.user != None:
                            user_name = r.emoji.user.name
                            user_id =  r.emoji.user.id
                            user_discriminator = r.emoji.user.discriminator
                            user_display_name = r.emoji.user.display_name
                        else:
                            user_name = None
                            user_id =  None
                            user_discriminator = None
                            user_display_name = None
                        created_at = r.emoji.created_at
                        url = r.emoji.url
                        roles = r.emoji.roles
                        is_usable = r.emoji.is_usable()
                        unicode = None
                    else:
                        name = None
                        id = None
                        require_colons = None
                        animated = None
                        managed = None
                        guild_id = None
                        available = None
                        user_name = None
                        user_id = None
                        user_discriminator = None
                        user_display_name = None
                        created_at = None
                        url = None
                        roles = None
                        is_usable = None
                        unicode = r.emoji

                    reactions.append([name, j.id, r.custom_emoji, None, u.name, u.discriminator, u.display_name, id, require_colons, animated, managed, guild_id, available, user_name, u.id, user_id, user_discriminator, user_display_name, created_at, str(url), str(roles), is_usable, str(r), str(r.emoji), r.me, unicode, message.guild.id])

            if len(records) + len(attachments) + len(reactions) > recordLimit:
                addLog(f'Record limit reached, saving partial and continuing...', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)

                con = openConnection()
                cur = con.cursor()

                #save messages
                cur.executemany('insert into MESSAGE_HISTORY (TTS, TYPE, AUTHOR, CONTENT, NONCE, EMBEDS, CHANNEL, CALL, MENTION_EVERYONE, MENTIONS, CHANNEL_MENTIONS, ROLE_MENTIONS, ID, WEBHOOK_ID, ATTACHMENTS, PINNED, FLAGS, REACTIONS, ACTIVITY, APPLICATION, GUILD, RAW_MENTIONS, RAW_CHANNEL_MENTIONS, RAW_ROLE_MENTIONS, CLEAN_CONTENT, CREATED_AT, EDITED_AT, JUMP_URL, IS_SYSTEM, SYSTEM_CONTENT, RAW, GUILD_ID, AUTHOR_ID, AUTHOR_DISCRIMINATOR, AUTHOR_DISPLAY_NAME, CHANNEL_ID) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', records)
                records = []

                #save attachments
                cur.executemany('insert into MESSAGE_ATTACHMENT_HISTORY (ID, SIZE, HEIGHT, WIDTH, FILENAME, URL, PROXY_URL, IS_SPOILER, CONTENTS, MESSAGE_ID, RAW, GUILD_ID) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', attachments)
                attachments = []

                #save reactions
                cur.executemany('insert into MESSAGE_REACTION_HISTORY (EMOJI, MESSAGE_ID, CUSTOM_EMOJI, REACTION_TIMESTAMP, USER, USER_DISCRIMINATOR, USER_DISPLAY_NAME, EMOJI_ID, EMOJI_REQUIRE_COLONS, ANIMATED, MANAGED, GUILD_ID, AVAILABLE, CREATOR, USER_ID, CREATOR_ID, CREATOR_DISCRIMINATOR, CREATOR_DISPLAY_NAME, CREATED_AT, URL, ROLES, IS_USABLE, RAW_REACTION, RAW_EMOJI, ME, UNICODE, REACTION_GUILD_ID) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', reactions)
                reactions = []

                con.commit()
                closeConnection(con)

    con = openConnection()
    cur = con.cursor()

    #save messages
    cur.executemany('insert into MESSAGE_HISTORY (TTS, TYPE, AUTHOR, CONTENT, NONCE, EMBEDS, CHANNEL, CALL, MENTION_EVERYONE, MENTIONS, CHANNEL_MENTIONS, ROLE_MENTIONS, ID, WEBHOOK_ID, ATTACHMENTS, PINNED, FLAGS, REACTIONS, ACTIVITY, APPLICATION, GUILD, RAW_MENTIONS, RAW_CHANNEL_MENTIONS, RAW_ROLE_MENTIONS, CLEAN_CONTENT, CREATED_AT, EDITED_AT, JUMP_URL, IS_SYSTEM, SYSTEM_CONTENT, RAW, GUILD_ID, AUTHOR_ID, AUTHOR_DISCRIMINATOR, AUTHOR_DISPLAY_NAME, CHANNEL_ID) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', records)

    #save attachments
    cur.executemany('insert into MESSAGE_ATTACHMENT_HISTORY (ID, SIZE, HEIGHT, WIDTH, FILENAME, URL, PROXY_URL, IS_SPOILER, CONTENTS, MESSAGE_ID, RAW, GUILD_ID) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', attachments)

    #save reactions
    cur.executemany('insert into MESSAGE_REACTION_HISTORY (EMOJI, MESSAGE_ID, CUSTOM_EMOJI, REACTION_TIMESTAMP, USER, USER_DISCRIMINATOR, USER_DISPLAY_NAME, EMOJI_ID, EMOJI_REQUIRE_COLONS, ANIMATED, MANAGED, GUILD_ID, AVAILABLE, CREATOR, USER_ID, CREATOR_ID, CREATOR_DISCRIMINATOR, CREATOR_DISPLAY_NAME, CREATED_AT, URL, ROLES, IS_USABLE, RAW_REACTION, RAW_EMOJI, ME, UNICODE, REACTION_GUILD_ID) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', reactions)

    con.commit()
    closeConnection(con)
    totaltime = time.time() - startTime
    await sendMessage(message, f'Server {message.guild.name} backed up in {totaltime} seconds.', deleteAfter = 10, triggeredCommand = trigger)
    addLog(f'Server {message.guild.name} backed up in {totaltime} seconds.', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)

#clears the backup of this server
async def clearBackup(message, trigger):
    addLog(f'Deleting backup for server {message.guild.id}', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
    await sendMessage(message, f'Deleting backup for server {message.guild.name}', deleteAfter = 10, triggeredCommand = trigger)
    con = openConnection()
    cur = con.cursor()
    cur.execute('delete from MESSAGE_HISTORY where GUILD_ID = ?', [message.guild.id])
    cur.execute('delete from MESSAGE_REACTION_HISTORY where REACTION_GUILD_ID = ?', [message.guild.id])
    cur.execute('delete from MESSAGE_ATTACHMENT_HISTORY where GUILD_ID = ?', [message.guild.id])
    con.commit()
    closeConnection(con)

#displays a list of admin commands
async def listAdminCommands(message, trigger):
    addLog(f'Listing admin commands', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
    x = ''
    s = filter(filterAdminFunctions, commands)
    for i in s:
        x = x + f'''**!{i.trigger.ljust(20)}** - \t{i.description}\n'''
    await sendMessage(message, x, deleteAfter = 20, triggeredCommand = trigger)

#ends the bot program
async def kill(message, trigger):
    addLog(f'Killing bot process...', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
    await sendMessage(message, 'Killing bot process...',  deleteAfter = 20, triggeredCommand = trigger)
    sys.stdout.flush()
    await exit()

#deletes the last bot message
async def deleteLastBotMessage(message, trigger):
    messages = await message.channel.history(limit = 100).flatten()
    for i in messages:
        if i.author == client.user:
            addLog(f'Deleting last bot message {i.id}...', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
            await sendMessage(message, 'Deleting last bot message...',  deleteAfter = 10, triggeredCommand = trigger)
            await i.delete()
            return
    await sendMessage(message, 'No bot messages found in the last 100 message',  deleteAfter = 20, triggeredCommand = trigger)

#sends a random file attachment from chat
async def randomAttachment(message, trigger):
    attachments = select(f'select author_id, url from message_attachment_history left join message_history on message_attachment_history.message_id = message_history.id')
    index = random.randrange(0, len(attachments), 1)
    attachment = attachments[index][1]
    author = client.get_user(attachments[index][0])
    await sendMessage(message, f'Courtesy of {author.mention}\n{attachment}', triggeredCommand = trigger)

#sends a random youtube video from chat
async def randomVideo(message, trigger):
    videos = select(f"select distinct content from (select content from MESSAGE_HISTORY where (content like '%youtube.com%' or '%youtu.be%') and author <> 'GlobalBot#9663' union select content from MESSAGES where (content like '%youtube.com%' or '%youtu.be%') and author <> 'GlobalBot#9663')")
    index = random.randrange(0, len(videos), 1)
    video = videos[index][0]
    await sendMessage(message, video, triggeredCommand = trigger)

#Moves a user into a specified voice channel
async def move(message, trigger):
    users = message.mentions
    channelName = removeCommand(message.content, f'!{trigger}')
    channelName = re.sub(r"<.*>", "", channelName).strip()
    if users == []:
        await sendMessage(message, 'Invalid format. Correct format is !move channel @user.', deleteAfter = 20, triggeredCommand = trigger)
    else:
        for x in users:
            if x.voice == None:
                await sendMessage(message, f'User {x.display_name} is not currently in a voice channel.', deleteAfter = 10, triggeredCommand = trigger)
            else:
                channel = getChannelByName(message.guild, channelName)
                if channel == None:
                    await sendMessage(message, f'There is currently no {channelName} channel.', deleteAfter = 10, triggeredCommand = trigger)
                else:
                    addLog(f'Moving user {x.display_name} to {channelName} voice channel.', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, targetUser = x.name, targetUserID = x.id, targetUserDiscriminator = x.discriminator, targetUserDisplayName = x.display_name, messageID = message.id)
                    await x.move_to(channel)
                    await sendMessage(message, f'Moving user {x.display_name} to voice channel {channelName}.', deleteAfter = 10, triggeredCommand = trigger)

#downloads the newest version of the source from github
async def update(message, trigger):

    await sendMessage(message, 'Updating bot code...', deleteAfter = 20, triggeredCommand = trigger)
    addLog(f'Updating bot source code...', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)          

    g = Github(githubToken)
    repo = g.get_repo('FiniteUI/GlobalBot')
    contents = repo.get_contents("GlobalBot.py")
    data = contents.decoded_content.decode('UTF-8')

    f = open('GlobalBot.py', 'w+')
    f.write(data)
    f.close() 

    await restart(message, trigger)

#nightly refresh, backup, update, restart
async def refresh():
    if len(client.guilds) > 0:
        for guild in client.guilds:
            await sendChannelMessage('Starting bot refresh...', guild.text_channels[0].id, deleteAfter = 10)
            lastMessage = await guild.text_channels[0].fetch_message(guild.text_channels[0].last_message_id)
            await backup(lastMessage, 'refresh')
        await restart(lastMessage, 'refresh')

#add the regresh into the main event loop
def callRefresh():
    global loop
    if date.today() != launchDate:
        thisRefresh = asyncio.run_coroutine_threadsafe(refresh(), loop)
        thisRefresh.result()

#load client
load_dotenv('.env')
token = os.getenv('DISCORD_TOKEN')
database = os.getenv('GLOBALBOT_DATABASE')
finiteui = os.getenv('DISCORD_ID')
githubToken = os.getenv('GITHUB_TOKEN')
loop = ''
launchDate = date.today()

client = discord.Client()

@client.event
async def on_ready():
    #grab current event loop
    global loop
    loop = asyncio.get_event_loop()

    addLog(f'{client.user} has connected to Discord!', inspect.currentframe().f_code.co_name)

    for x in client.guilds:
       addLog(f'Connected to server: {x}, {x.id}', inspect.currentframe().f_code.co_name, server = x.name, serverID = x.id)

@client.event
async def on_message(message):
    #saveMessage(message)
    if message.author == client.user:
        return
    elif message.content.startswith('!'):
        command = message.content[1:len(message.content)].split(' ')[0].lower()
        for x in commands:
            if command == x.trigger.lower():
                if x.userCommand:
                    addLog(f'{message.guild} user {message.author} triggered user command [{x.trigger}].', inspect.currentframe().f_code.co_name, command, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, arguments = str(x.arguments), invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
                    await globals()[x.function](message, x.arguments[0], x.arguments[1], triggeredCommand = x.trigger.lower())
                else:
                    if x.admin:
                        if int(message.author.id) != int(finiteui):
                            await sendMessage(message, 'This command is admin only.', deleteAfter = 20, triggeredCommand = x.trigger.lower())
                            return
                    addLog(f'{message.guild} user {message.author} triggered command [{x.trigger}].', inspect.currentframe().f_code.co_name, command, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
                    await globals()[x.function](message, x.trigger.lower())
                break

#load commands
commands = []
commands.append(command('help', 'Displays a list of available commands', 'help'))
commands.append(command('restart', 'Restarts the bot', 'restart', admin = True))
commands.append(command('addmessagecommand', 'Adds a new simple message command. Format: !addmessagecommand command, message', 'addUserCommand'))
commands.append(command('deletemessagecommand', 'Deletes a user message command. Format: !deletemessagecommand command', 'deleteUserCommand'))
commands.append(command('pin', 'Sends a random pinned message', 'sendRandomPinnedMessage'))
commands.append(command('kick', 'Kicks a user from voice. Format: !kick @user', 'kickUser'))
commands.append(command('usercommands', 'Displays a list of available user commands', 'listUserCommands'))
commands.append(command('setstatus', 'Sets the status of the bot', 'setStatus'))
commands.append(command('setname', 'Sets the display name of the bot', 'setName'))
commands.append(command('demote', 'Moves a user to the Tier 1 voice chat. Format: !demote @user', 'demote'))
commands.append(command('backup', 'Starts a server backup.', 'backup', admin = True))
commands.append(command('admincommands', 'Displays a list of available admin commands', 'listAdminCommands', admin = True))
commands.append(command('kill', 'Ends the bot program', 'kill', admin = True))
commands.append(command('deletelastbotmessage', 'Deletes the last message sent by the bot', 'deleteLastBotMessage', admin = True))
commands.append(command('roulette', 'Kicks a random user from voice chat', 'roulette'))
commands.append(command('ra', 'Sends a random attachment from the channel history', 'randomAttachment'))
commands.append(command('randomvideo', 'Sends a random youtube video from the channel history', 'randomVideo'))
commands.append(command('move', 'Moves a user into a specified voice channel. Format: !move channel @user', 'move', admin = True))
commands.append(command('clearbackup', 'Clears the backup of this server.', 'clearBackup', admin = True))
commands.append(command('update', 'Updates the source code from Github and restarts', 'update', admin = True))
loadUserCommands()

#launch the refresh timer
timer = threading.Timer(300, callRefresh)
timer.start()

#run the bot            
addLog('Running client...', inspect.currentframe().f_code.co_name)
client.run(token)

