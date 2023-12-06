import numpy as np
import mitsuba as mi

mi.set_variant("scalar_rgb")

sun_area = {
    'type': 'rectangle',
    'to_world': mi.ScalarTransform4f().look_at([0, 0, 1], [0,0,0], [0,1,0]).scale(0.5), # -Z normal, unit area
    'emitter': {
            'type': 'area',
            'radiance': {
                'type': 'rgb',
                'value': 1.0,
            }
        }
    }

sun_directional = {
        'type': 'directional',
        'direction':  [0, 0, -1],
        'irradiance': {
            'type': 'rgb',
            'value': 1.0,
        }
    }

path_integrator = {
        'type': 'path',
    }

ptracer_integrator = {
        'type': 'ptracer',
        'samples_per_pass': 32
    }
  
make_scene = lambda integrator, sun, spp: {
    'type': 'scene',
    'integrator': integrator,
    'camera_base': {
        'type': 'perspective',
        'fov': 70,
        'to_world': mi.ScalarTransform4f.look_at(
            origin=[0,1,2],
            target=[0,0,0],
            up=[0, 0, 1]), # Z up
        'film_base': {
            'type': 'hdrfilm',
            'pixel_format': 'rgba',
            'width': 8,
            'height': 8,
            'rfilter': {
                'type': 'box',
            },
        },
        'sampler_id': {
            'type': 'independent',
            'sample_count': spp
        }
    },       
    'rect': {
        'type': 'rectangle',
        'to_world': mi.ScalarTransform4f().look_at([0,0,0], [0,0,1], [0,1,0]).scale(0.5), # +Z normal, unit area
        'bsdf': {
            'type': 'twosided',
            'material': {
                'type': 'diffuse',
                'reflectance': {
                    'type': 'rgb',
                    'value': [1, 1, 1]
                }
            }
        },
        'sensor1': {
            'type': 'irradiancemeter',
            'sampler': {
                'type': 'independent',
                'sample_count': spp,
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
        },
    }, 
    'sun': sun, 
}

irradiance_sensor_spp = 1024**2
camera_sensor_spp = 1024
camera_sensor = 0
irradiance_sensor = 1

tests = [
    ('path-area-irradiancemeter', path_integrator, sun_area, irradiance_sensor, irradiance_sensor_spp),    
    ('ptracer-area-irradiancemeter', ptracer_integrator, sun_area, irradiance_sensor, irradiance_sensor_spp),    
    ('path-directional-irradiancemeter', path_integrator, sun_directional, irradiance_sensor, irradiance_sensor_spp),    
    ('ptracer-directional-irradiancemeter', ptracer_integrator, sun_directional, irradiance_sensor, irradiance_sensor_spp),
]

irradiance = []

for (label, integrator, sun, sensor, spp) in tests:

    scene_dict = make_scene(integrator, sun, spp)
    scene = mi.load_dict(scene_dict)
    img = mi.render(scene, sensor=sensor, spp=spp)
        
    if sensor == 0:        
        mi.util.write_bitmap(f'{label}.png', img)
        irradiance.append((label, np.mean(img, axis=(0, 1))[:3], spp))
    else:
        irradiance.append((label, img.array, spp))


column1 = 'Combination'; column2 = 'RGB'; column3 = 'SPP'; width = 78
print('-'*width)
print(f'{column1:35} | {column2:28} | {column3:5}')
print('-'*width)
for label, arr, spp in irradiance:
    integrator, emitter, sensor = label.split('-')
    rgb_values = ','.join([f'{v:9.2f}' for v in arr])
    print(f'{sensor:15} {emitter:11} {integrator:7} |{rgb_values} | {spp:>7}')
