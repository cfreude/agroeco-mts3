import mitsuba as mi

mi.set_variant("scalar_rgb")

area_emitter = {
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

directional_emitter = {
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

make_scene = lambda integrator, emitter, spp: {
    'type': 'scene',
    'integrator': integrator,
    'rect': {
        'type': 'rectangle',
        'to_world': mi.ScalarTransform4f().look_at([0,0,0], [0,0,1], [0,1,0]).scale(0.5), # +Z normal, unit area
        'material': {
            'type': 'diffuse',
            'reflectance': {
                'type': 'rgb',
                'value': [1, 1, 1]
            }
        },
        'sensor': {
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
    'emitter': emitter, 
}

spp = 1024**2

combinations = [
    ('path-area', path_integrator, area_emitter),    
    ('ptracer-area', ptracer_integrator, area_emitter),    
    ('path-directional', path_integrator, directional_emitter),    
    ('ptracer-directional', ptracer_integrator, directional_emitter),
]

irradiance = []

for (label, integrator, emitter) in combinations:
    scene_dict = make_scene(integrator, emitter, spp)
    scene = mi.load_dict(scene_dict)
    img = mi.render(scene, spp=spp)
    irradiance.append((label, img.array))

# print results
column1 = 'Combination'; column2 = f'RGB Irradiance, spp: {spp}'; width = 50
print('-'*width)
print(f'{column1:19} | {column2:28}')
print('-'*width)
for label, irr in irradiance:
    integrator, emitter = label.split('-')
    rgb_values = ','.join([f'{v:9.2f}' for v in irr])
    print(f'{emitter:11} {integrator:7} |{rgb_values}')
