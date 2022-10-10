
import time, os, logging
import dateutil
import dateutil.parser
import datetime
import numpy as np
import drjit as dr
import mitsuba as mi
from matplotlib import pyplot as plt
from pysolar.solar import *
import binary_loader

#mi.set_variant("cuda_ad_rgb")
#mi.set_variant("llvm_ad_rgb")
mi.set_variant("scalar_rgb")

from mitsuba import ScalarTransform4f as T

default_ground_size = 1e6 #100 km

class RendererMts3():

    def __init__(self, _verbose=False) -> None:
        self.mi_scene = None
        self.sensor_count = None
        self.verbose = _verbose

        logging.info('Mitsuba3 - available variants: %s', mi.variants())

        offset = [5, -5, 0]
        self.mi_base_scene = RendererMts3.create_base_scene(default_ground_size, offset, 512)

    def load_binary(self, _binary_array, _latitude, _longitude, _datetime_str) -> None:
        scene_dict = binary_loader.load_binary(_binary_array, self.verbose)
        self.load_dict(scene_dict,_latitude, _longitude, _datetime_str)

    def load_path(self, _path, _latitude, _longitude, _datetime_str) -> None:
        scene_dict = binary_loader.load_path(_path, self.verbose)
        self.load_dict(scene_dict,_latitude, _longitude, _datetime_str)

    def load_dict(self, _scene_dict, _latitude, _longitude, _datetime_str) -> None:
        sim_objects = RendererMts3.load_sim_scene(_scene_dict)

        merged_scene = {**self.mi_base_scene, **sim_objects}
        sun_direction = RendererMts3.get_sun_direction(_latitude, _longitude, _datetime_str)
        merged_scene['sun'] = RendererMts3.get_sun(sun_direction, 1000.0)
        #merged_scene['sun'] = get_sun([0, -1, 0], 1000.0)

        sensor_count = len(sim_objects.keys())
        logging.debug("Sensor count: %d", sensor_count)

        self.mi_scene = mi.load_dict(merged_scene)
        self.sensor_count = sensor_count

    def render(self, _ray_count) -> None:
        measurements = []
        for i in range(self.sensor_count ):
            img = mi.render(self.mi_scene, sensor=i+1, spp=_ray_count)
            measurements.append(img.array)
        return np.sum(np.array(measurements), axis=1)

    #skips the rendering, useful just for testing the loading overhead
    def render_dummy(self, _ray_count) -> None:
        measurements = []
        for i in range(self.sensor_count ):
            measurements.append(1.0)
        return np.array(measurements)

    def show_render(self):
        img = mi.render(self.mi_scene)
        plt.figure()
        plt.axis("off")
        plt.imshow(mi.util.convert_to_bitmap(img))
        plt.draw()

    @staticmethod
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
            'material':
            {
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

    @staticmethod
    def create_triangle_mesh(_name, _vertex_positions, _triangle_indices):

        vertex_pos = mi.TensorXf(_vertex_positions)
        face_indices = mi.TensorXu(_triangle_indices)

        props = mi.Properties()
        if 0:
            bsdf = mi.load_dict({
                'type': 'twosided',
                'material':
                {
                    'type': 'diffuse',
                    'reflectance': {
                        'type': 'rgb',
                        'value': [1, 0, 0]
                        }
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
            "bsdf": {
                'type': 'twosided',
                'material': {
                    'type': 'diffuse',
                    'reflectance': {
                        'type': 'rgb',
                        'value': [0.5, 0.5, 0.5]
                    }
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

    @staticmethod
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

    @staticmethod
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
                surface_vertices, surface_triangle_indices = RendererMts3.extract_triangle_data(vertex_positions, triangle_indices)
                mesh = RendererMts3.create_triangle_mesh(surface_name, surface_vertices, surface_triangle_indices)
                mi_scene[surface_name] = mesh
        return mi_scene

    @staticmethod
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

    @staticmethod
    def get_sun(_direction, _power):
        return {
            'type': 'directional',
            'direction':  [v*-1.0 for v in _direction],
            'irradiance': {
                'type': 'spectrum',
                'value': _power,
            }
        }

    @staticmethod
    def add_axis_spheres(mi_scene, _offset):

        mi_scene['sphere_x'] = {
            'type': 'sphere',
            'to_world': mi.ScalarTransform4f.translate(_offset).translate([0.5,0,0]).scale([0.2, 0.2, 0.2]),
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
            'to_world': mi.ScalarTransform4f.translate(_offset).translate([0,0.5,0]).scale([0.2, 0.2, 0.2]),
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
            'to_world': mi.ScalarTransform4f.translate(_offset).translate([0,0,0.5]).scale([0.2, 0.2, 0.2]),
            'bsdf': {
                'type': 'diffuse',
                'reflectance': {
                    'type': 'rgb',
                    'value': [0, 0, 1]
                }
            }
        }

        return mi_scene

    @staticmethod
    def test_sun():

        fig,ax = plt.subplots(1,1)
        image = np.array(np.zeros((256, 256, 3)))
        im = ax.imshow(image)

        mi_scene = RendererMts3.create_base_scene(default_ground_size, [0,0,0], 512)
        for i in range(6, 20):
            datetime_str = '2022-08-23T%00d:00:00+02:00' % i
            print(datetime_str)
            sun_direction = RendererMts3.get_sun_direction(48.21, 16.36, datetime_str)
            mi_scene['sun'] = RendererMts3.get_sun(sun_direction, 100.0)
            RendererMts3.add_axis_spheres(mi_scene, [0,0,0])
            scene = mi.load_dict(mi_scene)
            img = mi.render(scene)
            im.set_data(mi.util.convert_to_bitmap(img))
            fig.canvas.draw_idle()
            plt.pause(1)