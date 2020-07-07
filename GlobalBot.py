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
import subprocess
import pytz
import csv
import zipfile
import zlib
import matplotlib
import matplotlib.pyplot

#command class
class command:
    trigger = ''
    description = ''
    function = ''
    userCommand = False
    arguments = ''
    admin = False
    hidden = False
    server = -1

    def __init__(self, trigger, description, function = '', userCommand = False, arguments = '', admin = False, hidden = False, server = -1):
        self.trigger = trigger
        self.description = description
        
        if function == '':
            self.function = trigger
        else:
            self.function = function

        self.userCommand = userCommand
        self.arguments = arguments
        self.admin = admin
        self.hidden = hidden
        self.server = int(server)

    async def run(self, message):
        if self.userCommand:
            await globals()[self.function](message, *self.arguments, triggeredCommand = self.trigger)
        else:
            await globals()[self.function](message, trigger = self.trigger)
            
#returns and open connection to the database
def openConnection():
    con = sqlite3.connect(database)
    con.row_factory = sqlite3.Row
    return con

#closes the given database connection
def closeConnection(con):
    con.close()

#prints a message in the shell and adds it to BOT_LOG
def addLog(message, function = None, command = None, arguments = None, targetUser = None, targetUserID = None, server = None, serverID = None, channel = None, channelID = None, invokedUser = None, invokedUserID = None, invokedUserDiscriminator = None, invokedUserDisplayName = None, targetUserDiscriminator = None, targetUserDisplayName = None, messageID = None, printLog = True):
    con = openConnection()
    cur = con.cursor()
    if printLog:
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
            commands.append(command(x[1], f'Sends the text to speech message "{x[2]}"', 'sendMessage', True, [x[2], x[3]], server = x[5]))
        else:
            commands.append(command(x[1], f'Sends the message "{x[2]}"', 'sendMessage', True, [x[2], x[3]], server = x[5]))

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
async def sendMessage(triggerMessage, sendMessage, textToSpeech = False, deleteAfter = None, embedItem = None, embedItems = None, triggeredCommand = None, codeBlock = False, attachment = None):
    if sendMessage.strip() == '':
        return

    addLog(f'''Sending message "{sendMessage}" to channel {triggerMessage.channel} in server {triggerMessage.guild}, {triggerMessage.guild.id}.''', inspect.currentframe().f_code.co_name, server = triggerMessage.guild.name, serverID = triggerMessage.guild.id, channel = triggerMessage.channel.name, channelID = triggerMessage.channel.id, invokedUser = triggerMessage.author.name, invokedUserID = triggerMessage.author.id, invokedUserDiscriminator = triggerMessage.author.discriminator, invokedUserDisplayName = triggerMessage.author.nick, command = triggeredCommand)

    #message limit is 2000 characters, we may add 2 if codeBlock, so our limit is 1998
    if len(sendMessage) > 1998:
        x = chunkStringNewLine(sendMessage, 1998)
        for i in x:
            if codeBlock:
                await triggerMessage.channel.send(f'`{i}`', tts = textToSpeech, delete_after = deleteAfter, embed = embedItem, file = attachment)
            else:
                await triggerMessage.channel.send(i, tts = textToSpeech, delete_after = deleteAfter, embed = embedItem, file = attachment)
    else:
        if codeBlock:
            await triggerMessage.channel.send(f'`{sendMessage}`', tts = textToSpeech, delete_after = deleteAfter, embed = embedItem, file = attachment)
        else:
            await triggerMessage.channel.send(sendMessage, tts = textToSpeech, delete_after = deleteAfter, embed = embedItem, file = attachment)

#sends a message to the channel
async def sendChannelMessage(message, channelID, triggerMessage, textToSpeech = False, deleteAfter = None, embedItem = None, embedItems = None, triggeredCommand = None, codeBlock = False, attachment = None):
    sendChannel = client.get_channel(channelID)
    addLog(f'''Sending message "{message}" to channel {sendChannel.name} in server {sendChannel.guild}, {sendChannel.guild.id}.''', inspect.currentframe().f_code.co_name, server = sendChannel.guild.name, serverID = sendChannel.guild.id, channel = sendChannel.name, channelID = sendChannel.id, command = triggeredCommand)

    #message limit is 2000 characters, we may add 2 if codeBlock, so our limit is 1998
    if len(message) > 1998:
        x = chunkStringNewLine(message, 1998)
        for i in x:
            if codeBlock:
                await sendChannel.send(f'`{i}`', tts = textToSpeech, delete_after = deleteAfter, embed = embedItem, file = attachment)
            else:
                await sendChannel.send(i, tts = textToSpeech, delete_after = deleteAfter, embed = embedItem, file = attachment)
    else:
        if codeBlock:
            await sendChannel.send(f'`{message}`', tts = textToSpeech, delete_after = deleteAfter, embed = embedItem, file = attachment)
        else:
            await sendChannel.send(message, tts = textToSpeech, delete_after = deleteAfter, embed = embedItem, file = attachment)

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
    s = filterCommands(commands, message.guild.id)
    s = filter(filterUserFunctions, s)
    extractor = URLExtract()
    for i in s:
        if i.server == message.guild.id:
            description = i.description
            urls = extractor.find_urls(i.description)
            for url in urls:
                description = description.replace(url, f'<{url}>')
            x = x + f'''**!{i.trigger.ljust(20)}** - \t{description}\n'''
    await sendMessage(message, x, deleteAfter = 30, triggeredCommand = trigger)

#restart the bot
async def restart(message = None, trigger = None, silent = False, fromMessage = True):
    if not fromMessage:
        addLog(f'Restarting bot', inspect.currentframe().f_code.co_name, trigger, invokedUser = client.user.name, invokedUserDiscriminator = client.user.discriminator, invokedUserID = client.user.id)
    else:
        addLog(f'Restarting bot', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
    
    if not silent:
        #await sendMessage(message, 'Restarting bot...',  deleteAfter = 20, triggeredCommand = trigger, codeBlock = True)
        await sendMessage(message, 'Restarting bot...', triggeredCommand = trigger, codeBlock = True)
    
    #wait for message cleanup
    #await asyncio.sleep(30)

    os.execlp('python', '-m', 'C:/GlobalBot/GlobalBot.py')

    await kill(message, trigger)

#add a new simple message command
async def addUserCommand(message, trigger):
    x = removeCommand(message.content, f'!{trigger}')
    x = x.split(',')
    if len(x) >= 2:
        newTrigger = x.pop(0).strip().lower()
        spaceTest = newTrigger.split(' ')
        if len(spaceTest) > 1:
            await sendMessage(message, 'Invalid command name. Command names cannot include spaces',  deleteAfter = 20, triggeredCommand = trigger, codeBlock = True)
        else:
            messageToSend = ','
            messageToSend = messageToSend.join(x).strip()
            tempCommandList = filterCommands(commands, message.guild.id)
            for i in tempCommandList:
                if newTrigger == i.trigger:
                    await sendMessage(message, 'This command already exists.',  deleteAfter = 20, triggeredCommand = trigger, codeBlock = True)
                    return
            if messageToSend.startswith('/tts'):
                messageToSend = messageToSend.replace('/tts', '')
                tts = True
                z = 'text to speech '
            else:
                tts = False
                z = ''
            commands.append(command(newTrigger, f'''Sends the {z}message "{messageToSend}"''', 'sendMessage', True, [messageToSend, tts], server = message.guild.id))
            #await sendMessage(message, f'Adding user command [{newTrigger}]',  deleteAfter = 20, triggeredCommand = newTrigger, codeBlock = True)
            await sendMessage(message, f'Adding user command [{newTrigger}]', triggeredCommand = newTrigger, codeBlock = True)
            saveUserCommand(message, newTrigger, messageToSend, tts)
            addLog(f'Adding user command [{newTrigger}]', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
    else:
        await sendMessage(message, 'Invalid parameters. Format is !addmessagecommand command, message',  deleteAfter = 20, triggeredCommand = trigger)

#filters command list to only user functions
def filterUserFunctions(command):
    return (command.userCommand and not command.hidden)

#filters command list to only admin functions
def filterAdminFunctions(command):
    return (command.admin and not command.hidden)

#filters command list to only admin functions
def filterStandardFunctions(command):
    return (not command.userCommand and not command.admin and not command.hidden)

#returns a list of commands usable to this server
def filterCommands(commandList, serverID):
    x = []
    for i in commandList:
        if i.server == serverID or i.server == -1:
            x.append(i)
    return x

#deletes a user command from the database
def deleteUserCommandFromDatabase(serverID, command):
    con = openConnection()
    cur = con.cursor()
    cur.execute('delete from USER_COMMANDS where SERVER_ID = ? and TRIGGER = ?', [serverID, command])
    con.commit()
    closeConnection(con)

#delete an existing user command
async def deleteUserCommand(message, trigger):
    x = removeCommand(message.content, f'!{trigger}')

    s = filterCommands(commands, message.guild.id)
    s = filter(filterUserFunctions, s)
    for y in s:
        if y.trigger.lower() == x.lower():
            commands.remove(y)
            del y
            deleteUserCommandFromDatabase(message.guild.id, x.lower())
            addLog(f'Deleting user command [{x}] from server {message.guild.name}', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
            #await sendMessage(message, f'Deleting user command [{x}]',  deleteAfter = 20, triggeredCommand = trigger, codeBlock = True)
            await sendMessage(message, f'Deleting user command [{x}]', triggeredCommand = trigger, codeBlock = True)
            return
    await sendMessage(message, f'Command [{x}] not found',  deleteAfter = 20, triggeredCommand = trigger, codeBlock = True)

#send a random pinned message
async def sendRandomPinnedMessage(message, trigger):
    pin = await message.channel.pins()
    if len(pin) == 0:
        await sendMessage(message, 'This server has no pinned messages.', deleteAfter = 20, triggeredCommand = trigger, codeBlock = True)
    else:
        x = random.randrange(0, len(pin), 1)

        addLog(f'Sending random pinned message {pin[x]}', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
        await sendMessage(message, pin[x].jump_url, triggeredCommand = trigger)

#kicks a user out of voice chat
async def kickUser(message, trigger):
    users = message.mentions
    if users == []:
        await sendMessage(message, 'Invalid format. Correct format is !kick @user.', deleteAfter = 20, triggeredCommand = trigger, codeBlock = True)
    else:
        for x in users:
            if x.voice == None:
                await sendMessage(message, f'User {x.display_name} is not currently in a voice channel.', deleteAfter = 10, triggeredCommand = trigger, codeBlock = True)
            else:
                addLog(f'Kicking user {x.display_name} from voice', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, targetUser = x.name, targetUserID = x.id, targetUserDiscriminator = x.discriminator, targetUserDisplayName = x.display_name, messageID = message.id)
                await x.move_to(None)
                #await sendMessage(message, f'Kicking user {x.display_name} from voice', deleteAfter = 10, triggeredCommand = trigger, codeBlock = True)
                await sendMessage(message, f'Kicking user {x.display_name} from voice', triggeredCommand = trigger, codeBlock = True)

#kicks a random user out of voice chat
async def roulette(message, trigger):
    channels = message.guild.voice_channels
    x = []
    for i in channels:
        for j in i.members:
            x.append(j)
    if len(x) > 0:
        userIndex = random.randrange(0, len(x), 1)
        #await sendMessage(message, f'Kicking user {x[userIndex].display_name} from voice', deleteAfter = 10, triggeredCommand = trigger, codeBlock = True)
        await sendMessage(message, f'Kicking user {x[userIndex].display_name} from voice', triggeredCommand = trigger, codeBlock = True)
        addLog(f'Kicking user {x[userIndex].display_name} from voice', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, targetUser = x[userIndex].name, targetUserID = x[userIndex].id, targetUserDiscriminator = x[userIndex].discriminator, targetUserDisplayName = x[userIndex].display_name, messageID = message.id)
        await x[userIndex].move_to(None)  
    else:
        await sendMessage(message, 'There are no users currently in voice chat', deleteAfter = 10, triggeredCommand = trigger, codeBlock = True)  

#remove the command from the message
def removeCommand(message, command):
    redata = re.compile(re.escape(command), re.IGNORECASE)
    return redata.sub('', message).strip()

#sets the bots status
async def setStatus(message, trigger):
    y = discord.Game(removeCommand(message.content, f'!{trigger}'))
    await sendMessage(message, f'Setting status to "{y}"', deleteAfter = 10, triggeredCommand = trigger, codeBlock = True)
    addLog(f'Setting status to "{y}"', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
    await client.change_presence(status = discord.Status.online, activity = y)

#sets the bots status
async def setName(message, trigger):
    y = removeCommand(message.content, f'!{trigger}')

    if len(y) > 32:
        await sendMessage(message, f'Display names must be 32 characters or less.', deleteAfter = 10, triggeredCommand = trigger, codeBlock = True)
    else:
        #await sendMessage(message, f'Setting display name to "{y}"', deleteAfter = 10, triggeredCommand = trigger, codeBlock = True)
        await sendMessage(message, f'Setting display name to "{y}"', triggeredCommand = trigger, codeBlock = True)
        addLog(f'Setting display name to "{y}"', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
        member = message.guild.get_member(client.user.id)
        await member.edit(nick = y)

#sends a user to the tier 1 voice chat
async def demote(message, trigger):
    users = message.mentions
    if users == []:
        await sendMessage(message, 'Invalid format. Correct format is !demote @user.', deleteAfter = 20, triggeredCommand = trigger, codeBlock = True)
    else:
        for x in users:
            if x.voice == None:
                await sendMessage(message, f'User {x.display_name} is not currently in a voice channel.', deleteAfter = 10, triggeredCommand = trigger, codeBlock = True)
            else:
                tier1 = getChannelByName(message.guild, 'Tier 1')
                if tier1 == None:
                    await sendMessage(message, 'There is currently no Tier 1 voice channel.', deleteAfter = 10, triggeredCommand = trigger, codeBlock = True)
                else:
                    addLog(f'Moving user {x.display_name} to Tier 1 voice channel.', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, targetUser = x.name, targetUserID = x.id, targetUserDiscriminator = x.discriminator, targetUserDisplayName = x.display_name, messageID = message.id)
                    await x.move_to(tier1)
                    #await sendMessage(message, f'Demoting user {x.display_name} to Tier 1.', deleteAfter = 10, triggeredCommand = trigger, codeBlock = True)
                    await sendMessage(message, f'Demoting user {x.display_name} to Tier 1.', triggeredCommand = trigger, codeBlock = True)

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
async def backup(message = None, trigger = None, silent = False, fromMessage = True, overrideGuild = None):
    if fromMessage:
        guild = message.guild
        invokedUser = message.author
        messageID = message.id
        displayName = message.author.nick
        channelName = message.channel.name
        channelID = message.channel.id
    else:
        guild = overrideGuild
        invokedUser = client.user
        displayName = None
        messageID = None
        silent = True
        channelName = None
        channelID = None

    recordLimit = 10000

    addLog(f'Backing up server {guild.name}...', inspect.currentframe().f_code.co_name, trigger, server = guild.name, serverID = guild.id, channel = channelName, channelID = channelID, invokedUser = invokedUser.name, invokedUserID = invokedUser.id, invokedUserDiscriminator = invokedUser.discriminator, invokedUserDisplayName = displayName, messageID = messageID)
    if not silent:
        #await sendMessage(message, f'Backing up server {guild.name}...', deleteAfter = 10, triggeredCommand = trigger, codeBlock = True)
        await sendMessage(message, f'Backing up server {guild.name}...', triggeredCommand = trigger, codeBlock = True)
    startTime = time.time()
    top = grabTopStoredMesage(guild)
    records = []
    attachments = []
    reactions = []

    for i in guild.text_channels:
        if top == None:
            history = await i.history(limit = None, oldest_first = True).flatten()
        else:
            history = await i.history(limit = None, oldest_first = True, after = datetime.strptime(top, '%Y-%m-%d %H:%M:%S.%f')).flatten()
        for j in history:
            if j.type == 'call':
                call = j.call
            else:
                call = None
            records.append([datetime.now(), j.tts, str(j.type), str(j.author), str(j.content), j.nonce, str(j.embeds), str(j.channel), call, j.mention_everyone, str(j.mentions), str(j.channel_mentions), str(j.role_mentions), j.id, j.webhook_id, str(j.attachments), j.pinned, str(j.flags), str(j.reactions), str(j.activity), str(j.application), str(j.guild), str(j.raw_mentions), str(j.raw_channel_mentions), str(j.raw_role_mentions), j.clean_content, j.created_at, j.edited_at, j.jump_url, str(j.is_system()), j.system_content, str(j), j.guild.id, j.author.id, j.author.discriminator, j.author.display_name, j.channel.id, j.author.name, j.author.bot])

            #add attachments
            for a in j.attachments:
                #rawData = await a.read()
                rawData = None
                attachments.append([a.id, a.size, a.height, a.width, a.filename, a.url, a.proxy_url, a.is_spoiler(), rawData, j.id, str(a), j.guild.id])

            #save reactions
            for r in j.reactions:
                for u in await r.users().flatten():
                    if r.custom_emoji:
                        name = r.emoji.name
                        id = r.emoji.id
                        animated = r.emoji.animated
                        url = r.emoji.url
                        unicode = None
                        if type(r.emoji) == discord.PartialEmoji:
                            require_colons = None
                            managed = None
                            guild_id = None
                            available = None
                            user_name = None
                            user_id =  None
                            user_discriminator = None
                            user_display_name = None
                            created_at = None
                            roles = None
                            is_usable = None
                        else:
                            require_colons = r.emoji.require_colons
                            managed = r.emoji.managed
                            guild_id = r.emoji.guild_id
                            available = r.emoji.available
                            created_at = r.emoji.created_at
                            roles = r.emoji.roles
                            is_usable = r.emoji.is_usable()
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

                    reactions.append([name, j.id, r.custom_emoji, None, u.name, u.discriminator, u.display_name, id, require_colons, animated, managed, guild_id, available, user_name, u.id, user_id, user_discriminator, user_display_name, created_at, str(url), str(roles), is_usable, str(r), str(r.emoji), r.me, unicode, j.id])

            if len(records) + len(attachments) + len(reactions) > recordLimit:
                addLog(f'Record limit reached, saving partial and continuing...', inspect.currentframe().f_code.co_name, trigger, server = guild.name, serverID = guild.id, channel = channelName, channelID = channelID, invokedUser = invokedUser.name, invokedUserID = invokedUser.id, invokedUserDiscriminator = invokedUser.discriminator, invokedUserDisplayName = displayName, messageID = messageID)

                con = openConnection()
                cur = con.cursor()

                #save messages
                cur.executemany('insert into MESSAGE_HISTORY (RECORD_TIMESTAMP, TTS, TYPE, AUTHOR, CONTENT, NONCE, EMBEDS, CHANNEL, CALL, MENTION_EVERYONE, MENTIONS, CHANNEL_MENTIONS, ROLE_MENTIONS, ID, WEBHOOK_ID, ATTACHMENTS, PINNED, FLAGS, REACTIONS, ACTIVITY, APPLICATION, GUILD, RAW_MENTIONS, RAW_CHANNEL_MENTIONS, RAW_ROLE_MENTIONS, CLEAN_CONTENT, CREATED_AT, EDITED_AT, JUMP_URL, IS_SYSTEM, SYSTEM_CONTENT, RAW, GUILD_ID, AUTHOR_ID, AUTHOR_DISCRIMINATOR, AUTHOR_DISPLAY_NAME, CHANNEL_ID, AUTHOR_NAME, AUTHOR_BOT) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', records)
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
    cur.executemany('insert into MESSAGE_HISTORY (RECORD_TIMESTAMP, TTS, TYPE, AUTHOR, CONTENT, NONCE, EMBEDS, CHANNEL, CALL, MENTION_EVERYONE, MENTIONS, CHANNEL_MENTIONS, ROLE_MENTIONS, ID, WEBHOOK_ID, ATTACHMENTS, PINNED, FLAGS, REACTIONS, ACTIVITY, APPLICATION, GUILD, RAW_MENTIONS, RAW_CHANNEL_MENTIONS, RAW_ROLE_MENTIONS, CLEAN_CONTENT, CREATED_AT, EDITED_AT, JUMP_URL, IS_SYSTEM, SYSTEM_CONTENT, RAW, GUILD_ID, AUTHOR_ID, AUTHOR_DISCRIMINATOR, AUTHOR_DISPLAY_NAME, CHANNEL_ID, AUTHOR_NAME, AUTHOR_BOT) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', records)

    #save attachments
    cur.executemany('insert into MESSAGE_ATTACHMENT_HISTORY (ID, SIZE, HEIGHT, WIDTH, FILENAME, URL, PROXY_URL, IS_SPOILER, CONTENTS, MESSAGE_ID, RAW, GUILD_ID) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', attachments)

    #save reactions
    cur.executemany('insert into MESSAGE_REACTION_HISTORY (EMOJI, MESSAGE_ID, CUSTOM_EMOJI, REACTION_TIMESTAMP, USER, USER_DISCRIMINATOR, USER_DISPLAY_NAME, EMOJI_ID, EMOJI_REQUIRE_COLONS, ANIMATED, MANAGED, GUILD_ID, AVAILABLE, CREATOR, USER_ID, CREATOR_ID, CREATOR_DISCRIMINATOR, CREATOR_DISPLAY_NAME, CREATED_AT, URL, ROLES, IS_USABLE, RAW_REACTION, RAW_EMOJI, ME, UNICODE, REACTION_GUILD_ID) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', reactions)

    con.commit()
    closeConnection(con)
    totaltime = time.time() - startTime
    if not silent:
        await sendMessage(message, f'Server {guild.name} backed up in {totaltime} seconds.', triggeredCommand = trigger, codeBlock = True)
    addLog(f'Server {guild.name} backed up in {totaltime} seconds.', inspect.currentframe().f_code.co_name, trigger, server = guild.name, serverID = guild.id, channel = channelName, channelID = channelID, invokedUser = invokedUser.name, invokedUserID = invokedUser.id, invokedUserDiscriminator = invokedUser.discriminator, invokedUserDisplayName = displayName, messageID = messageID)

#clears the backup of this server
async def clearBackup(message, trigger):
    addLog(f'Deleting backup for server {message.guild.id}', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
    #await sendMessage(message, f'Deleting backup for server {message.guild.name}', deleteAfter = 10, triggeredCommand = trigger, codeBlock = True)
    await sendMessage(message, f'Deleting backup for server {message.guild.name}', triggeredCommand = trigger, codeBlock = True)
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
    #await sendMessage(message, 'Killing bot process...',  deleteAfter = 20, triggeredCommand = trigger, codeBlock = True)
    await sendMessage(message, 'Killing bot process...', triggeredCommand = trigger, codeBlock = True)
    await asyncio.sleep(30)
    sys.stdout.flush()
    await exit()

#deletes the last bot message
async def deleteLastBotMessage(message, trigger):
    messages = await message.channel.history(limit = 100).flatten()
    for i in messages:
        if i.author == client.user:
            addLog(f'Deleting last bot message {i.id}...', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
            await sendMessage(message, 'Deleting last bot message...',  deleteAfter = 10, triggeredCommand = trigger, codeBlock = True)
            await i.delete()
            return
    await sendMessage(message, 'No bot messages found in the last 100 messages',  deleteAfter = 20, triggeredCommand = trigger, codeBlock = True)

#converts a UTC datetime into a specific timezone
def convertUTCToTimezone(utc_timestamp, timezone):
    utc = pytz.timezone('UTC')
    newTimezone = pytz.timezone(timezone)
    utc_timestamp = utc.localize(utc_timestamp)
    newTimestamp = utc_timestamp.astimezone(newTimezone)
    return newTimestamp

#sends a random file attachment from chat
async def randomAttachment(message, trigger):
    attachments = select(f"select author_id, url, created_at from message_attachment_history left join message_history on message_attachment_history.message_id = message_history.id where (lower(URL) like '%.png' or lower(URL) like '%.jpg' or lower(URL) like '%.jpeg' or lower(URL) like '%.mp4' or lower(URL) like '%.gif') and message_history.guild_id = {message.guild.id} and message_attachment_history.id not in (select ATTACHMENT_ID from RANDOM_ATTACHMENT_BLACKLIST where GUILD_ID = {message.guild.id})")
    index = random.randrange(0, len(attachments), 1)
    attachment = attachments[index][1]
    author = client.get_user(attachments[index][0])

    utc_timestamp = datetime.strptime(attachments[index][2], '%Y-%m-%d %H:%M:%S.%f')
    central_timestamp = convertUTCToTimezone(utc_timestamp, 'US/Central')
    central_timestamp = datetime.strftime(central_timestamp, '%A %B %d, %Y at %I:%M %p')

    await sendMessage(message, f'Courtesy of {author.mention} on {central_timestamp}\n{attachment}', triggeredCommand = trigger)

#sends a random youtube video from chat
async def randomVideo(message, trigger):
    videos = select(f"select distinct author_id, created_at, content from MESSAGE_HISTORY where (content like '%youtube.com%' or '%youtu.be%') and author <> 'GlobalBot#9663' and GUILD_ID = {message.guild.id}")
    index = random.randrange(0, len(videos), 1)
    video = videos[index][2]
    extractor = URLExtract()
    urls = extractor.find_urls(video)

    utc_timestamp = datetime.strptime(videos[index][1], '%Y-%m-%d %H:%M:%S.%f')
    central_timestamp = convertUTCToTimezone(utc_timestamp, 'US/Central')
    central_timestamp = datetime.strftime(central_timestamp, '%A %B %d, %Y at %I:%M %p')

    author = client.get_user(videos[index][0])

    await sendMessage(message, f'Courtesy of {author.mention} on {central_timestamp}\n{urls[0]}', triggeredCommand = trigger)

#Moves a user into a specified voice channel
async def move(message, trigger):
    users = message.mentions
    channelName = removeCommand(message.content, f'!{trigger}')
    channelName = re.sub(r"<.*>", "", channelName).strip()
    if users == []:
        await sendMessage(message, 'Invalid format. Correct format is !move channel @user.', deleteAfter = 20, triggeredCommand = trigger, codeBlock = True)
    else:
        for x in users:
            if x.voice == None:
                await sendMessage(message, f'User {x.display_name} is not currently in a voice channel.', deleteAfter = 10, triggeredCommand = trigger, codeBlock = True)
            else:
                channel = getChannelByName(message.guild, channelName)
                if channel == None:
                    await sendMessage(message, f'There is currently no {channelName} channel.', deleteAfter = 10, triggeredCommand = trigger, codeBlock = True)
                else:
                    addLog(f'Moving user {x.display_name} to {channelName} voice channel.', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, targetUser = x.name, targetUserID = x.id, targetUserDiscriminator = x.discriminator, targetUserDisplayName = x.display_name, messageID = message.id)
                    await x.move_to(channel)
                    #await sendMessage(message, f'Moving user {x.display_name} to voice channel {channelName}.', deleteAfter = 10, triggeredCommand = trigger, codeBlock = True)
                    await sendMessage(message, f'Moving user {x.display_name} to voice channel {channelName}.', triggeredCommand = trigger, codeBlock = True)

#downloads the newest version of the source from github
async def update(message, trigger):

    #await sendMessage(message, 'Updating bot code...', deleteAfter = 20, triggeredCommand = trigger, codeBlock = True)
    await sendMessage(message, 'Updating bot code...', triggeredCommand = trigger, codeBlock = True)
    addLog(f'Updating bot source code...', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)          

    g = Github(githubToken)
    repo = g.get_repo('FiniteUI/GlobalBot')
    contents = repo.get_contents("GlobalBot.py")
    data = contents.decoded_content.decode('UTF-8')

    f = open('GlobalBot.py', 'w+', encoding = 'UTF-8')
    f.write(data)
    f.close() 

    await restart(message, trigger)

#nightly refresh, backup, update, restart
async def refresh(message = None, trigger = None, silent = False):
    if not silent:
        #await sendMessage(message, "Starting Global Refresh...", textToSpeech = False, deleteAfter = 20, triggeredCommand = trigger, codeBlock = True)
        startTime = time.time()
        await sendMessage(message, "Starting Global Refresh...", textToSpeech = False, triggeredCommand = trigger, codeBlock = True)
    if len(client.guilds) > 0:
        for guild in client.guilds:
            await backup(trigger = 'refresh', silent = True, fromMessage = False, overrideGuild = guild)
        await restart(message, trigger = 'refresh', silent = silent, fromMessage = False)
    if not silent:
        totaltime = time.time() - startTime
        await sendMessage(message, f"Global Refresh finished in {totaltime} seconds.", textToSpeech = False, triggeredCommand = trigger, codeBlock = True)

#add the regresh into the main event loop
def callRefresh():
    global loop
    if date.today() != launchDate:
        thisRefresh = asyncio.run_coroutine_threadsafe(refresh(silent = True), loop)
        thisRefresh.result()
    else:
        timer = threading.Timer(refreshInterval, callRefresh)
        timer.start()

#sends a message with the launch date and current uptime of the bot
async def uptime(message, trigger):
    uptime = datetime.now() - launchTime
    launchTimeTimeZone = convertUTCToTimezone(launchTime, 'US/Central')
    launchTimeTimeZone = datetime.strftime(launchTimeTimeZone, '%B %d, %Y at %I:%M %p')
    await sendMessage(message, f'The current instance of the bot was launched on {launchTimeTimeZone} CST. Current uptime is {uptime}.', triggeredCommand = trigger, codeBlock = True)

#sends the link to the bot source code
async def source(message, trigger):
    await sendMessage(message, 'https://github.com/FiniteUI/GlobalBot/blob/master/GlobalBot.py', triggeredCommand = trigger)

#sends a random message from the channel, optionally from a user
async def randomMessage(message, trigger):
    #grab a random message
    user = message.mentions
    filter = ''
    if user != []:
        filter = f' and author_id = {user[0].id}'
    messages = select(f"select distinct id from MESSAGE_HISTORY where content <> '' and guild_id = {message.guild.id} and channel_id = {message.channel.id}{filter}")
    x = random.randrange(0, len(messages), 1)
    randomMessage = messages[x][0]
    randomMessage = await message.channel.fetch_message(randomMessage)

    central_timestamp = convertUTCToTimezone(randomMessage.created_at, 'US/Central')
    central_timestamp = datetime.strftime(central_timestamp, '%A %B %d, %Y at %I:%M %p')

    text = f'On {central_timestamp}, {randomMessage.author.mention} said:\nLink: {randomMessage.jump_url}\n>>> {randomMessage.content}'
    addLog(f'Sending random message', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
    await sendMessage(message, text, triggeredCommand = trigger)

#check if the test.txt file exists
def checkTestMode():
    directory = os.getcwd()
    directory = os.path.join(directory, 'test.txt')
    if (os.path.isfile(directory)):
        print('The Bot is launching in TEST MODE...')
        return True
    else:
        return False

#creates a backup file of the server and sends it
async def getBackup(message, trigger):
    addLog(f'Generating backup archive', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
    
    #first run the backup to get any new messages
    await backup(trigger = trigger, silent = True, fromMessage = False, overrideGuild = message.guild)

    #now create the directory backup
    directory = os.getcwd()
    directory = os.path.join(directory, 'User Requested Backups', str(message.guild.id))

    if not os.path.isdir(directory):
        os.makedirs(directory)
    
    #now grab the data
    channels = select(f'select distinct channel_id from message_history where guild_id = {message.guild.id}')
    messages = select(f'select created_at, channel_id, channel, author_name, author_discriminator, author_display_name, clean_content, jump_url, tts, pinned, url from message_history left join message_attachment_history on message_history.id = message_attachment_history.message_id where message_history.guild_id = {message.guild.id} order by channel_id, created_at')

    #now create the files
    files = []
    for channel in channels:
        channelMessages = [x for x in messages if x[1] == channel[0]]
        timeStamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        fileName = f'{message.author.id}-{channel[0]}-{timeStamp}.csv'
        fullPath = os.path.join(directory, fileName)
        files.append([fileName, fullPath])

        with open(fullPath, 'wt+', encoding = 'utf-16', newline = '') as tempFile:
            writer = csv.writer(tempFile, quoting = csv.QUOTE_ALL)
            writer.writerow(['message_timestamp', 'channel_id', 'channel_name', 'author', 'author_discriminator', 'author_display_name', 'content', 'jump_url', 'text_to_speech', 'pinned', 'attachment'])
            writer.writerows(channelMessages)

    #now zip them up
    timeStamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    zipName = f'{message.author.id}-{message.guild.id}-{timeStamp}.zip'
    zipName = os.path.join(directory, zipName)
    with zipfile.ZipFile(zipName, mode = 'w') as tempZip:
        for file in files:
            tempZip.write(file[1], arcname = file[0], compress_type = zipfile.ZIP_DEFLATED)
            os.remove(file[1])
    
    #now send it
    backupAttachment = discord.File(zipName)
    await sendMessage(message, f'Here is your server backup {message.author.mention}', attachment = backupAttachment, triggeredCommand = trigger)
    os.remove(zipName)

#lists the guilds the bot is connected to
async def guilds(message, trigger):
    text = 'GlobalBot is connected to the following guilds:\n'
    for x in client.guilds:
        text = f'{text}{x.id}, {x.name}\n'
    await sendMessage(message, text, triggeredCommand = trigger, codeBlock = True)

#displays voice stats for the specified user
async def voiceStats(message, trigger):
    users = message.mentions
    if len(users) == 0:
        users = [message.author]
    for user in users:
        addLog(f'Generating voice stats for {user}', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
        chatTime = None
        streamTime = None
        mutedTime = None
        deafenedTime = None
        videoTime = None
        lastJoin = None
        lastChange = None
        lastDeafen = None
        lastMute = None
        lastVideo = None
        lastStream = None
        channel = None
        channels = {}
        last = None
        voiceLogs = select(f'select * from VOICE_ACTIVITY where GUILD_ID = {message.guild.id} and USER_ID = {user.id} order by RECORD_TIMESTAMP')
        for i in voiceLogs:
            if i['EVENT'] == 'JOIN_VOICE':
                lastJoin = datetime.strptime(i['RECORD_TIMESTAMP'], '%Y-%m-%d %H:%M:%S.%f')
                if i['AFTER_SELF_DEAF'] == 1:
                    lastDeafen = lastJoin
                elif i['AFTER_SELF_MUTE'] == 1:
                    lastMute = lastJoin

                if i['AFTER_SELF_STREAM'] == 1:
                    lastStream = lastJoin
                
                if i['AFTER_SELF_VIDEO'] == 1:
                    lastVideo = lastJoin

                channel = i['AFTER_CHANNEL_ID']
                if channel not in channels:
                    channels[channel] = datetime.now() - datetime.now()
                lastChange = lastJoin

            elif i['EVENT'] == 'DEAFEN':
                lastDeafen = datetime.strptime(i['RECORD_TIMESTAMP'], '%Y-%m-%d %H:%M:%S.%f')

            elif i['EVENT'] == 'MUTE':
                lastMute = datetime.strptime(i['RECORD_TIMESTAMP'], '%Y-%m-%d %H:%M:%S.%f')

            elif i['EVENT'] == 'VIDEO_START':
                lastVideo = datetime.strptime(i['RECORD_TIMESTAMP'], '%Y-%m-%d %H:%M:%S.%f')

            elif i['EVENT'] == 'STREAM_START':
                lastStream = datetime.strptime(i['RECORD_TIMESTAMP'], '%Y-%m-%d %H:%M:%S.%f')

            elif i['EVENT'] == 'LEAVE_VOICE':
                if lastJoin != None:
                    end = datetime.strptime(i['RECORD_TIMESTAMP'], '%Y-%m-%d %H:%M:%S.%f')
                    last = end - lastJoin
                    if chatTime != None:
                        chatTime = chatTime + last
                    else:
                        chatTime = last
                    lastJoin = None

                    if channel != None:
                        channels[channel] = channels[channel] + (end - lastChange)
                        channel = None
                        lastChange = None

                if lastDeafen != None:
                    end = datetime.strptime(i['RECORD_TIMESTAMP'], '%Y-%m-%d %H:%M:%S.%f')
                    if deafenedTime != None:
                        deafenedTime = deafenedTime + (end - lastDeafen)
                    else:
                        deafenedTime = (end - lastDeafen)
                    lastDeafen = None

                if lastMute != None:
                    end = datetime.strptime(i['RECORD_TIMESTAMP'], '%Y-%m-%d %H:%M:%S.%f')
                    if mutedTime != None:
                        mutedTime = mutedTime + (end - lastMute)
                    else:
                        mutedTime = (end - lastMute)
                    lastMute = None

                if lastVideo != None:
                    end = datetime.strptime(i['RECORD_TIMESTAMP'], '%Y-%m-%d %H:%M:%S.%f')
                    if videoTime != None:
                        videoTime = videoTime + (end - lastVideo)
                    else:
                        videoTime = (end - lastVideo)
                    lastVideo = None

                if lastStream != None:
                    end = datetime.strptime(i['RECORD_TIMESTAMP'], '%Y-%m-%d %H:%M:%S.%f')
                    if streamTime != None:
                        streamTime = streamTime + (end - lastStream)
                    else:
                        streamTime = (end - lastStream)
                    lastStream = None

            elif i['EVENT'] == 'UNDEAFEN':
                if lastDeafen != None:
                    end = datetime.strptime(i['RECORD_TIMESTAMP'], '%Y-%m-%d %H:%M:%S.%f')
                    if deafenedTime != None:
                        deafenedTime = deafenedTime + (end - lastDeafen)
                    else:
                        deafenedTime = (end - lastDeafen)
                    lastDeafen = None

            elif i['EVENT'] == 'UNMUTE':
                if lastMute != None:
                    end = datetime.strptime(i['RECORD_TIMESTAMP'], '%Y-%m-%d %H:%M:%S.%f')
                    if mutedTime != None:
                        mutedTime = mutedTime + (end - lastMute)
                    else:
                        mutedTime = (end - lastMute)
                    lastMute = None

            elif i['EVENT'] == 'VIDEO_END':
                if lastVideo != None:
                    end = datetime.strptime(i['RECORD_TIMESTAMP'], '%Y-%m-%d %H:%M:%S.%f')
                    if videoTime != None:
                        videoTime = videoTime + (end - lastVideo)
                    else:
                        videoTime = (end - lastVideo)
                    lastVideo = None

            elif i['EVENT'] == 'STREAM_END':
                if lastStream != None:
                    end = datetime.strptime(i['RECORD_TIMESTAMP'], '%Y-%m-%d %H:%M:%S.%f')
                    if streamTime != None:
                        streamTime = streamTime + (end - lastStream)
                    else:
                        streamTime = (end - lastStream)
                    lastStream = None
    
            elif i['EVENT'] == 'CHANNEL_CHANGE':
                end = datetime.strptime(i['RECORD_TIMESTAMP'], '%Y-%m-%d %H:%M:%S.%f')
                if channel != None:
                    channels[channel] = channels[channel] + (end - lastChange)
                lastChange = end
                
                channel = i['AFTER_CHANNEL_ID']
                if channel not in channels:
                    channels[channel] = datetime.now() - datetime.now()

        #now get current values if there are any
        if lastJoin != None:
            end = datetime.now()
            if chatTime != None:
                chatTime = chatTime + (end - lastJoin)
            else:
                chatTime = (end - lastJoin)
            channels[channel] = channels[channel] + (end - lastChange)

        if lastDeafen != None:
            end = datetime.now()
            if deafenedTime != None:
                deafenedTime = deafenedTime + (end - lastDeafen)
            else:
                deafenedTime = (end - lastDeafen)

        if lastMute != None:
            end = datetime.now()
            if mutedTime != None:
                mutedTime = mutedTime + (end - lastMute)
            else:
                mutedTime = (end - lastMute)

        if lastVideo != None:
            end = datetime.now()
            if videoTime != None:
                videoTime = videoTime + (end - lastVideo)
            else:
                videoTime = (end - lastVideo)
        
        if lastStream != None:
            end = datetime.now()
            if streamTime != None:
                streamTime = streamTime + (end - lastStream)
            else:
                streamTime = (end - lastStream)
        
        #now get channel names and format pie chart
        labels = ()
        sizes = []
        for i in channels:
            for x in message.guild.channels:
                if int(i) == x.id:
                    labels = labels + (x.name,)
            sizes.append(channels[i].total_seconds())
        
        totalSize = sum(sizes)
        for i in sizes:
            i = i / totalSize

        pieChart, ax1 = matplotlib.pyplot.subplots()
        ax1.pie(sizes, autopct='%1.2f%%',
        shadow=True, startangle=90)
        ax1.axis('equal')
        ax1.legend(labels = labels)

        #now save the chart
        directory = os.getcwd()
        directory = os.path.join(directory, 'User Requested Voice Stats', str(message.guild.id), str(message.author.id))
        if not os.path.isdir(directory):
            os.makedirs(directory)

        directory = os.path.join(directory, datetime.now().strftime('%Y%m%d%H%M%S%f'))
        matplotlib.pyplot.savefig(directory)
        chart = discord.File(f'{directory}.png')
        await sendChannelMessage('', 710669506498002954, message, attachment = chart)
        attachmentChannel = client.get_channel(710669506498002954)
        attachmentMessage = await attachmentChannel.fetch_message(attachmentChannel.last_message_id)
        
        if len(attachmentMessage.attachments) > 0:
            attachment = attachmentMessage.attachments[0].url
        else:
             attachment = discord.Embed.Empty

        start = convertUTCToTimezone(datetime.strptime('2020-04-28 01:08:16.990281', '%Y-%m-%d %H:%M:%S.%f'), 'US/Central')
        start = datetime.strftime(start, '%B %d, %Y at %I:%M %p')
        chatTime = formatTimeDelta(chatTime)
        mutedTime = formatTimeDelta(mutedTime)
        deafenedTime = formatTimeDelta(deafenedTime)
        streamTime = formatTimeDelta(streamTime)
        videoTime = formatTimeDelta(videoTime)

        e = discord.Embed(title = f"{user.display_name}'s Voice Stats", description = f'{client.user.name} started tracking voice activity on {start}.')
        e.set_author(name = client.user.name, icon_url = client.user.avatar_url)
        e.add_field(name = 'Time in Voice', value = chatTime, inline = True)
        e.add_field(name = 'Time Muted', value = mutedTime, inline = True)
        e.add_field(name = 'Time Deafened', value = deafenedTime, inline = True)
        e.add_field(name = 'Time Streaming', value = streamTime, inline = True)
        e.add_field(name ='Time in Video', value = videoTime, inline = True)

        e.set_image(url = attachment)

        await sendMessage(message, f'Here are your voice stats {user.mention}', triggeredCommand = trigger, embedItem = e)

#formats a timedelta object into a string with days, hours, minutes, seconds
def formatTimeDelta(duration):
    if duration == None:
        return '0 seconds'

    days, remainder = divmod(duration.total_seconds(), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    days = int(days)
    hours = int(hours)
    minutes = int(minutes)
    seconds = int(seconds)

    formattedDuration = ''
    if days != 0:
        formattedDuration = f'{days} days, {hours} hours, {minutes} minutes, {seconds} seconds'
    elif hours != 0:
        formattedDuration = f'{hours} hours, {minutes} minutes, {seconds} seconds'
    elif minutes != 0:
        formattedDuration = f'{minutes} minutes, {seconds} seconds'
    else:
        formattedDuration = f'{seconds} seconds'

    return formattedDuration

#sends tts message from the server
async def randomtts(message, trigger):
    #first run the backup to get any new messages
    #await backup(trigger = trigger, silent = True, fromMessage = False, overrideGuild = message.guild)

    #grab a random message
    messages = select(f"select distinct id from TTS_LOG A inner join MESSAGE_HISTORY B on A.MESSAGE_ID = B.ID where content <> '' and guild_id = {message.guild.id} and AUTHOR_ID <> {client.user.id}")
    if len(messages) > 0:
        x = random.randrange(0, len(messages), 1)
        randomMessage = messages[x][0]
        randomMessage = await message.channel.fetch_message(randomMessage)

        central_timestamp = convertUTCToTimezone(randomMessage.created_at, 'US/Central')
        central_timestamp = datetime.strftime(central_timestamp, '%A %B %d, %Y at %I:%M %p')

        text = f'On {central_timestamp}, {randomMessage.author.mention} said:\nLink: {randomMessage.jump_url}\n'
        addLog(f'Sending random tts message', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
        await sendMessage(message, text, triggeredCommand = trigger)
        await sendMessage(message, f'>>> {randomMessage.content}', triggeredCommand = trigger, textToSpeech = True)

#save tts message ids to TTS_LOG
def saveTTS(message):
    addLog(f'Saving TTS message', inspect.currentframe().f_code.co_name, '', server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id, printLog = False)
    con = openConnection()
    cur = con.cursor()
    cur.execute('insert into TTS_LOG (MESSAGE_ID) values (?)', [message.id])
    con.commit()
    closeConnection(con)

#load client
load_dotenv('.env')
token = os.getenv('DISCORD_TOKEN')
database = os.getenv('GLOBALBOT_DATABASE')
finiteui = os.getenv('DISCORD_ID')
githubToken = os.getenv('GITHUB_TOKEN')
testServer = int(os.getenv('DISCORD_TEST_SERVER_ID'))
loop = ''
launchDate = date.today()
refreshInterval = 300
launchTime = datetime.now()
testMode = checkTestMode()

client = discord.Client()

@client.event
async def on_ready():
    #grab current event loop
    global loop
    loop = asyncio.get_event_loop()

    addLog(f'{client.user} has connected to Discord!', inspect.currentframe().f_code.co_name)

@client.event
async def on_message(message):
    #check if running in test mode
    if testMode:
        if message.guild.id != testServer:
            return

    #save tts
    if message.tts:
        saveTTS(message)

    #check command
    if message.author.bot:
        return
    elif message.content.startswith('!'):
        command = message.content[1:len(message.content)].split(' ')[0].lower()
        commandList = filterCommands(commands, message.guild.id)
        for x in commandList:
            if command == x.trigger.lower():
                commandType = ''
                if x.userCommand:
                    commandType = 'user '
                else:
                    if x.admin:
                        commandType = 'admin '
                        if int(message.author.id) != int(finiteui):
                            await sendMessage(message, 'This command is admin only.', deleteAfter = 20, triggeredCommand = x.trigger.lower())
                            return
                addLog(f'{message.guild} user {message.author} triggered {commandType}command [{x.trigger}].', inspect.currentframe().f_code.co_name, command, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, arguments = str(x.arguments), invokedUserDiscriminator = message.author.discriminator, invokedUserDisplayName = message.author.nick, messageID = message.id)
                async with message.channel.typing():
                    await x.run(message)
                break

@client.event
async def on_voice_state_update(member, voiceStateBefore, voiceStateAfter):
    con = openConnection()
    cur = con.cursor()

    if (voiceStateBefore.channel == None):
        beforeChannelID = None
        beforeChannelName = None
    else:
        beforeChannelID = voiceStateBefore.channel.id
        beforeChannelName = voiceStateBefore.channel.name

    if (voiceStateAfter.channel == None):
        afterChannelID = None
        afterChannelName = None
    else:
        afterChannelID = voiceStateAfter.channel.id
        afterChannelName = voiceStateAfter.channel.name

    #set event
    if (voiceStateBefore.channel != None and voiceStateAfter.channel == None):
        event = 'LEAVE_VOICE'
    elif (voiceStateBefore.channel == None and voiceStateAfter.channel != None):
        event = 'JOIN_VOICE'
    elif (voiceStateBefore.channel != voiceStateAfter.channel):
        event = 'CHANNEL_CHANGE'
    elif (not voiceStateBefore.self_deaf and voiceStateAfter.self_deaf):
        event = 'DEAFEN'
    elif (voiceStateBefore.self_deaf and not voiceStateAfter.self_deaf):
        event = 'UNDEAFEN'
    elif (not voiceStateBefore.self_mute and voiceStateAfter.self_mute):
        event = 'MUTE'
    elif (voiceStateBefore.self_mute and not voiceStateAfter.self_mute):
        event = 'UNMUTE'
    elif (not voiceStateBefore.self_stream and voiceStateAfter.self_stream):
        event = 'STREAM_START'
    elif (voiceStateBefore.self_stream and not voiceStateAfter.self_stream):
        event = 'STREAM_END'
    elif (not voiceStateBefore.self_video and voiceStateAfter.self_video):
        event = 'VIDEO_START'
    elif (voiceStateBefore.self_video and not voiceStateAfter.self_video):
        event = 'VIDEO_END'
    else:
        event = 'OTHER'

    addLog(f'{member.guild.id} user {member} voice state update {event}.', inspect.currentframe().f_code.co_name, '', server = member.guild.name, serverID = member.guild.id, invokedUser = member.name, invokedUserID = member.id, invokedUserDiscriminator = member.discriminator, invokedUserDisplayName = member.nick)

    record = [datetime.now(), str(member.guild), member.guild.id, member.guild.name, member.id, member.name, member.discriminator, member.display_name, member.bot, member.is_on_mobile(), voiceStateBefore.deaf, voiceStateBefore.mute, voiceStateBefore.self_mute, voiceStateBefore.self_deaf, voiceStateBefore.self_stream, voiceStateBefore.self_video, voiceStateBefore.afk, str(voiceStateBefore.channel), beforeChannelID, beforeChannelName, voiceStateAfter.deaf, voiceStateAfter.mute, voiceStateAfter.self_mute, voiceStateAfter.self_deaf, voiceStateAfter.self_stream, voiceStateAfter.self_video, voiceStateAfter.afk, str(voiceStateAfter.channel), afterChannelID, afterChannelName, event]

    cur.execute('insert into VOICE_ACTIVITY (RECORD_TIMESTAMP, GUILD, GUILD_ID, GUILD_NAME, USER_ID, USER_NAME, USER_DISCRIMINATOR, USER_DISPLAY_NAME, BOT, MOBILE, BEFORE_DEAF, BEFORE_MUTE, BEFORE_SELF_MUTE, BEFORE_SELF_DEAF, BEFORE_SELF_STREAM, BEFORE_SELF_VIDEO, BEFORE_AFK, BEFORE_CHANNEL, BEFORE_CHANNEL_ID, BEFORE_CHANNEL_NAME, AFTER_DEAF, AFTER_MUTE, AFTER_SELF_MUTE, AFTER_SELF_DEAF, AFTER_SELF_STREAM, AFTER_SELF_VIDEO, AFTER_AFK, AFTER_CHANNEL, AFTER_CHANNEL_ID, AFTER_CHANNEL_NAME, EVENT) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', record)

    con.commit()
    closeConnection(con)

@client.event
async def on_reaction_add(reaction, user):
    #for now just using this to log blacklisting of random attachment attachments with ❌
    #check if this was on a message sent by Global Bot
    if (reaction.message.author == client.user):
        #check if proper emoji
        if (str(reaction.emoji) == "\u274c"): 
            #check if this was a random attachment message
            if "Courtesy of" in reaction.message.content and "https://cdn.discordapp.com/attachments" in reaction.message.content:
                #check if we have 3 or more votes
                if reaction.count >= 2:
                    #first get some extra info. Need the attachment ID and original message ID
                    #url is https://cdn.discordapp.com/attachments/***CHANNEL-ID***/***ATTACHMENT-ID***/***ATTACHMENT_NAME***
                    extractor = URLExtract()
                    urls = extractor.find_urls(reaction.message.content)
                    
                    if len(urls) > 0:
                        attachmentURL = urls[0]
                        attachmentID = attachmentURL.replace(f'https://cdn.discordapp.com/attachments/', '')
                        attachmentID = attachmentID.split('/')[1]
                        result = select(f"select RECORD_ID, URL, MESSAGE_ID from MESSAGE_ATTACHMENT_HISTORY where ID = '{attachmentID}'")
                        if len(result) > 0:
                            attachmentLocalID = result[0]['RECORD_ID']
                            originalMessageID = result[0]['MESSAGE_ID']
                        else:
                            attachmentLocalID = None
                            originalMessageID = None

                        #build full blacklister string
                        blacklisters = ''
                        userList = await reaction.users().flatten()
                        for i in userList:
                            if blacklisters == '':
                                blacklisters = str(i.id)
                            else:
                                blacklisters = blacklisters + ', ' + str(i.id)

                        addLog(f'User {user} blacklisting attachment {attachmentID} in guild {reaction.message.guild.id}', inspect.currentframe().f_code.co_name, '', server = reaction.message.guild.name, serverID = reaction.message.guild.id, channel = reaction.message.channel.name, channelID = reaction.message.channel.id, invokedUser = user.name, invokedUserID = user.id, invokedUserDiscriminator = user.discriminator, invokedUserDisplayName = user.nick, messageID = reaction.message.id)
                    
                        #here add it to the blacklist table
                        #check if it already exists first
                        
                        existingRecord = select(f"select RECORD_ID from RANDOM_ATTACHMENT_BLACKLIST where ATTACHMENT_ID = '{attachmentID}'")

                        con = openConnection()
                        cur = con.cursor()

                        #still need to do something if this a new instance of the same attachment
                        if (len(existingRecord) > 0):
                            cur.execute(f"update RANDOM_ATTACHMENT_BLACKLIST set ALL_BLACKLISTERS = '{blacklisters}' where RECORD_ID = {existingRecord[0]['RECORD_ID']}")
                        else:
                            data = [datetime.now(), reaction.message.guild.id, user.id, user.name, user.discriminator, reaction.message.id, attachmentID, attachmentLocalID, attachmentURL, originalMessageID, blacklisters]
                            cur.execute('insert into RANDOM_ATTACHMENT_BLACKLIST (RECORD_TIMESTAMP, GUILD_ID, BLACKLISTER_ID, BLACKLISTER_NAME, BLACKLISTER_DISCRIMINATOR, RANDOM_ATTACHMENT_MESSAGE_ID, ATTACHMENT_ID, ATTACHMENT_LOCAL_ID, ATTACHMENT_URL, ORIGINAL_MESSAGE_ID, ALL_BLACKLISTERS) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', data)
                        
                        con.commit()
                        closeConnection(con)

                        await reaction.message.add_reaction("\u2705")

#load commands
commands = []
commands.append(command('help', 'Displays a list of available commands'))
commands.append(command('restart', 'Restarts the bot', 'restart', admin = True))
commands.append(command('addusercommand', 'Adds a new simple message command. Format: !addusercommand command, message', 'addUserCommand'))
commands.append(command('deleteusercommand', 'Deletes a user message command. Format: !deleteusercommand command', 'deleteUserCommand'))
commands.append(command('randompin', 'Sends a random pinned message', 'sendRandomPinnedMessage'))
commands.append(command('kick', 'Kicks a user from voice. Format: !kick @user', 'kickUser', admin = True))
commands.append(command('usercommands', 'Displays a list of available user commands', 'listUserCommands'))
commands.append(command('setstatus', 'Sets the status of the bot', 'setStatus', admin = True))
commands.append(command('setname', 'Sets the display name of the bot', 'setName'))
commands.append(command('demote', 'Moves a user to the Tier 1 voice chat. Format: !demote @user'))
commands.append(command('backup', 'Starts a server backup.', admin = True))
commands.append(command('admincommands', 'Displays a list of available admin commands', 'listAdminCommands', admin = True))
commands.append(command('kill', 'Ends the bot program', 'kill', admin = True))
commands.append(command('deletelastbotmessage', 'Deletes the last message sent by the bot', 'deleteLastBotMessage', admin = True))
commands.append(command('roulette', 'Kicks a random user from voice chat'))
commands.append(command('ra', 'Sends a random attachment from the channel history', 'randomAttachment'))
commands.append(command('randomvideo', 'Sends a random youtube video from the channel history', 'randomVideo'))
commands.append(command('move', 'Moves a user into a specified voice channel. Format: !move channel @user', admin = True))
commands.append(command('clearbackup', 'Clears the backup of this server.', 'clearBackup', admin = True))
commands.append(command('update', 'Updates the source code from Github and restarts', admin = True))
commands.append(command('uptime', 'Displays the launch time and uptime of the bot'))
commands.append(command('refresh', 'Runs a backup of every guild the bot is in, then restarts the bot', admin = True))
commands.append(command('randommessage', 'Sends a random message from the channel. Optionally a user can be specified. Format: !randommessage @user', 'randomMessage'))
commands.append(command('source', 'Sends the link to the bot source code'))
commands.append(command('getbackup', 'Creates and sends a backup of the server', 'getBackup'))
commands.append(command('guilds', 'Displays a list of guilds the bot is connected to', admin = True))
commands.append(command('voicestats', 'Displays voice stats for the specified user. Optionally a user can be specified. Format: !voicestats @user', 'voiceStats'))
commands.append(command('rtts', 'Sends a random tts message from the server', 'randomtts'))
loadUserCommands()

#launch the refresh timer
timer = threading.Timer(refreshInterval, callRefresh)
timer.start()

#run the bot            
addLog('Running client...', inspect.currentframe().f_code.co_name)
client.run(token)

