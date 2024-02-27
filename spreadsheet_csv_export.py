import nuke
nuke.tprint("adding %s"%__name__)

# This Example shows how to register a custom menu to the Spreadsheet View and exports the contents of the Spreadsheet as a CSV file.
# Usage: Right-click on a row of the Spreadsheet, select Export > Spreadsheet to .CSV
# Note: The 'Action' column is not currently hooked up and it does not currently take 'Drop Frame' into account.

import hiero.core
from PySide2.QtWidgets import QAction
from PySide2.QtWidgets import QMenu
from PySide2.QtGui import QDesktopServices
from PySide2.QtWidgets import QFileDialog
from PySide2.QtCore import QUrl
import os, csv
import re

#### Shot Methods ####
def getStatus(trackItem):
  status = 'OK'
  if not trackItem.isMediaPresent():
    status = 'OFF'
  return status

def timecodePrefCheck():
  # We need to check the user Preference for 'Timecode > EDL-Style Spreadsheet Timecodes'
  return int(hiero.core.ApplicationSettings().boolValue('useVideoEDLTimecodes'))

def getReelName(trackItem):
  reelName = ""
  M = trackItem.metadata()
  if M.hasKey('foundry.edl.sourceReel'):
    reelName = M.value('foundry.edl.sourceReel')
  return reelName

def getVersion(trackItem):
  fullName = trackItem.currentVersion().name()
  versionCheck = re.search("_v[0-9]", fullName)
  if versionCheck:
    versionIndex = fullName.split("_v")[-1]
    return "v"+versionIndex
  else:
    return "-"


def getSrcIn(trackItem, display="TC"):
  fps = trackItem.parent().parent().framerate()
  clip = trackItem.source()
  
  if display == "Frame":
    display_type = hiero.core.Timecode.kDisplayFrames
    clipstart = clip.sourceIn()
  else:
    display_type = hiero.core.Timecode.kDisplayTimecode
    clipstart = clip.timecodeStart()

  #convert float to int for NukeStudio/Hiero 15
  srcIn = hiero.core.Timecode.timeToString(int(clipstart+trackItem.sourceIn()), fps, display_type)
  return srcIn

def getSrcOut(trackItem, display="TC"):

  fps = trackItem.parent().parent().framerate()
  clip = trackItem.source()

  if display == "Frame": #option for converting to frames
    display_type = hiero.core.Timecode.kDisplayFrames
    clipstart = clip.sourceIn()
  else:
    display_type = hiero.core.Timecode.kDisplayTimecode
    clipstart = clip.timecodeStart()

  #convert float to int for NukeStudio/Hiero 15
  srcOut = hiero.core.Timecode.timeToString(int(clipstart+trackItem.sourceOut()+timecodePrefCheck()), fps, display_type)
  return srcOut

def getDstIn(trackItem, display="TC"):
  seq = trackItem.parent().parent()
  tStart = seq.timecodeStart()
  fps = seq.framerate()
  if display == "Frame": #option for converting to frames
    display_type = hiero.core.Timecode.kDisplayFrames
    dstIn = hiero.core.Timecode.timeToString(trackItem.timelineIn(), fps , display_type)
  else:
    display_type = hiero.core.Timecode.kDisplayTimecode
    dstIn = hiero.core.Timecode.timeToString(tStart+trackItem.timelineIn(), fps , display_type)
   
  return dstIn

def getDstOut(trackItem, display="TC"):
  seq = trackItem.parent().parent()
  tStart = seq.timecodeStart()
  fps = seq.framerate()
  if display == "Frame":
    display_type = hiero.core.Timecode.kDisplayFrames
    dstOut = hiero.core.Timecode.timeToString(trackItem.timelineOut()+timecodePrefCheck(), fps, display_type)
  else:
    display_type = hiero.core.Timecode.kDisplayTimecode
    dstOut = hiero.core.Timecode.timeToString(tStart+trackItem.timelineOut()+timecodePrefCheck(), fps, display_type)
  return dstOut

# Get a Nuke Read node style file path
def getNukeStyleFilePath(trackItem):
  fi = trackItem.source().mediaSource().fileinfos()[0]
  filename = fi.filename()
  first = fi.startFrame()
  last = fi.endFrame()
  if trackItem.source().mediaSource().singleFile():
    return filename
  else:
    return "%s %i-%i" % (filename,first,last)

#### The guts!.. Writes a CSV file from a Sequence Object ####
def writeCSVFromSequence(seq):

  csvSavePath = os.path.join(os.getenv('HOME'),'Desktop',seq.name()+'.csv')
  savePath,filter = QFileDialog.getSaveFileName(None,caption="Save CSV As...",dir = csvSavePath, filter = "*.csv")
  print('Saving To: ' + str(savePath))

  if len(savePath)==0:
    return

  # The Header row for the CSV.. note that 'Action' is not currently supported.
  csvHeader = ['Event',
               'Status',
               'Shot Name',
               'Version',
               'Reel',
               'Track',
               'Speed',
               'Src In TC',
               'Src Out TC',
               'Src In Frames',
               'Src Out Frames',
               'Src Duration',
               'Dst In TC',
               'Dst Out TC',
               'Dst In Frames',
               'Dst Out Frames',
               'Dst Duration',
               'Clip',
               'Clip Media']

  # Get a CSV writer object
  csvWriter = csv.writer(open(savePath, 'w'), delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL, lineterminator = '\n')

  # Write the Header row to the CSV file
  csvWriter.writerow(csvHeader)

  # Get all Tracks in the Sequence...
  vTracks = seq.videoTracks()
  aTracks = seq.audioTracks()
  tracks = vTracks+aTracks
  rowindex = 1
  if len(tracks)>0:
    for v in tracks:
      for item in v:
        if isinstance(item, hiero.core.TrackItem):
          M = item.metadata()
          if M.hasKey('foundry.edl.editNumber'):
            event = M.value('foundry.edl.editNumber')
          else:
            event = rowindex
          rowindex+=1

          table_data = [str(event),
                        str(getStatus(item)),
                        str(item.name()),
                        str(getVersion(item)),
                        str(getReelName(item)),
                        str(item.parent().name()),
                        "%.1f" % (100.0*float(item.playbackSpeed())),
                        str(getSrcIn(item)),
                        str(getSrcOut(item)),
                        str(getSrcIn(item,display="Frame")),
                        str(getSrcOut(item,display="Frame")),
                        str(item.sourceOut()-item.sourceIn()+1),
                        str(getDstIn(item)),
                        str(getDstOut(item)),
                        str(getDstIn(item,display="Frame")),
                        str(getDstOut(item,display="Frame")),
                        str(item.duration()),
                        str(item.source().name()),
                        str(getNukeStyleFilePath(item))]
          csvWriter.writerow(table_data)

  # Conveniently show the CSV file in the native file browser...
  QDesktopServices.openUrl(QUrl('file:///%s' % (os.path.dirname(savePath))))


#### Adds Export... > Spreadsheet to CSV file in the Spreadsheet Menu ####
class SpreadsheetExportCSVMenu:

  def __init__(self):
    hiero.core.events.registerInterest("kShowContextMenu/kSpreadsheet", self.eventHandler)
    self._exportAllSpreadsheetToCSV = self.createMenuAction("Spreadsheet To CSV", self.exportCSV)
    self._exportCSVMenu = QMenu('Export...')

  def createMenuAction(self, title, method):
    action = QAction(title,None)
    action.triggered.connect( method )
    return action

  def eventHandler(self, event):
    self.selection = event.sender.selection()
    enabled = True
    if (self.selection is None) or (len(self.selection)==0):
      self.selection = ()
      enabled = False

    self._exportAllSpreadsheetToCSV.setEnabled(enabled)
    self._exportCSVMenu.setEnabled(enabled)

    # Insert the custom Menu, divided by a separator
    event.menu.addSeparator()

    event.menu.addMenu(self._exportCSVMenu)

    # Insert the action to the Export CSV menu
    self._exportCSVMenu.addAction(self._exportAllSpreadsheetToCSV)

  # Call the Method above to write the Sequence to a CSV file..
  def exportCSV( self ):
    print('exporting CSV...')

    # Ignore transitions from the selection
    self.selection = [item for item in self.selection if isinstance(item, hiero.core.TrackItem)]
    seq = self.selection[0].parent().parent()
    print('seq is', seq)
    if isinstance(seq, hiero.core.Sequence):
      writeCSVFromSequence(seq)
    else:
      print('Unable to Export Sequence')

#### Add the Menu... ####
csvActions = SpreadsheetExportCSVMenu()
