# Honoruty, a message converter for SMG1's BMG message files, (c) 2020 EPICHICKENSOUP
# This software is under the GNU GPL 3.0 license. Find out more at https://www.gnu.org/licenses/.

import struct
import csv
import os
import sys
from pathlib import Path

def error(string, errtype=0):
    """Predefined/preformatted error function."""
    if errtype == 1:
        pre = 'XML error!'
    else:
        pre = 'Error!'
    print('\n'+pre, string, '\n')
    input('Press enter to exit.')
    quit(-1)

debug = False # debug mode. Unlike msg2xml, doesn't control verbosity

try:
    xmlfilepath = sys.argv[1]
except:
    error('Please input a file.\nExample: python xml2msg.py message.xml')
if os.name == 'nt': # if windows
    indexlasttick = xmlfilepath.rfind('\\')
else: # if normal
    indexlasttick = xmlfilepath.rfind('/')
folder = xmlfilepath[0 : indexlasttick + 1]
filename = xmlfilepath[indexlasttick + 1 :]
filename = filename[0:filename.rfind('.')]

endian = '>' # Gonna do this just like msg2xml.py does it... with a character we set to the whichever endian
escape = b'\x00\x1A'
if debug:
    print('Folder: ' + folder)   
with open(xmlfilepath, 'r') as f: # Make sure the path to the xml file is valid
    magic = f.read(10)
    if magic != '<MESGbmg1>':
        if magic == '<GSEM1gmb>': # It is in 3DAS mode!
            print('Converting to little endian file for 3DAS!')
            endian = '<'
            escape = b'\x1A\x00'
        else:
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

def getcsvmore(f):
    """Get the "more" value (usually the last one) from one of the csvs."""
    source = csv.reader(open(f))
    redict = dict(source)
    return redict.get('more')

# use this to find the csv folder
scriptpath = Path(os.path.dirname(os.path.realpath(sys.argv[0])))
if debug:
    print('Script at path ' + str(scriptpath))
csv_folder = scriptpath / 'csv'
# Import all the dictionaries from attatched CSVs
print('Fetching CSV files...')
if endian == '>': # if smg
    demoji = getinvdict(csv_folder / 'emoji_hex.csv')
    emoji_unknown_text = getcsvmore(csv_folder / 'emoji_hex.csv')
else: # if 3das
    demoji = getinvdict(csv_folder / 'emoji_3das.csv')
    emoji_unknown_text = getcsvmore(csv_folder / 'emoji_3das.csv')
print(f'emoji_unknown_text is "{emoji_unknown_text}"')
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

def formmessageinf(tup): # input a string of a tuple and recieve an 8 byte long bytearray that is the message inf
    actualtuple = str(tup).replace('(', '').replace(')','').split(',')
    print(f'   actualtuple {actualtuple}')
    camerashort = bytearray(struct.pack(f'{endian}H', int(actualtuple[0])))
    actualtuple = actualtuple[1:]
    ret = camerashort
    for i in actualtuple:
        ret.append(int(i))
    return ret

inf1 = bytearray()             # inf1 section contains a bunch of bytes in order `pointer` (4 bytes), `info` (for smg, 8 bytes)
dat1 = bytearray(b'\x00\x00')  # Bytearray to put all of the message strings into. Written to file at the end of parsing.
                               # Preloaded with the 2 null bytes for blank messages to point to.
                               # Fun fact, I'm reading the file wrong... the very first message is named "" and has no content. It does have properties though.
# Bonus. I could replace these bytearrays with a bunch of "message" structs containing the name, inf, and data. Then, just write them all to the file at the end.
# In this way, I could add automatic message sorting.

v = True # Verbosity setting
total = 0
if debug:
    totaltags = 0
message_name = ''

text = bytearray()
begintail = ''

# A list of messages to debug.
ldebug = ['AstroGalaxy_ButlerMap006','AstroGalaxy_Tico027','AstroGalaxy_Rosetta057','CONT_10_2','ForestHomeZone_HoneyBee005','HeavensDoorInsideZone_Tico004','Layout_StoryDemoKoopaTalk006','PictureBookChapter4_Page4_001','ScenarioName_CosmosGardenGalaxy4','Select_ReturnToAstro_No','SurfingLv2Galaxy_Penguin015']

print('Beginning XML parsing...')

with open(xmlfilepath, 'r') as xmlf: # open xml file
    
    inmessage = False   # We are not currently in a message. Keep track
    message_text = bytearray()   # build message into this variable, it's a bytearray because of binary escapes
    while True:
        char = xmlf.read(1) # repeat until first '<' idk
        if char == '<': # look at you finding a tag
            if v: print('"<" at ' + str(xmlf.tell()))
            xml_tag = ''
            while True: # Get the tag real quick
                char = xmlf.read(1)
                if (char == ' ' or char == '\n' or char == '>' or char == '/') and not xml_tag == '': # allow spaces and all sorts of silly stuff before the tag
                    break
                xml_tag += char
                # Now we know the inside of the XML tag!

            if xml_tag.startswith('/'): # End tag. If it starts with a '/' it's an end tag, so basically ignore it
                if xml_tag == '/message':  # Message ended!
                    inmessage = False # Message ended!
                    message_text.extend(b'\x00\x00') # Add the null character at the end of the message
                    if v: print('Message ended as "' + str(message_text) + '"!')
                    dat1 += message_text # Add the message to the dat
                    message_text = bytearray() # clear the message, we are done reading it
                
                if xml_tag == '/MESGbmg1' or xml_tag == '/GSEM1gmb': # We must have reached the end of the file! Break the big while loop
                    break

            
            elif xml_tag == 'message': # Start of a message.
                total += 1  # add to the message count to track errors for the user
                inmessage = True

                dat1start = len(dat1) # Record where message is going to start when added (as long as message isn't blank)
                if v: print('Message starting at ' + hex(dat1start))

                namefound = False # keep track of whether we've found the name while we're looking for it
                message_name = ''
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
                        message_name = prop[6:-1]
                        if v: print(f'Name property found, very good. It\'s "{message_name}"')
                        # You could check the name against the original file somewhere in here if you were to, say, check for missing messages.
                        namefound = True
                    elif prop.startswith('info="'): # info property found, use our inf packing function
                        # put info in a variable
                        inf = formmessageinf(prop[6:-1])
                        if v: print('Info property found, very good. It\'s "' + prop[6:-1] + '" aka "' + str(inf) + '"')
                    if char == '/' or char == '>':
                        if not namefound: # got to end without finding name??
                            error('name property of message ' + str(total) + ' not found!', 1)
                        if not (len(inf) > 1): # Also check if info existed, since we will be writing that
                            error(f'info property of message {message_name} not found!', 1)
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


            elif xml_tag == 'note': # keeping support for this bc it's easier to type
                if endian == '>': # if smg, big endian
                    message_text.extend(b'\x26\x6A') # apparently this is ascii '&j', who knew?
                else: # if 3das
                    message_text.extend(b'\x6A\x26')
                while True: # do while to get to the end of the note tag
                    char = xmlf.read(1) # keep advancing 1 char at a time
                    if char == '>':
                        break
            
            elif xml_tag in dnames: # If the tag shows up in our names dictionary
                tagid = int(dnames.get(xml_tag))
                if v: print('Tag "' + xml_tag + '" has id ' + str(tagid))
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
                    error(f'Message "{message_name}": Element "{xml_tag}" has no properties', 1)
                else:
                    if v: print('     Properties: "' + props + '"')
                if tagid == 1: # Pauses
                    if props[0:8] == 'length="':
                        lengthstr = props[8:-1]  # Write to a string to easier check the dictionaries
                        if lengthstr in doddpause:
                            lengthid = int(doddpause.get(lengthstr))
                            message_text.extend(escape)
                            message_text.extend(b'\x06\x01')    # Extend with the escape character, lenth of 6, and id 1
                            message_text.extend(struct.pack('>H', lengthid))  # Pack number from dictionary as a big endian unsigned short and append
                        elif lengthstr in dpause:
                            lengthid = int(dpause.get(lengthstr))
                            message_text.extend(escape)
                            message_text.extend(b'\x08\x01')    # Extend with escape character, length of 8, and id of 1
                            message_text.extend(struct.pack('>I', lengthid))  # Pack number from dictionary as a big endian unsigned int and append
                        else:
                            error(f'Message "{message_name}": {xml_tag} tag has invalid length property "{lengthstr}"', 1)
                            # Descriptive errors to make it as user friendly as possible :D
                    else:
                        error(f'Message "{message_name}": {xml_tag} tag missing "length" property', 1)
                elif tagid == 2: # Sound tag
                    if props[0:6] == 'name="':
                        namestr = bytearray(props[6:-1], "utf-16-be")  # Encode the name string
                        print('     !! Sound found, sound name is "' + props[6:-1] + '" !!')
                        message_text.extend(escape) # Escape character
                        message_text.extend(struct.pack('>B', (6 + len(namestr)))) # Pack string length (+6 for the escape sequence itself and first null bytes) to a single byte and add it.
                        message_text.extend(b'\x02\x00\x00') # Add escape identifier and 2 null bytes for no good reason.
                        message_text.extend(namestr) # Finally, add the actual name string.
                    else:
                        error(f'Message "{message_name}": {xml_tag} tag missing "name" property', 1)
                elif tagid == 3: # Emoji tag
                    if props[0:6] == 'name="':
                        if props[6:-1] in demoji:
                            nameid = int(demoji.get(props[6:-1])) # Get the ID of the emoji using the properties string and our dictionary
                        elif props[6:-1].startswith(emoji_unknown_text): # need to check if the first letters are the csv entry for 'unknown' / 'more' 
                            try:
                                nameid = int(props[6 + len(emoji_unknown_text):-1])
                            except:
                                error(f'Message "{message_name}": Special "{emoji_unknown_text}" {xml_tag} tag: "{props[len(emoji_unknown_text):-1]}" is not a valid integer.')
                        else:
                            error(f'Message "{message_name}": {xml_tag} tag has invalid name property "{props [6:-1]}"')
                    else:
                        error(f'Message "{message_name}": {xml_tag} tag missing "name" property', 1)
                    message_text.extend(escape)
                    message_text.extend(b'\x06\x03')  # Add escape character, length, and identifier
                    message_text.extend(struct.pack('>H', nameid))  # Pack emoji ID to a (big endian) short and add it
                elif tagid == 4: # Text size
                    if props[0:6] == 'name="':
                        if props[6:-1] in dsizes:
                            nameid = int(dsizes.get(props[6:-1]))
                        else:
                            error(f'Message "{message_name}": {xml_tag} tag has invalid name property "{props[6:-1]}"', 1)
                        message_text.extend(escape)
                        message_text.extend(b'\x06\x04')
                        message_text.extend(struct.pack('>H', nameid))
                    else:
                        error(f'Message "{message_name}": {xml_tag} tag missing "name" property')
                elif tagid == 5: # Player's name
                    if props[0:7] == 'style="':
                        if props[7:-1] in dplumber:
                            nameid = int(dplumber.get(props[7:-1]))
                        else:
                            error(f'Message "{message_name}": {xml_tag} tag has invalid style property "{props[7:-1]}"', 1)
                    else:
                        error(f'Message "{message_name}": {xml_tag} tag missing "style" property')
                    message_text.extend(escape)
                    message_text.extend(b'\x08\x05\x00') # Add the escape character, length, and escape ID.  Also a null byte to allign the number.
                    message_text.extend(struct.pack('>H', nameid))  # Pack the name number into 2 bytes
                    message_text.extend(b'\x00')  # Add some null to allign it
                elif tagid == 6 or tagid == 7: # Number or system text. Pretty weird.
                    if props[0:4] == 'id="':
                        nameid = packtuple(props[4:-1]) # reusing the nameid variable, guess it stands for "name/id" now
                        message_text.extend(escape)
                        if tagid == 6: # Add the escape character, the length of the escape, and either 6 or 7 for the escape ID (LEN 4)
                            message_text.extend(b'\x0E\x06')
                        else:
                            message_text.extend(b'\x0E\x07')
                        message_text.extend(b'\x00') # A null byte to allign the first number of the ID (LEN 5)
                        message_text.extend(struct.pack('>B', nameid[0])) # Pack and add first number (LEN 6)
                        message_text.extend(b'\x00\x00\x00\x00\x00\x00\x00') # 7 null bytes to allign the second number (LEN 13)
                        message_text.extend(struct.pack('>B', nameid[1])) # Pack and add second number (LEN 14 = 0xE)
                    else:
                        error(f'Message "{message_name}": {xml_tag} tag has invalid id property "{props [4:-1]}"', 1)
                elif tagid == 9: # No tag 8 for some reason, maybe it's a secret!
                    message_text.extend(escape)
                    message_text.extend(b'\x06\x09\x00\x05')  # tagid 9 is the race time. No part of it changes (in the original game...)
                elif tagid == 255: # lol why is color -1 or FF depending on if this number is technically signed or not?
                    if props[0:6] == 'name="': # Check if they wrote the name property validly
                        if props[6:-1] in dcolor:
                            nameid = int(dcolor.get(props[6:-1]))
                        else:
                            error(f'Message "{message_name}": {xml_tag} tag has invalid name property "{props[6:-1]}"', 1)
                    else:
                        error(f'Message "{message_name}": {xml_tag} tag missing "name" property', 1)
                    message_text.extend(escape)
                    message_text.extend(b'\x08\xFF\x00') # Add escape character, escape length, escape ID, and a null byte because just like plumber names, the actual id is alligned awkwardly
                    message_text.extend(struct.pack('>H', nameid)) # Add the actual data as derived from the dictionary
                    message_text.extend(b'\x00') # Add the null to bring us to length of 8
            else:
                if xml_tag != 'MESGbmg1' and xml_tag != 'GSEM1gmb': # don't call the file name ones invalid
                    error(f'Message "{message_name}": tag "{xml_tag}" not recognized', 1)
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
                    if endian == '>': # if big endian
                        message_text.extend(bytearray(xmlescname, "utf-16-be"))
                    else: # if 3das
                        message_text.extend(bytearray(char, "utf-16-le"))
                    break
                else:
                    xmlescname += char
                    if len(xmlescname) > 4:
                        error(f'Message "{message_name}": Invalid XML escape "&{xmlescname}"', 1) # Don't let a missed ';' destroy everything
        elif inmessage: # if char not '<'
            if endian == '>': # if big endian
                message_text.extend(bytearray(char, "utf-16-be")) # add the char to the message (using proper encoding!)
            else: # if 3das
                message_text.extend(bytearray(char, "utf-16-le"))


if total == 2464:
    print('Processed 2464 messages.')
else:
    print(f'\nWARNING! There are supposed to be 2464 messages, but instead {total} were found. This will probably cause glitches in the game.\n')

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
    if endian == '>': # if smg
        mfile.write(b'MESGbmg1')
    else: # if 3das
        mfile.write(b'GSEM1gmb')
    mfile.write(struct.pack(f'{endian}I', len(inf1) + len(dat1) + 16 + 8 + 32)) # Length of file at 0x08 in header
    #mfile.write(b'\x00\x00\x00\x04')
    mfile.write(struct.pack(f'{endian}I', 4))  # 4 is the number of sections in the file (inf1, dat1, flw1, and fli1)
    mfile.write(b'\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00') # 2 is the encoding (utf-16), and the zeros are unknown

    if endian == '>': # if smg
        mfile.write(b'INF1') # inf1 section magic
    else: # if 3das
        mfile.write(b'1FNI')
    mfile.write(struct.pack(f'{endian}I', len(inf1) + 16)) # +16 to compensate for inf1 section header
    mfile.write(struct.pack(f'{endian}H', total)) # number of messages
    mfile.write(struct.pack(f'{endian}H', 12)) # 0x0C is the length of each inf1 entry
    mfile.write(b'\x00\x00\x00\x00') # Some padding
    mfile.write(inf1) # write the inf1 we've been compiling
    inf1 = bytearray() # empty this variable

    if endian == '>': # if smg
        mfile.write(b'DAT1') # dat1 section magic
    else: # if 3das
        mfile.write(b'1TAD') # lol tad
    mfile.write(struct.pack(f'{endian}I', len(dat1) + 8)) # length of dat1 +8 for the dat1 section header
    mfile.write(dat1) # write the actual dat1
    dat1 = bytearray() # empty this variable

    mfile.write(flbytes) # put the fl bytes we copied
    flbytes = bytearray() # empty this variable for no good reason since ending the script will free the memory anyway
    print('Finished writing BMG file. Have a nice day!')

# print('\nWARNING! At the moment, there is a bug where random parts of messages get removed. This issue is known and is being worked on.')

# # # 