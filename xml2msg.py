import struct
import csv
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

def getinvdict(f):
    """Return a dictionary created from a csv file."""
    source = csv.reader(open(f))
    redict = dict(source)
    invdict = {v: k for k, v in redict.items()}
    return invdict

csv_folder = Path('csv')
# Import all the dictionaries from attatched CSVs
demoji = getinvdict(csv_folder / 'emoji_hex.csv')
dcolor = getinvdict(csv_folder / 'color_hex.csv')
dpause = getinvdict(csv_folder / 'pause_hex.csv')
doddpause = getinvdict(csv_folder / 'oddpause_hex.csv')
dnumber = getinvdict(csv_folder / 'number_hex.csv')
dnames = getinvdict(csv_folder / 'names_hex.csv')
dsizes = getinvdict(csv_folder / 'sizes_hex.csv')
dplumber = getinvdict(csv_folder / 'plumber_hex.csv')

def tuple2bytes(s):
    """Converts a tuple string to a tuple"""
    l = str(s).replace('(','').replace(')','').split(', ')
    ret = bytearray()
    for n in l:
        ret.append(int(n))
    return ret

tree = ET.parse('messages_short_beta.xml')
root = tree.getroot()

print(root.tag)
if root.tag != 'MESGbmg1':
    raise Exception('Please input a valid MESGbmg1 XML file.')

curmsgnum = 0
dat1 = bytearray(b'\x00\x00')
pointers = bytearray()
names = bytearray()
names.append(0)
namepointers = bytearray(b'\xFF\xFF\xFF\xFF\x00\x00\x00\x00')
oldnameslen = len(names)
empty = True
olddatlen = len(dat1)

# so it looks like this file's gonna be made all linearly
for event, elem in ET.iterparse('messages_beta.xml', events=('start','end')):
    if event == 'start':
        tag = bytearray()
        # Assume empty until proven not
        empty = True
        if elem.tag == 'note':
            # I don't think anything starts with notes, but this'll take care of it
            empty = False
            tag.extend(b'\x26\x6A')
        elif elem.tag in dnames:
            # If there's a thing here, it's not empty
            empty = False
            tagid = int(dnames.get(elem.tag))
            tag = bytearray(b'\x00\x1A')
            attrib = elem.attrib
            
            # --All dat1 from here!-- #
            # So this part is basically msg2xml but reversed
            if tagid == 1:
                # It's a pause
                # curattrib is generic; it is used for any attribute
                curattrib = attrib.get('length')
                if curattrib in doddpause:
                    tag.extend(b'\x06\x01')
                    tag.extend(struct.pack('>H', int(doddpause.get(curattrib))))
                    #print(str(struct.pack('>H', int(doddpause.get(curattrib)))))
                else:
                    # 'Numeric' pause length
                    tag.extend(b'\x08\x01')
                    tag.extend(struct.pack('>I', int(dpause.get(curattrib))))
            elif tagid == 2:
                # Sound or anim, whatever it is
                curattrib = attrib.get('name')
                tag.append((len(curattrib) * 2) + 6)
                tag.extend(b'\x02\x00\x00')
                tag.extend(bytearray(curattrib,'utf-16be'))
            elif tagid == 3:
                # EMOJI! Hooray!
                tag.extend(b'\x06\x03')
                curattrib = attrib.get('name')
                tag.extend(struct.pack('>H', int(demoji.get(curattrib))))
            elif tagid == 4:
                # Text sizes
                tag.extend(b'\x06\x04')
                curattrib = attrib.get('name')
                tag.extend(struct.pack('>H', int(dsizes.get(curattrib))))
            elif tagid == 5:
                # Plumber
                tag.extend(b'\x08\x05')
                curattrib = attrib.get('style')
                tag.extend(struct.pack('>I', int(dplumber.get(curattrib))))
            elif tagid == 6 or tagid == 7:
                # System text or inset number
                tag.extend(b'\x0E')
                tag.append(tagid)
                curattrib = attrib.get('id')
                attribtuple = tuple2bytes(curattrib)
                tag.append(0)
                tag.append(attribtuple[0])
                tag.extend(b'\x00\x00\x00\x00\x00\x00\x00')
                tag.append(attribtuple[1])
            elif tagid == 9:
                # Racetime, which doesn't (seem to) change
                tag.extend(b'\x06\x09\x00\x05')
            elif tagid == 255:
                # Colors
                tag.extend(b'\x08\xFF\x00')
                curattrib = attrib.get('name')
                tag.extend(struct.pack('>H', int(dcolor.get(curattrib))))
                tag.append(0)
            else:
                # Error catch? I don't know if this will work in game so let's (not) see
                tag.extend(b'\x04\x00')
        # I put this elif at the end so it doesn't get tricked by text that starts with
        # a binary escape
        elif elem.tag == 'message':  
            # Add inf1 data for this message.
            curmsginf = tuple2bytes(elem.attrib.get('info'))

            if elem.text is not None:
                empty = False
                dat1.extend(bytes(elem.text,'utf-16be'))
                empty = False

            # Handles what goes into messageid.tbl
            namepointers.extend(struct.pack('>i',curmsgnum))
            if curmsgnum == 0:
                namepointers.extend(b'\x00\x00\x00\x00')
            else:
                namepointers.extend(struct.pack('>I',oldnameslen))
            oldnameslen = len(names)
            names.extend(bytearray(elem.attrib.get('name'),'utf-8'))
            names.append(0)
        else:
            elemtag = elem.tag
        #print('start ' + elemtag + ' ' + str(elem.attrib))
        dat1.extend(tag)
    if event == 'end':
        #print('end ' + elem.tag)
        # ignore trailing whitespace
        if elem.tag == 'message':
            # First add the pointer
            if not empty:
                # Add a pointer to where the text is going to start
                dat1.extend(bytes(b'\x00\x00'))
                if curmsgnum == 1:
                    pointers.extend(b'\x00\x00\x00\x00')
                else:
                    pointers.extend(struct.pack('>I', olddatlen))
            else:
                pointers.extend(b'\x00\x00\x00\x00')
                empty = True
            olddatlen = len(dat1)
            
            # Then add the info
            pointers.extend(curmsginf)
            
            curmsgnum = curmsgnum + 1
        elif elem.tag is not None:
            elemtail = elem.tail
            if elemtail is not None:
                dat1.extend(bytes(elemtail,'utf-16be'))

pointshort = pointers[: len(pointers) - 12]

with open('message.bmg','rb') as mo:
    # Get the default F sections and hope they work
    mo.seek(8)
    flw1offset = struct.unpack('>I', mo.read(4))[0]
    mo.seek(flw1offset)
    defaultfs = mo.read()

# OK dat1 should be written by now
while (len(dat1) - 8) % 16 != 0:
    dat1.append(0)

with open('dat1output_beta.bmg','wb') as d:
    fulldat1 = bytearray(b'DAT1')
    fulldat1.extend(struct.pack('>I', len(dat1) + 10))
    # you put this in the wrong spot! fulldat1.extend(b'\x00\x00')
    fulldat1.extend(dat1)
    d.write(fulldat1)

# Um... I think the INF1 section is done... wow!
with open('inf1output_beta.bmg', 'wb') as i:
    fullinf1 = bytearray(b'INF1')
    inf1filelen = len(pointshort) + 1 + 12
    inf1filelen = inf1filelen + 16 - (inf1filelen % 16)
    fullinf1.extend(struct.pack('>I', inf1filelen))
    fullinf1.extend(struct.pack('>H', curmsgnum))
    fullinf1.extend(b'\x00\x0c\x00\x00\x00\x00')
    # WTF DUDE YOU MESSED IT UP!!!
    # # Add a default inf1 in case the game wants it
    # fullinf1.extend(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xFF\xFF')
    fullinf1.extend(pointshort)
    # Add some spare bytes at the end because why not
    fullinf1.append(0)
    while len(fullinf1) % 16 != 0:
        fullinf1.append(0)
    i.write(fullinf1)

with open('message_output_beta.bmg','wb') as m:
    header = bytearray(b'MESGbmg1')
    header.extend(struct.pack('>I',32 + len(fullinf1) + len(fulldat1)))
    header.extend(struct.pack('>I',4))
    header.extend(b'\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    m.write(header)
    m.write(fullinf1)
    m.write(fulldat1)
    m.write(defaultfs)

with open('messageid_output_beta.tbl','wb') as ifile:
    header = bytearray()
    header.extend(struct.pack('>I',curmsgnum))
    # I'm pretty much copying the original file here, hopefully it works for other things
    header.extend(b'\x00\x00\x00\x02\x00\x00\x00\x28\x00\x00\x00\x08')
    header.extend(b'\x21\x9D\x43\x62\xFF\xFF\xFF\xFF\x00\x04\x00\x06\x04\x38\x38\xB2')
    ifile.write(header)
    ifile.write(namepointers)
    names.extend(b'\x40\x40')
    while (len(names) + len(namepointers)) % 16 != 0:
        names.extend(b'\x40')
    ifile.write(names)