import struct
import csv
import os
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

def error(string, errtype=0):
    if errtype == 1:
        pre = 'XML error!'
    else:
        pre = 'Error!'
    print('\n'+pre, string, '\n')
    if os.name == 'nt': #if windows
        os.system('pause')
    else: #assume posix, even though nothing else supports it :P
        os.system('read -n1 -r -p "Press any key to continue..."')
    quit(-1)

debug = False

try:
    xmlfilepath = sys.argv[1]
except:
    error('Please input a file.')
indexlasttick = xmlfilepath.rfind('\\')
folder = xmlfilepath[0 : indexlasttick + 1]
filename = xmlfilepath[indexlasttick + 1 :]
filename = filename[0:filename.rfind('.')]

if debug:
    print('Folder: ' + folder)      # Debug if the path to the file is valid and stuff
tree = ET.parse(xmlfilepath)
root = tree.getroot()
if root.tag != 'MESGbmg1':
    error('Please input a valid MESGbmg1 XML file.')

ids = bytearray()
names = bytearray()
names.append(0)
num = 1

# Um yeah I'm doing the message names in a separate function

for event, elem in ET.iterparse(xmlfilepath, events=('start','end')):
    if elem.tag == 'message' and event == 'start':
        ids.extend(struct.pack('>I',num)) 
        num += 1
        ids.extend(struct.pack('>I',len(names)))
        names.extend(str(elem.get('name')).encode('utf_8'))
        names.append(0)
while (len(names) + len(ids) + 16) % 32 != 0:    # Round of the length of the file by padding it with @ chars
    names.append(64)
### Adding messages is still in beta, thus the file is never written.
#with open(folder + 'messageid_beta.tbl', 'wb') as t:
#    print('Num messages ' + str(num - 1))
#    t.write(struct.pack('>I', num - 1))  # Add the number of 'entries' which is the first thing in the file
#    t.write(b'\x00\x00\x00\x02\x00\x00\x00\x28\x00\x00\x00\x08')
#    t.write(b'\x21\x9D\x43\x62\xFF\xFF\xFF\xFF\x00\x04\x00\x06\x04\x38\x38\xB2') 
#    t.write(b'\xFF\xFF\xFF\xFF\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
#    # Remove the id for that blank message at the end... you'd better keep it in when editing!
#    t.write(ids[:-8])
#    t.write(names[:-1])

def getinvdict(f):
    """Return the inverse of a dictionary created from a csv file."""
    source = csv.reader(open(f))
    redict = dict(source)
    invdict = {v: k for k, v in redict.items()}
    return invdict

scriptpath = Path(os.path.dirname(os.path.realpath(sys.argv[0])))
if debug:
    print('Script at path ' + str(scriptpath))
csv_folder = scriptpath / 'csv'
# Import all the dictionaries from attatched CSVs
print('Fetching CSV files...')
demoji = getinvdict(csv_folder / 'emoji_hex.csv')
dcolor = getinvdict(csv_folder / 'color_hex.csv')
dpause = getinvdict(csv_folder / 'pause_hex.csv')
doddpause = getinvdict(csv_folder / 'oddpause_hex.csv')
dnumber = getinvdict(csv_folder / 'number_hex.csv')
dnames = getinvdict(csv_folder / 'names_hex.csv')
dsizes = getinvdict(csv_folder / 'sizes_hex.csv')
dplumber = getinvdict(csv_folder / 'plumber_hex.csv')
print('All CSV files loaded.\n')

def packtuple(t):
    """Pack a string tuple into a bytearray"""
    r = bytearray()
    tl = str(t).replace('(', '').replace(')','').split(',')
    for i in tl:
        r.append(int(i))
    return r

# class Error(Exception):
#     print('Error!')
#     exit()
# class UnnamedMessageError(Error):
#     print('Error! Message without name.')
#     exit()
# class TagNotFoundError(Error):
#     print('Error! Tag does not exist.')
#     exit()

inf1 = bytearray(b'\x00\x00\x00\x00')
dat1 = bytearray()
total = 0
if debug:
    totaltags = 0
name = ''

text = bytearray()
begintail = ''

# A list of messages to debug.
ldebug = ['AstroGalaxy_ButlerMap006','AstroGalaxy_Tico027','AstroGalaxy_Rosetta057','CONT_10_2','ForestHomeZone_HoneyBee005','HeavensDoorInsideZone_Tico004','Layout_StoryDemoKoopaTalk006','PictureBookChapter4_Page4_001','ScenarioName_CosmosGardenGalaxy4','Select_ReturnToAstro_No','SurfingLv2Galaxy_Penguin015']

print('Beginning XML parsing...')
for event, elem in ET.iterparse(xmlfilepath, events=('start','end')):
    if elem.tag == 'message':							# All message starts and ends are already handled here...
        if event == 'start':
            inf1.extend(packtuple(elem.get('info')))
            inf1.extend(struct.pack('>I',len(dat1)))
            if elem.text is not None:
                text.extend(elem.text.encode('utf_16_be'))
            name = elem.get('name')
            if name is None:
                error('Message' + str(total) + 'does not have a "name" attribute.', 1)
        elif event == 'end':
            if dat1 == bytearray():
                dat1.extend(b'\x00\x00')
            if text != bytearray():
                dat1.extend(text)
                dat1.extend(b'\x00\x00')
                text = bytearray()
            else:
                # If it's blank, replace the pointer with a pointer to 0.
                inf1 = inf1[:-12]
                inf1.extend(packtuple(elem.get('info')))
                inf1.extend(b'\x00\x00\x00\x00')
            total += 1
    elif elem.tag != 'MESGbmg1':
        if event == 'start':
            if elem.tag == 'note':
                text.extend(b'\x26\x6A')
            else:
                tempgettag = dnames.get(elem.tag)
                if tempgettag is None:
                    error('Message "' + name + '": Tag "' + elem.tag + '" is not valid.', 1) 
                tag = int(dnames.get(elem.tag))
                text.extend(b'\x00\x1A')
                if tag == 1:
                    if elem.get('length') in doddpause:
                        text.extend(b'\x06\x01')
                        text.extend(struct.pack('>H', int(doddpause.get(elem.get('length')))))
                    else:
                        text.extend(b'\x08\x01')
                        text.extend(struct.pack('>I', int(dpause.get(elem.get('length')))))
                elif tag == 2:  # Super difficult sound tag
                    tx = elem.get('name')
                    text.append(6 + (len(tx) * 2))
                    text.extend(b'\x02\x00\x00')
                    text.extend(tx.encode('utf_16_be'))
                elif tag == 3:
                    text.extend(b'\x06\x03')
                    text.extend(struct.pack('>H', int(demoji.get(elem.get('name')))))
                elif tag == 4:
                    text.extend(b'\x06\x04')
                    text.extend(struct.pack('>H', int(dsizes.get(elem.get('name')))))
                elif tag == 5:
                    text.extend(b'\x08\x05\x00')     # Plumber names (actually the second-to-last byte)
                    text.extend(struct.pack('>H', int(dplumber.get(elem.get('style')))))
                    text.extend(b'\x00')
                elif tag == 6 or tag == 7:
                    text.extend(b'\x0e')
                    text.append(tag)
                    text.extend(b'\x00')
                    tup = packtuple(elem.get('id'))
                    text.append(tup[0])
                    text.extend(b'\x00\x00\x00\x00\x00\x00\x00')
                    text.append(tup[1])
                elif tag == 9:
                    text.extend(b'\x06\x09\x00\x05')
                elif tag == 255:                 # Color tags, which seem to be causing problems?
                    text.extend(b'\x08\xFF\x00\x00')
                    text.append(int(dcolor.get(elem.get('name'))))
                    text.extend(b'\x00')
                
            begintail = elem.tail

            # if elem.tail is not None:  
            #     text.extend(elem.tail.encode('utf_16_be'))
            # if total > 100 and total < 140:
            #     print(str(elem.tail))
        elif event == 'end':
            if elem.tail != begintail:
                if debug:
                    print('Beginning tail: ',begintail) # oddly enough, these are never called
                    print('End tail: ',elem.tail)
            if elem.tail is not None:
                text.extend(elem.tail.encode('utf_16_be'))          # so try this line out see if it fixes it

    if debug:
        if event == 'start':
            if elem.tag != 'MESGbmg1':
                if name in ldebug:
                    if elem.tag == 'color':
                        print('message',total,'global tag',totaltags,'('+name+',',elem.tag+'"'+elem.get('name')+'")')
                    else:
                        print('message',total,'global tag',totaltags,'('+name+',',elem.tag+')')
            totaltags += 1

if total == 2464:
    print('Processed 2464 messages.')
else:
    print('\nWARNING! There are supposed to be 2464 messages, but instead',total,'were found. This will probably cause glitches in the game.\n')

while len(inf1) % 32 != 0:
    inf1.append(0)
# with open('inf1beta.bmg', 'wb') as ifile:
#     ifile.write(b'INF1')
#     ifile.write(struct.pack('>I', len(inf1) + 16))
#     ifile.write(struct.pack('>H', total))
#     ifile.write(b'\x00\x0c\x00\x00\x00\x00')
#     ifile.write(inf1)

while (len(dat1) - 8) % 32 != 0:
    dat1.append(0)
# with open('dat1betatest.bmg', 'wb') as dfile:
#     dfile.write(b'DAT1')
#     dfile.write(struct.pack('>I', len(dat1) + 8))
#     dfile.write(dat1)

print("Copying bytes from original BMG...")

flbytes = bytearray()
# Get the fl sections at the end using the existing bmg,
# because I have no idea what they actually mean.
try: # Check two places for the original BMG.
    fget = open(folder + filename + '.bmg', 'rb')
except:
    try:
        fget = open(folder + 'message.bmg', 'rb')
    except:
        error('Please put the XML file in the same folder as the original BMG.')
fget.seek(8)
flwoffset = struct.unpack('>I', fget.read(4))[0] # Nab the offset of the fl sections.
fget.seek(flwoffset)                             # Then go to that offset
# save flbytes for later because we're gonna overwrite the file
flbytes = fget.read()
fget.close()

with open(folder + filename + '.bmg', 'wb') as mfile:
    print('Writing BMG file...')
    mfile.write(b'MESGbmg1')
    mfile.write(struct.pack('>I', len(inf1) + len(dat1) + 16 + 8 + 32))
    mfile.write(b'\x00\x00\x00\x04')
    mfile.write(b'\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

    mfile.write(b'INF1')
    mfile.write(struct.pack('>I', len(inf1) + 16))
    mfile.write(struct.pack('>H', total))
    mfile.write(b'\x00\x0c\x00\x00\x00\x00')
    mfile.write(inf1)

    mfile.write(b'DAT1')
    mfile.write(struct.pack('>I', len(dat1) + 8))
    mfile.write(dat1)

    mfile.write(flbytes)
    print('Finished writing BMG file.')

print('\nWARNING! At the moment, there is a bug where random parts of messages get removed. This issue is known and is being worked on.')

# # # 