import logging
from RendererMts3 import RendererMts3
from http.server import BaseHTTPRequestHandler, HTTPServer

class RenderServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        global args
        global renderer

        length = int(self.headers['Content-Length'])
        latitude, longitude, datetime, rays = float(self.headers['La']), float(self.headers['Lo']), self.headers['Ti'], self.headers['Ra']
        rawData = self.rfile.read(length)

        renderer.load_binary(rawData, latitude, longitude, datetime)
        measurements = renderer.render(args.rays if rays == None or rays <= 0 else rays)

        self.send_response(200)
        self.send_header("Content-type", "application/octet-stream")
        self.end_headers()
        self.wfile.write(bytes(measurements))

    def log_message(self, format, *args):
        return

if __name__ == "__main__":

    """
    Options:
    -h,--help | Print this help message and exit
    --port (unsighed int, default=9000) | Port to start the server
    --rays (unsigned int, default=128) | Number of rays to cast from each triangle in the mesh
    --verbose | Be verbose.
    --show | Show the rendering.
    """

    import argparse

    parser = argparse.ArgumentParser(description='Irradaince measurment tool based on Mitsuba 3.')
    parser.add_argument('--port', type=int, default=9000, help='Port to start the server.')
    parser.add_argument('--rays', type=int, default=128, help='Number of rays per element.')
    parser.add_argument('--verbose', type=bool, default=False, help='Verbose output to the console.')
    parser.add_argument('--show', type=bool, default=False, help='Show the rendering.')

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
        server.serve_forever()
