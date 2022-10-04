import subprocess
import requests
import time
import random
import numpy as np

port = f"{9000}"
server = subprocess.Popen(["python3", "render-server.py", "--port", port])
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
    data = bytearray()
    data += np.array([1, 1], dtype=np.uint32).tobytes() # 1 entity, 1 surface
    data += np.array([2], dtype=np.uint8).tobytes() # 2 triangles

    data += np.array([0, 1, 2, 0, 2, 3], dtype=np.uint32).tobytes()

    data += np.array([4], dtype=np.uint32).tobytes() # 4 points

    data += np.array([0.0, 0.0, 1.0], dtype=np.float32).tobytes()
    data += np.array([1.0, 0.0, 1.0], dtype=np.float32).tobytes()
    data += np.array([1.0, 0.0, 0.0], dtype=np.float32).tobytes()
    data += np.array([0.0, 0.0, 0.0], dtype=np.float32).tobytes()
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