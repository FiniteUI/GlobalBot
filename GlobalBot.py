#GlobalBot.py

import os
import discord
import sqlite3
import inspect
import random
import re
import time
from datetime import datetime, date
from dotenv import load_dotenv
from urlextract import URLExtract
import asyncio
import threading
import pytz
from PIL import Image
import pytesseract
import io
from PIL import UnidentifiedImageError

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
    format = ''
    parameters = ''
    fullDescription = ''

    def __init__(self, trigger, description, function = '', userCommand = False, arguments = '', admin = False, hidden = False, server = -1, parameters = ''):
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
        self.parameters = parameters

        self.format = f'!{self.trigger} {self.parameters}'.strip()

        if self.parameters != '':
            self.fullDescription = f'{self.description} Format: {self.format}'
        else:
            self.fullDescription = self.description

    async def run(self, message, includeCommand = False):
        if self.userCommand:
            tempArguments = self.arguments[:]
            if includeCommand:
                tempArguments[0] = f'**{self.trigger}**: {tempArguments[0]}'
            await globals()[self.function](message, *tempArguments, triggeredCommand = self.trigger)
        else:
            await globals()[self.function](message, trigger = self.trigger)

#utility functions

#returns and open connection to the database
def openConnection():
    con = sqlite3.connect(database)
    con.row_factory = sqlite3.Row
    return con

#closes the given database connection
def closeConnection(con):
    con.close()

#executes a select statement from the database, returns the result
def select(SQL, trigger = None):
    addLog(f'Executing select SQL [{SQL}]', inspect.currentframe().f_code.co_name, command = trigger)
    con = openConnection()
    cur = con.cursor()
    cur.execute(SQL)
    x = cur.fetchall() 
    closeConnection(con)
    return x

#chunks a string into pieces of size length, but respects line breaks
def chunkStringNewLine(string, length):
    splitString = string.split('\n')
    if splitString[0] == '':
        splitString.pop(0)
    returnStrings = []
    tempString = ''
    for i in splitString:
        if len(i) + len(tempString) > length:
            returnStrings.append(tempString)
            tempString = i
        else:
            tempString = tempString + '\n' +  i
    returnStrings.append(tempString)
    addLog(f'chunkStringNewLine returning chunked string: {returnStrings}', inspect.currentframe().f_code.co_name)
    return returnStrings

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

#remove the command from the message
def removeCommand(message, command):
    redata = re.compile(re.escape(command), re.IGNORECASE)
    return redata.sub('', message).strip()

#grabs the top stored message id
def grabTopStoredMesage(guild, trigger):
    x = select(f'select created_at from MESSAGE_HISTORY where GUILD_ID = {guild.id} order by created_at desc limit 1', trigger = trigger)
    if x == []:
        return None
    else:
        return x[0][0]
    
#converts a UTC datetime into a specific timezone
def convertUTCToTimezone(utc_timestamp, timezone):
    if type(utc_timestamp) is str:
        #timestamp may or may not have timezone on it
        if utc_timestamp.find('+') == -1:
            utc_timestamp = utc_timestamp + "+00:00"
        utc_timestamp = datetime.strptime(utc_timestamp, '%Y-%m-%d %H:%M:%S.%f%z')

    utc = pytz.timezone('UTC')

    if utc_timestamp.tzinfo == None:
        utc_timestamp = utc.localize(utc_timestamp)

    newTimezone = pytz.timezone(timezone)
    newTimestamp = utc_timestamp.astimezone(newTimezone)
    return newTimestamp

#updates database flags
def updateDatabaseFlags():
    con = openConnection()
    cur = con.cursor()
    cur.execute("update MESSAGE_ATTACHMENT_HISTORY set IMAGE = 1 where lower(FILENAME) like '%.png' or lower(FILENAME) like '%.jpg' or lower(FILENAME) like '%.jpeg' or lower(FILENAME) like '%.mp4' or lower(FILENAME) like '%.gif' or lower(FILENAME) like '%.apng' or lower(FILENAME) like '%.avif' or lower(FILENAME) like '%.svg' or lower(FILENAME) like '%.webp' or lower(FILENAME) like '%.heic' or lower(FILENAME) like '%.tif' or lower(FILENAME) like '%.tiff' or lower(FILENAME) like '%.bmp';")
    cur.execute("update MESSAGE_HISTORY set YOUTUBE = 1 where (lower(content) like '%youtube.com%' or '%youtu.be%');")
    cur.execute("update MESSAGE_HISTORY set SPOTIFY = 1 where (lower(content) like '%open.spotify.com/%');")
    con.commit()
    closeConnection(con)

#add the fullbackup timer
def dailyBackup():
    global loop
    if date.today() != launchDate:
        thisRefresh = asyncio.run_coroutine_threadsafe(fullBackup(silent = True), loop)
        thisRefresh.result()
    else:
        timer = threading.Timer(backupInterval, dailyBackup)
        timer.start()

#check if the test.txt file exists
def checkTestMode():
    directory = os.path.dirname(os.path.realpath(__file__))
    directory = os.path.join(directory, 'test.txt')
    if (os.path.isfile(directory)):
        print('The Bot is launching in TEST MODE...')
        return True
    else:
        return False
    
#save tts message ids to TTS_LOG
def saveTTS(message):
    addLog(f'Saving TTS message', inspect.currentframe().f_code.co_name, '', server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, messageID = message.id, printLog = False)
    con = openConnection()
    cur = con.cursor()
    cur.execute('insert into TTS_LOG (MESSAGE_ID) values (?)', [message.id])
    con.commit()
    closeConnection(con)

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
    
#prints a message in the shell and adds it to BOT_LOG
def addLog(message, function = None, command = None, arguments = None, targetUser = None, targetUserID = None, server = None, serverID = None, channel = None, channelID = None, invokedUser = None, invokedUserID = None, messageID = None, printLog = True, target = None):
    con = openConnection()
    cur = con.cursor()
    if printLog:
        print(f'{datetime.now()}: {message}')
    data = [datetime.now(), message, server, serverID, channel, channelID, invokedUser, invokedUserID, command, arguments, function, targetUser, targetUserID, messageID, target]
    cur.execute('insert into BOT_LOG (LOG_TIME, MESSAGE, SERVER, SERVER_ID, CHANNEL, CHANNEL_ID, INVOKED_USER, INVOKED_USER_ID, COMMAND, ARGUMENTS, FUNCTION, TARGET_USER, TARGET_USER_ID, MESSAGE_ID, TARGET) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', data)
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

#loads user commands from USER_COMMANDS
def loadUserCommands():
    addLog('Loading user commands...', inspect.currentframe().f_code.co_name)
    userMessages = select('select * from USER_COMMANDS')
    for x in userMessages:
        if x[3]:
            commands.append(command(str(x[1]), f'Sends the text to speech message "{x[2]}"', 'sendMessage', True, [x[2], x[3]], server = x[5]))
        else:
            commands.append(command(str(x[1]), f'Sends the message "{x[2]}"', 'sendMessage', True, [x[2], x[3]], server = x[5]))

#sends a message to the channel
async def sendMessage(triggerMessage, sendMessage, textToSpeech = False, deleteAfter = None, embedItem = None, embedItems = None, triggeredCommand = None, codeBlock = False, attachment = None):
    if sendMessage.strip() == '':
        return

    addLog(f'''Sending message "{sendMessage}" to channel {triggerMessage.channel} in server {triggerMessage.guild}, {triggerMessage.guild.id}.''', inspect.currentframe().f_code.co_name, server = triggerMessage.guild.name, serverID = triggerMessage.guild.id, channel = triggerMessage.channel.name, channelID = triggerMessage.channel.id, invokedUser = triggerMessage.author.name, invokedUserID = triggerMessage.author.id, command = triggeredCommand)

    #message limit is 2000 characters, we may add 2 if codeBlock, so our limit is 1998
    if len(sendMessage) > 1998:
        x = chunkStringNewLine(sendMessage, 1998)
        for i in x:
            if i != '':
                if codeBlock:
                    await triggerMessage.channel.send(f'`{i}`', tts = textToSpeech, delete_after = deleteAfter, embed = embedItem, file = attachment)
                else:
                    await triggerMessage.channel.send(i, tts = textToSpeech, delete_after = deleteAfter, embed = embedItem, file = attachment)
    else:
        if codeBlock:
            await triggerMessage.channel.send(f'`{sendMessage}`', tts = textToSpeech, delete_after = deleteAfter, embed = embedItem, file = attachment)
        else:
            await triggerMessage.channel.send(sendMessage, tts = textToSpeech, delete_after = deleteAfter, embed = embedItem, file = attachment)

#admin commands

#sets the bots status
async def setStatus(message, trigger):
    y = discord.Game(removeCommand(message.content, f'!{trigger}'))
    await sendMessage(message, f'Setting status to "{y}"', deleteAfter = 10, triggeredCommand = trigger, codeBlock = True)
    addLog(f'Setting status to "{y}"', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, messageID = message.id)
    await client.change_presence(status = discord.Status.online, activity = y)

#sets the bots status
async def setName(message, trigger):
    y = removeCommand(message.content, f'!{trigger}')

    if len(y) > 32:
        await sendMessage(message, f'Display names must be 32 characters or less.', deleteAfter = 10, triggeredCommand = trigger, codeBlock = True)
    else:
        await sendMessage(message, f'Setting display name to "{y}"', triggeredCommand = trigger, codeBlock = True)
        addLog(f'Setting display name to "{y}"', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, messageID = message.id, target = y)
        member = message.guild.get_member(client.user.id)
        await member.edit(nick = y)

#launches a backup of the server
async def backup(message = None, trigger = None, silent = False, fromMessage = True, overrideGuild = None):
    if fromMessage:
        guild = message.guild
        invokedUser = message.author
        messageID = message.id
        channelName = message.channel.name
        channelID = message.channel.id
    else:
        guild = overrideGuild
        invokedUser = client.user
        messageID = None
        silent = True
        channelName = None
        channelID = None

    recordLimit = 10000

    addLog(f'Backing up server {guild.name}...', inspect.currentframe().f_code.co_name, trigger, server = guild.name, serverID = guild.id, channel = channelName, channelID = channelID, invokedUser = invokedUser.name, invokedUserID = invokedUser.id, messageID = messageID, target = guild.id)
    if not silent:
        await sendMessage(message, f'Backing up server {guild.name}...', triggeredCommand = trigger, codeBlock = True)
    startTime = time.time()
    top = grabTopStoredMesage(guild, trigger)
    if top == None:
        top = '2010-01-01 12:00:00.000000+00:00'
    
    if top.find('+') == -1:
        top = top + "+00:00"
    top = datetime.strptime(top, '%Y-%m-%d %H:%M:%S.%f%z')

    addLog(f'Last stored message timestamp: {top}...', inspect.currentframe().f_code.co_name, trigger, server = guild.name, serverID = guild.id, channel = channelName, channelID = channelID, invokedUser = invokedUser.name, invokedUserID = invokedUser.id, messageID = messageID, target = guild.id)
    
    records = []
    attachments = []

    for i in guild.text_channels:
        async for j in i.history(limit = None, oldest_first = True, after = top):
            records.append([datetime.now(), j.tts, str(j.type), str(j.author), str(j.system_content), str(j.channel), j.mention_everyone, j.id, str(j.attachments), j.pinned, str(j.reactions), str(j.guild), str(j.raw_mentions), j.created_at, j.edited_at, j.jump_url, str(j.is_system()), j.guild.id, j.author.id, j.author.display_name, j.channel.id, j.author.bot])

            #add attachments
            for a in j.attachments:
                if (a.filename.endswith(('.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG', '.heic', '.HEIC', '.webp', '.WEBP'))):

                    rawData = await a.read()
                    
                    try:
                        image = Image.open(io.BytesIO(rawData))
                        imageText = pytesseract.image_to_string(image)
                        imageText = imageText.upper()
                        image.close()
                    except (TypeError, UnidentifiedImageError):
                        imageText = None
                else:
                    imageText = None

                #not actually going to save this for now, so clearing
                rawData = None

                attachments.append([a.id, a.filename, a.url, a.is_spoiler(), j.id, j.guild.id, imageText])

            if len(records) + len(attachments) > recordLimit:
                addLog(f'Record limit reached, saving partial and continuing...', inspect.currentframe().f_code.co_name, trigger, server = guild.name, serverID = guild.id, channel = channelName, channelID = channelID, invokedUser = invokedUser.name, invokedUserID = invokedUser.id, messageID = messageID)

                con = openConnection()
                cur = con.cursor()

                #save messages
                cur.executemany('insert into MESSAGE_HISTORY (RECORD_TIMESTAMP, TTS, TYPE, AUTHOR, CONTENT, CHANNEL, MENTION_EVERYONE, ID, ATTACHMENTS, PINNED, REACTIONS, GUILD, RAW_MENTIONS, CREATED_AT, EDITED_AT, JUMP_URL, IS_SYSTEM, GUILD_ID, AUTHOR_ID, AUTHOR_DISPLAY_NAME, CHANNEL_ID, AUTHOR_BOT) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', records)
                records = []

                #save attachments
                cur.executemany('insert into MESSAGE_ATTACHMENT_HISTORY (ID, FILENAME, URL, IS_SPOILER, MESSAGE_ID, GUILD_ID, IMAGE_TEXT) values (?, ?, ?, ?, ?, ?, ?)', attachments)
                attachments = []

                con.commit()
                closeConnection(con)

    con = openConnection()
    cur = con.cursor()

    #save messages
    cur.executemany('insert into MESSAGE_HISTORY (RECORD_TIMESTAMP, TTS, TYPE, AUTHOR, CONTENT, CHANNEL, MENTION_EVERYONE, ID, ATTACHMENTS, PINNED, REACTIONS, GUILD, RAW_MENTIONS, CREATED_AT, EDITED_AT, JUMP_URL, IS_SYSTEM, GUILD_ID, AUTHOR_ID, AUTHOR_DISPLAY_NAME, CHANNEL_ID, AUTHOR_BOT) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', records)

    #save attachments
    cur.executemany('insert into MESSAGE_ATTACHMENT_HISTORY (ID, FILENAME, URL, IS_SPOILER, MESSAGE_ID, GUILD_ID, IMAGE_TEXT) values (?, ?, ?, ?, ?, ?, ?)', attachments)

    con.commit()
    closeConnection(con)

    totaltime = time.time() - startTime
    if not silent:
        await sendMessage(message, f'Server {guild.name} backed up in {totaltime} seconds.', triggeredCommand = trigger, codeBlock = True)
    addLog(f'Server {guild.name} backed up in {totaltime} seconds.', inspect.currentframe().f_code.co_name, trigger, server = guild.name, serverID = guild.id, channel = channelName, channelID = channelID, invokedUser = invokedUser.name, invokedUserID = invokedUser.id, messageID = messageID)

#clears the backup of this server
async def clearBackup(message, trigger):
    addLog(f'Deleting backup for server {message.guild.id}', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, messageID = message.id, target = message.guild.id)
    await sendMessage(message, f'Deleting backup for server {message.guild.name}', triggeredCommand = trigger, codeBlock = True)
    con = openConnection()
    cur = con.cursor()
    cur.execute('delete from MESSAGE_HISTORY where GUILD_ID = ?', [message.guild.id])
    cur.execute('delete from MESSAGE_ATTACHMENT_HISTORY where GUILD_ID = ?', [message.guild.id])
    con.commit()
    closeConnection(con)

#displays a list of admin commands
async def listAdminCommands(message, trigger):
    addLog(f'Listing admin commands', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, messageID = message.id)
    x = ''
    s = filter(filterAdminFunctions, commands)
    for i in s:
        x = x + f'''**!{i.trigger.ljust(20)}** - \t{i.fullDescription}\n'''
    await sendMessage(message, x, triggeredCommand = trigger)

#deletes the last bot message
async def deleteLastBotMessage(message, trigger):
    #messages = await message.channel.history(limit = 100).flatten()
    messages = [message async for message in message.channel.history(limit = 100)]
    for i in messages:
        if i.author == client.user:
            addLog(f'Deleting last bot message {i.id}...', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, messageID = message.id, target = i.id)
            await sendMessage(message, 'Deleting last bot message...',  deleteAfter = 10, triggeredCommand = trigger, codeBlock = True)
            await i.delete()
            return
    await sendMessage(message, 'No bot messages found in the last 100 messages',  deleteAfter = 20, triggeredCommand = trigger, codeBlock = True)

#nightly backup
async def fullBackup(message = None, trigger = None, silent = False):
    if not silent:
        startTime = time.time()
        await sendMessage(message, "Starting Global Refresh...", textToSpeech = False, triggeredCommand = trigger, codeBlock = True)
    if len(client.guilds) > 0:
        for guild in client.guilds:
            await backup(trigger = 'refresh', silent = True, fromMessage = False, overrideGuild = guild)
    updateDatabaseFlags()
    if not silent:
        totaltime = time.time() - startTime
        await sendMessage(message, f"Global Refresh finished in {totaltime} seconds.", textToSpeech = False, triggeredCommand = trigger, codeBlock = True)

#regular commands

#lists available commands
async def help(message, trigger):
    addLog(f'Listing commands', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, messageID = message.id)
    x = '**Know what you own:**\n'
    s = filter(filterStandardFunctions, commands)
    for i in s:
        x = x + f'''**!{i.trigger.ljust(20)}** - \t{i.fullDescription}\n'''
    await sendMessage(message, x, triggeredCommand = trigger)

#lists available user commands
async def listUserCommands(message, trigger):
    addLog(f'Listing user commands', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, messageID = message.id)
    x = ''
    s = filterCommands(commands, message.guild.id)
    s = filter(filterUserFunctions, s)
    #extractor = URLExtract()
    for i in s:
        if i.server == message.guild.id:
            #this is way too long in our server
            #may add this as a seperate function later
            #description = i.fullDescription
            #urls = extractor.find_urls(i.description)
            #for url in urls:
            #    description = description.replace(url, f'<{url}>')
            #x = x + f'''**!{i.trigger.ljust(20)}** - \t{description}\n'''
            if len(x) + 2 + len(i.trigger) > 2000:
                await sendMessage(message, x, triggeredCommand = trigger)
                x = ''
            
            if x != '':
                x += ', ' + i.trigger
            else:
                x += '**User Commands:** ' + i.trigger

    if x != '':
        await sendMessage(message, x, triggeredCommand = trigger)

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
            await sendMessage(message, f'Adding user command [{newTrigger}]', triggeredCommand = newTrigger, codeBlock = True)
            saveUserCommand(message, newTrigger, messageToSend, tts)
            addLog(f'Adding user command [{newTrigger}]', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, messageID = message.id, target = newTrigger)
    else:
        await sendMessage(message, 'Invalid parameters. Format is !addusercommand command, message',  deleteAfter = 20, triggeredCommand = trigger)

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
            addLog(f'Deleting user command [{x}] from server {message.guild.name}', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, messageID = message.id, target = x.lower())
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

        addLog(f'Sending random pinned message {pin[x]}', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, messageID = message.id)
        await sendMessage(message, pin[x].jump_url, triggeredCommand = trigger)

#kicks a random user out of voice chat
async def roulette(message, trigger):
    channels = message.guild.voice_channels
    x = []
    for i in channels:
        for j in i.members:
            x.append(j)
    if len(x) > 0:
        userIndex = random.randrange(0, len(x), 1)
        await sendMessage(message, f'Kicking user {x[userIndex].display_name} from voice', triggeredCommand = trigger, codeBlock = True)
        addLog(f'Kicking user {x[userIndex].display_name} from voice', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, targetUser = x[userIndex].name, targetUserID = x[userIndex].id, messageID = message.id)
        await x[userIndex].move_to(None)  
    else:
        await sendMessage(message, 'There are no users currently in voice chat', deleteAfter = 10, triggeredCommand = trigger, codeBlock = True)  

#sends a random file attachment from chat
async def randomAttachment(message, trigger):
    user = message.mentions
    filter = ''
    if user != []:
        filter = f' and author_id = {user[0].id}'
        targetUser = user[0].name
        targetUserID = user[0].id
    else:
        targetUser = None
        targetUserID = None

    numberOfAttachments = removeCommand(message.content, f'!{trigger}')
    numberOfAttachments = re.sub(r"<.*>", "", numberOfAttachments).strip()
    if numberOfAttachments.isnumeric():
        numberOfAttachments = int(numberOfAttachments)
        if numberOfAttachments > 10:
            numberOfAttachments = 10
            await sendMessage(message, '!ra has a 10 attachment maximum.', triggeredCommand = trigger, deleteAfter = 10, codeBlock = True)
    else:
        numberOfAttachments = 1

    for i in range(numberOfAttachments):
        record = select(f"select message_attachment_history.id, author_id, url, created_at from message_attachment_history left join message_history on message_attachment_history.message_id = message_history.id where IMAGE = 1 and message_history.guild_id = {message.guild.id}{filter} and message_attachment_history.id not in (select ATTACHMENT_ID from RANDOM_ATTACHMENT_BLACKLIST where GUILD_ID = {message.guild.id}) order by RANDOM() limit 1", trigger = trigger)
        if len(record) > 0:
            attachment = record[0][2]
            author = message.guild.get_member(int(record[0][1]))
            central_timestamp = convertUTCToTimezone(record[0][3], 'US/Central')
            central_timestamp = datetime.strftime(central_timestamp, '%A %B %d, %Y at %I:%M %p')
            
            addLog(f'Sending random attachment', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, messageID = message.id, targetUser = targetUser, targetUserID = targetUserID, target = record[0][0])
            await sendMessage(message, f'Courtesy of {author.mention} on {central_timestamp}\n{attachment}', triggeredCommand = trigger)
            
#sends a random youtube video from chat
async def randomVideo(message, trigger):
    user = message.mentions
    filter = ''
    if user != []:
        filter = f' and author_id = {user[0].id}'
        targetUser = user[0].name
        targetUserID = user[0].id
    else:
        targetUser = None
        targetUserID = None

    videos = select(f"select distinct id, author_id, created_at, content from MESSAGE_HISTORY where YOUTUBE = 1 and author <> 'GlobalBot#9663' and GUILD_ID = {message.guild.id}{filter} order by RANDOM() limit 1", trigger = trigger)
    if len(videos) > 0:
        video = videos[0][3]
        extractor = URLExtract()
        urls = extractor.find_urls(video)

        central_timestamp = convertUTCToTimezone(videos[0][2], 'US/Central')
        central_timestamp = datetime.strftime(central_timestamp, '%A %B %d, %Y at %I:%M %p')

        author = client.get_user(videos[0][1])

        addLog(f'Sending random video', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, messageID = message.id, targetUser = targetUser, targetUserID = targetUserID, target = videos[0][0])
        await sendMessage(message, f'Courtesy of {author.mention} on {central_timestamp}\n{urls[0]}', triggeredCommand = trigger)

#sends a random spotify link from chat
async def randomSpotify(message, trigger):
    user = message.mentions
    filter = ''
    if user != []:
        filter = f' and author_id = {user[0].id}'
        targetUser = user[0].name
        targetUserID = user[0].id
    else:
        targetUser = None
        targetUserID = None

    links = select(f"select distinct id, author_id, created_at, content from MESSAGE_HISTORY where SPOTIFY = 1 and author <> 'GlobalBot#9663' and GUILD_ID = {message.guild.id}{filter} order by RANDOM() limit 1", trigger = trigger)

    if len(links) > 0:
        link = links[0][3]
        extractor = URLExtract()
        urls = extractor.find_urls(link)

        central_timestamp = convertUTCToTimezone(links[0][2], "US/Central")
        central_timestamp = datetime.strftime(central_timestamp, '%A %B %d, %Y at %I:%M %p')

        author = client.get_user(links[0][1])

        addLog(f'Sending random spotify link', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, messageID = message.id, targetUser = targetUser, targetUserID = targetUserID, target = links[0][0])
        await sendMessage(message, f'Courtesy of {author.mention} on {central_timestamp}\n{urls[0]}', triggeredCommand = trigger)

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
        targetUser = user[0].name
        targetUserID = user[0].id
    else:
        targetUser = None
        targetUserID = None

    messages = select(f"select distinct id from MESSAGE_HISTORY where content <> '' and guild_id = {message.guild.id} and channel_id = {message.channel.id}{filter} order by RANDOM() limit 1", trigger)
    if len(messages) > 0:
        randomMessage = messages[0][0]
        randomMessage = await message.channel.fetch_message(randomMessage)

        central_timestamp = convertUTCToTimezone(randomMessage.created_at, 'US/Central')
        central_timestamp = datetime.strftime(central_timestamp, '%A %B %d, %Y at %I:%M %p')

        text = f'On {central_timestamp}, {randomMessage.author.mention} said:\nLink: {randomMessage.jump_url}\n>>> {randomMessage.content}'
        addLog(f'Sending random message', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, messageID = message.id, targetUser = targetUser, targetUserID = targetUserID, target = messages[0][0])
        await sendMessage(message, text, triggeredCommand = trigger)

#lists the guilds the bot is connected to
async def guilds(message, trigger):
    text = 'GlobalBot is connected to the following guilds:\n'
    for x in client.guilds:
        text = f'{text}{x.id}, {x.name}\n'
    await sendMessage(message, text, triggeredCommand = trigger, codeBlock = True)

#sends tts message from the server
async def randomtts(message, trigger):
    user = message.mentions
    filter = ''
    if user != []:
        filter = f' and author_id = {user[0].id}'
        targetUser = user[0].name
        targetUserID = user[0].id
    else:
        targetUser = None
        targetUserID = None

    #grab a random message
    messages = select(f"select distinct MESSAGE_ID, CHANNEL_ID from TTS_LOG A inner join MESSAGE_HISTORY B on A.MESSAGE_ID = B.ID where content <> '' and guild_id = {message.guild.id} and AUTHOR_ID <> {client.user.id}{filter} order by RANDOM() limit 1", trigger)
    if len(messages) > 0:
        randomMessage = messages[0][0]
        channel = await message.guild.fetch_channel(messages[0][1])
        randomMessage = await channel.fetch_message(randomMessage)

        print(randomMessage.created_at)
        central_timestamp = convertUTCToTimezone(randomMessage.created_at, 'US/Central')
        central_timestamp = datetime.strftime(central_timestamp, '%A %B %d, %Y at %I:%M %p')

        text = f'On {central_timestamp}, {randomMessage.author.mention} said:\nLink: {randomMessage.jump_url}\n'
        addLog(f'Sending random tts message', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, messageID = message.id, targetUser = targetUser, targetUserID = targetUserID)
        await sendMessage(message, text, triggeredCommand = trigger)
        await sendMessage(message, f'>>> {randomMessage.content}', triggeredCommand = trigger, textToSpeech = True)

#sends user command from the server
async def randomUserCommand(message, trigger):
    #get message list
    userCommands = filterCommands(commands, message.guild.id)
    userCommands = filter(filterUserFunctions, userCommands)
    userCommands = list(userCommands)

    #grab a random message
    if len(userCommands) > 0:
        x = random.randrange(0, len(userCommands), 1)
        randomUserCommand = userCommands[x]
    
        addLog(f'{message.guild} user {message.author} triggered user command [{randomUserCommand.trigger}] via !ruc.', inspect.currentframe().f_code.co_name, randomUserCommand.trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, arguments = str(randomUserCommand.arguments), messageID = message.id, target = randomUserCommand.trigger)
        #async with message.channel.typing():
        await randomUserCommand.run(message, includeCommand = True)

#sends a random file attachment with the specified text from chat
async def randomAttachmentSearch(message, trigger):
    filter = removeCommand(message.content, f'!{trigger}')

    if(filter != ""):
        filter = f" and IMAGE_TEXT like '%{filter.upper()}%'"
        attachments = select(f"select message_attachment_history.id, author_id, url, created_at from message_attachment_history left join message_history on message_attachment_history.message_id = message_history.id where IMAGE = 1 and message_history.guild_id = {message.guild.id}{filter} and message_attachment_history.id not in (select ATTACHMENT_ID from RANDOM_ATTACHMENT_BLACKLIST where GUILD_ID = {message.guild.id}) order by RANDOM() limit 1", trigger = trigger)
        if len(attachments) > 0:
            attachment = attachments[0][2]
            author = message.guild.get_member(int(attachments[0][1]))

            central_timestamp = convertUTCToTimezone(attachments[0][3], "US/Central")
            central_timestamp = datetime.strftime(central_timestamp, '%A %B %d, %Y at %I:%M %p')

            addLog(f'Sending random attachment', inspect.currentframe().f_code.co_name, trigger, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, messageID = message.id, target = attachments[0][0])
            await sendMessage(message, f'Courtesy of {author.mention} on {central_timestamp}\n{attachment}', triggeredCommand = trigger)
        else:
            await sendMessage(message, 'No images matching passed filter found.', triggeredCommand = trigger, deleteAfter = 10, codeBlock = True)
    else:
        await sendMessage(message, 'Invalid arguments. Correct format is !rasearch search-text', triggeredCommand = trigger, deleteAfter = 10, codeBlock = True)

#main bot code

#load client
testMode = checkTestMode()
    
directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), '.env')
load_dotenv(directory)

if (testMode):
    database = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'GlobalBotData.db')
else:
    database = os.getenv('GLOBALBOT_DATABASE')

token = os.getenv('DISCORD_TOKEN')
finiteui = os.getenv('DISCORD_ID')
githubToken = os.getenv('GITHUB_TOKEN')
testServer = int(os.getenv('DISCORD_TEST_SERVER_ID'))
loop = ''
launchDate = date.today()
backupInterval = 300
launchTime = datetime.now()
players = {}

intents = discord.Intents.all()
intents.members = True

client = discord.Client(intents=intents)

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
                addLog(f'{message.guild} user {message.author} triggered {commandType}command [{x.trigger}].', inspect.currentframe().f_code.co_name, command, server = message.guild.name, serverID = message.guild.id, channel = message.channel.name, channelID = message.channel.id, invokedUser = message.author.name, invokedUserID = message.author.id, arguments = str(x.arguments), messageID = message.id)
                #async with message.channel.typing():
                await x.run(message)
                break

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
                        userList = [user async for user in reaction.users()]
                        for i in userList:
                            if blacklisters == '':
                                blacklisters = str(i.id)
                            else:
                                blacklisters = blacklisters + ', ' + str(i.id)

                        addLog(f'User {user} blacklisting attachment {attachmentID} in guild {reaction.message.guild.id}', inspect.currentframe().f_code.co_name, '', server = reaction.message.guild.name, serverID = reaction.message.guild.id, channel = reaction.message.channel.name, channelID = reaction.message.channel.id, invokedUser = user.name, invokedUserID = user.id, messageID = reaction.message.id)
                    
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

                        #delete message
                        await reaction.message.delete(delay = 2)

#load commands
commands = []

#admin commands
commands.append(command('setstatus', 'Sets the status of the bot', 'setStatus', admin = True, parameters = 'status'))
commands.append(command('backup', 'Starts a server backup.', admin = True))
commands.append(command('setname', 'Sets the display name of the bot', 'setName', admin = True))
commands.append(command('admincommands', 'Displays a list of available admin commands', 'listAdminCommands', admin = True))
commands.append(command('deletelastbotmessage', 'Deletes the last message sent by the bot', 'deleteLastBotMessage', admin = True))
commands.append(command('clearbackup', 'Clears the backup of this server.', 'clearBackup', admin = True))
commands.append(command('fullbackup', 'Runs a backup of every guild the bot is in', 'fullBackup', admin = True))
commands.append(command('guilds', 'Displays a list of guilds the bot is connected to', admin = True))

#regular commands
commands.append(command('help', 'Displays a list of available commands'))
commands.append(command('addusercommand', 'Adds a new simple message command.', 'addUserCommand', parameters = 'command, message'))
commands.append(command('deleteusercommand', 'Deletes a user message command.', 'deleteUserCommand', parameters = 'command'))
commands.append(command('randompin', 'Sends a random pinned message', 'sendRandomPinnedMessage'))
commands.append(command('usercommands', 'Displays a list of available user commands', 'listUserCommands'))
commands.append(command('roulette', 'Kicks a random user from voice chat'))
commands.append(command('ra', 'Sends a random attachment from the server history', 'randomAttachment', parameters = 'optional-@user, optional-numberOfAttachments'))
commands.append(command('randomvideo', 'Sends a random youtube video from the server history', 'randomVideo', parameters = 'optional-@user'))
commands.append(command('uptime', 'Displays the launch time and uptime of the bot'))
commands.append(command('randommessage', 'Sends a random message from the server.', 'randomMessage', parameters = 'optional-@user'))
commands.append(command('source', 'Sends the link to the bot source code'))
commands.append(command('rtts', 'Sends a random tts message from the server.', 'randomtts', parameters = 'optional-@user'))
commands.append(command('ruc', 'Triggers a random user command from the server.', 'randomUserCommand'))
commands.append(command('rasearch', 'Sends a random attachment from the server history with the passed text in it.', 'randomAttachmentSearch', parameters = 'search-text'))
commands.append(command('randomspotify', 'Sends a random spotify link from the server history.', 'randomSpotify', parameters = 'optional-@user'))

loadUserCommands()

#launch the refresh timer
timer = threading.Timer(backupInterval, dailyBackup)
timer.start()

#run the bot            
addLog('Running client...', inspect.currentframe().f_code.co_name)
client.run(token)

