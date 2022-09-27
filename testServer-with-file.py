import subprocess
from tabnanny import verbose
import requests
import time
import random
import numpy as np
import binary_loader

port = f"{9000}"
server = subprocess.Popen(["python", "render-server.py", "--port", port, '--verbose', f"{0}"])
time.sleep(1)

url = f"http://localhost:{port}"

#test GET
print("Testing GET ...")
try:
    response = requests.get(url)
    print(response)
    print("")
except Exception as e:
    print(e)
    print ("FAILED!")

#test fixed POST
print("Testing POST ...")

try:
    headers = {"La": "0.0", "Lo": "0.0", "Ti": f"2022-09-21T14:53:57+02:00", 'Content-Type': 'application/octet-stream'}
    data = binary_loader.load_path('./data/t700.mesh', _return_binary=True)
    response = requests.post(url = url, headers = headers, data = bytes(data))
    print(response.status_code)
    print(response.headers)
    print(response._content)
    print("SUCCESS!" if response._content == b'\x00\x00\x00\x00' else "ERROR!")
    print("")
except Exception as e:
    print(e)
    print ("FAILED!")

#test random POST
"""
print("Testing POST ...")
try:
    headers = {"La": f"{random.uniform(-90, 90)}", "Lo": f"{random.uniform(-180, 180)}", "Ti": f"2022-09-21T14:53:57+00:00", 'Content-Type': 'application/octet-stream'}
    response = requests.post(url = url)
    print("")
except:
    print ("FAILED!")
"""

#print("")
print("Done.")
server.terminate()