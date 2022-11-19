import logging
from RendererMts3 import RendererMts3
from http.server import BaseHTTPRequestHandler, HTTPServer
import numpy as np

class RenderServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        global args
        global renderer

        length = int(self.headers['Content-Length'])
        latitude, longitude, datetime, rays = float(self.headers['La']), float(self.headers['Lo']), self.headers['Ti'], self.headers['Ra']
        camera = self.headers["Cam"]
        rawData = self.rfile.read(length)

        if rays == None or int(rays) <= 0:
            rays = 128 if args.rays == None else int(args.rays)
        else:
            rays = int(rays)

        if args.dummy:
            print("DUMMY MODE")
            count = int(self.headers['C'])
            #measurements = np.ones(count, dtype=np.float32)
            measurements = renderer.render_dummy(count)
        else:
            if camera is None:
                renderer.load_binary(rawData, latitude, longitude, datetime, rays)
                measurements = renderer.render(rays)
            else:
                #print(camera)
                allCameraParams = np.fromstring(camera, dtype=np.float32, sep=' ')
                cam = {}
                cam['origin'] = np.array(allCameraParams[:3])
                cam['target'] = cam['origin'] - np.array(allCameraParams[3:6])
                cam['fov'] = allCameraParams[6]
                cam['width'] = np.int32(allCameraParams[7])
                cam['height'] = np.int32(allCameraParams[8])

                renderer.load_binary(rawData, latitude, longitude, datetime, rays, cam)
                measurements = renderer.render_for_cam(rays)
                #measurements = np.zeros(width * height * 3, dtype=np.float32)
                #print(measurements)

        self.send_response(200)
        self.send_header("Content-type", "application/octet-stream")
        self.end_headers()
        self.wfile.write(measurements.tobytes())

    def log_message(self, format, *args):
        return

if __name__ == "__main__":

    """
    Options:
    -h,--help | Print this help message and exit
    --port (unsighed int, default=9000) | Port to start the server
    --rays (unsigned int, default=128) | Number of rays to cast from each triangle in the mesh
    --verbose | Be verbose.
    --dummy | Dummy mode that returns only ones. The count needs to be specified in a header `C`.
    """

    import argparse

    parser = argparse.ArgumentParser(description='Irradaince measurment tool based on Mitsuba 3.')
    parser.add_argument('--port', type=int, default=9000, help='Port to start the server.')
    parser.add_argument('--rays', type=int, default=128, help='Number of rays per element.')
    parser.add_argument('--verbose', type=bool, default=False, help='Verbose output to the console.')
    parser.add_argument('--dummy', type=bool, default=False, help='Dummy mode that returns only ones.')

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
        #logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.ERROR)

    logging.debug('Args: %s', args)
    renderer = RendererMts3(args.verbose)

    print("Starting rendering server ...")
    with HTTPServer(('', args.port), RenderServer) as server:
        print(f"Serving a renderer at port {args.port}")
        print("Verbose mode enabled." if renderer.verbose else "")

        server.serve_forever()
