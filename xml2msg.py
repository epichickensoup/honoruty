import struct
import csv
import os
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

try:
    xmlfilepath = sys.argv[1]
    folder = xmlfilepath[0:xmlfilepath.rfind('\\') + 1]
except:
    raise Exception('Please input a file.')

print('Folder: ' + folder)      # Debug if the path to the file is valid and stuff
tree = ET.parse(xmlfilepath)
root = tree.getroot()
if root.tag != 'MESGbmg1':
    raise Exception('Please input a valid MESGbmg1 XML file.')

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
### Adding messages is still in beta.
# with open('messageid_beta.tbl', 'wb') as t:
#     print('Num messages ' + str(num - 1))
#     t.write(struct.pack('>I', num - 1))  # Add the number of 'entries' which is the first thing in the file
#     t.write(b'\x00\x00\x00\x02\x00\x00\x00\x28\x00\x00\x00\x08')
#     t.write(b'\x21\x9D\x43\x62\xFF\xFF\xFF\xFF\x00\x04\x00\x06\x04\x38\x38\xB2') 
#     t.write(b'\xFF\xFF\xFF\xFF\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
#     # Remove the id for that blank message at the end... you'd better keep it in when editing!
#     t.write(ids[:-8])
#     t.write(names[:-1])

def getinvdict(f):
    """Return a dictionary created from a csv file."""
    source = csv.reader(open(f))
    redict = dict(source)
    invdict = {v: k for k, v in redict.items()}
    return invdict

scriptpath = Path(os.path.dirname(os.path.realpath(sys.argv[0])))
print('Script at path ' + str(scriptpath))
csv_folder = scriptpath / 'csv'
# Import all the dictionaries from attatched CSVs
demoji = getinvdict(csv_folder / 'emoji_hex.csv')
dcolor = getinvdict(csv_folder / 'color_hex.csv')
dpause = getinvdict(csv_folder / 'pause_hex.csv')
doddpause = getinvdict(csv_folder / 'oddpause_hex.csv')
dnumber = getinvdict(csv_folder / 'number_hex.csv')
dnames = getinvdict(csv_folder / 'names_hex.csv')
dsizes = getinvdict(csv_folder / 'sizes_hex.csv')
dplumber = getinvdict(csv_folder / 'plumber_hex.csv')

def packtuple(t):
    """Pack a string tuple into a bytearray"""
    r = bytearray()
    tl = str(t).replace('(', '').replace(')','').split(',')
    for i in tl:
        r.append(int(i))
    return r

inf1 = bytearray(b'\x00\x00\x00\x00')
dat1 = bytearray()
total = 0

text = bytearray()

for event, elem in ET.iterparse(xmlfilepath, events=('start','end')):
    if elem.tag == 'message':
        if event == 'start':
            inf1.extend(packtuple(elem.get('info')))
            inf1.extend(struct.pack('>I',len(dat1)))
            if elem.text is not None:
                text.extend(elem.text.encode('utf_16_be'))
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
                tag = int(dnames.get(elem.tag))
                text.extend(b'\x00\x1A')
                if tag == 1:
                    if elem.get('length') in doddpause:
                        text.extend(b'\x06\x01')
                        text.extend(struct.pack('>H', int(doddpause.get(elem.get('length')))))
                    else:
                        text.extend(b'\x08\x01')
                        text.extend(struct.pack('>I', int(dpause.get(elem.get('length')))))
                elif tag == 2:
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
                    text.extend(b'\x08\x05')     # Plumber names
                    text.extend(struct.pack('>I', int(dplumber.get(elem.get('style')))))
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
                elif tag == 255:
                    text.extend(b'\x08\xFF\x00\x00')
                    text.append(int(dcolor.get(elem.get('name'))))
                    text.append(0)
                
                if elem.tail is not None:
                    text.extend(elem.tail.encode('utf_16_be'))


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

flbytes = bytearray()
# Get the fl sections at the end using the existing bmg,
# because I have no idea what they actually mean.
with open(folder + 'message.bmg', 'rb') as fget:
    fget.seek(8)
    flwoffset = struct.unpack('>I', fget.read(4))[0]
    fget.seek(flwoffset)
    # save flbytes for later because we're gonna overwrite the file
    flbytes = fget.read()

with open(folder + 'message.bmg', 'wb') as mfile:
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

# # # 