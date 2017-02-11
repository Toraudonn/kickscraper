## imports
import requests
from bs4 import BeautifulSoup as bs
from geopy.geocoders import Nominatim 
import sys, glob, os
import csv
import time
import json
from collections import deque

## google sheets api
import httplib2
from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools
try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Kickstarter'

## set up global variable
rootdir = os.environ['PWD']
session = requests.Session()
headers = {"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit 537.36 (KHTML, like Gecko) Chrome","Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"}
session.headers.update(headers)

'''
functions:
'''
## number of pages
def getNumberOfPages(url):
    print("Getting number of pages...")
    try:
        req = session.get(url)
        req.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print e
        return None, None
    except requests.exceptions.TooManyRedirects as e:
        print e
        return None, None
    except requests.exceptions.Timeout as e:
        print e
        return getDataForProject(url, True)
    except requests.exceptions.RequestException as e:
        print e
        return None, None
    try:
        bsObj = bs(req.text, "html.parser")
        total = bsObj.find("b", {"class": "count", "class": "green"}).get_text()
        numberOfProjects = int(bsObj.find("b", {"class": "count", "class": "green"}).get_text().split()[0])
        numberOfPages = numberOfProjects/20 + 1
        print("Done!\n")
    except AttributeError as e:
        return None, None
    return numberOfProjects, numberOfPages

## get the links
def getLinks(url):
    try:
        req = session.get(url)
        req.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print e
        return None
    except requests.exceptions.TooManyRedirects as e:
        print e
        return None
    except requests.exceptions.Timeout as e:
        print e
        return getDataForProject(url, True)
    except requests.exceptions.RequestException as e:
        print e
        return None
    try:
        bsObj = bs(req.text, "html.parser")
        projects = bsObj.findAll("li", {"class": "project"})
        links = []
        for project in projects:
            link = project.find("h6", {"project-title"}).a['href']
            link = "https://www.kickstarter.com"+link
            links.append(link)
    except AttributeError as e:
        return None
    return links

## get data for each projects        
def getDataForProjects(url):
    try:
        req = session.get(url)
        req.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print e
        return None
    except requests.exceptions.TooManyRedirects as e:
        print e
        return None
    except requests.exceptions.Timeout as e:
        print e
        return getDataForProject(url, True)
    except requests.exceptions.RequestException as e:
        print e
        return None
    try:
        bsObj = bs(req.text, "html.parser")
        '''
        get parts of data
        [date, backers, fund, fund(in $), percent, (extend with the url)]
        '''
        current_date = time.strftime("%x")
        backers = float(bsObj.find("div", {"id": "backers_count"})['data-backers-count'])
        fund = float(bsObj.find("div", {"id": "pledged"})['data-pledged'])
        percent = float(bsObj.find("div", {"id": "pledged"})['data-percent-raised'])
        currency = bsObj.find("div", {"id": "pledged"}).span['class'][1].encode('ascii', 'ignore').lower()
        fund_in_dollars = fund
        rate = 1.0
        if currency != 'usd':
            rootdir = os.environ['PWD'] + '/rates'
            filenames = os.listdir(rootdir)
            for file in filenames:
                if file == currency+'.csv':
                    with open(rootdir+'/'+file, 'rb') as csvfile:
                        csvReader =csv.reader(csvfile)
                        rows = list(csvReader)
                        rate = float(rows[0][0])
                        fund_in_dollars = fund * rate
        reward_backers = []
        rewards = bsObj.findAll("li", {"class": "hover-group", "class": "js-reward-available"})
        if not (rewards is None):
            for reward in rewards:
                if not(reward.find("div", {"class": "pledge__backer-stats"}) is None):
                    backer_in_reward = str(reward.find("div", {"class": "pledge__backer-stats"}).find("span", {"class": "pledge__backer-count"}).get_text()).split(' ')[0]
                    try:
                        backer_in_reward = backer_in_reward.replace(",", "")
                    finally:
                        try:
                            backer_in_reward = float(backer_in_reward)
                        except:
                            backer_in_reward = float(-1.0)
                    reward_backers.append(backer_in_reward)
        data = [current_date, backers, fund, fund_in_dollars, currency, rate, percent, url, reward_backers]
    except AttributeError as e:
        print e
        return None
    return data

## basic data for projects
def getGeneralDataForProject(url, writeToCsv):
    try:
        req = session.get(url)
        req.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print e
        return None
    except requests.exceptions.TooManyRedirects as e:
        print e
        return None
    except requests.exceptions.Timeout as e:
        print e
        return getDataForProject(url, True)
    except requests.exceptions.RequestException as e:
        print e
        return None
    try:
        bsObj = bs(req.text, "html.parser")
        '''
        get general data (untracked data)
        '''
        title = bsObj.find("h2", {"class": "normal", "class": "mb2"}).find("a", {"class": "green-dark"}).get_text().encode("ascii", "ignore")
        location = bsObj.find("span", {"class": "ksr-icon__location"})
        if location is None:
            city = "NA"
            country = "NA"
        else:
            location = location.parent.get_text().split("\n")[1]
            city, country = getLocation(location)
        tag = bsObj.find("span", {"class": "ksr-icon__tag"})
        if tag is None:
            tag = "NA"
        else:
            tag = tag.parent.get_text().split("\n")[1].encode("ascii", "ignore")
        company = bsObj.find("h5", {"class": "mobile-hide"})
        if company is None:
            company = "NA"
        else:
            company = company.find("a").get_text().encode("ascii", "ignore")
        website = bsObj.find("a", {"class": "bold", "class": "popup"})
        if website is None:
            website = "NA"
        else:
            website = website.get_text().encode("ascii", "ignore")
        end_date = bsObj.find("div", {"class": "ksr_page_timer", "class": "poll"})
        if end_date is None:
            end_date = "NA"
        else:
            end_date = end_date['data-end_time'].split('T')[0].encode("ascii", "ignore")
        goal = bsObj.find("div", {"id": "pledged"})
        if goal is None:
            goal = "NA"
            currency = "NA"
        else:
            currency = goal.span['class'][1].encode('ascii', 'ignore').lower()
            goal = float(goal["data-goal"])
        short_description = bsObj.find("p", {"class": "f3", "class": "mb3", "class": "mb5-sm"})
        if short_description is None:
            short_description = "NA"
        else:
            short_description = short_description.get_text().split("\n")[1].encode("ascii", "ignore")
        reward_list = []
        rewards = bsObj.findAll("li", {"class": "hover-group", "class": "js-reward-available"})
        if not (rewards is None):
            for reward in rewards:
                if not (reward.find("h2", {"class": "pledge__amount"}).find("span") is None):
                    reward_title = reward.find("h3", {"class": "pledge__title"}).get_text().split("\n")[1].encode("ascii", "ignore")
                    reward_amount = str(reward.find("span", {"class": "pledge__currency-conversion"}).find("span").get_text().encode("ascii", "ignore")).split(' ')[0].split('$')[1]
                    try:
                        reward_amount = reward_amount.replace(",", "")
                    finally:
                        try:
                            reward_amount = float(reward_amount)
                        except:
                            reward_amount = float(-1.0)
                    reward_list.append([reward_title, reward_amount])
                    
        title = unicode(title, "utf-8")
        tag = unicode(tag, "utf-8")
        company = unicode(company, "utf-8")
        end_date = unicode(end_date, "utf-8")
        currency = unicode(currency, "utf-8")
        short_description = unicode(short_description, "utf-8")
        date = time.strftime("%x")
        data = [date, title, url, city, country, tag, company, website, end_date, currency, goal, short_description, reward_list]
        ## write to csv
        if writeToCsv is True:
            f = open(rootdir+'/data.csv', 'ab')
            csvWriter = csv.writer(f)
            csvWriter.writerow(data)
            f.close()
    except AttributeError as e:
        print e
        return None
    return data

## getting city and country based on location
def getLocation(location):
    geolocator = Nominatim()
    try:
        country = geolocator.geocode(location, language='en').address.split(', ')[-1].encode("ascii", "ignore")
        if country is None:
            country = 'NA'
    except:
        try:
            country = geolocator.geocode(location.split(', ')[-1], language='en').address.split(', ')[-1].encode("ascii", "ignore")
        except:
            if len(location.split(', ')[1]) == 2:
                country = 'United States of America'.encode("ascii", "ignore")
            else:
                country = location.split(', ')[1].encode("ascii", "ignore")
    try:
        if country == 'United States of America':
            city = location.encode("ascii", "ignore")
        else:
            city = geolocator.geocode(location, language='en').address.split(', ')[0].encode("ascii", "ignore")
        if city is None:
            city = 'NA'
    except:
        city = location.split(',')[0].encode("ascii", "ignore")
    
    city = unicode(city, "utf-8")
    country = unicode(country, "utf-8")
    return city, country
        
## getting exchange rates for currency
def getRates():
    rootdir = os.environ['PWD'] + '/rates'
    url = "http://www.xe.com/currencytables/?from=USD" # shhhhhh
    try:
        req = session.get(url)
        req.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print e
        return None
    except requests.exceptions.TooManyRedirects as e:
        print e
        return None
    except requests.exceptions.Timeout as e:
        print e
        return getDataForProject(url, True)
    except requests.exceptions.RequestException as e:
        print e
        return None
    try:
        bsObj = bs(req.text, "html.parser")
        '''
        get exchange rates (currency to USD) and put it in a folder called 'rates'
        '''
        currencies = bsObj.find("table", {"id": "historicalRateTbl"}).find("tbody").findAll("tr")
        for currency in currencies:
            name = currency.findAll('td')[0].find('a').get_text().encode("ascii", "ignore")
            rate = currency.findAll('td')[3].get_text().encode("ascii", "ignore")
            rate = float(rate)
            filename = name.lower() + '.csv'
            
            f = open(rootdir+'/'+filename, 'w+')
            csvWriter = csv.writer(f)
            csvWriter.writerow([rate])
            f.close()
        
    except AttributeError as e:
        print e
        return None
    return True

## make header for csv
def makeHeader(filePath, header):
    f = open(filePath, 'ab')
    csvWriter = csv.writer(f)
    csvWriter.writerow(header)
    f.close()

## get the lastrow
def getLastRow(csv_filename):
    with open(rootdir+'/projects/'+csv_filename, 'r') as f:
        try:
            lastrow = deque(csv.reader(f), 1)[0]
        except IndexError:  # empty file
            lastrow = [None]
        return lastrow[0]

## put data into csv
def putDataInCSV(csv_filename, data):
    with open(rootdir+'/projects/'+csv_filename, 'ab') as f:
        try:
            csvWriter = csv.writer(f)
            csvWriter.writerow(data)
        except IndexError:
            print("error in saving to csv")
            
def searchInDir(filenames, filename):
    exists = False
    for file in filenames:
        if file == filename:
            exists = True
    return exists
    
def saveToGoogle(service, spreadsheetId, rangeOutput, mybody):
    try:
        service.spreadsheets().values().append(spreadsheetId=spreadsheetId, range=rangeOutput, body=mybody, valueInputOption="RAW", insertDataOption="INSERT_ROWS").execute()
    except HTTPError as e:
        print e
    pass

## Get credentials for google sheets api    
def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    credential_path = os.path.join(credential_dir,
                               'sheets.googleapis.com-kickstater.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

'''
Start script here:
'''
def main():
    ## Step 0: initial settings
    filenames = os.listdir(rootdir)
    exists = searchInDir(filenames, "data.csv")
            
    ## init csv for the data.csv
    if not exists:
        print("Initializing [data.csv]...\n")
        header = ["current_date", "title", "url", "city", "country", "tag", "company", "website", "end_date", "currency", "goal", "short_description", "reward_list"]
        makeHeader(rootdir+"/data.csv", header)
    
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    service = discovery.build('sheets', 'v4', http=http, discoveryServiceUrl=discoveryUrl)
    
    # reading spreadsheetId from some csv file (for private use just type it in!)
    csvReader =csv.reader(csvfile)
    rows = list(csvReader)
    spreadsheetId = rows[0][0]
    
    ## Step 1: getting all of the projects url
    print("STEP 1: \n")
    numberOfProjects, numberOfPages = getNumberOfPages("https://www.kickstarter.com/discover/advanced?state=live&category_id=16&sort=newest&seed=2444597&page=1")
    links = []
    if numberOfPages == None:
        print("Kickstarter is broken: need to rewrite code")
    else:
        pages = ["https://www.kickstarter.com/discover/advanced?state=live&category_id=16&sort=newest&seed=2444597&page=%d" %(n) for n in range (1,numberOfPages+1)]
        for page in pages:
            linksInPage = getLinks(page)
            if linksInPage == None:
                print("Error in %s page" % page)
            else:
                print("Successfully crawled:")
                print("\t"+page)
                links.extend(linksInPage)
                
    ## Step 2: scraping each project
    print("STEP 2: \n")
    filenames = os.listdir(rootdir + '/projects')
    if not links: 
        print("no projects") # nothing in the array
    else:
        print("====================================================")
        print("The number of projects: %d" % len(links))
        print("====================================================")
        
        ## get rates
        didGetRates = getRates()
        if didGetRates == None:
            return
            
        for link in links:
            filename = link.split('/')[4] + '.csv'
            isafile = searchInDir(filenames, filename)
            
            if isafile == False:
                generalData = getGeneralDataForProject(link, True)
                if generalData == None:
                    print("Error in getting gerneal data:")
                else:
                    ## init csv for the project
                    header = ["current date", "# of backers", "fund", "fund in dollars", "currency", "exchange rate", "percent of goal", "url", "# of backers for each reward"]
                    makeHeader(rootdir+'/projects/'+filename, header)
                    
                    ## send the new project to google sheets
                    date = generalData[0]
                    title = generalData[1]
                    url = generalData[2]
                    city = generalData[3]
                    country= generalData[4]
                    tag = generalData[5]
                    company = generalData[6]
                    website = generalData[7]
                    end_date = generalData[8]
                    currency = generalData[9]
                    pledge_goal = generalData[10]
                    short_description = generalData[11]
                    reward_list = str(generalData[12]) # array buggy
                    
                    ## API of google sheets:
                    ggl = [date, title, url, city, country, tag, company, website, end_date, currency, pledge_goal, short_description, reward_list]
                    mybody = {u'values': [ggl], u'majorDimension': "ROWS"}
                    rangeOutput = 'Sheet1!A2:M2'
                    try:
                        saveToGoogle(service, spreadsheetId, rangeOutput, mybody)
                        print("Saved to Google Sheets!")
                    except:
                        print("Could not save to Google Sheets, skipped!")
                print("\t" + link)
            
            ## Don't have duplicates for each day
            lastrow = getLastRow(filename)
            date = time.strftime("%x")
            if not (lastrow == date):
                data = getDataForProjects(link)
                if data == None:
                    print("Error in page:") # could not get anything in the project
                else:
                    putDataInCSV(filename, data)
                    print("Successfully scraped daily data:")
                print("\t" + link)


if __name__ == "__main__":
    main()