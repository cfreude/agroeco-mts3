import subprocess
import requests
import time
import random
import numpy as np

def exampleV1(data):
    data += np.array([1, 1], dtype=np.uint32).tobytes() # 1 entity, 1 surface
    data += np.array([2], dtype=np.uint8).tobytes() # 2 triangles

    data += np.array([0, 1, 2, 0, 2, 3], dtype=np.uint32).tobytes()

    data += np.array([4], dtype=np.uint32).tobytes() # 4 points

    data += np.array([0.0, 0.0, 1.0], dtype=np.float32).tobytes()
    data += np.array([1.0, 0.0, 1.0], dtype=np.float32).tobytes()
    data += np.array([1.0, 0.0, 0.0], dtype=np.float32).tobytes()
    data += np.array([0.0, 0.0, 0.0], dtype=np.float32).tobytes()

def exampleV3(data):
    data += np.array([3], dtype=np.uint8).tobytes() # v3
    data += np.array([2], dtype=np.uint32).tobytes() # 2 entities

    #first entity is an umbrella
    data += np.array([2], dtype=np.uint32).tobytes() # 2 surfaces

    data += np.array([2], dtype=np.uint8).tobytes() # cylinder (pole)
    data += np.array([2.2, 0.04], dtype=np.float32).tobytes() #height and half thickness
    data += np.array([1, 0, 0, 1,    0, 1, 0, 0,    0, 0, 1, 1], dtype=np.float32).tobytes() #position
    data += np.array([False], dtype=np.bool_).tobytes() #not a sensor

    data += np.array([1], dtype=np.uint8).tobytes() # disk
    data += np.array([0.75, 0, 0, 1,    0, 0.75, 0, 2.2,    0, 0, 0.75, 1], dtype=np.float32).tobytes() #position
    data += np.array([False], dtype=np.bool_).tobytes() #not a sensor

    #second entity is a simple plant with no leaves
    data += np.array([1], dtype=np.uint32).tobytes() # 1 surfaces

    data += np.array([2], dtype=np.uint8).tobytes() # cylinder (pole)
    data += np.array([0.2, 0.005], dtype=np.float32).tobytes() #height and half thickness
    data += np.array([1, 0, 0, 0.1,    0, 1, 0, -0.2,    0, 0, 1, 0.1], dtype=np.float32).tobytes() #position below the surface
    data += np.array([True], dtype=np.bool_).tobytes() #sensor

port = f"{9001}"
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
    headers = {"La": "0.0", "Lo": "0.0", "Ti": "2022-09-21T14:53:57+02:00", "TiE": "2022-09-22T14:53:57+02:00", "Ra": "128", 'Content-Type': 'application/octet-stream'}
    #optional header "Env": "true" returns the environment map
    #optional header "Cam": "camera matrix" returns the rendering as seen from position and rotation specified in the value

    data = bytearray()
    exampleV3(data)
    response = requests.post(url = url, headers = headers, data = bytes(data))
    print(response.status_code)
    print(response.headers)
    print(response._content)
    print("SUCCESS!" if response._content == b'\x00\x00\x00\x00' else "ERROR!")
    print("")
except Exception as e:
    print(e)
    print ("FAILED!")

print("Terminating server.")
server.terminate()
print("Done.")