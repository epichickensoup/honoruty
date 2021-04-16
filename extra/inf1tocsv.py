import struct
import csv
import os
import sys
from pathlib import Path

def error(string):
    print('\nError!',string,'\n')
    if os.name == 'nt': #if windows
        os.system('pause')
    else: #assume posix, even though nothing else supports it :P
        os.system('read -n1 -r -p "Press any key to continue . . ."')
    quit()

def getdict(f):
    """Return a dictionary created from a csv file."""
    try:
        source = csv.reader(open(f))
        redict = dict(source)
        return redict
    except:
        error('CSV file at "' + str(f) + '" not found! \nMake sure the "csv" folder is present in the executable directory.')

scriptpath = Path(os.path.dirname(os.path.realpath(sys.argv[0]))).parents[0]
csv_folder = scriptpath / 'csv'
# Import all the dictionaries from attatched CSVs
print('Fetching CSV files...')
demoji = getdict(csv_folder / 'emoji_hex.csv')
dcolor = getdict(csv_folder / 'color_hex.csv')
dpause = getdict(csv_folder / 'pause_hex.csv')
doddpause = getdict(csv_folder / 'oddpause_hex.csv')
dnumber = getdict(csv_folder / 'number_hex.csv')
dnames = getdict(csv_folder / 'names_hex.csv')
dsizes = getdict(csv_folder / 'sizes_hex.csv')
dplumber = getdict(csv_folder / 'plumber_hex.csv')
print('All CSV files loaded.')

debug = False

def getmsgname(id):
    pid = id        # this will start at 1
    retname = ''
    startofnames = 32 + ((msgtblnum + 1) * 8) # msgnum +1 because the blank message is unaccounted for???
    if pid < (msgnum + 1):    # if the message exists...
        msgnameoffset = struct.unpack('>I', idtbloffset(32 + (pid * 8) + 4, 4))[0]  # Without that +4, reads the message id.
                                                                                    # Get what the file says is the location of the name.
        try:
            b = struct.unpack('>B', idtbloffset(startofnames + msgnameoffset, 1))[0]  # Get the first character of the text.
                                                                                        # Do this by adding the file-given offset to the position the text pool starts at.
        except:
            error('Failed to read name of message ' + str(id) + ' from ' + hex(startofnames + msgnameoffset) + ' (as listed at ' + hex(32 + (pid * 8) + 4) + ')')

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

def offset(o, l):
    """Get bytes at offset o for length l."""
    # You can give this function either hex or int byte values!
    if type(o) is str:
        f.seek(int(o, 16))
    else:
        f.seek(o)
    return f.read(l)

def getmsgflw(id):
    return struct.unpack('>I', offset(48 + (id * slen) + 4, 4))[0]

def getmsginf(id):
    """Given a message ID, returns the INF, including offset and parameters"""
    tempinf = struct.unpack('>BBBB', offset(48 + (id * slen) + 8, slen - 8))
    return tempinf

def getfullmsginf(id) -> tuple:
    camerashort = struct.unpack('>H', offset(48 + ((id - 1) * slen) + 4, 2))
    otherinf = struct.unpack('>BBBBBB', offset(48 + ((id - 1) * slen) + 4 + 2, slen - 6))
    return (camerashort + otherinf) # combines the two tuples # + ("offset", hex(48 + (id * slen) + 4))

def getmsgoff(id):
    """Gets the offset into DAT1 of a message."""
    return struct.unpack('>I', offset(48 + (id * slen), 4))[0]

def getmsg(id):
    """Get a message by its ID."""
    # msglen is ineffective, since some message IDs are blank / padding.
    # msglen = getmsgoff(id + 1) - getmsgoff(id)
    result = ""
    inc = 0
    curmsgoff = getmsgoff(id)
    bb = struct.unpack('>BB', offset(dat1o + 8 + curmsgoff, 2)) # get two-byte character
    # Check each 2 bytes and add the char to the result, but stop on a null double byte
    while bb != (0,0):
        if bb == (0, 26):
            # Found an escape char
            idtuple = struct.unpack('>BB', offset(dat1o + 10 + curmsgoff + inc, 2))
            result = result + '[' + dnames.get(str(idtuple[1]), dnames.get('more')) + ' '
            if idtuple[1] == 1:
                # It's a pause
                if idtuple[0] == 8:
                    pauselen = struct.unpack('>I', offset(dat1o + 12 + curmsgoff + inc, 4))[0]
                    gotlen = dpause.get(str(pauselen), dpause.get('more'))
                else:
                    pauselen = struct.unpack('>H', offset(dat1o + 12 + curmsgoff + inc, 2))[0]
                    gotlen = doddpause.get(str(pauselen), dpause.get('more'))
                result = result + gotlen
            elif idtuple[1] == 2:
                # It's a sound
                miniinc = 2
                animname = ''
                while miniinc < idtuple[0] - 4:
                    animname = animname + chr(struct.unpack('>BB', offset(dat1o + 12 + curmsgoff + inc + miniinc, 2))[1])
                    miniinc = miniinc + 2
                result = result + animname
            elif idtuple[1] == 3:
                # It's an emoji
                emojiid = struct.unpack('>H', offset(dat1o + 12 + curmsgoff + inc, 2))[0]
                result = result + demoji.get(str(emojiid), demoji.get('more'))
            elif idtuple[1] == 4:
                # There are 2 sizes they use... but I'll bet there are 3!  Anyway... sizes.
                sizeid = struct.unpack('>H', offset(dat1o + 12 + curmsgoff + inc, 2))[0]
                result = result + dsizes.get(str(sizeid), demoji.get('more'))
            elif idtuple[1] == 5:
                # The plumber names were already handled... or so I thought
                plumberid = round(struct.unpack('>I', offset(dat1o + 12 + curmsgoff + inc, 4))[0] / 256)
                result = result + dplumber.get(str(plumberid), dplumber.get("more"))
            elif idtuple[1] == 6 or idtuple[1] == 7:
                # This is a number or systemtext. They are entered the same way! Also, no information is lost, so hooray!
                systextuple = struct.unpack('>BBBBBBBBBB', offset(dat1o + 12 + curmsgoff + inc, 10))
                needed = (systextuple[1], systextuple[9])
                result = result + str(needed)
            elif idtuple[1] == 9:
                #Race time.
                #Racetime ID seems to always be (0, 5)
                # unpack = struct.unpack('>BB', offset(dat1o + 8 + 4 + curmsgoff + inc, 2))
                # result = result + 'id="' + str(unpack) + '"'
                pass
            elif idtuple[1] == 255:
                # It's a color identifier
                # Divide colorid by 256 because it's actually in the 3rd byte, not the 4th (dunno why I did it this way)
                colorid = round(struct.unpack('>I', offset(dat1o + 12 + curmsgoff + inc, 4))[0] / 256)
                result = result + dcolor.get(str(colorid), dcolor.get("more"))
                # dcolor.get(, dcolor.get("more"))
            else:
                # It's gonna show me any binary things I haven't gotten yet
                print('Oops, apparently I missed an element with ID "' + str(idtuple) + '", please report this on Github!')
            # So this is super cool... they put the offset to the next normal text in the first byte after 001A.
            # Thus, this will automatically skip any weird characters... our XML is officially valid now!
            # but I should probably still add all the idtuple[1] values I can find for full support
            # and to prevent loss of info when reimporting
            inc = inc + idtuple[0]
            result = result + ']'
        else:
            # Only add chars that aren't binary things
            if bb == (38, 106):
                result = result + '[note]'
            else:
                result = result + str(chr(bb[1]))
            inc = inc + 2
        bb = struct.unpack('>BB', offset(dat1o + 8 + curmsgoff + inc, 2))
    return result

try:
    messagefilepath = sys.argv[1]
except:
    error('Please input a file.')
indexlasttick = messagefilepath.rfind('\\')
folder = messagefilepath[0:indexlasttick + 1]
filename = messagefilepath[indexlasttick + 1:]
filename = filename[0:filename.rfind('.')]

with open(messagefilepath, mode='rb') as f:
    # Get the 'file magic' to display the file type
    magic = offset(0,8)
    if debug:
        print(str(magic))
    if str(magic) != "b'MESGbmg1'":
        error('Please input a BMG type file.')
    totalbytelen = struct.unpack('>I', offset(8, 4))[0]
    if debug:
        print('Length of file in bytes is ' + str(totalbytelen))
        # Total length in bytes is the offset of the FLW1 header
        print('so I guess it ignores everything past ' + str(offset(totalbytelen, 4)) + '?')
    if debug:
        sections = struct.unpack('>I', offset('0C', 4))[0]
        print('OK there are ' + str(sections) + ' sections (should be 4 for SMG!)')
    slen = struct.unpack('>H', offset('2A',2))[0]
    if debug:
        print('The length of each ID is ' + str(slen))
        print('The first message inf is ' + str(getfullmsginf(0)))
    # Offset of DAT1 section is length of INF1 plus 32 bytes
    dat1o = 32 + struct.unpack('>I', offset(36, 4))[0]
    if debug:
        print('Offset of DAT1 section is ' + str(dat1o))
        print('\n')

    msgnum = struct.unpack('>H', offset('28', 2))[0]
    print('There are ' + str(msgnum) + ' messages in the BMG file.') 

    # This next section made the xml and now makes a csv instead
    
    try: # Try to open {filename}.tbl
        msgidtbl = open(folder + filename + '.tbl', 'rb')
    except:
        try: # Try to open {filename}id.tbl
            msgidtbl = open(folder + filename + 'id.tbl', 'rb')
        except: 
            try: # Finally, try to open messageid.tbl
                msgidtbl = open(folder + 'messageid.tbl','rb')
            except: 
                error('Did not find messageid.tbl. Please make sure it is in the same directory as your BMG file.')
    with msgidtbl: # I should put an error for if it can't find this file!
        msgtblnum = struct.unpack('>H', idtbloffset(2, 2))[0]
        print('There are ' + str(msgtblnum) + ' messages in the TBL file.')

        allblanknames = ''
        print('Creating CSV from ' + filename + '.bmg...')
        csvlines = []
        i = 0
        while i < msgnum:
            line = str(i) + ','
            temptext = getmsg(i).replace('\n', '\\n')
            i = i + 1 # I don't like this, it should be at the end...
            
            if i < (msgtblnum + 1):
                msgname = getmsgname(i)
            else:
                msgname = "[inf1tocsv.py: MISSING MESSAGE NAME]"
                print('WARNING: A message name is missing!')
            if len(msgname) > 0:
                line += '"' + msgname + '",'
            else:
                line += ','
            
            fullmsginf = getfullmsginf(i)
            for value in fullmsginf:
                line += str(value)
                line += ','
              
            if len(temptext) > 0:
                line += '"' + temptext + '"'
            csvlines.append(line)
        
        print("Done.")

        print("Writing CSV...")
        
        with open(folder + filename + '.csv','w',encoding='utf-8') as msgfile:
            msgfile.write('\n'.join(csvlines))
            print("Done.")
