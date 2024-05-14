from PIL import Image
from PIL import UnidentifiedImageError
import pytesseract
import sqlite3
import os
from dotenv import load_dotenv
import requests
import io

limit = 100

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
    #addLog(f'Executing select SQL [{SQL}]', inspect.currentframe().f_code.co_name, command = trigger)
    con = openConnection()
    cur = con.cursor()
    cur.execute(SQL)
    x = cur.fetchall() 
    closeConnection(con)
    return x

#load variables
load_dotenv('.env')
database = os.getenv('GLOBALBOT_DATABASE')
pytesseract.pytesseract.tesseract_cmd = os.getenv('TESSERACT_PATH')

filename = os.path.join(os.getcwd(), 'LastRecord.dat')
if os.path.isfile(filename):
    with open(filename, 'r') as infile:   
        lastRecord = infile.read()
else:
    lastRecord = -1
    
attachments = select(f"select RECORD_ID, URL from MESSAGE_ATTACHMENT_HISTORY where (lower(URL) like '%.png' or lower(URL) like '%.jpg' or lower(URL) like '%.jpeg') and RECORD_ID > {lastRecord}")

con = openConnection()
cur = con.cursor()
counter = 0
records = []
for attachment in attachments:
    counter += 1
    print(f'Processing record {counter} out of {len(attachments)}. [ID {attachment[0]}][URL: {attachment[1]}]')
    imageData = requests.get(attachment[1], stream = True).content
    
    try:
        image = Image.open(io.BytesIO(imageData))
        imageText = pytesseract.image_to_string(image).strip()
    except (TypeError, UnidentifiedImageError):
        print('Invalid image format. Skipping...')
        imageText = ''
    image.close()
    if imageText != '':
        records.append((imageText, int(attachment[0])))

    if len(records) >= limit:
        print('Limit reached. Committing changes...')
        cur.executemany('update MESSAGE_ATTACHMENT_HISTORY set IMAGE_TEXT = ? where RECORD_ID = ?', records)
        con.commit()
        records = []

        filename = os.path.join(os.getcwd(), 'LastRecord.dat')
        with open(filename, 'w') as outfile:   
            outfile.write(str(attachment[0]))
            outfile.close()

if len(records) > 0:
    print('Committing final changes...')
    cur.executemany('update MESSAGE_ATTACHMENT_HISTORY set IMAGE_TEXT = ? where RECORD_ID = ?', records)
    con.commit()
    
    filename = os.path.join(os.getcwd(), 'LastRecord.dat')
    with open(filename, 'w') as outfile:   
        outfile.write(str(attachment[0]))
        outfile.close()

closeConnection(con)
print('Done!')