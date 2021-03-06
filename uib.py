import argparse
import format
import urllib
import json

from util import *
from http.server import *

DEF_CONT_TYPE_MAP = {
	"js": "application/x-javascript",
	"css": "text/css",
	"html": "text/html",
	"jpg": "image/jpeg"
}

eng = None

def INT_hascard(self, query):
	self.sendJSON({ "suc": eng.hasCard() })

def INT_verify(self, query):
	res = eng.verify()

	self.sendJSON(res)

	return

	if "beep" in query:
		if res["suc"]:
			eng.beep("suc")
		else:
			eng.beep("failed")

def INT_init(self, query):
	global eng

	if eng != None:
		self.sendJSON({ "suc": True })
		return

	parser = argparse.ArgumentParser()

	parser.add_argument("--driver", help = "driver", type = str, default = format.DEF_DRIVER)
	parser.add_argument("-s", "--server", help = "specify a server", type = str, default = format.DEF_AUTHSERV)
	parser.add_argument("--no-server", help = "don't use server", action = "store_true")

	parser.add_argument("-p", "--port", help = "specify a port", type = str)

	argv = parser.parse_args()

	port = None

	if argv.port:
		port = argv.port
	else:
		port = format.SDEngine.searchCOM()

	if port == None:
		self.sendJSON({ "suc": False, "msg": "no device found" })
		return

	serv = argv.server

	if argv.no_server:
		print("server check disabled")
		serv = None

	print("found device at " + port)
	eng = format.SDEngine(port, server = serv, driv = argv.driver)

	self.sendJSON({ "suc": True })

# read admin card
def INT_radmin(self, query):
	if not "pw" in query:
		self.sendJSON({ "suc": False, "msg": "wrong argument" })
		return

	pw = query["pw"]
	res = eng.readAdminCard(pw)

	if not res["suc"]:
		self.sendJSON({ "suc": False, "msg": res["msg"] })
		return

	ctp = eng.applyAdminCard(res["type"], res["key"])

	self.sendJSON({ "suc": True, "type": ctp })

def INT_info(self, query):
	self.sendJSON({ "suc": True, "info": eng.getInfo() })

DEF_INT_MAP = {
	"hascard": INT_hascard,
	"init": INT_init,
	"verify": INT_verify,
	"radmin": INT_radmin,
	"info": INT_info
}

class UIHandler(BaseHTTPRequestHandler):
	def parseQuery(self):
		res = urllib.parse.urlparse(self.path)
		
		self.parse = {
			"path": res.path,
			"query": dict(urllib.parse.parse_qsl(res.query))
		}

		return self.parse

	def setHeader(self, head = {}, status = 200, version = b"HTTP/1.1"):
		self.protocal_version = version
		self.send_response(status)

		for key in head:
			self.send_header(key, head[key])
		
		self.end_headers()

	def response(self, cont):
		if type(cont) != bytes:
			cont = cont.encode("latin1")
		self.wfile.write(cont)

	def sendJSON(self, dat):
		self.setHeader({ "Content-Type": "application/json" })
		self.response(json.dumps(dat))

	def routeStatic(self, pref):
		print(self.parse)
		path = self.parse["path"]

		if path.find(pref) == 0:
			with open(path[1:], "rb") as fp:
				suf = path.split(".")[-1]

				if suf in DEF_CONT_TYPE_MAP:
					self.setHeader({ "Content-Type": DEF_CONT_TYPE_MAP[suf] })

				self.response(fp.read())

			return True
		else:
			return False

	def do_GET(self):
		try:
			self.parseQuery()

			if self.routeStatic("/ui/"): return

			if self.parse["path"] == "/":
				# main page
				self.setHeader({
					"Content-Type": "text/html"
				})

				with open("ui/main.html") as fp:
					self.response(fp.read())
			else:
				cmd = self.parse["path"][1:].split("/")
				print(cmd)

				if cmd[0] == "int" and \
				   len(cmd) > 1 and \
				   cmd[1] in DEF_INT_MAP:
					DEF_INT_MAP[cmd[1]](self, self.parse["query"])
				else:
					self.setHeader(status = 404)
					self.response("page missing " + self.parse["path"])
		# except:
		#	self.setHeader(status = 500)
		#	self.response("something wrong inside")
		finally: pass

addr = "127.0.0.1", int(3134)
server = HTTPServer(addr, UIHandler)

server.serve_forever()
