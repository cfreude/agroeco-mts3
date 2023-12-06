from tabnanny import verbose
import requests
import time
import numpy as np
import binary_loader
import sys, os

PLOT_VALUES = True
PLOT_ENV_DIFF_IMG = True
TAMASHII_PATH = None #'F:/projects/agroeco-tamashii' #
TEST_FILE = "./data/01174.prim"   

#args = sys.argv[1:]
#print('Args: ', args)
#port = f"{int(args[0])}"

TAMASHII_PORT = 9000
MTS_PORT = 9002

import subprocess
server = subprocess.Popen(["python", "render-server.py", "--port", f'{MTS_PORT}', '--verbose', f"{0}"])
time.sleep(1)

url = "http://localhost:%d"
print('Using:', url % MTS_PORT, 'for Mitsuba.')

# test GET
print("Testing GET ...")
try:
    response = requests.get(url % MTS_PORT)
    print(response)
    print("")
    
    if TAMASHII_PATH is not None:
        response = requests.get(url % TAMASHII_PORT)
        print(response)
        print("")
except Exception as e:
    print(e)
    print ("FAILED!")

# test fixed POST
print("Testing POST ...")
import os, struct
try:
    headers = {
        "La": "0.0", # latitude
        "Lo": "0.0", # longitude
        "Ti": f"2022-06-01T6:00:00+00:00", # sky model begin time
        "TiE": f"2022-06-01T7:00:00+00:00", # sky model end time
        "Ra": "1024", # number of rays for light simulation
        'Content-Type': 'application/octet-stream'
        }
    
    for path in [TEST_FILE]:
        
        file = os.path.split(path)[-1]
                
        data = binary_loader.load_path(path, _return_binary=True)
        print('Data len:', len(data))
        
        # Mitsuba
        start = time.time()
        response = requests.post(url = url % 9002, headers = headers, data = bytes(data))
        mts_label = f"Mitsuba - {time.time()-start:.2f} sec."
        print(mts_label)
        
        print(file, 'Mitsuba - Sensor count:', len(response._content)/4)
        mts_vals = []
        for i in range(0, len(response._content), 4):
            float_bytes = response._content[i:i+4]
            [val] = struct.unpack('f', float_bytes)
            mts_vals.append(val)
        
        if TAMASHII_PATH is not None:
            # Tamashii
            start = time.time()
            response = requests.post(url = url % 9000, headers = headers, data = bytes(data))
            tamashii_label = f"Tamashii - {time.time()-start:.2f} sec."
            print(tamashii_label)
            
            print(file, 'Tamashii - Sensor count:', len(response._content)/4)
            tamashii_vals = []
            for i in range(0, len(response._content), 4):
                float_bytes = response._content[i:i+4]
                [val] = struct.unpack('f', float_bytes)
                tamashii_vals.append(val)
                
            if PLOT_ENV_DIFF_IMG:                    
                import matplotlib.pyplot as plt
                tamashii_env = os.path.join(TAMASHII_PATH, 'env.ppm')
                mitsuba_env = './env.ppm'
                
                from PIL import Image, ImageChops
                tms_im = Image.open(tamashii_env)            
                mts_im = Image.open(mitsuba_env)
                diff = np.abs(np.array(tms_im) - np.array(mts_im))
                plt.figure("tms"); plt.imshow(np.array(tms_im), cmap='gray')
                plt.figure("mts"); plt.imshow(np.array(mts_im), cmap='gray')
                plt.figure(); plt.imshow(diff)
                plt.show()
            
            if PLOT_VALUES:
                import matplotlib.pyplot as plt
                x = range(int(len(response._content)/4))
                fig, axs = plt.subplots(1,2)
                axs[0].set_title(mts_label)
                axs[0].scatter(x, mts_vals, s=3, label="mts3")
                axs[1].set_title(tamashii_label)
                axs[1].scatter(x, tamashii_vals, s=3, label="tamashii")
                plt.show()
            
except Exception as e:
    print(e)
    print ("FAILED!")

print("Done.")

server.terminate()