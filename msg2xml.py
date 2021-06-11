# Honoruty, a message converter for SMG1's BMG message files, (c) 2020 EPICHICKENSOUP
# This software is under the GNU GPL 3.0 license. Find out more at https://www.gnu.org/licenses/.

import struct
import csv
import os
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

def error(string):
    print('\nError!',string,'\n')
    input('Press enter to exit.')
    quit(-1)

def getdict(f):
    """Return a dictionary created from a csv file."""
    try:
        source = csv.reader(open(f))
        redict = dict(source)
        return redict
    except:
        error('CSV file at "' + str(f) + '" not found! \nMake sure the "csv" folder is present in the executable directory.')

def offset(o, l):
    """Get bytes at offset o for length l."""
    # You can give this function either hex or int byte values!
    if type(o) is str:
        f.seek(int(o, 16))
    else:
        f.seek(o)
    return f.read(l)

debug = False


try: # get the path to the bmg file
    messagefilepath = sys.argv[1]
except:
    error('Please input a file.')
if os.name == 'nt': # true if windows, false if else
    indexlasttick = messagefilepath.rfind('\\')
else:
    indexlasttick = messagefilepath.rfind('/')
folder = messagefilepath[0:indexlasttick + 1]
filename = messagefilepath[indexlasttick + 1:]
filename = filename[0:filename.rfind('.')]

# First of all (before loading the CSVs), check the file magic.
endian = '>'
with open(messagefilepath, mode='rb') as f:
    # Get the 'file magic' to display the file type
    magic = offset(0,8)
    if debug:
        print(str(magic))
    if str(magic) == "b'GSEM1gmb'":
        print('Error... just kidding, you\'re converting SM3DAS text. Have fun!')
        endian = '<'
    elif str(magic) != "b'MESGbmg1'":
        error('Please input a BMG type file.')

scriptpath = Path(os.path.dirname(os.path.realpath(sys.argv[0])))
#print('Script at path:')
#print(scriptpath)
csv_folder = scriptpath / 'csv'
# Import all the dictionaries from attatched CSVs
print('Fetching CSV files...')
if endian == '<': # if 3das
    demoji = getdict(csv_folder / 'emoji_3das.csv')
else: # if normal
    demoji = getdict(csv_folder / 'emoji_hex.csv')
dcolor = getdict(csv_folder / 'color_hex.csv')
dpause = getdict(csv_folder / 'pause_hex.csv')
doddpause = getdict(csv_folder / 'oddpause_hex.csv')
dnumber = getdict(csv_folder / 'number_hex.csv')
dnames = getdict(csv_folder / 'names_hex.csv')
dsizes = getdict(csv_folder / 'sizes_hex.csv')
dplumber = getdict(csv_folder / 'plumber_hex.csv')
print('  All CSV files loaded.')


def getmsgname(id): 
    """Get message name at index 'id' from messageid.tbl."""
    pid = id        # this will start at 1
    retname = ''
    startofnames = 32 + ((msgnum + 1) * 8) # msgnum +1 because the blank message is unaccounted for???
    if pid < (msgnum + 1):    # if the message exists...
        msgnameoffset = struct.unpack(f'{endian}I', idtbloffset(32 + (pid * 8) + 4, 4))[0]  # Without that +4, reads the message id.
                                                                                    # Get what the file says is the location of the name.

        #print(f'Attempting to read a char from {hex(startofnames + msgnameoffset)} ({hex(startofnames)} + {hex(msgnameoffset)})')

        b = struct.unpack('>B', idtbloffset(startofnames + msgnameoffset, 1))[0]  # Get the first character of the text.
                                                                                  # Do this by adding the file-given offset to the position the text pool starts at.
        i = 0
        while b != 0 and b != 40: # if not a null or an @ char, add it to the name
            retname = retname + chr(b)
            i = i + 1
            b = struct.unpack('>B', idtbloffset(startofnames + msgnameoffset + i, 1))[0]
    return retname

def idtbloffset(o, l):
    """Get bytes of the messageid tbl at offset o for length l."""
    msgidtbl.seek(o)
    return msgidtbl.read(l)

def getmsginf(id):
    """Given a message ID, returns the INF, including offset and parameters"""
    tempinf = struct.unpack('>BBBB', offset(48 + (id * slen) + 8, slen - 8))
    return tempinf

def getfullmsginf(id) -> tuple:
    camerashort = struct.unpack(f'{endian}H', offset(48 + ((id - 1) * slen) + 4, 2))
    otherinf = struct.unpack('>BBBBBB', offset(48 + ((id - 1) * slen) + 4 + 2, slen - 6))
    return (camerashort + otherinf) # combines the two tuples # + ("offset", hex(48 + (id * slen) + 4))

def getmsgoff(id):
    """Gets the offset into DAT1 of a message."""
    return struct.unpack(f'{endian}I', offset(48 + (id * slen), 4))[0]

def getmsg(id):
    """Get a message by its ID."""
    # msglen is ineffective, since some message IDs are blank / padding.
    # msglen = getmsgoff(id + 1) - getmsgoff(id)
    result = ""
    inc = 0
    curmsgoff = getmsgoff(id)
    charbytes = bytearray(offset(dat1o + 8 + curmsgoff, 2)) # get two-byte character
    bb = struct.unpack('>BB', offset(dat1o + 8 + curmsgoff, 2)) # get the same thing as a tuple because apparently I'm really stupid and can't figure out how bytearray() works.
    # Check each 2 bytes and add the char to the result, but stop on a null double byte
    while bb != (0, 0): # can't figure out how to do this with charbytes for some reason
        if endian == '<': # if little endian (3DAS), flip the two read bytes backwards
            newbb = (bb[1], bb[0])
            bb = newbb
            charbytes.reverse()
        
        # print(charbytes)
        if charbytes == bytearray(b'\x00\x1A'): # our escape character
            # print('Found an escape char')
            idtuple = struct.unpack('>BB', offset(dat1o + 10 + curmsgoff + inc, 2))
            result = result + '<' + dnames.get(str(idtuple[1]), dnames.get('more')) + ' '
            if idtuple[1] == 1:
                # It's a pause
                if idtuple[0] == 8:
                    # used to get a big endian integer, switched to a halfword in the last 2 bytes because of 3das. Interesting that there are 2 always-zero bytes at the beginning. They probably are padding due to Nintendo using the same if length system I am.
                    pauselen = struct.unpack(f'{endian}H', offset(dat1o + 12 + curmsgoff + inc + 2, 2))[0]
                    gotlen = dpause.get(str(pauselen), dpause.get('more'))
                else:
                    pauselen = struct.unpack(f'{endian}H', offset(dat1o + 12 + curmsgoff + inc, 2))[0]
                    gotlen = doddpause.get(str(pauselen), dpause.get('more'))
                result = result + 'length="' + gotlen + '"'
            elif idtuple[1] == 2:
                # It's an animation... or maybe a sound?
                miniinc = 2
                animname = ''
                while miniinc < idtuple[0] - 4:
                    animname = animname + chr(struct.unpack('>BB', offset(dat1o + 12 + curmsgoff + inc + miniinc, 2))[1])
                    miniinc = miniinc + 2
                result = result + 'name="' + animname + '"'
            elif idtuple[1] == 3:
                # print("It's an emoji")
                emojiid = struct.unpack(f'{endian}H', offset(dat1o + 12 + curmsgoff + inc, 2))[0]
                # print(str(emojiid))
                # print('<emoji name="' + demoji.get(str(emojiid), demoji.get("more")) + '"/>')
                # adding emoji id for debug purposes, would be pretty nice if it stayed but people can just edit the CSVs (shrug)
                result = result + 'name="' + demoji.get(str(emojiid), demoji.get('more') + str(emojiid)) + '"'
            elif idtuple[1] == 4:
                # There are 3 sizes they use (thanks, Hackio)!  Anyway... sizes.
                sizeid = struct.unpack(f'{endian}H', offset(dat1o + 12 + curmsgoff + inc, 2))[0]
                result = result + 'name="' + dsizes.get(str(sizeid), dsizes.get('more')) + '"'
            elif idtuple[1] == 5:
                # The plumber names were already handled... or so I thought
                plumberid = round(struct.unpack('>I', offset(dat1o + 12 + curmsgoff + inc, 4))[0] / 256)
                result = result + 'style="' + dplumber.get(str(plumberid), dplumber.get("more")) + '"'
            elif idtuple[1] == 6 or idtuple[1] == 7:
                # This is a number or systemtext. They are entered the same way! Also, no information is lost, so hooray!
                systextuple = struct.unpack('>BBBBBBBBBB', offset(dat1o + 12 + curmsgoff + inc, 10)) # grab 10 bytes. Admittedly lazy
                if endian == '>':
                    needed = (systextuple[1], systextuple[9])
                else: # if 3das
                    needed = (systextuple[0], systextuple[6]) # evidently of type "int16" and "int32"
                result = result + 'id="' + str(needed) + '"'
            elif idtuple[1] == 9:
                #Race time.
                #Racetime ID seems to always be (0, 5)
                # unpack = struct.unpack('>BB', offset(dat1o + 8 + 4 + curmsgoff + inc, 2))
                # result = result + 'id="' + str(unpack) + '"'
                pass
            elif idtuple[1] == 255:
                # It's a color identifier
                # Divide colorid by 256 because it's actually in the 3rd byte, not the 4th (dunno why I did it this way)
                    # and it still works in 3das XD
                colorid = round(struct.unpack('>I', offset(dat1o + 12 + curmsgoff + inc, 4))[0] / 256)
                result = result + 'name="' + dcolor.get(str(colorid), dcolor.get("more")) + '"'
                # dcolor.get(, dcolor.get("more"))
            else:
                # It's gonna show me any binary things I haven't gotten yet
                print(f'Message {id}: Oops, apparently I missed an escape tag with ID "' + str(idtuple) + '", please report this on Github.')
                quit()
            # So this is super cool... they put the offset to the next normal text in the first byte after 001A.
            # Thus, this will automatically skip any weird characters... our XML is officially valid now!
            # but I should probably still add all the idtuple[1] values I can find for full support
            # and to prevent loss of info when reimporting
            inc = inc + idtuple[0]
            result = result + '/>'
        else:
            # Add the character to the message. The music note is a utf-16 character!
            result = result + '</note>'# charbytes.decode('utf-16-be') temp fix until xml2msg is not dumb
            inc = inc + 2
        charbytes = bytearray(offset(dat1o + 8 + curmsgoff + inc, 2))
        bb = struct.unpack('>BB', offset(dat1o + 8 + curmsgoff + inc, 2))
    return result

with open(messagefilepath, mode='rb') as f: # opening the bmg file for reading... all the other things are just functions
    # We've already got the 'file magic', did that first
    totalbytelen = struct.unpack(f'{endian}I', offset(8, 4))[0]
    if debug:
        print('Length of file in bytes is ' + str(totalbytelen))
        # Total length in bytes is the offset of the FLW1 header
        print('so I guess it ignores everything past ' + str(offset(totalbytelen, 4)) + '?')
    #sections = struct.unpack('>I', offset('0C', 4))[0]
    #print('OK there are ' + str(sections) + ' sections (should be 4 for SMG!)')
    slen = struct.unpack(f'{endian}H', offset('2A',2))[0]
    if debug:
        print('The length of each ID is ' + str(slen))
        print('The first message inf is ' + str(getfullmsginf(0)))
    # Offset of DAT1 section is length of INF1 plus 32 bytes
    dat1o = 32 + struct.unpack(f'{endian}I', offset(36, 4))[0]
    if debug:
        print('Offset of DAT1 section is ' + str(dat1o))
        print('\n')

    msgnum = struct.unpack(f'{endian}H', offset('28', 2))[0]
    print('There are ' + str(msgnum) + ' messages in the file.')
    
    # print("\nTesting escape sequences:")
    #print(getmsg(2))

    # This next section makes the xml
    if endian == '>':
        root = ET.Element('MESGbmg1')
    else:
        root = ET.Element('GSEM1gmb') # if 3das do the 3das thing
    
    try: # Try to open {filename}.tbl
        msgidtbl = open(folder + filename + '.tbl', 'rb')
    except:
        print(f'Reading {folder}{filename}id.tbl')
        try: # Try to open {filename}id.tbl
            msgidtbl = open(f'{folder}{filename}id.tbl', 'rb')
        except: 
            try: # Finally, try to open messageid.tbl
                print(f'Failed! Reading {folder}messageid.tbl')
                msgidtbl = open(f'{folder}messageid.tbl','rb')
            except: 
                error('Did not find messageid.tbl. Please make sure it is in the same directory as your BMG file.')
    with msgidtbl: # I should put an error for if it can't find this file!
        # allmsginf = ''
        # soundid = int(input("Search for sound "))
        soundid = 255
        soundsearch = []
        infsearch = ''
        infsearchlist = []
        i = 0
        while i < msgnum:
            i = i + 1
            # allmsginf = allmsginf + "{0:0=4d}".format(i) + ': ' + str(getfullmsginf(i)) + ' ' + getmsgname(i) + '\n'
            # tempcursoundid = getfullmsginf(i)[2]
            # if not tempcursoundid in allsoundids:
            #     allsoundids.append(tempcursoundid)
            #     allsoundids.append(getmsgname(i))
            # if tempcursoundid == soundid:
                # gotname = getmsgname(i)
                # print(gotname)
                # soundsearch.append(gotname)
            thismsginf = getfullmsginf(i)
            if not thismsginf in infsearchlist:
                infsearchlist.append(thismsginf)
                infsearch = infsearch + str(thismsginf) + '\n'
        # Uncomment the following if you'd like to research message properties.
        # with open('allusedinfsections.txt','w') as a:
        #     # allsoundids.sort()
        #     a.write(infsearch)
        #     soundsearch = []
        #     infsearch = ''

        allblanknames = ''
        print('Creating XML from ' + filename + '.bmg...')
        i = 0
        while i < msgnum:
            temptext = getmsg(i)
            i = i + 1
            # if temptext != '':
            s = ET.SubElement(root, 'message')
            s.set('name', getmsgname(i))
            s.set('info', str(getfullmsginf(i)))
            # s.set('flow', str(getmsgflw(i)))    
            s.text = temptext
            
        #     else:
        #         allblanknames = allblanknames + getmsgname(i) + '\n'
        
        # with open('allblankmessagenames.txt','w') as a:
        #     a.write(allblanknames)
        #     allblanknames = ''
        
        print("  Done.")
        tree = ET.ElementTree(root)
        tree.write(folder + filename + '.xml', encoding='utf-8')

        print("Fixing XML because I was lazy...")
        # Unfilter the created XML.  Hopefully y'all didn't use any greater/less-than symbols!
        readstr = ''
        with open(folder + filename + '.xml','r',encoding='utf-8') as msgfile:
            readstr = msgfile.read()
            readstr = readstr.replace('&gt;', '>').replace('&lt;', '<').replace('<message ', '\n     <message ').replace('</MESGbmg1>', '\n</MESGbmg1>').replace('</GSEM1gmb>', '\n</GSEM1gmb>') # GSEM1gmb
        with open(folder + filename + '.xml','w',encoding='utf-8') as msgfile:
            msgfile.write(readstr)
            print("  Done.")

        # nvm: minidom pretty print? more like minidom ugly print xd
        # # OK so xmlstr doesn't like invalid chars, so we're gonna have to filter those out first
        # xmlstr = minidom.parseString(readstr).toprettyxml(indent="   ")
        # with open('messages_beta.xml', 'w') as outputfile:
        #     outputfile.write(xmlstr)
