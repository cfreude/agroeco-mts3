
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

        self.mi_base_scene = RendererMts3.create_base_scene(default_ground_size, 512)

    def load_binary(self, _binary_array, _latitude, _longitude, _datetime_str) -> None:
        scene_dict = binary_loader.load_binary(_binary_array, self.verbose)
        self.load_dict(scene_dict,_latitude, _longitude, _datetime_str)

    def load_path(self, _path, _latitude, _longitude, _datetime_str) -> None:
        scene_dict = binary_loader.load_path(_path, self.verbose)
        self.load_dict(scene_dict,_latitude, _longitude, _datetime_str)

    def load_dict(self, _scene_dict, _latitude, _longitude, _datetime_str) -> None:
        sim_objects, stats = RendererMts3.load_sim_scene(_scene_dict)

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

    def show_render(self, _ray_count=0, _show=True, _save=''):
        img = mi.render(self.mi_scene, spp=_ray_count)
        if (len(_save)):
            mi.util.write_bitmap(_save, img)
        if _show:
            plt.figure()
            plt.axis("off")
            plt.imshow(mi.util.convert_to_bitmap(img*0.01))
            plt.savefig('result.png', format='png')
            plt.show()

    @staticmethod
    def create_base_scene(_size, _res=512, _camera_distance = 5.0):

        base_scene = {
            'type': 'scene',
            'integrator_base': {
                'type': 'path',
            },
            'camera_base': {
                'type': 'perspective',
                'fov': 70,
                'to_world': mi.ScalarTransform4f.look_at(
                    origin=[0, _camera_distance, _camera_distance*2], # Y up
                    target=[0, 0, 0],
                    up=[0, 1, 0]), # Y up
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

        base_scene['ground_top'] = {
            'type': 'disk',
            'to_world': mi.ScalarTransform4f.scale([_size, _size, _size]).rotate([1, 0, 0], -90.0), # Y up
            'material': {
                'type': 'diffuse',
                'reflectance': {
                    'type': 'rgb',
                    'value': [0.5, 0.5, 0.5]
                }
            }
        }

        base_scene['ground_bottom'] = {
            'type': 'disk',
            'to_world': mi.ScalarTransform4f.translate([0, -10, 0]).scale([_size, _size, _size]).rotate([1, 0, 0], 90.0), # Y up
            'material': {
                'type': 'diffuse',
                'reflectance': {
                    'type': 'rgb',
                    'value': [0.5, 0.5, 0.5]
                }
            }
        }

        base_scene['ground_side'] = {
            'type': 'cylinder',
            'radius': _size,
            'p0': [0, -10, 0],
            'p1': [0, 0, 0],
            'material': {
                'type': 'diffuse',
                'reflectance': {
                    'type': 'rgb',
                    'value': [0.5, 0.5, 0.5]
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

        avgv = np.average(vertex_positions, axis=0)
        minv = np.min(vertex_positions, axis=0)
        maxv = np.max(vertex_positions, axis=0)
        logging.debug(f'Vertex position statistics: min={minv}, avg={avgv}, max={maxv}')

        for objk, surfaces in objects.items():
            for surfk, tindices in surfaces.items():
                surface_name = '%s-%s' % (objk, surfk)
                #print(surface_name)
                triangle_indices = np.array(tindices)
                surface_vertices, surface_triangle_indices = RendererMts3.extract_triangle_data(vertex_positions, triangle_indices)
                mesh = RendererMts3.create_triangle_mesh(surface_name, surface_vertices, surface_triangle_indices)
                mi_scene[surface_name] = mesh
        return mi_scene, (minv, avgv, maxv)

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
        z, x = -np.sin(azimut_in_rad), np.cos(azimut_in_rad)
        y = np.sin(altitude * deg2rad)

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
    def get_sky(_power):
        return {
            'type': 'envmap',
            'filename': "./data/stuttgart_hillside_4k.exr",
            'scale': _power,            
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

        mi_scene = RendererMts3.create_base_scene(default_ground_size, 512)
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
            plt.pause(0.1)

    @staticmethod
    def test_sun_optimized():

        fig,ax = plt.subplots(1,1)
        image = np.array(np.zeros((256, 256, 3)))
        im = ax.imshow(image)
                
        datetime_str = '2022-08-23T%00d:00:00+02:00' % 0
        sun_direction = RendererMts3.get_sun_direction(48.21, 16.36, datetime_str)
        sun_dir = np.array([v*-1.0 for v in sun_direction])
        sun_dir /= np.linalg.norm(sun_dir)
        sun_dir = sun_dir.tolist()

        mi_scene = RendererMts3.create_base_scene(default_ground_size, 512)
        mi_scene['sun'] = RendererMts3.get_sun(sun_direction, 100.0)
        mi_scene['sky'] = RendererMts3.get_sky(20.0)
        RendererMts3.add_axis_spheres(mi_scene, [0,0,0])
        

        up = np.array([0, 1, 0])
        scene = mi.load_dict(mi_scene)
        params = mi.traverse(scene)
        print(params)
        up_ = mi.coordinate_system(mi.scalar_rgb.Point3f(mi.Vector3f(sun_dir)))
        print(up)
        print(T.look_at([0,0,0], sun_dir, [0,1,0]))
        print(params['sun.to_world']) 
        print(params['sun.irradiance.value'])       
        print(params['sky.scale'])
        quit()

        for i in range(6, 20):
            datetime_str = '2022-08-23T%00d:00:00+02:00' % i
            print(datetime_str)
            sun_direction = RendererMts3.get_sun_direction(48.21, 16.36, datetime_str)
            dot_scaler = np.max(0, np.dot(up, sun_direction))
            sun_power = dot_scaler * 100.0
            sky_power = dot_scaler * 20



            img = mi.render(scene)
            im.set_data(mi.util.convert_to_bitmap(img))
            fig.canvas.draw_idle()
            plt.pause(0.1)