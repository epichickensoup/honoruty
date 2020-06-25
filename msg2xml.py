import struct
import csv
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
# from xml.dom import minidom

def getdict(f):
    """Return a dictionary created from a csv file."""
    source = csv.reader(open(f))
    redict = dict(source)
    return redict

csv_folder = Path('csv')
# Import all the dictionaries from attatched CSVs
demoji = getdict(csv_folder / 'emoji_hex.csv')
dcolor = getdict(csv_folder / 'color_hex.csv')
dpause = getdict(csv_folder / 'pause_hex.csv')
doddpause = getdict(csv_folder / 'oddpause_hex.csv')
dnumber = getdict(csv_folder / 'number_hex.csv')
dnames = getdict(csv_folder / 'names_hex.csv')
dsizes = getdict(csv_folder / 'sizes_hex.csv')
dplumber = getdict(csv_folder / 'plumber_hex.csv')

def getmsgname(id):
    pid = id
    retname = ''
    if pid < msgnum:
        msgnameoffset = struct.unpack('>I', idtbloffset(40 + pid * 8 + 4, 4))[0]
        # print('offset ' + str(msgnameoffset))
        b = struct.unpack('>B', idtbloffset(msgnameoffset + 40 + msgnum * 8, 1))[0]
        i = 0
        while b != 0 and b != 40:
            retname = retname + chr(b)
            i = i + 1
            b = struct.unpack('>B', idtbloffset(msgnameoffset + 40 + msgnum * 8 + i, 1))[0]
    return retname

def idtbloffset(o, l):
    """Get bytes of messageid.tbl at offset o for length l."""
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
    return struct.unpack('>BBBBBBBB', offset(48 + (id * slen) + 4, slen - 4)) # + ("offset", hex(48 + (id * slen) + 4))

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
    bb = struct.unpack('>BB', offset(dat1o + 8 + curmsgoff, 2))
    # Check each 2 bytes and add the char to the result, but stop on a null double byte
    while bb != (0,0):
        # print(bb)
        if bb == (0, 26):
            # print('Found an escape char')
            idtuple = struct.unpack('>BB', offset(dat1o + 10 + curmsgoff + inc, 2))
            result = result + '<' + dnames.get(str(idtuple[1]), dnames.get('more')) + ' '
            if idtuple[1] == 1:
                # It's a pause
                if idtuple[0] == 8:
                    pauselen = struct.unpack('>I', offset(dat1o + 12 + curmsgoff + inc, 4))[0]
                    gotlen = dpause.get(str(pauselen), dpause.get('more'))
                else:
                    pauselen = struct.unpack('>H', offset(dat1o + 12 + curmsgoff + inc, 2))[0]
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
                emojiid = struct.unpack('>H', offset(dat1o + 12 + curmsgoff + inc, 2))[0]
                # print(str(emojiid))
                # print('<emoji name="' + demoji.get(str(emojiid), demoji.get("more")) + '"/>')
                result = result + 'name="' + demoji.get(str(emojiid), demoji.get('more')) + '"'
            elif idtuple[1] == 4:
                # There are 2 sizes they use... but I'll bet there are 3!  Anyway... sizes.
                sizeid = struct.unpack('>H', offset(dat1o + 12 + curmsgoff + inc, 2))[0]
                result = result + 'name="' + dsizes.get(str(sizeid), demoji.get('more')) + '"'
            elif idtuple[1] == 5:
                # The plumber names were already handled... or so I thought
                plumberid = round(struct.unpack('>I', offset(dat1o + 12 + curmsgoff + inc, 4))[0] / 256)
                result = result + 'style="' + dplumber.get(str(plumberid), dplumber.get("more")) + '"'
            elif idtuple[1] == 6 or idtuple[1] == 7:
                # This is a number or systemtext. They are entered the same way! Also, no information is lost, so hooray!
                systextuple = struct.unpack('>BBBBBBBBBB', offset(dat1o + 12 + curmsgoff + inc, 10))
                needed = (systextuple[1], systextuple[9])
                result = result + 'id="' + str(needed) + '"'
            elif idtuple[1] == 9:
                #Race time.
                #Racetime ID seems to always be (0, 5)
                # unpack = struct.unpack('>BB', offset(dat1o + 8 + 4 + curmsgoff + inc, 2))
                # result = result + 'id="' + str(unpack) + '"'
                pass
            elif idtuple[1] == 255:
                # It's a color identifier
                # Divide colorid by 256 because it's actually in the 3rd byte, not the 4th (dunno why I did this tbh)
                colorid = round(struct.unpack('>I', offset(dat1o + 12 + curmsgoff + inc, 4))[0] / 256)
                result = result + 'name="' + dcolor.get(str(colorid), dcolor.get("more")) + '"'
                # dcolor.get(, dcolor.get("more"))
            else:
                # It's gonna show me any binary things I haven't gotten yet
                print("Oops, apparently I missed an element with ID " + str(idtuple))
            # So this is super cool... they put the offset to the next normal text in the first byte after 001A.
            # Thus, this will automatically skip any weird characters... our XML is officially valid now!
            # but I should probably still add all the idtuple[1] values I can find for full support
            # and to prevent loss of info when reimporting
            inc = inc + idtuple[0]
            result = result + '/>'
        else:
            # Only add chars that aren't binary things
            if bb == (38, 106):
                result = result + '<note />'
            else:
                result = result + str(chr(bb[1]))
            inc = inc + 2
        bb = struct.unpack('>BB', offset(dat1o + 8 + curmsgoff + inc, 2))
    return result

try:
    messagefilepath = sys.argv[1]
    folder = messagefilepath[0:messagefilepath.rfind('\\') + 1]
except:
    raise Exception("Please input a file.")

with open(messagefilepath, mode='rb') as f:
    # Get the 'file magic' to display the file type
    magic = offset(0,8)
    print(str(magic))
    if str(magic) != "b'MESGbmg1'":
        raise Exception("Please input a valid BMG file.")
    totalbytelen = struct.unpack('>I', offset(8, 4))[0]
    print('Length of file in bytes is ' + str(totalbytelen))
    # Total length in bytes is the offset of the FLW1 header
    print('so I guess it ignores everything past ' + str(offset(totalbytelen, 4)) + '?')
    #sections = struct.unpack('>I', offset('0C', 4))[0]
    #print('OK there are ' + str(sections) + ' sections (should be 4 for SMG!)')
    slen = struct.unpack('>H', offset('2A',2))[0]
    print('The length of each ID is ' + str(slen))
    print('The first message inf is ' + str(getmsginf(0)))
    # Offset of DAT1 section is length of INF1 plus 32 bytes
    dat1o = 32 + struct.unpack('>I', offset(36, 4))[0]
    print('Offset of DAT1 section is ' + str(dat1o))
    print('\n')

    msgnum = struct.unpack('>H', offset('28', 2))[0]
    print('There are ' + str(msgnum) + ' messages in the file')
    
    # print("\nTesting escape sequences:")
    print(getmsg(2))

    # This next section makes the xml
    root = ET.Element('MESGbmg1')
    with open(folder + 'messageid.tbl','rb') as msgidtbl:

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
        with open('allusedinfsections.txt','w') as a:
            # allsoundids.sort()
            a.write(infsearch)
            soundsearch = []
            infsearch = ''

        allblanknames = ''
        print("Creating XML from message.bmg...")
        i = 0
        while i < msgnum:
            i = i + 1
            temptext = getmsg(i)
            if temptext != '':
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
        
        print("Done.")
        tree = ET.ElementTree(root)
        tree.write(folder + 'messages_short_beta.xml')

        print("Fixing XML because I was lazy...")
        # Unfilter the created XML.  Hopefully y'all didn't use any greater/less-than symbols!
        readstr = ""
        with open(folder + 'messages_short_beta.xml','r') as msgfile:
            readstr = msgfile.read()
            readstr = readstr.replace('&gt;', '>').replace('&lt;', '<').replace('<message ', '\n   <message ').replace('</messageBMG>', '\n</messageBMG>')
        with open(folder + 'messages_short_beta.xml','w') as msgfile:
            msgfile.write(readstr)
            print("Done.")

        # nvm: minidom pretty print? more like minidom ugly print xd
        # # OK so xmlstr doesn't like invalid chars, so we're gonna have to filter those out first
        # xmlstr = minidom.parseString(readstr).toprettyxml(indent="   ")
        # with open('messages_beta.xml', 'w') as outputfile:
        #     outputfile.write(xmlstr)