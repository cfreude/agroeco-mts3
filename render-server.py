import logging
from RendererMts3 import RendererMts3
from http.server import BaseHTTPRequestHandler, HTTPServer
import numpy as np
import os.path
import sys
import struct

DEBUG_WRITE_IMG = False

class RenderServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        global args
        global renderer

        length = int(self.headers['Content-Length'])
        latitude, longitude, starttime, endtime, rays, reqEnv = float(self.headers['La']), float(self.headers['Lo']), self.headers['Ti'], self.headers['TiE'], self.headers['Ra'], self.headers['Env']
        camera = self.headers["Cam"]
        
        rawData = self.rfile.read(length)

        if rays == None or int(rays) <= 0:
            rays = 128 if args.rays == None else int(args.rays)
        else:
            rays = int(rays)

        defaultEPW = os.path.join("epw", "AUT_Vienna.Schwechat.110360_IWEC", "AUT_Vienna.Schwechat.110360_IWEC.epw")

        if args.dummy:
            print("DUMMY MODE")
            count = int(self.headers['C'])
            measurements = renderer.render_dummy(count)
        else:
            if camera is None:
                envmap, hoy_count = renderer.load_binary(rawData, latitude, longitude, starttime, rays, defaultEPW, endtime)
                measurements = renderer.render(rays) # irradaince W/m2
                # convert to Jouls/m2
                measurements *= hoy_count * 3600.0 # multiply by timespan in hours * seconds per hour
            else:
                allCameraParams = np.fromstring(camera, dtype=np.float32, sep=' ')
                cam = {}
                cam['origin'] = np.array(allCameraParams[:3])
                cam['target'] = cam['origin'] - np.array(allCameraParams[3:6])
                cam['fov'] = allCameraParams[6]
                cam['width'] = np.int32(allCameraParams[7])
                cam['height'] = np.int32(allCameraParams[8])

                envmap = renderer.load_binary(rawData, latitude, longitude, starttime, rays, defaultEPW, endtime, cam)
                measurements = renderer.render_for_cam(rays)

            if DEBUG_WRITE_IMG:
                cam = {}
                cam['origin'] = np.array([5,5,12])
                cam['target'] = np.array([5,0,0])
                cam['fov'] = 70.0
                cam['width'] = 512
                cam['height'] = 512   
                envmap = renderer.load_binary(rawData, latitude, longitude, starttime, rays, defaultEPW, endtime, cam)
                _ = renderer.render_for_cam(rays)

        self.send_response(200)
        self.send_header("Content-type", "application/octet-stream")
        self.end_headers()
        if reqEnv is not None:
            order = '<H' if sys.byteorder == 'little' else '>H'
            envmap = envmap[:,:,0]
            self.wfile.write(struct.pack(order, envmap.size))
            self.wfile.write(struct.pack(order, envmap.shape[1]))
            self.wfile.write(envmap.tobytes())
        self.wfile.write(measurements.tobytes())

    def log_message(self, format, *args):
        return

if __name__ == "__main__":

    """
    Options:
    -h,--help | Print this help message and exit
    --port (unsighed int, default=9001) | Port to start the server
    --rays (unsigned int, default=128) | Number of rays to cast from each triangle in the mesh
    --verbose | Be verbose.
    --dummy | Dummy mode that returns only ones. The count needs to be specified in a header `C`.
    """

    import argparse

    parser = argparse.ArgumentParser(description='Irradaince measurment tool based on Mitsuba 3.')
    parser.add_argument('--port', type=int, default=9002, help='Port to start the server.')
    parser.add_argument('--rays', type=int, default=1024, help='Number of rays per element.')
    parser.add_argument('--verbose', type=bool, default=False, help='Verbose output to the console.')
    parser.add_argument('--dummy', type=bool, default=False, help='Dummy mode that returns only ones.')

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
        #logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.ERROR)

    logging.debug('Args: %s', args)
    renderer = RendererMts3(args.verbose, _use_batch_render=True)

    print("Starting rendering server ...")
    with HTTPServer(('', args.port), RenderServer) as server:
        print(f"Serving a renderer at port {args.port}")
        print("Verbose mode enabled." if renderer.verbose else "")

        server.serve_forever()