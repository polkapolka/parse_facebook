import re
import os
import xml.etree.ElementTree as ET
#from bs4 import BeautifulSoup
#from bs4 import UnicodeDammit
import csv
import string
import itertools
import pandas as pd
import folium
from datetime import date, datetime

drop = ['contact_info.htm','photos.htm', 'pokes.htm', 'timeline.htm', 'videos.htm']
r = re.compile(".*htm")
files = [f for f in filter(r.match, os.listdir(".")) if f not in drop]


##  Ads.htm
##  Apps.htm
##
##  map locations with folium
##  https://georgetsilva.github.io/posts/mapping-points-with-folium/


def extract_data_from_file(filename):
	html_file = open(filename,'r')
	tree = ET.parse(html_file)
	return tree


def is_date(date_string):
	try:
		d = datetime.strptime(date_string,'%A, %B %d, %Y at %H:%M%p %Z')
		result = True
	except ValueError:
		pass
		result = False
	return result





def clean_messages(messages_elem, headers):
	'''
	input:  messages ET elem
	output:  list of message items
	'''
	dat = []
	for l in range(1,len(messages_elem)):
		mtree = ET.parse('../'+messages_elem[l][0].attrib['href'])
		mroot = mtree.getroot()
		mtext = [i for i in mroot[1][3].itertext() if 'Download file:' not in i]


		participants = [messages_elem[0].text] + [i.strip() for i in re.sub('Participants:','',mtext[1]).split(',')]

		message = dict(zip(headers,['','','']))		
		for m in range(2,len(mtext)):
			if mtext[m] in participants:
				message[headers[0]]=mtext[m]
				next
			elif is_date(mtext[m]):
				message[headers[1]]=mtext[m]
				next
			else:
				message[headers[2]]=mtext[m]
				dat.append(message)
				message = dict(zip(headers,['','','']))
	return dat

def clean_event(event_elem):
	'''
	input: event ET elem
	output: list of event items
	'''
	event = []
	#Event Name
	event.append(event_elem.text) 
	#Event Location Missing?
	if len(list(event_elem[0]))==1: 
		# Event Location 
		event.append('')
		# Event Start Date
		event.append(event_elem[0].text.split(' - ')[0])
		# Event End Date
		event.append(event_elem[0].text.split(' - ')[1])
		# Attendance
		event.append(event_elem[0][0].tail)
	else:
		# Event Location 
		event.append(event_elem[0].text)
		# Event Start Date
		event.append(event_elem[0][0].tail.split(' - ')[0])
		# Event End Date
		event.append(event_elem[0][0].tail.split(' - ')[1])
		# Attendance
		event.append(event_elem[0][1].tail )
	return event



def clean_events(events_elem, headers):
	'''
	input: ET Element
	structure: 
	output: data elements as list
	'''
	dat = []
	# Meh
	Name = {'Name': events_elem[0].text}
	for e in range(len(events_elem[2])):
		event_row = dict(zip(headers, clean_event(events_elem[2][e])))
		dat.append(event_row)

	return dat


def clean_friend(friend_string):
	'''
	input: friend string format 'Name (Date)'
	Adding current year to replace empty date year
	output: list containing [Name, Date] as 2 string elements
	'''
	friend = str.split(re.sub('\)','',friend_string.text),' (')
	if re.search('[0-9]{4}',friend[1]) is None:
		friend[1] = friend[1]+', '+str(date.today().year)
	return friend


def clean_friends(friends_elem, headers):
	'''
	input: Friend ET Element
	structure: Name, header, list, header, list,...,Life Status Tag (LST_tag)
	output: data elements as list
	'''
	dat = []
	# Two one off peices of info I don't know what to do with
	Name = {'Name': friends_elem[0].text}
	LST_tag = {friends_elem[len(friends_elem)-1].text:friends_elem[len(friends_elem)-1].tail}

	for l in range(1,len(friends_elem)-1,2):
		status = friends_elem[l].text
		for f in list(friends_elem[l+1]):
			friend_row = dict(zip(headers,clean_friend(f)+[status]))
			dat.append(friend_row)
	return dat

def clean_ads(ads_elem, headers):
	'''
	input: Ads ET Element
	output: data elements as a list
	'''
	ad = [i for i in ads_elem.itertext()]

	split = ad.index('Advertisers with your contact info')
	cc = ad[split+1:]
	ad = ad[2:split]

	dat = [{headers[0]:i,headers[1]:j} for (i,j) in itertools.zip_longest(ad,cc)]
#	dat.append({headers[1]:i} for i in ad[split+1:])

	return dat

def clean_apps(apps_elem, headers):
	'''
	input: Apps ET Element
	output: data elements as a list
	'''
	dat = []
	apps = [i for i in apps_elem.itertext()][2:]
	dat = [{headers[0]:i} for i in apps]

	return dat

def merge_two_dicts(x, y):
    z = x.copy()   # start with x's keys and values
    if y is not None:
	    z.update(y)    # modifies z with y's keys and values & returns None
    return z


def clean_security(security_elem, headers):
	'''
	input: Security ET element
	note: ignoring cookies and ip addresses for now, should really be two separate csvs because first two columns and last two colu
	outpu: logins, logoffs, lat, long as a list
	'''
	dat = []

	text = [i for i in security_elem.itertext()]
	location = [re.sub('Estimated location inferred from IP','',i) for i in text if re.search(re.compile('Estimated location inferred from IP'),i)]
	location = [dict(zip(headers[2:4],l.split(', '))) for l in location]
	start = text.index('Logins and Logouts')
	end = text.index('Login Protection Data')


	logs = text[start+1:end]
	logs = [l for l in logs if re.search(re.compile('Log Out|Login'),l)]

	log = dict(zip(headers[0:2],['','']))
	for l in range(len(logs)):
		if re.match('Login',logs[l]) is not None:
			log[headers[0]]=re.sub('Login ','',logs[l]).strip()
			dat.append(log)
			log = dict(zip(headers[0:2],['','']))
			next
		elif re.match('Log Out',logs[l]) is not None:
			log[headers[1]]=re.sub('Log Out ','',logs[l]).strip()
			next

	dat = [merge_two_dicts(i,j) for (i,j) in itertools.zip_longest(dat,location)]

	return dat

def clean_data(li, file, head):
	'''
	input: iterable list object, input filename, header list
	output: list dictionary block
	'''
	if file=='events.htm':
		return clean_events(li[1], head)
	elif file=='friends.htm':
		return clean_friends(li[1], head)
	elif file=='messages.htm':
		return clean_messages(li[1], head)
	elif file=='ads.htm':
		return clean_ads(li[1], head)
	elif file=='apps.htm':
		return clean_apps(li[1],head)
	elif file=='security.htm':
		return clean_security(li[1], head)
	else:
		return 



for file in files:
	# load each file
	tree = extract_data_from_file(file)
	root = tree.getroot()

	#Title
	#Meaningless, don't know what to do with it
	title = root.find('head/title').text

	#Headers dictionary
	heads = {"events.htm":["Event Name","Location","Start Datetime","End Datetime","Attendance"], "ads.htm":["Ads Topics","Creeper Companies"],
			"friends.htm":["Name","Date","Status"], "messages.htm":["Name","Datetime Sent","Message"],
			"apps.htm":["Applications"], "security.htm":["Login","Log Out","Lat","Long"]}


	#Data
	# Data is in body in content.
	data = clean_data(root.findall('body/div'), file, heads[file])


	#Write the data to a file
	newfile = re.sub('htm','csv',file)
	pd.DataFrame(data).to_csv(newfile, index=False, encoding='utf-8')




