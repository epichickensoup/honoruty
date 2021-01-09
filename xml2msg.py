# Honoruty, a message converter for SMG1's BMG message files, (c) 2020 EPICHICKENSOUP
# This software is under the GNU GPL 3.0 license. Find out more at https://www.gnu.org/licenses/.

import struct
import csv
import os
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

windows = (os.name == 'nt') # true if windows, false if else

def error(string, errtype=0):
    if errtype == 1:
        pre = 'XML error!'
    else:
        pre = 'Error!'
    print('\n'+pre, string, '\n')
    if windows: #if windows
        os.system('pause')
    else: #assume posix, even though nothing else supports it :P
        os.system('read -n1 -r -p "Press any key to continue . . ."')
    quit(-1)

debug = False

try:
    xmlfilepath = sys.argv[1]
except:
    error('Please input a file.\nExample: python xml2msg.py message.xml')
if windows:
    indexlasttick = xmlfilepath.rfind('\\')
else:
    indexlasttick = xmlfilepath.rfind('/')
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

def getinvdict(f):
    """Return the inverse of a dictionary created from a csv file."""
    source = csv.reader(open(f))
    redict = dict(source)
    invdict = {v: k for k, v in redict.items()}
    return invdict

# use this to find the csv folder
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
dnames = getinvdict(csv_folder / 'names_hex.csv') # Names of tags
dsizes = getinvdict(csv_folder / 'sizes_hex.csv')
dplumber = getinvdict(csv_folder / 'plumber_hex.csv')
print('All CSV files loaded.\n')

def packtuple(t):
    """Pack a string-formatted tuple into a bytearray"""
    r = bytearray()
    tl = str(t).replace('(', '').replace(')','').split(',')
    for i in tl:
        r.append(int(i))
    return r

inf1 = bytearray()             # inf1 section contains a bunch of bytes in order `pointer` (4 bytes), `info` (for smg, 8 bytes)
dat1 = bytearray(b'\x00\x00')  # Bytearray to put all of the message strings into. Written to file at the end of parsing.
                               # Preloaded with the 2 null bytes for blank messages to point to.
                               # Fun fact, I'm reading the file wrong... the very first message is named "" and has no content. It does have properties though.
# Bonus. I could replace these bytearrays with a bunch of "message" structs containing the name, inf, and data. Then, just write them all to the file at the end.
# In this way, I could add automatic message sorting.

v = False # Verbosity setting
total = 0
if debug:
    totaltags = 0
name = ''

text = bytearray()
begintail = ''

# A list of messages to debug.
ldebug = ['AstroGalaxy_ButlerMap006','AstroGalaxy_Tico027','AstroGalaxy_Rosetta057','CONT_10_2','ForestHomeZone_HoneyBee005','HeavensDoorInsideZone_Tico004','Layout_StoryDemoKoopaTalk006','PictureBookChapter4_Page4_001','ScenarioName_CosmosGardenGalaxy4','Select_ReturnToAstro_No','SurfingLv2Galaxy_Penguin015']

print('Beginning XML parsing...')

with open(xmlfilepath, 'r') as xmlf: # open xml file
    if xmlf.read(10) != "<MESGbmg1>": # check the beginning of the xml
        error("Please input a valid MESGbmg1 XML file.")
    inmessage = False   # We are not currently in a message
    message = bytearray()   # build message into this variable, it's a bytearray because of binary escapes
    while True:
        char = xmlf.read(1) # repeat until first '<' idk
        if char == '<': # look at you finding a tag
            if v: print('"<" at ' + str(xmlf.tell()))
            tag = ''
            while True: # Get the tag real quick
                char = xmlf.read(1)
                if (char == ' ' or char == '\n' or char == '>' or char == '/') and not tag == '': # allow spaces and all sorts of silly stuff before the tag
                    break
                tag += char
            # Now we know what the tag looks like!

            if tag.startswith('/'): # If it starts with a '/' it's an end tag, so basically ignore it
                if tag == '/message':  # Message ended!
                    inmessage = False
                    message.extend(b'\x00\x00') # Add the null character at the end of the message!
                    if v: print('Message ended as "' + str(message) + '"!')
                    # Add the message to the dat!
                    dat1 += message
                    
                    message = bytearray() # clear the message, we are done reading it
                
                if tag == '/MESGbmg1': # We have reached the end of the file! Break the big while loop
                    break

            
            elif tag == 'message':
                total += 1  # add to the message count to track errors for the user
                inmessage = True

                dat1start = len(dat1) # Record where message is going to start when added (as long as message isn't blank)
                if v: print('Message starting at ' + hex(dat1start))

                namefound = False # keep track of whether we've found the name while we're looking for it
                name = ''
                while True: # Loop through all properties of the current message
                    prop = '' # This little function gets the whole property
                    inquote = False
                    while True:
                        char = xmlf.read(1) # advance through text
                        if char == '"': # We have entered or exited a quote
                            inquote = not inquote
                        if (char == ' ' or char == '/' or char == '>' or char == '\n') and not inquote:  # something ended
                            break   # this works because the while loop will keep advancing through every ' ', '/' or '>'
                        prop += char
                    if prop.startswith('name="'):  # Getting the name of the message. A messageid.tbl writer would in theory hook in here.
                        name = prop[6:-1]
                        if v: print('Name property found, very good. It\'s "' + name + '"')
                        # You could check the name against the original file somewhere in here if you were to, say, check for missing messages.
                        namefound = True
                    elif prop.startswith('info="'):
                        # put info in a variable
                        inf = packtuple(prop[6:-1])
                        if v: print('Info property found, very good. It\'s "' + prop[6:-1] + '" aka "' + str(inf) + '"')
                    if char == '/' or char == '>':
                        if not namefound: # got to end without finding name??
                            error('name property of message ' + str(total) + ' not found!', 1)
                        if not (len(inf) > 1): # Also check if info existed, since we will be writing that
                            error('info property of message ' + name + ' not found!', 1)
                        if char == '/':
                            if v: print('Oh no, message is empty!')
                            inmessage = False
                            # no need to advance to the '>' char because we step until we find a '<'

                            # Add 0 pointer for blank message
                            inf1.extend(b'\x00\x00\x00\x00') # Pointer to beginning of dat1, 0.
                        else: # Message was not empty, add offset to inf
                            inf1.extend(struct.pack('>I', dat1start))
                        
                        inf1 += inf
                        inf = bytearray() # Reset inf so we can accurately check if it exists next time
                        # print("Inf1 so far is " + str(inf1))
                        
                        break   # End of tag, found all properties.

            elif tag == 'note':
                message.extend(b'\x26\x6A') # apparently this is ascii '&j', who knew?
                while True: # do while to get to the end of the note tag
                    char = xmlf.read(1) # keep advancing 1 char at a time
                    if char == '>':
                        break
            elif tag in dnames: # If the tag shows up in our names dictionary
                tagid = int(dnames.get(tag))
                if v: print('Tag "' + tag + '" has id ' + str(tagid))
                props = ''  # we can parse this pretty strictly, so put it all in one
                while True:  # get properties + stuff
                    char = xmlf.read(1)
                    if char == '"':
                        inquote = not inquote
                    elif (char == '/' or char == ' ') and not inquote:
                        char = xmlf.read(1)# done reading tag properties, advance to end of tag
                        if char == '>':
                            break
                    props += char
                if props == '' and not tagid == 9: # racetime tag (id 9) requires no properties
                    error('Message "' + name + '": Element "' + tag + '" has no properties', 1)
                else:
                    if v: print('     Properties: "' + props + '"')
                if tagid == 1: # Pauses
                    if props[0:8] == 'length="':
                        lengthstr = props[8:-1]  # Write to a string to easier check the dictionaries
                        if lengthstr in doddpause:
                            lengthid = int(doddpause.get(lengthstr))
                            message.extend(b'\x00\x1A\x06\x01')    # Extend with the escape character, lenth of 6, and id 1
                            message.extend(struct.pack('>H', lengthid))  # Pack number from dictionary as a big endian unsigned short and append
                        elif lengthstr in dpause:
                            lengthid = int(dpause.get(lengthstr))
                            message.extend(b'\x00\x1A\x08\x01')    # Extend with escape character, length of 8, and id of 1
                            message.extend(struct.pack('>I', lengthid))  # Pack number from dictionary as a big endian unsigned int and append
                        else:
                            error('Message "' + name + '": ' + tag + ' tag has invalid length property "' + lengthstr + '"', 1)
                            # Descriptive errors to make it as user friendly as possible :D
                    else:
                        error('Message "' + name + '": ' + tag + ' tag missing "length" property', 1)
                elif tagid == 2: # Sound tag
                    if props[0:6] == 'name="':
                        namestr = bytearray(props[6:-1], "utf-16-be")  # Encode the name string
                        print('     !! Sound found, sound name is "' + props[6:-1] + '" !!')
                        message.extend(b'\x00\x1A') # Escape character
                        message.extend(struct.pack('>B', (6 + len(namestr)))) # Pack string length (+6 for the escape sequence itself and first null bytes) to a single byte and add it.
                        message.extend(b'\x02\x00\x00') # Add escape identifier and 2 null bytes for no good reason.
                        message.extend(namestr) # Finally, add the actual name string.
                    else:
                        error('Message "' + name + '": ' + tag + ' tag missing "name" property', 1)
                elif tagid == 3: # emoji
                    if props[0:6] == 'name="':
                        if props[6:-1] in demoji:
                            nameid = int(demoji.get(props[6:-1])) # Get the ID of the emoji using the properties string and our dictionary
                        else:
                            error('Message "' + name + '": ' + tag + ' tag has invalid name property "' + props [6:-1] + '"')
                    else:
                        error('Message "' + name + '": ' + tag + ' tag missing "name" property', 1)
                    message.extend(b'\x00\x1A\x06\x03')  # Add escape character, length, and identifier
                    message.extend(struct.pack('>H', nameid))  # Pack emoji ID to a (big endian) short and add it
                elif tagid == 4: # Text size
                    if props[0:6] == 'name="':
                        if props[6:-1] in dsizes:
                            nameid = int(dsizes.get(props[6:-1]))
                        else:
                            error('Message "' + name + '": ' + tag + ' tag has invalid name property "' + props[6:-1] + '"', 1)
                        message.extend(b'\x00\x1A\x06\x04')
                        message.extend(struct.pack('>H', nameid))
                    else:
                        error('Message "' + name + '": ' + tag + ' tag missing "name" property')
                elif tagid == 5: # Player's name
                    if props[0:7] == 'style="':
                        if props[7:-1] in dplumber:
                            nameid = int(dplumber.get(props[7:-1]))
                        else:
                            error('Message "' + name + '": ' + tag + ' tag has invalid style property "' + props[7:-1] + '"', 1)
                    else:
                        error('Message "' + name + '": ' + tag +' tag missing "style" property')
                    message.extend(b'\x00\x1A\x08\x05\x00') # Add the escape character, length, and escape ID.  Also a null byte to allign the number.
                    message.extend(struct.pack('>H', nameid))  # Pack the name number into 2 bytes
                    message.extend(b'\x00')  # Add some null to allign it
                elif tagid == 6 or tagid == 7: # Number or system text. Pretty weird.
                    if props[0:4] == 'id="':
                        nameid = packtuple(props[4:-1]) # reusing the nameid variable, guess it stands for "name/id" now
                        if tagid == 6: # Add the escape character, the length of the escape, and either 6 or 7 for the escape ID (LEN 4)
                            message.extend(b'\x00\x1A\x0E\x06')
                        else:
                            message.extend(b'\x00\x1A\x0E\x07')
                        message.extend(b'\x00') # A null byte to allign the first number of the ID (LEN 5)
                        message.extend(struct.pack('>B', nameid[0])) # Pack and add first number (LEN 6)
                        message.extend(b'\x00\x00\x00\x00\x00\x00\x00') # 7 null bytes to allign the second number (LEN 13)
                        message.extend(struct.pack('>B', nameid[1])) # Pack and add second number (LEN 14 = 0xE)
                    else:
                        error('Message "' + name+ '": ' + tag + ' tag has invalid id property "' + props [4:-1] + '"', 1)
                elif tagid == 9: # No tag 8 for some reason, maybe it's a secret!
                    message.extend(b'\x00\x1A\x06\x09\x00\x05')  # tagid 9 is the race time. No part of it changes (in the original game...)
                elif tagid == 255: # lol why is color -1 or FF depending on if this number is technically signed or not?
                    if props[0:6] == 'name="': # Check if they wrote the name property validly
                        if props[6:-1] in dcolor:
                            nameid = int(dcolor.get(props[6:-1]))
                        else:
                            error('Message "' + name + '": ' + tag + ' tag has invalid name property "' + props[6:-1] + '"', 1)
                    else:
                        error('Message "' + name + '": ' + tag + ' tag missing "name" property', 1)
                    message.extend(b'\x00\x1A\x08\xFF\x00') # Add escape character, escape length, escape ID, and a null byte because just like plumber names, the actual id is alligned awkwardly
                    message.extend(struct.pack('>H', nameid)) # Add the actual data as derived from the dictionary
                    message.extend(b'\x00') # Add the null to bring us to length of 8
            else:
                error('Message "' + name + '": tag "' + tag + '" not recognized', 1)
                break
            # if total > 5:  # debug
            #     break
        elif char == '&': # if char not '<'
            # Handle xml escape characters!?
            xmlescname = '' # put stuff in here as we go
            while True:
                char = xmlf.read(1) # increment through text
                if char == ';': # "Properly" add the corresponding character to the message
                    oldxmlescname = xmlescname
                    xmlescname.replace('amp','&').replace('lt','<').replace('gt','>').replace('quot','"').replace('apos',"'")    
                    message.extend(bytearray(xmlescname, "utf-16-be"))
                    break
                else:
                    xmlescname += char
                    if len(xmlescname) > 4:
                        error('Message "' + name + '": Invalid XML escape "&' + xmlescname + '"', 1) # Don't let a missed ';' destroy everything
        elif inmessage: # if char not '<'
            message.extend(bytearray(char, "utf-16-be")) # add the char to the message (using proper encoding!)

# quit(-1)





# for event, elem in ET.iterparse(xmlfilepath, events=('start','end')):
#     if elem.tag == 'message':							# All message starts and ends are already handled here...
#         if event == 'start':
#             inf1.extend(packtuple(elem.get('info')))
#             inf1.extend(struct.pack('>I',len(dat1)))
#             if elem.text is not None:
#                 text.extend(elem.text.encode('utf_16_be'))
#             name = elem.get('name')
#             if name is None:
#                 error('Message' + str(total) + 'does not have a "name" attribute.', 1)
#         elif event == 'end':
#             if dat1 == bytearray():
#                 dat1.extend(b'\x00\x00')
#             if text != bytearray():
#                 dat1.extend(text)
#                 dat1.extend(b'\x00\x00')
#                 text = bytearray()
#             else:
#                 # If it's blank, replace the pointer with a pointer to 0.
#                 inf1 = inf1[:-12]
#                 inf1.extend(packtuple(elem.get('info')))
#                 inf1.extend(b'\x00\x00\x00\x00')
#             total += 1
#     elif elem.tag != 'MESGbmg1':
#         if event == 'start':
#             if elem.tag == 'note':
#                 text.extend(b'\x26\x6A')
#             else:
#                 tempgettag = dnames.get(elem.tag)
#                 if tempgettag is None:
#                     error('Message "' + name + '": Tag "' + elem.tag + '" is not valid.', 1) 
#                 tag = int(dnames.get(elem.tag))
#                 text.extend(b'\x00\x1A')
#                 if tag == 1:
#                     if elem.get('length') in doddpause:
#                         text.extend(b'\x06\x01')
#                         text.extend(struct.pack('>H', int(doddpause.get(elem.get('length')))))
#                     else:
#                         text.extend(b'\x08\x01')
#                         text.extend(struct.pack('>I', int(dpause.get(elem.get('length')))))
#                 elif tag == 2:  # Super difficult sound tag
#                     tx = elem.get('name')
#                     text.append(6 + (len(tx) * 2))
#                     text.extend(b'\x02\x00\x00')
#                     text.extend(tx.encode('utf_16_be'))
#                 elif tag == 3:
#                     text.extend(b'\x06\x03')
#                     text.extend(struct.pack('>H', int(demoji.get(elem.get('name')))))
#                 elif tag == 4:
#                     text.extend(b'\x06\x04')
#                     text.extend(struct.pack('>H', int(dsizes.get(elem.get('name')))))
#                 elif tag == 5:
#                     text.extend(b'\x08\x05\x00')     # Plumber names (actually the second-to-last byte)
#                     text.extend(struct.pack('>H', int(dplumber.get(elem.get('style')))))
#                     text.extend(b'\x00')
#                 elif tag == 6 or tag == 7:
#                     text.extend(b'\x0e')
#                     text.append(tag)
#                     text.extend(b'\x00')
#                     tup = packtuple(elem.get('id'))
#                     text.append(tup[0])
#                     text.extend(b'\x00\x00\x00\x00\x00\x00\x00')
#                     text.append(tup[1])
#                 elif tag == 9:
#                     text.extend(b'\x06\x09\x00\x05')
#                 elif tag == 255:                 # Color tags, which seem to be causing problems?
#                     text.extend(b'\x08\xFF\x00\x00')
#                     text.append(int(dcolor.get(elem.get('name'))))
#                     text.extend(b'\x00')
                
#             begintail = elem.tail

#             # if elem.tail is not None:  
#             #     text.extend(elem.tail.encode('utf_16_be'))
#             # if total > 100 and total < 140:
#             #     print(str(elem.tail))
#         elif event == 'end':
#             if elem.tail != begintail:
#                 if debug:
#                     print('Beginning tail: ',begintail) # oddly enough, these are never called
#                     print('End tail: ',elem.tail)
#             if elem.tail is not None:
#                 text.extend(elem.tail.encode('utf_16_be'))          # so try this line out see if it fixes it

#     if debug:
#         if event == 'start':
#             if elem.tag != 'MESGbmg1':
#                 if name in ldebug:
#                     if elem.tag == 'color':
#                         print('message',total,'global tag',totaltags,'('+name+',',elem.tag+'"'+elem.get('name')+'")')
#                     else:
#                         print('message',total,'global tag',totaltags,'('+name+',',elem.tag+')')
#             totaltags += 1

if total == 2464:
    print('Processed 2464 messages.')
else:
    print('\nWARNING! There are supposed to be 2464 messages, but instead',total,'were found. This will probably cause glitches in the game.\n')

while len(inf1) % 32 != 0: # pad to a multiple of 32
    inf1.append(0)
# with open('inf1beta.bmg', 'wb') as ifile:
#     ifile.write(b'INF1')
#     ifile.write(struct.pack('>I', len(inf1) + 16))
#     ifile.write(struct.pack('>H', total))
#     ifile.write(b'\x00\x0c\x00\x00\x00\x00')
#     ifile.write(inf1)

while (len(dat1) - 8) % 32 != 0: # pad to a multiple of 32
    dat1.append(0)
# with open('dat1betatest.bmg', 'wb') as dfile:
#     dfile.write(b'DAT1')
#     dfile.write(struct.pack('>I', len(dat1) + 8))
#     dfile.write(dat1)

print("Copying flow section bytes from original BMG...")

flbytes = bytearray()
# Get the fl sections at the end using the existing bmg,
# because I have no idea what they actually mean.
try: # Check two places for the original BMG.
    fget = open(folder + filename + '.bmg', 'rb')
except:
    try:
        fget = open(folder + 'message.bmg', 'rb')
    except:
        error('Please put the XML file in the same folder as the original BMG. (Unable to copy FLW and FLI bytes!)')
fget.seek(8)
flwoffset = struct.unpack('>I', fget.read(4))[0] # Nab the offset of the fl sections.
fget.seek(flwoffset)                             # Then go to that offset
# save flbytes for later because we're gonna overwrite the file
flbytes = fget.read()
fget.close()

with open(folder + filename + '.bmg', 'wb') as mfile:
    print('Writing BMG file...')
    mfile.write(b'MESGbmg1')
    mfile.write(struct.pack('>I', len(inf1) + len(dat1) + 16 + 8 + 32)) # Length of file at 0x08 in header
    mfile.write(b'\x00\x00\x00\x04') # 4 is the number of sections in the file (inf1, dat1, flw1, and fli1)
    mfile.write(b'\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00') # 2 is the encoding (utf-16), and the zeros are unknown

    mfile.write(b'INF1') # inf1 section magic
    mfile.write(struct.pack('>I', len(inf1) + 16)) # +16 to compensate for inf1 section header
    mfile.write(struct.pack('>H', total)) # number of messages
    mfile.write(b'\x00\x0c\x00\x00\x00\x00') # 0x0C is the length of each inf1 entry
    mfile.write(inf1) # write the inf1 we've been compiling
    inf1 = bytearray() # empty this variable

    mfile.write(b'DAT1') # dat1 section magic
    mfile.write(struct.pack('>I', len(dat1) + 8)) # length of dat1 +8 for the dat1 section header
    mfile.write(dat1) # write the actual dat1
    dat1 = bytearray() # empty this variable

    mfile.write(flbytes) # put the fl bytes we copied
    flbytes = bytearray() # empty this variable for no good reason since ending the script will free the memory anyway
    print('Finished writing BMG file. Have a nice day!')

# print('\nWARNING! At the moment, there is a bug where random parts of messages get removed. This issue is known and is being worked on.')

# # # 