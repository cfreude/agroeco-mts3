import mitsuba as mi
mi.set_variant("scalar_rgb")

import numpy as np
from icosphere import icosphere

def built_geometry(_shape, _albedo_array=None, _sensor_spp=None):

    vertices, _ = icosphere(8)

    objs = {}

    for i, v in enumerate(vertices):    
        
        v *= 1.0 # scale icosphere vertices
        scale = 0.07 # per vertex object scale

        color = np.array([0.5, 0.5, 0.5]) if _albedo_array is None else _albedo_array[i]
        key = f'obj{i}'

        up = [0,0,1]
        if np.abs(np.dot(v, [0,0,1])) > 0.95:
            up = [0,1,0]

        objs[key] = {
            'type': _shape,
            'to_world': mi.ScalarTransform4f().look_at(v, (v*2).tolist(), up).scale(scale),
            'material': {
                'type': 'diffuse',
                'reflectance': {
                    'type': 'rgb',
                    'value': color.tolist(),
                },
            },
        }
        
        if _sensor_spp is not None:
            objs[key]['sensor'] = {
                'type': 'irradiancemeter',
                'sampler': {
                    'type': 'independent',
                    'sample_count': _sensor_spp
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

    return objs, vertices.shape[0]


base_scene = {
    'type': 'scene',
    'integrator': {
        'type': 'path',
    },
    'camera': {
        'type': 'perspective',
        'fov': 70,
        'to_world': mi.ScalarTransform4f.look_at([0,-3,0], [0,0,0], [0,0,1]),
        'film': {
            'type': 'hdrfilm',
            'pixel_format': 'rgba',
            'width': 512,
            'height': 512,
        },
        'sampler': {
            'type': 'independent',
            'sample_count': 128
        }
    }, 
}

emitter = {
    'emitter' : {
        'type': 'directional',
        'direction':  [-1, 0.1, -1],
        'irradiance': {
            'type': 'rgb',
            'value': 1.0,
        }
    }
}

shape = 'sphere'

sensors, sensor_count = built_geometry(_shape=shape, _sensor_spp = 128)
scene_dict = {**base_scene, **emitter, **sensors}
scene = mi.load_dict(scene_dict)

# render camera senor
img = mi.render(scene)
mi.util.write_bitmap(f'irradiancemeter-{shape}-rendering.png', img)

# render irradiancemeters
measurements = []
for i in range(sensor_count):
    img = mi.render(scene, sensor=i+1, spp=128)
    measurements.append(np.array(img.array))

emitter = {
    'emitter' : {
        'type': 'constant',
        'radiance': {
            'type': 'rgb',
            'value': 1.0,
        }
    }
}

sensors, sensor_count = built_geometry(_shape=shape, _albedo_array=measurements)
scene_dict = {**base_scene, **emitter, **sensors}
scene = mi.load_dict(scene_dict)

# render camera senor
img = mi.render(scene)
mi.util.write_bitmap(f'irradiancemeter-{shape}-visualisation.png', img)