# Kickscraper

Kickstarter webscraper implimented on python2 with BeautifulSoup. The data scraped would be parsed to Google Sheets via googledrive API.

## Installation

Dependencies (for python 2.7):
```
beautifulsoup4            4.4.1
requests                  2.11.1
geopy                     1.11.0
google-api-python-client  1.5.2
httplib2                  0.9.2
oauth2client              3.0.0
```

Follow the tutorial for [google sheets API](https://developers.google.com/sheets/api/quickstart/python).
Move the `client_secret.json` file and create a csv file in the top directory to save the `spreadsheetId`.

(I think it could work with python3 since I first made `crawler.py` on python 3.5, but I tweaked the code a bit)

## Usage

Make sure your directory is formated as below:
```
crawler
├── projects (directory to save projects for reference)
├── rates (directory to save exchange rates for reference)
├── client_secret.json
├── crawler.py something.csv (to save spreadsheetId)
└── something.csv (to save spreadsheetId)
```

Then, all you have to do is run the code on a terminal :)

## Disclaimer
This project was made for educational purposes (not for profit).   
Try not to overload the servers with a bunch of requests :)
