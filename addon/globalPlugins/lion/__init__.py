import globalPluginHandler
import addonHandler
import scriptHandler
import api
import contentRecog, contentRecog.uwpOcr
import screenBitmap
import logHandler
import gui
import tones
import textInfos
import ui
import time
import queueHandler
import threading
import config
import wx
import locationHelper
from . import lionGui
from scriptHandler import getLastScriptRepeatCount, script

from difflib import SequenceMatcher
import ctypes


addonHandler.initTranslation()
active=False

prevString=""
counter=0
recog = contentRecog.uwpOcr.UwpOcr()


confspec={
	"cropUp": "integer(0,100,default=0)",
	"cropLeft": "integer(0,100,default=0)",
	"cropRight": "integer(0,100,default=0)",
	"cropDown": "integer(0,100,default=0)",
	"target": "integer(0,3,default=1)",
	"threshold": "float(0.0,1.0,default=0.5)",
	"interval": "float(0.0,10.0,default=1.0)"
}
config.conf.spec["lion"]=confspec
class GlobalPlugin(globalPluginHandler.GlobalPlugin):

	
	user32 = ctypes.windll.user32
	resX, resY= user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
	
	
	def __init__(self):
		super(GlobalPlugin, self).__init__()
		self.createMenu()
		
	def createMenu(self):
		self.prefsMenu = gui.mainFrame.sysTrayIcon.menu.GetMenuItems()[0].GetSubMenu()
		self.lionSettingsItem = self.prefsMenu.Append(wx.ID_ANY,
			# Translators: name of the option in the menu.
			_("&LION Settings..."),
			# Translators: tooltip text for the menu item.
			_("modify OCR zone and interval"))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onSettings, self.lionSettingsItem)

	def terminate(self):
		try:
			self.prefsMenu.RemoveItem(self.lionSettingsItem)
		except wx.PyDeadObjectError:
			pass

	def onSettings(self, evt):
		if gui.isInMessageBox:
			return
		gui.mainFrame.prePopup()
		d = lionGui.frmMain(gui.mainFrame)
		d.Show()
		gui.mainFrame.postPopup()

	def script_ReadLiveOcr(self, gesture):
		repeat = getLastScriptRepeatCount()
#		if repeat>=2:
#			ui.message("o sa vine profile")
			return
		global active
		
		if(active==False):
			active=True
			tones.beep(444,333)
			ui.message(_("lion started"))
			nav=api.getNavigatorObject()

			threading.Thread(target=self.ocrLoop).start()
		
		else:
			
			active=False
			tones.beep(222,333)
			ui.message(("lion stopped"))
			
	def cropRectLTWH(self, r):
		cfg=config.conf["lion" ]
		if r is None: return locationHelper.RectLTWH(0,0,0,0)
		return locationHelper.RectLTWH(int((r.left+r.width)*cfg['cropLeft']/100.0), int((r.top+r.height)*cfg['cropUp']/100.0), int(r.width-(r.width*cfg['cropRight']/100.0)), int(r.height-(r.height*cfg['cropDown']/100.0)))
	
	def ocrLoop(self):
		cfg=config.conf["lion" ]
		
		self.targets={
			0:api.getNavigatorObject().location,
			#1:locationHelper.RectLTRB(int(cfg["cropLeft"]*self.resX/100.0), int(cfg["cropUp"]*self.resY/100.0), int(self.resX-cfg["cropRight"]*self.resX/100.0), int(self.resY-cfg["cropDown"]*self.resY/100.0)).toLTWH(),
			1:self.cropRectLTWH(locationHelper.RectLTWH(0,0, self.resX, self.resY)),
			2:self.cropRectLTWH(api.getForegroundObject().location),
			3:api.getFocusObject().location
		}
		#print( self.targets)
		global active


		while(active==True ):
			self.OcrScreen()
			time.sleep(config.conf["lion"]["interval"])

	def OcrScreen(self):
		
		global recog
		
		

		left,top, width,height=self.targets[config.conf["lion"]["target"]]
		
		recog = contentRecog.uwpOcr.UwpOcr()

		imgInfo = contentRecog.RecogImageInfo.createFromRecognizer(left, top, width, height, recog)
		sb = screenBitmap.ScreenBitmap(imgInfo.recogWidth, imgInfo.recogHeight) 
		pixels = sb.captureImage(left, top, width, height) 
		recog.recognize(pixels, imgInfo, recog_onResult)


		
	__gestures={
	"kb:nvda+alt+l":"ReadLiveOcr"
	}
	
def recog_onResult(result):
	global prevString
	global recog
	global counter
	counter+=1
	o=type('NVDAObjects.NVDAObject', (), {})()
	info=result.makeTextInfo(o, textInfos.POSITION_ALL)
	threshold=SequenceMatcher(None, prevString, info.text).ratio()
	if threshold<config.conf['lion']['threshold'] and info.text!="" and info.text!="Play":
		ui.message(info.text)
		prevString=info.text

	if counter>9:
		del recog
		counter=0