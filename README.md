# honoruty
A message editor for SMG1.

`msg2xml.py` will convert a valid Super Mario Galaxy 1 message BMG file into a more easily editable XML file. Simply drop `message.bmg` onto the script, and it'll create a `message.xml` file.

`xml2msg.py` does the opposite, and creates a Super Mario Galaxy 1 message BMG file from an XML file.  Simply drop `message.xml` onto the python script.


**Warning** - As long as this software is in a 0.x.x version, I can change the formatting used by the XML at any time, _invalidating any previously made XMLs_. However, you can try converting your XML to a BMG with the old version, and then reconvert that BMG to an XML with the new version. This may not always work, however, especially in the case of the missing text bug.

---


At the moment, _please do not add entries to the XML file!_ This program does not edit `messageid.tbl` and thus can _not_ properly handle additional messages.  (I may add that in later.)

If you need to know a name or identifier for any particular thing (color, emoji, whatever), check the files in the [CSV folder](https://github.com/epichickensoup/honoruty/tree/master/csv). You can also edit these to your liking, just make sure you know what you're doing as it will be harder to help you with problems.
