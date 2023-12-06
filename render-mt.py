import time, os, logging, sys
import dateutil
import datetime
import numpy as np
from matplotlib import pyplot as plt
from pysolar.solar import *
from binary_loader import load

import drjit as dr
import mitsuba as mi

#mi.set_variant("cuda_ad_rgb")
#mi.set_variant("llvm_ad_rgb")
mi.set_variant("scalar_rgb")

from mitsuba import ScalarTransform4f as T

from functools import partial
from itertools import repeat
from multiprocessing import Pool, freeze_support

default_ground_size = 1e6 #100 km

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
                origin=[_offset[0], _offset[1]+_size*2, _offset[2]+_size],
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
        'naterial': {
            'type': 'twosided',
            'material': {
                'type': 'diffuse',
                'reflectance': {
                    'type': 'rgb',
                    'value': [0.5, 0.5, 0.5]
                }
            }
        }
    }

    return base_scene

def get_sun(_direction, _power):
    return {
        'type': 'directional',
        'direction':  [v*-1.0 for v in _direction],
        'irradiance': {
            'type': 'spectrum',
            'value': _power,
        }
    }

def create_triangle_mesh(_name, _vertex_positions, _triangle_indices, _id):

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

    tmp_file_name = os.path.join(tmp_path, "%s-%d.ply" % (_name, _id))
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

def load_sim_scene(_scene_data, _id):

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
            triangle_indices = np.array(tindices)
            surface_vertices, surface_triangle_indices = extract_triangle_data(vertex_positions, triangle_indices)
            mesh = create_triangle_mesh(surface_name, surface_vertices, surface_triangle_indices, _id)
            mi_scene[surface_name] = mesh
    return mi_scene

def add_axis_spheres(mi_scene):

    mi_scene['sphere_x'] = {
        'type': 'sphere',
        'to_world': mi.ScalarTransform4f.translate(offset).translate([0.5,0,0]).scale([0.2, 0.2, 0.2]),
        'bsdf': {
            'type': 'diffuse',
            'reflectance': {
                'type': 'rgb',
                'value': [1, 0, 0]
            }
        }
    }

    mi_scene['sphere_y'] = {
        'type': 'sphere',
        'to_world': mi.ScalarTransform4f.translate(offset).translate([0,0.5,0]).scale([0.2, 0.2, 0.2]),
        'bsdf': {
            'type': 'diffuse',
            'reflectance': {
                'type': 'rgb',
                'value': [0, 1, 0]
            }
        }
    }

    mi_scene['sphere_z'] = {
        'type': 'sphere',
        'to_world': mi.ScalarTransform4f.translate(offset).translate([0,0,0.5]).scale([0.2, 0.2, 0.2]),
        'bsdf': {
            'type': 'diffuse',
            'reflectance': {
                'type': 'rgb',
                'value': [0, 0, 1]
            }
        }
    }

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

    azimut, altitude = get_azimuth(_lat, _long, date), get_altitude(_lat, _long, date)

    logging.debug("Date: %s, azimut: %f, altitude: %f", date, azimut, altitude)

    azimut_in_rad = rad(azimut)
    x, y = np.sin(azimut_in_rad), np.cos(azimut_in_rad)
    z = np.sin(altitude * deg2rad)

    return [x, y, z]

def render(_id, _index_range, sim_scene, _lat, _long, _datetime_str, _ray_count, _verbose):

    logging.info('Mitsuba3 - available variants: %s', mi.variants())

    offset = [5, -5, 0]

    mi_scene = create_base_scene(default_ground_size, offset, 512)
    sun_direction = get_sun_direction(_lat, _long, _datetime_str)

    mi_scene['sun'] = get_sun(sun_direction, 1000.0)

    sim_objects = load_sim_scene(sim_scene, _id)
    mi_scene = {**mi_scene, **sim_objects}

    sensor_count = len(sim_objects.keys())
    logging.debug("Sensor count: %d", sensor_count)

    if 0:

        mi_scene['objs'] = {
            'type': 'obj',
            'filename': 'data/t700.obj',
            'to_world': mi.Transform4f.translate([0, 5, 5]).rotate(axis=[1, 0, 0], angle=90),
            'emitter': {
                'type': 'area',
                'radiance': {
                    'type': 'rgb',
                    'value': [10,0,0],
                }
            }
        }

    scene = mi.load_dict(mi_scene)

    measurements = []
    for i in _index_range:
        start = time.perf_counter_ns()
        img = mi.render(scene, sensor=i+1, spp=_ray_count, seed=i)
        measurements.append(img.array)

    measurements = np.sum(np.array(measurements), axis=1)
    return measurements

def main(_path, _lat, _long, _datetime_str, _ray_count=128, _verbose=False, _show_render=False):

    sim_scene = load(_path, _verbose)
    obj_count = 0
    for ek, ev in sim_scene['entities'].items():
        obj_count += len(ev.keys())

    cpu_count = os.cpu_count()
    print(cpu_count, obj_count)
    a_args = np.array_split(np.arange(obj_count), cpu_count)
    a_args = [(id, x.tolist(), sim_scene, _lat, _long, _datetime_str, _ray_count, _verbose) for id, x in enumerate(a_args)]
    with Pool() as pool:
        measurements = pool.starmap(render, a_args)

    measurements = np.concatenate(measurements).ravel()
    print(measurements)

    out_path = os.path.splitext(os.path.split(_path)[-1])[0]
    measurements.tofile(out_path+'.irrbin')

    if _show_render:
        img = mi.render(sim_scene)
        plt.figure()
        plt.axis("off")
        plt.imshow(mi.util.convert_to_bitmap(img))
        plt.show()


if __name__ == "__main__":

    start = time.perf_counter_ns()

    """
    Options:
    -h,--help | Print this help message and exit
    --scene_path (string, required) | Path to Scene
    --lat (flaot, required) | Latitude
    --long (flaot, required) | Longitude
    --rays-per-triangle (unsigned int, default=128) | Number of rays to cast from each triangle in the mesh
    --time (string, required) Time of day - should be in %Y-%m-%dT%H:%M:%S%z format
    --timestep (FLOAT, required) | Timestep (h)
    --verbose | Be verbose.
    --gui | Show GUI.
    """

    import argparse

    parser = argparse.ArgumentParser(description='Irradaince measurment tool based on Mitsuba 3.')
    parser.add_argument('scene_path', type=str, help='Path of the simulation scene file.')
    parser.add_argument('lat', type=float, help='Latitude of the simulation location.')
    parser.add_argument('long', type=float, help='Longitude of the simulation location.')
    parser.add_argument('datetime_str', type=str, help='Time of day - should be in %Y-%m-%dT%H:%M:%S%z format')
    parser.add_argument('--ray_count', type=int, default=128, help='Number of rays per element.')
    parser.add_argument('--verbose', type=bool, default=False, help='Number of rays per element.')

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.ERROR)

    logging.debug('Args: %s', args)
    main(args.scene_path, args.lat, args.long, args.datetime_str, args.ray_count, _show_render=False)
    logging.info('dur.: %.3f sec.' % ((time.perf_counter_ns()-start) * 1e-9))