import time, os, logging
import dateutil
import datetime
import numpy as np
import drjit as dr
import mitsuba as mi
from matplotlib import pyplot as plt
from pysolar.solar import *
from binary_loader import loadData
from http.server import BaseHTTPRequestHandler, HTTPServer

#mi.set_variant("cuda_ad_rgb")
#mi.set_variant("llvm_ad_rgb")
mi.set_variant("scalar_rgb")

from mitsuba import ScalarTransform4f as T

def create_base_scene(_size, _offset, _res=512):

    base_scene = {
        'type': 'scene',
        'integrator_base': {
            'type': 'path',
        },
        'camera_base': {
            'type': 'perspective',
            'fov': 70,
            'to_world': mi.ScalarTransform4f.look_at(
                origin=[_offset[0], _offset[1]-_size*2, _offset[2]+_size],
                target=_offset,
                up=[0, 0, 1]),
            'film_base': {
                'type': 'hdrfilm',
                'pixel_format': 'rgba',
                'width': _res,
                'height': _res
            },
            'sampler_id': {
                'type': 'independent',
                'sample_count': 128
            }
        }
    }

    base_scene['ground'] = {
        'type': 'disk',
        'to_world': mi.ScalarTransform4f.translate(_offset).scale([_size, _size, _size]),
        'material': {
            'type': 'diffuse',
            'reflectance': {
                'type': 'rgb',
                'value': [0.5, 0.5, 0.5]
            }
        }
    }

    return base_scene

def create_triangle_mesh(_name, _vertex_positions, _triangle_indices):

    vertex_pos = mi.TensorXf(_vertex_positions)
    face_indices = mi.TensorXu(_triangle_indices)

    props = mi.Properties()
    if 0:
        bsdf = mi.load_dict({
            'type': 'diffuse',
            'reflectance': {
                'type': 'rgb',
                'value': [1, 0, 0]
                }
            })
        emitter = mi.load_dict({
            'type': 'area',
            'radiance': {
                'type': 'rgb',
                'value': [1, 0, 0],
                }
            })
        props["mesh_bsdf"] = bsdf
        #props["mesh_emitter"] = emitter

    mesh = mi.Mesh(
        _name,
        vertex_count=_vertex_positions.shape[0],
        face_count=_triangle_indices.shape[0],
        has_vertex_normals=False,
        has_vertex_texcoords=False,
        props=props
    )
    mesh_params = mi.traverse(mesh)
    mesh_params["vertex_positions"] = dr.ravel(vertex_pos)
    mesh_params["faces"] = dr.ravel(face_indices)
    mesh_params.update()

    tmp_path = 'tmp/'
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)

    tmp_file_name = os.path.join(tmp_path, "%s.ply" % _name)
    mesh.write_ply(tmp_file_name)
    mesh = mi.load_dict({
        "type": "ply",
        "filename": tmp_file_name,
        "bsdf": {'type': 'diffuse',
            'reflectance': {
            'type': 'rgb',
            'value': [0.5, 0.5, 0.5]
            }
        },
        #'emitter': {
        #    'type': 'area',
        #    'radiance': {
        #        'type': 'rgb',
        #        'value': [10, 0, 0],
        #        },
        #}
        'sensor': {
            'type': 'irradiancemeter',
            'sampler': {
                'type': 'independent',
                'sample_count': 128
            },
            'film': {
                'type': 'hdrfilm',
                'width': 1,
                'height': 1,
                'rfilter': {
                    'type': 'box',
                },
                'pixel_format': 'rgb',
            },
        }
    })

    return mesh

def extract_triangle_data(_vertex_positions, _triangle_indices):
    shape = _triangle_indices.shape
    index_map = {}
    triangle_vertex_positions = []
    triangle_indices = []
    new_ind = 0
    for ind in np.ravel(_triangle_indices):
        if ind in index_map:
            triangle_indices.append(index_map[ind])
        else:
            triangle_vertex_positions.append(_vertex_positions[ind])
            triangle_indices.append(new_ind)
            index_map[ind] = new_ind
            new_ind +=1
    triangle_vertex_positions = np.array(triangle_vertex_positions)
    triangle_indices = np.array(triangle_indices)
    triangle_indices = np.reshape(triangle_indices, newshape=shape)
    return triangle_vertex_positions, triangle_indices

def load_sim_scene(_scene_data):

    mi_scene = {}

    objects = _scene_data['entities']
    vertex_positions = np.array(_scene_data['pointArray'])

    # rotate 90 around X
    vertex_positions = vertex_positions[:, [0, 2, 1]]
    vertex_positions[:, 1] *= -1.0
    logging.debug('Average vertex position: %s', np.average(vertex_positions, axis=0))

    for objk, surfaces in objects.items():
        for surfk, tindices in surfaces.items():
            surface_name = '%s-%s' % (objk, surfk)
            #print(surface_name)
            triangle_indices = np.array(tindices)
            surface_vertices, surface_triangle_indices = extract_triangle_data(vertex_positions, triangle_indices)
            mesh = create_triangle_mesh(surface_name, surface_vertices, surface_triangle_indices)
            mi_scene[surface_name] = mesh
    return mi_scene

def get_sun_direction( _lat, _long, _datetime_str):

    deg2rad = np.pi/180.0
    rad = lambda a: -a * deg2rad  + np.pi * 0.5 # convert azimut in degrees to radians: f(azimut) = - x * PI/180 + Pi/2

    date = dateutil.parser.parse(_datetime_str)
    date.replace(tzinfo=datetime.timezone.utc)

    if 0:
        print(date)
        print(date.date())
        print(date.time())
        print(date.timetz())
        print(date.utcoffset())
        print(date.tzname())
        print(date.timetuple())
        print(_lat)
        print(_long)

    azimut = get_azimuth(_lat, _long, date)
    altitude = get_altitude(_lat, _long, date)

    logging.debug("Date: %s, azimut: %f, altitude: %f", date, azimut, altitude)

    azimut_in_rad = rad(azimut)
    y, x = np.sin(azimut_in_rad), np.cos(azimut_in_rad)
    z = np.sin(altitude * deg2rad)

    return [x, y, z]

def get_sun(_direction, _power):
    return {
        'type': 'directional',
        'direction':  [v*-1.0 for v in _direction],
        'irradiance': {
            'type': 'spectrum',
            'value': _power,
        }
    }

class RenderServer(BaseHTTPRequestHandler):
    def do_POST(self):
        global mi_scene
        global args
        length = int(self.headers['Content-Length'])
        latitude, longitude, datetime = float(self.headers['La']), float(self.headers['Lo']), self.headers['Ti']

        rawData = self.rfile.read(length)
        sceneData = loadData(rawData)
        sim_objects = load_sim_scene(sceneData)

        merged_scene = {**mi_scene, **sim_objects}
        sun_direction = get_sun_direction(latitude, longitude, datetime)
        merged_scene['sun'] = get_sun(sun_direction, 1000.0)
        #merged_scene['sun'] = get_sun([0, -1, 0], 1000.0)

        sensor_count = len(sim_objects.keys())
        logging.debug("Sensor count: %d", sensor_count)

        scene = mi.load_dict(merged_scene)
        measurements = []
        for i in range(sensor_count):
            img = mi.render(scene, sensor=i+1, spp=args.rays)
            measurements.append(img.array)
        measurements = np.sum(np.array(measurements), axis=1)

        self.send_response(200)
        self.send_header("Content-type", "application/octet-stream")
        self.end_headers()
        self.wfile.write(bytes(measurements))

        if args.show:
            img = mi.render(scene)
            plt.figure()
            plt.axis("off")
            plt.imshow(mi.util.convert_to_bitmap(img))
            plt.draw()
    def log_message(self, format, *args):
        return

if __name__ == "__main__":

    #test_sun(); quit()

    """
    Options:
    -h,--help | Print this help message and exit
    --port (unsighed int, default=9000) | Port to start the server
    --rays (unsigned int, default=128) | Number of rays to cast from each triangle in the mesh
    --verbose | Be verbose.
    --show | Show the rendering.
    """

    import argparse

    # example CMD
    # python render.py data/t700.mesh 48.21 16.36 2022-08-23T10:34:48+00:00

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
    logging.info('Mitsuba3 - available variants: %s', mi.variants())

    offset = [5, -5, 0]
    mi_scene = create_base_scene(5.0, offset, 512)

    print("Starting rendering server ...")
    with HTTPServer(('', args.port), RenderServer) as server:
        print(f"Serving a renderer at port {args.port}")
        server.serve_forever()