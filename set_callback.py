# set callback

import http.client
import json
import base64
from IPython.display import Image, display
import time


server_ip = "113.44.176.165"  # Replace with your server IP
server_port = 2531
port = 2531
gewe_token = ""  # Replace with your gewe-token, or leave empty for first-time login
app_id = ""  # Will be updated after successful login
wxid_jim = "" # Will be updated after getting friend list, replace with Jim's wxid if you know it already
app_id="wx_1Evjqp0uqLMBC8HLZFyX0"
wxid_me="wxid_5x95xpifbnh512"
token="484e412380744c7eac7690045a23c875"



conn = http.client.HTTPConnection(f"{server_ip}:{port}") 
payload = json.dumps({
   "token": token,
   "callbackUrl": "http://20.36.6.105:8000/wechat/callback"
})
headers = {
   'X-GEWE-TOKEN': token,
   'Content-Type': 'application/json'
}
conn.request("POST", "/v2/api/tools/setCallback", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))