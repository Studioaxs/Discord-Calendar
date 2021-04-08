# Google calendar API
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
# Discord API
from discord.ext import commands, tasks
# Others
import datetime
import time
import schedule
import asyncio
import pickle
import os.path

print(">>> Discord Calendar a démarré ...")

# SCOPE and credentials file to connect to the ggle calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar']  # Do not touch
CREDENTIALS_FILE = ''  # The path to your secret client file

alarm_time = '07:30'  # Set the alarm
target_channel_id = None # The id of the channel where you want to display the timetable
time_delta = (0, 15, 0) # Set the time delta between the alarm time and the latest event you want to catch (hours, minutes, seconds)
notif_delay = 5 # Delay between the notification and the beginning of the event

bot = commands.Bot("!") # Connect to discord client

def rfc3339_to_HM(d):
    """ Converts a datetime given with the rcf3339 convention into H:M format :  2021-04-04T20:00:00+02:00 --> 20 : 00 (24h format) """
    return d[11:16]


def get_calendar_service():
    """ Connection to google calendar API's services """
    print(">>> Connection to google calendar services ...")
    # https://karenapp.io/articles/how-to-automate-google-calendar-with-python-using-the-calendar-api/ (Source)
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    print(">>> Connected !")
    return service


service = get_calendar_service() # Connect to the ggle calendar API


def get_events(service, time_delta=(0, 24, 0), max_result=10):
    """ Get events list from the google calendar"""

    # Get current time and the time in 15 hours
    now = datetime.datetime.utcnow()
    evening = now + datetime.timedelta(days=time_delta[0], hours=time_delta[1], minutes=time_delta[2])

    # Format the date to ISO format
    now = now.isoformat() + 'Z'  # 'Z' indicates UTC time
    evening = evening.isoformat() + 'Z'  # 'Z' indicates UTC time

    # Get the event list
    events_result = service.events().list(
        calendarId='primary', timeMin=now, timeMax=evening,
        maxResults=max_result, singleEvents=True,
        orderBy='startTime').execute()
    # Get events list
    events = events_result['items']
    return events


def get_attributs(events_list):
    """ Get the attributs of the events as title, description ... """
    # Create a dict to store attributs
    attributs = {'starts': [],
                 'ends': [],
                 'status': [],
                 'titles': [],
                 'description': []}
    f = '%H:%M'  # (Hours : Minutes) format
    for i in events_list:
        # Get the attributs
        attributs['starts'].append(rfc3339_to_HM(
            i['start'].get('dateTime', i['start'].get('date'))))
        attributs['ends'].append(rfc3339_to_HM(
            i['end'].get('dateTime', i['end'].get('date'))))
        attributs['status'].append(i['status'])
        attributs['titles'].append(i['summary'])
        try:
            # Use a try/except because absence of description stops the programme
            attributs['description'].append(i['description'])
        except:
            #print(f"--> {i['summary']} has no description ")
            attributs['description'].append(None)
    return attributs


@tasks.loop()
async def display_day_TT():
    """ Display the timetable at {alarm_time} """

    events = get_events(service, time_delta)  # get the today's event list
    attributs = get_attributs(events)  # get the attributs of the events

    delay = datetime.timedelta(minutes=notif_delay) # define a delay between the notification and the beginning of the event
    starts = [datetime.datetime.strptime(
        attributs['starts'][i], '%H:%M') for i in range(len(events))] # List that contains the start times of each event
    reminder_list = [starts[i] - delay for i in range(len(events))] # Contains the notification time for each event

    f = '%H:%M'  # (Hours : Minutes) format
    now = datetime.datetime.strftime(
        datetime.datetime.now(), f)  # Get current time

    if now == alarm_time:  # Compare with the alarm time, if equals, display the timetable
        print(">>> Display today's timetable ...")

        msg = "@everyone\n**# ---------------------------- Emploi du temps de la journée --------------------------- #**\n"
        for i in range(len(attributs['titles'])):
            msg += f"__**{attributs['titles'][i]}**__ :\n*{attributs['starts'][i]} à {attributs['ends'][i]}*\n```Description :\n {attributs['description'][i]}```\n ---------------------------------------------------------------------------- \n"

        message_channel = bot.get_channel(target_channel_id)  # Get the channel to send the msg
        await message_channel.send(msg)  # Send the msg

        asyncio.sleep(90)  # Wait 90s to avoid multiple messages

    now = datetime.datetime.strptime(now, f)
    for i in range(len(events)):
        start = datetime.datetime.strptime(attributs['starts'][i], f)
        if now < start and now > reminder_list[i]:
            # Get the channel to send the msg
            message_channel = bot.get_channel(target_channel_id)
            print(f">>> {attributs['titles'][i]} starts in 5 minutes")
            msg = f"!-- @everyone\n>>> **{attributs['titles'][i]}** commence dans 5 minutes.\n```Description :\n {attributs['description'][i]}```"
            sent_msg = await message_channel.send(msg)  # Send the msg
            await asyncio.sleep(300) # Wait 5 minutes to avoid multiple msg
            await sent_msg.delete() # Delete the notification after 5 minutes


@display_day_TT.before_loop
async def before():
    await bot.wait_until_ready()
    print("Finished waiting")

display_day_TT.start()
bot.run('EKsynw2HlP7qBlU0bmviEYmerTSYqoQN') # Put your discord bot token here
