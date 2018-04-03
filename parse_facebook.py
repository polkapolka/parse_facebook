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


def align_messages(mlist):
	'''
	I am certain there is an easier way to do this, but I am trying to line the dates all up in the right spots for the parsing to be correct.
	'''
	inds = [i for (i,j) in enumerate(mlist) if is_date(j)==True]
	d_prev = inds.pop(0)
	d = inds.pop(0)
	while inds:
		if d-d_prev==3:
			d_prev = d
			d = inds.pop(0)
		if d-d_prev==2:
			mlist.insert(d_prev+1,'')
			inds = [i for (i,j) in enumerate(mlist) if is_date(j)==True and i >d_prev]
			d = inds.pop(0)
		if d-d_prev==1:
			mlist.insert(d_prev+1,'')
			mlist.insert(d_prev+1,'')
			inds = [i for (i,j) in enumerate(mlist) if is_date(j)==True and i >d_prev]
			d = inds.pop(0)
	return mlist




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

		if is_date(mtext[2]): #If date, then process nameless messages
			for m in range(2,len(mtext),2):
					message_row =  dict(zip(headers[1:], mtext[m:m+2] # Sent Date,Message
										))
					dat.append(message_row)
		else: #If not date, assume name and process named message
			if any([is_date(i)==False for i in mtext[3::3]]):  #the problem is here if there is one
				mtext = align_messages(mtext)
			for m in range(2,len(mtext),3):
				message_row =  dict(zip(headers, mtext[m:m+3] # Name, Sent Date,Message
									))
				dat.append(message_row)
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

def clean_security(security_list, headers):
	'''
	All I want is the location data out of this.
	There is a bunch of other stuff, ip's and logon/logoff times, but I don't think that I learn much about me from logon logoff stuff.
	'''
	dat = []

	text = [i for i in security_list.itertext()]
	location = [i for i in text if re.search(re.compile('Estimated location inferred from IP'),i)]
	start = text.index('Logins and Logouts')
	end = text.index('Login Protection Data')
	logs = text[start:end]
	print(location)
	print('\n\n\n')
	print(logs)

	return dat

def clean_data(li, file, head):
	'''
	input: iterable list object, input filename, header list
	output: list dictionary block
	'''
	if file=='events.htm':
		return clean_events(li[1], head)
	if file=='friends.htm':
		return clean_friends(li[1], head)
	if file=='messages.htm':
		return clean_messages(li[1], head)
	if file=='ads.htm':
		return clean_ads(li[1], head)
	if file=='apps.htm':
		return clean_apps(li[1],head)
	if file=='security.htm':
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
			"friends.htm":["Name","Date","Status"], "messages.htm":["Name","Datetime Sent","Message"],"apps.htm":["Applications"], "security.htm":["Lat","Long"]}


	#Data
	# Data is in body in content.
	data = clean_data(root.findall('body/div'), file, heads[file])


	#Write the data to a file
	newfile = re.sub('htm','csv',file)
	pd.DataFrame(data).to_csv(newfile, index=False, encoding='utf-8')


