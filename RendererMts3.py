from distutils.log import debug
import os, logging, sys
import dateutil
import dateutil.parser
import datetime
import numpy as np
import drjit as dr
import mitsuba as mi
from pysolar.solar import *
import binary_loader
from cumulative_sky import CumulativeSky

#mi.set_variant("cuda_ad_rgb")
#mi.set_variant("llvm_ad_rgb")
mi.set_variant("scalar_rgb")

from mitsuba import ScalarTransform4f as T

ADD_GROUND = True

default_ground_size = 1e6 #100 km

class RendererMts3():

    def __init__(self, _verbose=False, _use_batch_render=False) -> None:
        self.mi_scene = None
        self.sensor_count = None
        self.verbose = _verbose
        self.use_batch = _use_batch_render

        logging.info('Mitsuba3 - available variants: %s', mi.variants())

        mi.set_variant("scalar_rgb")
        origin, target = RendererMts3.get_camera(2.0, 4.0)
        self.mi_base_scene = RendererMts3.create_base_scene(default_ground_size, _spp=16, _cam_origin=origin, _cam_target=target)

    def load_binary(self, _binary_array, _latitude, _longitude, _datetime_str, _spp, _epw_path=None, _end_datetime_str=None, cam = None):
        scene_dict = binary_loader.load_binary(_binary_array, self.verbose)
        return self.load_sim_dict(scene_dict,_latitude, _longitude, _datetime_str, _spp, _epw_path, _end_datetime_str, cam)

    def load_path(self, _path, _latitude, _longitude, _datetime_str, _spp, _epw_path=None, _end_datetime_str=None):
        scene_dict = binary_loader.load_path(_path, self.verbose)
        return self.load_sim_dict(scene_dict,_latitude, _longitude, _datetime_str, _spp, _epw_path, _end_datetime_str)

    def load_sim_dict(self, _scene_dict, _latitude, _longitude, _datetime_str, _spp, _epw_path=None, _end_datetime_str=None, _cam = None):
        sim_objects, (minv, avgv, maxv), sensor_count = RendererMts3.load_sim_scene(_scene_dict, _spp, self.use_batch)
        logging.debug(f"Scene statistics: {minv}, {avgv}, {maxv}")
        logging.debug(f"Sensor count: {sensor_count}")

        return self.load_dict(sim_objects, sensor_count, _latitude, _longitude, _datetime_str, _spp, _epw_path, _end_datetime_str, _cam)


    @staticmethod
    def encodeName(objk, surfk):
        return '%s-%s' % (str(objk).zfill(5), str(surfk).zfill(5))

    def load_dict(self, _scene_dict, _sensor_count, _latitude, _longitude, _datetime_str, _spp, _epw_path=None, _end_datetime_str=None, _cam = None) -> None:

        scene_center = [2.5,0.0,0.0]; height = 5.0; distance = 7.0

        if _cam is None:
            origin, target = RendererMts3.get_camera(height, distance, scene_center)
            width = 512
            height = width
            fov = 70
        else:
            width = int(_cam['width'])
            height = int(_cam['height'])
            fov = float(_cam['fov'])
            origin = _cam['origin'].tolist()
            target = _cam['target'].tolist()

        logging.debug(f'camera origin: {origin}, target: {target}')

        self.mi_base_scene  = RendererMts3.create_base_scene(default_ground_size, _width=width, _height=height, _fov=fov, _spp=_spp, _cam_origin=origin, _cam_target=target)

        start_date = dateutil.parser.parse(_datetime_str)
        start_date.replace(tzinfo=datetime.timezone.utc)

        if  _epw_path is not None and _end_datetime_str is not None:
            logging.info(f'Computing cumulative sky form \'{_datetime_str}\' to \'{_end_datetime_str}\' (EPW file: \'{os.path.split(_epw_path)[-1]}\')')
            end_date = dateutil.parser.parse(_end_datetime_str)
            end_date.replace(tzinfo=datetime.timezone.utc)

            cum_sky = CumulativeSky()
            envmap, hoy_count = cum_sky.compute(_epw_path, start_date, end_date, _only_sun=False)
            sun_sky = { 'sun_sky': RendererMts3.get_envmap(envmap*0.01, 1.0) }
        else:
            sun_direction = RendererMts3.get_sun_direction(_latitude, _longitude, start_date)
            sun_sky, _, _ = RendererMts3.get_sun_sky(sun_direction, 1000.0)
            envmap = None; hoy_count = 1

        merged_scene = {**self.mi_base_scene, **sun_sky, **_scene_dict}

        self.mi_scene = mi.load_dict(merged_scene)
        self.sensor_count = _sensor_count
        return envmap, hoy_count

    def render(self, _ray_count) -> None:
        measurements = []
        if self.use_batch:
            measurements = mi.render(self.mi_scene, sensor=1, spp=_ray_count)
            measurements = np.squeeze(measurements, axis=0)
        else:
            for i in range(self.sensor_count):
                img = mi.render(self.mi_scene, sensor=i+1, spp=_ray_count)
                measurements.append(img.array)
            measurements = np.array(measurements)
        if len(measurements) > 0:
            logging.info(measurements.shape)
            sum = np.sum(measurements, axis=1)
            minv = np.min(sum)
            mean = np.mean(sum)
            maxv = np.max(sum)
            logging.info(f'{minv}, {mean}, {maxv}')
            measurements = sum
        else:
            logging.warn('No measurements computed.')
            return None
        
        return measurements

    # used for debug overlay, renders the scene from a custom camera (camera parameters are incl. in the request)
    def render_for_cam(self, _ray_count, _write_debug_img=False):
        img = mi.render(self.mi_scene, spp=_ray_count)
        
        if _write_debug_img:
            bm = mi.util.convert_to_bitmap((img / (img+1.0)) ** (1.0/2.2))        
            mi.util.write_bitmap('./img.png', bm, write_async=True)
            
        result = np.array(img.array)
        rgb = result[np.mod(np.arange(result.size), 4) != 3]
        max = np.max(rgb)
        return rgb / max if max > 0 else rgb

    # skips the rendering, useful just for testing the loading overhead and debugging indexing
    def render_dummy(self, _sensor_count) -> None:
        measurements = []
        for i in range(_sensor_count):
            measurements.append(i)
        return np.array(measurements, dtype=np.float32)

    def get_render_image(self, _ray_count=128):
        img = mi.render(self.mi_scene, spp=_ray_count)
        img = mi.util.convert_to_bitmap((img / (img+1.0)) ** (1.0/2.2))
        return img

    @staticmethod
    def save_render_image(_path, _img):
        logging.info(f'saving image to: {_path}')
        mi.util.write_bitmap(_path, _img)

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
                'fov_axis': 'y',
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

        if ADD_GROUND:
            base_scene['ground_top'] = {
                'type': 'disk',
                'to_world': mi.ScalarTransform4f.translate([5,0,5]).scale([np.sqrt(5*5*2)]*3).rotate([1, 0, 0], -90.0), # Y up
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
    def load_sim_scene(_scene_data, _spp=128, _use_batch=False):
        if _scene_data['format'] == 1:
            return RendererMts3.load_sim_scene_meshes(_scene_data, _spp)
        elif _scene_data['format'] >= 2:
            return RendererMts3.load_sim_scene_primitives(_scene_data, _spp, _use_batch=_use_batch)

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
                surface_name = RendererMts3.encodeName(objk, surfk)
                triangle_indices = np.array(tindices)
                surface_vertices, surface_triangle_indices = RendererMts3.extract_triangle_data(vertex_positions, triangle_indices)
                mesh = RendererMts3.create_triangle_mesh(surface_name, surface_vertices, surface_triangle_indices, _spp)
                mi_scene[surface_name] = mesh
                sensor_count += 1

        # add obstacles
        objects = _scene_data['obstacles']
        for objk, surfaces in objects.items():
            for surfk, tindices in surfaces.items():
                surface_name = RendererMts3.encodeName(objk, surfk)
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
            'to_world': T(mat),
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
    def load_sim_scene_primitives(_scene_data, _spp=128, _use_batch=False):

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

        batch_shapes = []

        minv = np.array([sys.float_info.max]*3)
        avgv = np.array([0.0,0.0,0.0])
        maxv = np.array([sys.float_info.min]*3)

        sensor = {
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

        # add sensors
        sensor_count = 0
        objects = _scene_data['sensors']
        for objk, surfaces in objects.items():
            for surfk, data in surfaces.items():
                surface_name = RendererMts3.encodeName(objk, surfk)
                
                # process AABB
                pos = None
                
                if 'center' in data:
                    pos = data['center']

                if pos is not None:
                    avgv += pos
                    minv = np.minimum(minv, pos)
                    maxv = np.maximum(maxv, pos)

                primitive = primitive_map[data['type']](data)

                if _use_batch:
                    mi_scene[f'{surface_name}-sensor'] = sensor
                    primitive[f'{surface_name}-shape-sensor-ref'] = {
                            'type': 'ref',
                            'id': f'{surface_name}-sensor',
                        }
                    batch_shapes.append((surface_name, primitive))
                else:
                    primitive['sensor'] = sensor
                    mi_scene[surface_name] = mi.load_dict(primitive)
                sensor_count += 1

        if _use_batch:
            batch_sensor = {
                'type': 'batch',
                'sampler': {
                    'type': 'independent',
                    'sample_count': _spp,
                },
                'film': {
                    'type': 'hdrfilm',
                    'width': sensor_count,
                    'height': 1,
                    'rfilter': {
                        'type': 'box',
                    },
                    'pixel_format': 'rgb',
                },
            }

            for (surface_name, primitive) in batch_shapes:
                batch_sensor[f'{surface_name}-batch-sensor-ref'] = {
                        'type': 'ref',
                        'id': f'{surface_name}-sensor',
                    }
                mi_scene[surface_name] = primitive

            mi_scene['dbatchsensor'] = batch_sensor

        # add obstacles
        objects = _scene_data['obstacles']

        for objk, surfaces in objects.items():
            for surfk, data in surfaces.items():
                surface_name = RendererMts3.encodeName(objk, surfk)
                type_id = data['type']
                func = primitive_map[type_id]
                mi_scene[surface_name] = mi.load_dict(func(data))


        if sensor_count < 1:
            logging.warn('No sensors defined.')
        else:
            avgv /= sensor_count

        return mi_scene, (minv, avgv, maxv), sensor_count

    @staticmethod
    def get_sun_direction( _lat, _long, _date):

        deg2rad = np.pi/180.0
        rad = lambda a: -a * deg2rad  + np.pi * 0.5 # convert azimut in degrees to radians: f(azimut) = - x * PI/180 + Pi/2

        azimut = get_azimuth(_lat, _long, _date)
        altitude = get_altitude(_lat, _long, _date)

        logging.debug(f"Date: {_date}, azimut: {azimut}, altitude: {altitude}")

        azimut_in_rad = rad(azimut)
        z, x = -np.sin(azimut_in_rad), np.cos(azimut_in_rad)
        y = np.sin(altitude * deg2rad)

        return [x, y, z]

    @staticmethod
    def get_sun(_direction, _power):
        return {
            'type': 'disk',
            'to_world': mi.ScalarTransform4f().look_at(origin=[v*100.0 for v in _direction], target=[0,0,0], up=[0,1,0]).scale(10.0),
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
        _dot = (_dot + 0.2) / 1.2 # hack to make sun light up already before horizon
        dot_scaler = np.max([0.0, _dot])

        sun_power = dot_scaler * _power * 5.0/6.0 # -1/6 for clowdy sky
        sky_power = dot_scaler * 10.0

        scene = {}
        scene['sun'] = RendererMts3.get_sun(_direction, sun_power)
        if not _disable_sky:
            scene['sky'] = RendererMts3.get_sky(sky_power)

        return scene, sun_power, sky_power

    @staticmethod
    def get_envmap(_array, _power):
        return {
            'type': 'envmap',
            'bitmap': mi.Bitmap(_array),
            'scale': _power
        }

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
    def test_sun(_display_callback):
        origin, target = RendererMts3.get_camera(2.0, 4.0)
        origin = [-2.0, 1.0, 1.0]
        mi_scene = RendererMts3.create_base_scene(default_ground_size, _spp=16, _cam_origin=origin, _cam_target=target)
        i = 0
        for h in range(5, 21):
            for m in range(0, 59, 5):
                datetime_str = '2022-08-23T%00d:%00d:00+02:00' % (h, m)
                logging.debug(datetime_str)
                sun_direction = RendererMts3.get_sun_direction(48.21, 16.36, datetime_str)
                sun_sky, _, _ = RendererMts3.get_sun_sky(sun_direction, 1000.0, _disable_sky=True)
                mi_scene = {**mi_scene, **sun_sky}
                RendererMts3.add_axis_spheres(mi_scene, [0,0,0])
                scene = mi.load_dict(mi_scene)
                img = mi.render(scene)
                RendererMts3.save_render_image(f'./tmp/sun_test_{i}.png', img)
                _display_callback(img)
                i+=1

    @staticmethod
    def test_sun_optimized(_display_callback):

        datetime_str = '2022-08-23T%00d:00:00+02:00' % 0
        sun_direction = RendererMts3.get_sun_direction(48.21, 16.36, datetime_str)
        sun_sky, _, _ = RendererMts3.get_sun_sky(sun_direction, 1000.0)
        origin, target = RendererMts3.get_camera(2.0, 4.0)
        mi_scene = RendererMts3.create_base_scene(default_ground_size, _spp=16, _cam_origin=origin, _cam_target=target)

        mi_scene = {**mi_scene, **sun_sky}
        RendererMts3.add_axis_spheres(mi_scene, [0,0,0])

        scene = mi.load_dict(mi_scene)
        params = mi.traverse(scene)

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
            _display_callback(img)

    @staticmethod
    def get_sun_radius(distance):
        half_sun_disk_angle = 0.26095 * 0.5
        distance = 100.0
        return np.tan(half_sun_disk_angle * np.pi / 180.0) * distance