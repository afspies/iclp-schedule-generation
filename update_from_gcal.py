from calendar import day_name
import yaml
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

from dateutil.parser import parse
import datetime
from collections import defaultdict
import os
from pathlib import Path
from google.auth.transport.requests import Request
from operator import itemgetter
# require python >= 3.10

import yaml
from yaml.representer import SafeRepresenter

# modify how PyYAML represents strings
class SafeString(str):
    pass

def represent_safestr(dumper, value):
    node = yaml.representer.SafeRepresenter.represent_str(dumper, value)
    node.style = '"'
    return node

yaml.add_representer(SafeString, represent_safestr, Dumper=yaml.SafeDumper)

# Use your own Google Calendar API credentials here
SECRET = Path("~/Documents/gcal_oauth_secret.json").expanduser()
TOKEN = Path("~/Documents/gcal_oauth_token.json").expanduser()
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


def main():
    creds = load_credentials()
    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time

    events_result = service.events().list(
        calendarId='a0743f85a7e10fa90a0dabedbc0742ffd67995ae7ad5a8d90ed0ed35efacdf5e@group.calendar.google.com', timeMin=now, singleEvents=True,
        orderBy='startTime').execute()

    events = events_result.get('items', [])

    data = defaultdict(list)

    # Parse events 
    data = parse_events(events)
# output_dir = './_talks'
# for event in events:
#     day = parse(event['start'].get('dateTime', event['start'].get('date'))).date()
#     summary = event.get('summary', '')
#     location = event.get('location', 'Room A')

#     data[day].append({
#         'name': summary,
#         'time_start': event['start'].get('dateTime'),
#         'time_end': event['end'].get('dateTime'),
#         'location': location
#     })
    
#     # Generate Markdown file for each event
#     filename = summary.lower().replace(' ', '_').replace(':', '') + '.md'
#     filepath = os.path.join(output_dir, filename)

#     with open(filepath, 'w') as file:
#         file.write('---\n')
#         summary = summary.split(':')[1] if ':' in summary else summary
#         file.write(f'name: {summary}\n')
#         file.write('speakers:\n')
#         for speaker in event.get('speakers', []):
#             file.write(f'  - {speaker}\n')

#         #! Add Category information
#         file.write('categories:\n')
#         if 'workshop' in summary.lower():
#             file.write('  - Workshop\n')
#         elif 'keynote' in summary.lower():
#             file.write('  - Keynote\n')
#         elif 'break' in summary.lower():
#             file.write('  - Break\n')

#         for category in event.get('categories', ''):# Parse manually
#             file.write(f'  - {category}\n')
#         if event.get('hide', False):
#             file.write(f'hide: {str(event["hide"]).lower()}\n')
#         file.write('---\n')

    # print(f"Created Markdown file: {filepath}")

    # Write to yaml
    days = []
    for day, events in data.items():
        # Convert to day of the week
        day_of_week = day.strftime('%A')
        day_data = {'name': day_of_week, 'abbr': day_of_week[:2], 'date': day, 'rooms': []}

        room_data = defaultdict(list)
        for event in events:
            room_data[event['location']].append({
                'name': event['name'],
                'time_start': SafeString(str(parse(event['time_start']).time().strftime("%H:%M"))),
                'time_end': SafeString(parse(event['time_end']).time().strftime("%H:%M")),
            })

        for room, talks in room_data.items():
            day_data['rooms'].append({
                'name': room,
                'talks': talks
            })

        days.append(day_data)


    # Output YAML file
    yaml_data = {'days': days}

    with open('./_data/program.yml', 'w') as file:
        documents = yaml.dump(yaml_data, file, Dumper=yaml.SafeDumper)

from collections import defaultdict
from dateutil.parser import parse

def parse_events(events):
    data = defaultdict(list)
    
    # Sort events by start time
    events.sort(key=lambda event: event['start'].get('dateTime', event['start'].get('date')))
    
    break_copies_to_add = defaultdict(list)
    for event in events:
        day = parse(event['start'].get('dateTime', event['start'].get('date'))).date()
        summary = event.get('summary', '')
        location = event.get('location', 'Room A')

        start_time = parse(event['start'].get('dateTime')).time().strftime("%H:%M")
        end_time = parse(event['end'].get('dateTime')).time().strftime("%H:%M")

        # Check if new event occurs during an existing event
        # If this event is a "break" event, modify previous events that overlap with it

        broken_once = False
        if "break" in summary.lower():

            print('found break ', summary)
            for last_event in reversed(data[day]):
                if last_event['name'].lower() == 'break':
                    continue  # Skip breaks

                print('\t matched to ', last_event['name'], ' on ', day)
                if start_time >= last_event['time_start'] and start_time < last_event['time_end']:
                    # This "break" event starts during the last_event.
                    # Modify the last_event's end time, and create a new event starting after the break.
                    after_break_event = last_event.copy()
                    last_event['time_end'] = start_time
                    after_break_event['time_start'] = end_time
                    data[day].append(after_break_event)
                    #  Make copies of the break even so it looks nicer
                    if broken_once:
                        break_copies_to_add[day].append({
                            'name': SafeString(summary),
                            'time_start': SafeString(start_time),
                            'time_end': SafeString(end_time),
                            'location': SafeString(location)
                        })
                    broken_once = True
                    # break  # Stop checking previous events since we've handled this break

        # Append the new event to the day's list of events.
        data[day].append({
            'name': SafeString(summary),
            'time_start': SafeString(start_time),
            'time_end': SafeString(end_time),
            'location': SafeString(location)
        })

    for day, event in break_copies_to_add.items():
        data[day].extend(event)
        
    # Sort the talks for each day by name
    for day in data:
        data[day] = sorted(data[day], key=itemgetter('name'))

    return data



def load_credentials():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                SECRET, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(TOKEN, 'w') as token:
            token.write(creds.to_json())
    return creds

if __name__ == '__main__':
    main()
        