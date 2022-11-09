import os, logging, time, datetime
import numpy as np
from RendererMts3 import RendererMts3
from render import main
from binary_loader import load_path
import itertools    
import mitsuba as mi

def get_sensor_icosphere(_sensor, _color_array=None, _spp=128):
    from icosphere import icosphere
    nu = 8  # or any other integer
    vertices, _ = icosphere(nu)

    scene = {}

    for i, v in enumerate(vertices):    
        
        v=v*1.5 # size
        scale = 0.1
        color = [0.5, 0.5, 0.5] if _color_array is None else _color_array[i]
        key = f'obj{i}'

        scene[key] = {
            'type': 'disk',
            'to_world': mi.ScalarTransform4f().translate([0,2,0]).look_at(v, (v*2).tolist(), [0,1,0]).scale(scale),
            'material': {
                'type': 'diffuse',
                'reflectance': {
                    'type': 'rgb',
                    'value': color,
                },
            },
        }
        
        if _sensor:
            scene[key]['sensor'] = {
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

    return scene, vertices.shape[0]


def get_sensor_cubegrid(_sensor, _color_array=None, _spp=128):

    scene = {}

    count = 10
    x = np.linspace(-1., 1., count, endpoint=True)
    y = np.linspace(1., 3., count, endpoint=True)
    z = np.linspace(-1., 1., count, endpoint=True)
    xyz = list(itertools.product(x,y,z))

    for i, coord in enumerate(xyz):
        
        color = [0.5, 0.5, 0.5] if _color_array is None else _color_array[i]
        key = f'obj{i}'

        scene[key] = {
            'type': 'cube',
            'to_world': mi.ScalarTransform4f().translate(coord).scale(1.0/float(count)),
            'material': {
                'type': 'diffuse',
                'reflectance': {
                    'type': 'rgb',
                    'value': color,
                },
            },
        }
        
        if _sensor:
            scene[key]['sensor'] = {
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

    return scene, len(xyz)     

def test_sensors(ind, datetime_str, _spp=128):

    #geom_func = get_sensor_cubegrid
    geom_func = get_sensor_icosphere

    cam = {}
    cam['width'] = cam['height'] = 512
    cam['fov'] = fov = 70
    cam['origin'] = origin = np.array([-2,4,5])
    cam['target'] = target = np.array([0,2,0])

    obstacle = {
        'type': 'sphere',
        'to_world': mi.ScalarTransform4f().translate([2,2,2]).scale(1.0),
        'material': {
            'type': 'diffuse',
            'reflectance': {
                'type': 'rgb',
                'value': [0.5, 0.5, 0.5],
            },
        },
    }
    
    scene, sensor_count = geom_func(True, None, _spp)
    #scene['obst'] = obstacle

    renderer = RendererMts3(False)

    if 0:
        scene['env'] = {
            'type': 'constant',
            'radiance': {
                'type': 'rgb',
                'value': 10.0,
            }
        }    

        renderer.mi_base_scene = RendererMts3.create_base_scene(100.0, _spp=16, _cam_origin=origin.tolist(), _cam_target=target.tolist(), _fov=fov)
        renderer.sensor_count = len(xyz)
        merged_scene = {**renderer.mi_base_scene, **scene}    
        renderer.mi_scene = mi.load_dict(merged_scene)

    renderer.load_dict(scene, sensor_count, 48.21, 16.36, datetime_str, _spp, _cam=cam) 
    measurements = renderer.render(_spp)
     
    renderer.show_render(16, False, _save=f'./tmp/{str(ind).zfill(5)}-render.jpg')
    
    # normalize
    maxv = np.max(measurements)
    if maxv == 0.0:
        maxv = 1.0
    
    scene, _ = geom_func(False, [[v/maxv]*3 for v in measurements], _spp)    
    #scene['obst'] = obstacle

    scene['env'] = {
        'type': 'constant',
        'radiance': {
            'type': 'rgb',
            'value': 10.0,
        }
    }    

    renderer.mi_base_scene = RendererMts3.create_base_scene(100.0, _spp=16, _cam_origin=origin.tolist(), _cam_target=target.tolist(), _fov=fov)
    merged_scene = {**renderer.mi_base_scene, **scene}    
    renderer.mi_scene = mi.load_dict(merged_scene)
    renderer.show_render(16, _show=False, _save=f'./tmp/{str(ind).zfill(5)}-vis.jpg')

def day_cylce_test_sensors(_spp):

     # test day cycle
    start = datetime.datetime(2022, 4, 15, 8, 0, 0)
    end = datetime.datetime(2022, 4, 15, 20, 0, 0)
    step = datetime.timedelta(minutes=120)
    c = 1
    
    #test_sensor_cubegrid(c, start.isoformat()+'+01:00', 128); quit()
    while (start <= end):
        print(start)
        test_sensors(c, start.isoformat()+'+1:00', 1024)
        start += step
        c += 1

def test_day_cylce():

    h = []
    val = []

    hour = 22
    day = 2
    for i in range(23):
        datetime_str = '2022-02-%00dT%00d:00:00+02:00' % (day, hour)
        measurments = main('./data/t1999.mesh', 48.21, 16.36, datetime_str, 128, _show_render=False)        
        avg = np.mean(measurments)   
        h.append(hour)
        val.append(avg)     
        logging.debug(datetime_str, avg)
        hour = (hour + 1) % 24
        day += 1
    
    import matplotlib.pyplot as plt
    plt.plot(val)
    plt.show()

def test_directional():

    '''
    ScalarVector3f direction(dr::normalize(props.get<ScalarVector3f>("direction")));
    auto [up, unused] = coordinate_system(direction);

    m_to_world = ScalarTransform4f::look_at(0.0f, ScalarPoint3f(direction), up);
    '''
    import numpy as np
    import mitsuba as mi

    #mi.set_variant("cuda_ad_rgb")
    #mi.set_variant("llvm_ad_rgb")
    mi.set_variant("scalar_rgb")

    from mitsuba import ScalarTransform4f as T

    direction = [1, 1, 0]
    
    scene = mi.load_dict({
        'type': 'scene',
        'sun': {
                'type': 'directional',
                'direction':  direction,
                'irradiance': {
                    'type': 'rgb',
                    'value': 1.0,
                }
            }
        })

    params = mi.traverse(scene)
    logging.debug(params['sun.to_world']) 
    
    dn = np.linalg.norm(direction)
    direction = [v / dn for v in direction]
    up, _ = mi.coordinate_system(direction)
    logging.debug(T.look_at([0,0,0], direction, up))
    

if __name__ == "__main__":
    
    np.random.seed(0)

    logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
    FORMAT = '%(name)s :: %(levelname)-8s :: %(message)s'
    FORMAT = '%(levelname)-8s :: %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.INFO)
    day_cylce_test_sensors(128); quit()
    

    #load_path('./data/t126.mesh', True); quit()
    #test_directional(); quit()
    
    # test sun cycle
    #s = time.perf_counter_ns(); RendererMts3.test_sun(); logging.debug('classic', time.perf_counter_ns()-s); quit()
    #s = time.perf_counter_ns(); RendererMts3.test_sun_optimized(); logging.debug('optimized', time.perf_counter_ns()-s); quit()
    
    #main('./data/t126.mesh', 48.21, 16.36, "2022-08-23T10:34:48+00:00", 128, _verbose=True, _show_render=True); quit()

    if 0:
        show_render = True
        # test MESH scene simulation / rendering
        logging.info('Mesh test:')
        main('./data/t1999.mesh', 48.21, 16.36, "2022-08-23T10:34:48+00:00", 128, _verbose=True, _show_render=show_render)
        # test PRIMITIVE scene simulation / rendering
        logging.info('Primitive test:')
        main('./data/t1999.prim', 48.21, 16.36, "2022-08-23T10:34:48+00:00", 128, _verbose=True, _show_render=show_render)
        quit()


    # test day cycle
    #test_day_cylce(); quit()
    start = datetime.datetime(2022, 1, 30)
    end = datetime.datetime(2021, 2, 2)
    step = datetime.timedelta(minutes=30)
    c = 1

    print(start >= end)
    while (start >=  end):
        print(start)
        main('./data/t1999.prim', 48.21, 16.36, start.isoformat()+'+01:00', 4, _save_render=f'./{str(c).zfill(5)}.jpg')
        start += step
        c += 1

