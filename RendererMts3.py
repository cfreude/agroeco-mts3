from distutils.log import debug
import os, logging, sys
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

from mitsuba import PositionSample3f, ScalarTransform4f as T, SurfaceInteraction3f

default_ground_size = 1e6 #100 km

class RendererMts3():

    def __init__(self, _verbose=False) -> None:
        self.mi_scene = None
        self.sensor_count = None
        self.verbose = _verbose

        logging.info('Mitsuba3 - available variants: %s', mi.variants())
        
        mi.set_variant("scalar_rgb")
        origin, target = RendererMts3.get_camera(2.0, 4.0)
        self.mi_base_scene = RendererMts3.create_base_scene(default_ground_size, _spp=16, _cam_origin=origin, _cam_target=target)

    def load_binary(self, _binary_array, _latitude, _longitude, _datetime_str, _spp, cam = None) -> None:
        scene_dict = binary_loader.load_binary(_binary_array, self.verbose)
        self.load_sim_dict(scene_dict,_latitude, _longitude, _datetime_str, _spp, cam)

    def load_path(self, _path, _latitude, _longitude, _datetime_str, _spp) -> None:
        scene_dict = binary_loader.load_path(_path, self.verbose)
        self.load_sim_dict(scene_dict,_latitude, _longitude, _datetime_str, _spp)

    def load_sim_dict(self, _scene_dict, _latitude, _longitude, _datetime_str, _spp, _cam = None) -> None:
        sim_objects, (minv, avgv, maxv), sensor_count = RendererMts3.load_sim_scene(_scene_dict, _spp)        
        logging.debug(f"Scene statistics: {minv}, {avgv}, {maxv}")
        logging.debug(f"Sensor count: {sensor_count}")

        distance = np.linalg.norm(maxv-minv)*0.5
        if distance <= 0:
            distance = 5.0
        height = maxv[1]
        if maxv[1] == avgv[1]:
            height += 0.5
        scene_center = avgv.tolist()

        self.load_dict(sim_objects, sensor_count, _latitude, _longitude, _datetime_str, _spp, _cam)

    def load_dict(self, _scene_dict, _sensor_count, _latitude, _longitude, _datetime_str, _spp, _cam = None) -> None:
        
        scene_center = [2.5,0.0,0.0]; height = 5.0; distance = 7.0

        if _cam is None:
            origin, target = RendererMts3.get_camera(height, distance, scene_center)
            width = 512
            height = width
            fov = 70
            logging.debug(f'camera origin: {origin}, target: {target}')
        else:
            width = int(_cam['width'])
            height = int(_cam['height'])
            fov = float(_cam['fov'])
            origin = _cam['origin'].tolist()
            target = _cam['target'].tolist()

        self.mi_base_scene  = RendererMts3.create_base_scene(default_ground_size, _width=width, _height=height, _fov=fov, _spp=_spp, _cam_origin=origin, _cam_target=target)

        sun_direction = RendererMts3.get_sun_direction(_latitude, _longitude, _datetime_str)
        sun_sky, _, _ = RendererMts3.get_sun_sky(sun_direction, 1000.0)

        merged_scene = {**self.mi_base_scene, **sun_sky, **_scene_dict}

        '''
        transf = T(np.array([
                    1.0, 0.0, 0.0, 2.5,
                    0.0, 2.0, 0.0, 0.1,
                    0.0, 0.0, 1.0, 2.5,
                    0, 0, 0, 1]).reshape((4,4)))
        transf = T.translate([0, 2, 0]).rotate([0,1,0], 90).scale([0.5,2,1])
        print(transf)

        merged_scene['test_rect'] = {
            'type': 'rectangle',
            'to_world': transf,
            #'to_world': T.translate([2.5, 0.1, 2.5]),#@T.rotate([1,0,0], 90),
            'bsdf': {
                'type': 'twosided',
                'material': {
                    'type': 'diffuse',
                    'reflectance': {
                        'type': 'rgb',
                        'value': [1,0,0]
                    }
                }
            }
        }
        '''

        # DEBUG AXIS
        #RendererMts3.add_axis_spheres(merged_scene, [2.5, 0.0, 2.5])

        self.mi_scene = mi.load_dict(merged_scene)
        self.sensor_count = _sensor_count
        return merged_scene

    def render(self, _ray_count) -> None:
        measurements = []
        for i in range(self.sensor_count):
            img = mi.render(self.mi_scene, sensor=i+1, spp=_ray_count)
            measurements.append(img.array)
        if len(measurements) > 0:
            return np.sum(np.array(measurements), axis=1)
        else:
            logging.warn('No measurements computed.')
            return None

    def render_for_cam(self, _ray_count):
        return np.array(mi.render(self.mi_scene, spp=_ray_count).array)

    #skips the rendering, useful just for testing the loading overhead
    def render_dummy(self, _ray_count) -> None:
        measurements = []
        for i in range(self.sensor_count ):
            measurements.append(1.0)
        return np.array(measurements)

    def show_render(self, _ray_count=128, _show=True, _save=''):
        img = mi.render(self.mi_scene, spp=_ray_count) * 0.01
        if len(_save):
            logging.info(f'saving image to: {_save}')
            mi.util.write_bitmap(_save, img)
        if _show:
            plt.figure()
            plt.axis("off")
            plt.imshow(mi.util.convert_to_bitmap((img / (img+1.0)) ** (1.0/2.2)))
            plt.savefig('result.png', format='png')
            plt.show()

    @staticmethod
    def create_base_scene(_size, _width=512, _height=512, _spp=128, _cam_origin=[0,1,1], _cam_target=[0,0,0], _fov=70):

        base_scene = {
            'type': 'scene',
            'integrator_base': {
                'type': 'path',
            },
            'camera_base': {
                'type': 'perspective',
                'fov': _fov,
                'to_world': mi.ScalarTransform4f.look_at(
                    origin=_cam_origin,
                    target=_cam_target,
                    up=[0, 1, 0]), # Y up
                'film_base': {
                    'type': 'hdrfilm',
                    'pixel_format': 'rgba',
                    'width': _width,
                    'height': _height
                },
                'sampler_id': {
                    'type': 'independent',
                    'sample_count': _spp
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
    def create_triangle_mesh(_name, _vertex_positions, _triangle_indices, _spp=0):

        #print(_name)
        #print(_vertex_positions)
        #print(_triangle_indices)

        vertex_pos = mi.TensorXf(_vertex_positions)
        face_indices = mi.TensorXu(_triangle_indices)

        props = mi.Properties()

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

        del mesh

        ply = {
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
            }
        }

        if _spp > 0:
            ply['sensor'] = {
                'type': 'irradiancemeter',
                'sampler': {
                    'type': 'independent',
                    'sample_count': _spp
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

        mesh = mi.load_dict(ply)        
        os.remove(tmp_file_name)

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
    def load_sim_scene(_scene_data, _spp=128):

        if _scene_data['format'] == 1:
            return RendererMts3.load_sim_scene_meshes(_scene_data, _spp)
        elif _scene_data['format'] == 2:
            return RendererMts3.load_sim_scene_primitives(_scene_data, _spp)

    @staticmethod
    def load_sim_scene_meshes(_scene_data, _spp=128):

        mi_scene = {}

        vertex_positions = np.array(_scene_data['pointArray'])
        avgv = np.average(vertex_positions, axis=0)
        minv = np.min(vertex_positions, axis=0)
        maxv = np.max(vertex_positions, axis=0)
        logging.debug(f'Vertex position statistics: min={minv}, avg={avgv}, max={maxv}')

        # add sensors
        sensor_count = 0
        objects = _scene_data['sensors']
        for objk, surfaces in objects.items():
            for surfk, tindices in surfaces.items():
                surface_name = '%s-%s' % (objk, surfk)
                #print(surface_name)
                triangle_indices = np.array(tindices)
                surface_vertices, surface_triangle_indices = RendererMts3.extract_triangle_data(vertex_positions, triangle_indices)
                mesh = RendererMts3.create_triangle_mesh(surface_name, surface_vertices, surface_triangle_indices, _spp)
                mi_scene[surface_name] = mesh
                sensor_count += 1

        # add obstacles
        objects = _scene_data['obstacles']
        for objk, surfaces in objects.items():
            for surfk, tindices in surfaces.items():
                surface_name = '%s-%s' % (objk, surfk)
                #print(surface_name)
                triangle_indices = np.array(tindices)
                surface_vertices, surface_triangle_indices = RendererMts3.extract_triangle_data(vertex_positions, triangle_indices)
                mesh = RendererMts3.create_triangle_mesh(surface_name, surface_vertices, surface_triangle_indices)
                mi_scene[surface_name] = mesh

        if sensor_count < 1:
            logging.warn('No sensors defined.')

        return mi_scene, (minv, avgv, maxv), sensor_count

    @staticmethod
    def disk(data):
        '''
        float32 matrix 4x3 (the bottom row is always 0 0 0 1) !ROW MAJOR
        '''
        mat = np.array(data['matrix']+[0,0,0,1]).reshape((4,4))
        out = {
            'type': 'disk',
            'to_world': T(mat)@T.rotate([1,0,0], 90),
            'bsdf': {
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
        return out
    @staticmethod
    def cylinder(data):
        '''
        float32 length
        float32 radius
        float32 matrix 4x3 (the bottom row is always 0 0 0 1)
        '''
        mat = np.array(data['matrix']+[0,0,0,1]).reshape((4,4))
        out = {
            'type': 'cylinder',
            'p0': [0, 0, 0],
            'p1': [0, data['length'], 0],
            'radius': data['radius'],
            'to_world': T(mat),
            'bsdf': {
                'type': 'diffuse',
                'reflectance': {
                    'type': 'rgb',
                    'value': [0.5, 0.5, 0.5]
                }
            }
        }
        return out

    @staticmethod
    def sphere(data):
        '''
        3xfloat32 center
        float32 radius
        '''
        out = {
            'type': 'sphere',
            'center': data['center'],
            'radius': data['radius'],
            'bsdf': {
                'type': 'diffuse',
                'reflectance': {
                    'type': 'rgb',
                    'value': [0.5, 0.5, 0.5]
                }
            }
        }
        return out

    @staticmethod
    def rectangle(data):
        '''
        float32 matrix 4x3 (the bottom row is always 0 0 0 1)
        '''
        mat = np.array(data['matrix']+[0,0,0,1]).reshape((4,4))
        out = {
            'type': 'rectangle',
            'to_world': T(mat),#@T.rotate([1,0,0], 90),
            'bsdf': {
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
        return out

    @staticmethod
    def load_sim_scene_primitives(_scene_data, _spp=128):

        #(1 = disk, 2 = cylinder/stem, 4 = sphere/shoot, 8 = rectangle/leaf)
        primitive_map = {
            1: RendererMts3.disk,
            2: RendererMts3.cylinder,
            4: RendererMts3.sphere,
            8: RendererMts3.rectangle,
        }

        primitive_map_name = {
            1: 'disk',
            2: 'cylinder',
            4: 'sphere',
            8: 'rectangle',
        }

        mi_scene = {}

        minv = np.array([sys.float_info.max]*3)
        avgv = np.array([0.0,0.0,0.0])
        maxv = np.array([sys.float_info.min]*3)

        # add sensors
        sensor_count = 0
        objects = _scene_data['sensors']
        for objk, surfaces in objects.items():
            for surfk, data in surfaces.items():
                surface_name = '%s-%s' % (objk, surfk)

                # process AABB
                pos = None
                #if 'matrix' in data:
                #    mat = data['matrix']
                #    pos = np.array([mat[3], mat[7], mat[11]])

                if 'center' in data:
                    pos = data['center']

                if pos is not None:
                    avgv += pos
                    minv = np.minimum(minv, pos)
                    maxv = np.maximum(maxv, pos)

                primitive = primitive_map[data['type']](data)
                primitive['sensor'] = {
                    'type': 'irradiancemeter',
                    'sampler': {
                        'type': 'independent',
                        'sample_count': _spp
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
                mi_scene[surface_name] = mi.load_dict(primitive)
                sensor_count += 1

        # add obstacles
        objects = _scene_data['obstacles']

        for objk, surfaces in objects.items():
            for surfk, data in surfaces.items():
                surface_name = '%s-%s' % (objk, surfk)
                type_id = data['type']
                func = primitive_map[type_id]
                #logging.debug(primitive_map_name[type_id])
                mi_scene[surface_name] = mi.load_dict(func(data))


        if sensor_count < 1:
            logging.warn('No sensors defined.')
        else:
            avgv /= sensor_count

        return mi_scene, (minv, avgv, maxv), sensor_count

    @staticmethod
    def get_sun_direction( _lat, _long, _datetime_str):

        deg2rad = np.pi/180.0
        rad = lambda a: -a * deg2rad  + np.pi * 0.5 # convert azimut in degrees to radians: f(azimut) = - x * PI/180 + Pi/2

        date = dateutil.parser.parse(_datetime_str)
        date.replace(tzinfo=datetime.timezone.utc)

        '''
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
        '''

        azimut = get_azimuth(_lat, _long, date)
        altitude = get_altitude(_lat, _long, date)

        logging.debug(f"Date: {date}, azimut: {azimut}, altitude: {altitude}")

        azimut_in_rad = rad(azimut)
        z, x = -np.sin(azimut_in_rad), np.cos(azimut_in_rad)
        y = np.sin(altitude * deg2rad)

        return [x, y, z]

    @staticmethod
    def get_sun(_direction, _power):
        '''return {
            'type': 'directional',
            'direction':  [v*-1.0 for v in _direction],
            'irradiance': {
                'type': 'rgb',
                'value': _power,
            }
        }'''
        return {
            'type': 'disk',
            'to_world': mi.ScalarTransform4f().look_at([v*100.0 for v in _direction], [0,0,0], [0,1,0]).scale(10.0),
            'emitter': {
                'type': 'area',
                'radiance': {
                    'type': 'rgb',
                    'value': _power*10.0,
                }
            }
        }

    @staticmethod
    def get_sky(_power):
        '''return {
            'type': 'envmap',
            'filename': "./imgs/stuttgart_hillside_1k.exr",
            'scale': _power,
        }'''
        return {
            'type': 'constant',
            'radiance': {
                'type': 'rgb',
                'value': _power,
            }
        }

    @staticmethod
    def get_sun_sky(_direction, _power=1000.0, _disable_sky=False):

        _dot = np.dot([0,1,0], _direction)
        dot_scaler = np.max([0.0, _dot])

        sun_power = dot_scaler * _power * 5.0/6.0 # -1/6 for clowdy sky
        sky_power = dot_scaler * 10.0

        scene = {}
        scene['sun'] = RendererMts3.get_sun(_direction, sun_power)
        if not _disable_sky:
            scene['sky'] = RendererMts3.get_sky(sky_power)

        return scene, sun_power, sky_power

    @staticmethod
    def add_axis_spheres(mi_scene, _offset):

        mi_scene['sphere_x'] = {
            'type': 'cylinder',
            'p1': [1, 0, 0],
            'radius': 0.1,
            'to_world': mi.ScalarTransform4f.translate(_offset),
            'material': {
                'type': 'diffuse',
                'reflectance': {
                    'type': 'rgb',
                    'value': [0.9, 0, 0]
                }
            }
        }

        mi_scene['sphere_y'] = {
            'type': 'cylinder',
            'p1': [0, 1, 0],
            'radius': 0.1,
            'to_world': mi.ScalarTransform4f.translate(_offset),
            'material': {
                'type': 'diffuse',
                'reflectance': {
                    'type': 'rgb',
                    'value': [0, 0.9, 0]
                }
            }
        }

        mi_scene['sphere_z'] = {
            'type': 'cylinder',
            'p1': [0, 0, 1],
            'radius': 0.1,
            'to_world': mi.ScalarTransform4f.translate(_offset),
            'material': {
                'type': 'diffuse',
                'reflectance': {
                    'type': 'rgb',
                    'value': [0, 0, 0.9]
                }
            }
        }

        return mi_scene

    @staticmethod
    def get_camera(_height, _distance, _scene_center=[0,0,0]):
        origin = np.array([0, _height, _distance]) + np.array(_scene_center)
        target = _scene_center
        return origin.tolist(), target

    @staticmethod
    def test_sun():

        fig,ax = plt.subplots(1,1)
        image = np.array(np.zeros((256, 256, 3)))
        im = ax.imshow(image)

        origin, target = RendererMts3.get_camera(2.0, 4.0)
        mi_scene = RendererMts3.create_base_scene(default_ground_size, _spp=16, _cam_origin=origin, _cam_target=target)
        for i in range(6, 21):
            datetime_str = '2022-08-23T%00d:00:00+02:00' % i
            logging.debug(datetime_str)
            sun_direction = RendererMts3.get_sun_direction(48.21, 16.36, datetime_str)
            sun_sky, _, _ = RendererMts3.get_sun_sky(sun_direction, 1000.0)
            mi_scene = {**mi_scene, **sun_sky}
            RendererMts3.add_axis_spheres(mi_scene, [0,0,0])
            scene = mi.load_dict(mi_scene)
            img = mi.render(scene)
            im.set_data(mi.util.convert_to_bitmap((img / (img+1.0)) ** (1.0/2.2)))
            fig.canvas.draw_idle()
            plt.pause(0.1)

    @staticmethod
    def test_sun_optimized():

        fig,ax = plt.subplots(1,1)
        image = np.array(np.zeros((256, 256, 3)))
        im = ax.imshow(image)

        datetime_str = '2022-08-23T%00d:00:00+02:00' % 0
        sun_direction = RendererMts3.get_sun_direction(48.21, 16.36, datetime_str)
        sun_sky, _, _ = RendererMts3.get_sun_sky(sun_direction, 1000.0)
        origin, target = RendererMts3.get_camera(2.0, 4.0)
        mi_scene = RendererMts3.create_base_scene(default_ground_size, _spp=16, _cam_origin=origin, _cam_target=target)

        mi_scene = {**mi_scene, **sun_sky}
        RendererMts3.add_axis_spheres(mi_scene, [0,0,0])

        scene = mi.load_dict(mi_scene)
        params = mi.traverse(scene)

        '''
        print(params)
        print('#########')
        print(params['sun.to_world'])
        print(params['sun.irradiance.value'])
        print(params['sky.scale'])
        '''

        for i in range(6, 21):
            datetime_str = '2022-08-23T%00d:00:00+02:00' % i
            logging.debug(datetime_str)
            sun_direction = RendererMts3.get_sun_direction(48.21, 16.36, datetime_str)
            _, sun_power, sky_power = RendererMts3.get_sun_sky(sun_direction, 1000.0)

            dn = np.linalg.norm(sun_direction)
            direction = [-v / dn for v in sun_direction]
            up_coord, _ = mi.coordinate_system(direction)
            params['sun.to_world'] = T.look_at([0,0,0], direction, up_coord)
            params['sun.irradiance.value'] = [sun_power]*3
            params['sky.scale'] = sky_power
            params.update()

            img = mi.render(scene)
            im.set_data(mi.util.convert_to_bitmap((img / (img+1.0)) ** (1.0/2.2)))
            fig.canvas.draw_idle()
            plt.pause(0.1)
