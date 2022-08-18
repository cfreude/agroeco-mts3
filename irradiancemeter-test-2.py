from turtle import color
import mitsuba as mi
import drjit as dr
from matplotlib import pyplot as plt
import numpy as np
import time

print('available variants:', mi.variants())

#mi.set_variant("cuda_ad_rgb")
#mi.set_variant("llvm_ad_rgb")
mi.set_variant("scalar_rgb")

from mitsuba import ScalarTransform4f as T

#scene = mi.load_file('./scene-sensors.xml')
#params = mi.traverse(scene)
#print(params)
#quit()

def probe(loc, add_sensor, scale=0.05, col=None, emi=None):
    box = {
        'type': 'sphere',
        'to_world': T.translate(loc).scale(scale)
    }
    if col:
        box['bsdf'] = {
            'type': 'diffuse',
            'reflectance': {'type': 'rgb', 'value': col},
        }
    if emi:
        box['emitter'] = {
            'type':'area',
            'radiance': {
                'type': 'rgb',
                'value': emi,
            }
        }
    if add_sensor:
        box['sensor'] = {
            'type': 'irradiancemeter',   
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
    return box

def prepare_scene(_for_rendering=True, _no_light=False, _res=128, _spp=128):

    data = mi.cornell_box()    
    
    del data['small-box']
    del data['large-box']
    del data['light']

    if not _no_light:
        data['green-wall']['emitter'] = {
                'type':'area',
                'radiance': {
                    'type': 'rgb',
                    'value': [0.0, 0.8, 0.0],
                }
            }

        data['red-wall']['emitter'] = {
                'type':'area',
                'radiance': {
                    'type': 'rgb',
                    'value': [0.8, 0.0, 0.0],
                }
            }
    
    data['integrator']['max_depth'] = -1

    if _for_rendering:        
        data['sensor']['sampler']['sample_count'] = _spp
        data['sensor']['film']['rfilter']['type'] = 'tent'
        data['sensor']['film']['width'] = _res
        data['sensor']['film']['height'] = _res
    else:
        del data['sensor']

    return data

scene_data = prepare_scene(_for_rendering=False)
scene_data['probe'] = probe([0,0,0], add_sensor=True, col=None, emi=None)

#for k, v in scene_data.items():
#    print(k, v)

scene = mi.load_dict(scene_data)
params = mi.traverse(scene)

#print(params)
#print(params['probe.to_world'])
#quit()

count = 51
scale = 0.5 / count

positions = []
measurements = []

time_sum = 0
total_start = time.perf_counter_ns()

for x in np.linspace(-(1-scale*2), (1-scale*2), count):
    
    #for y in np.linspace(-(1-scale*2), (1-scale*2), count):    
    #for z in np.linspace(-(1-scale*2), (1-scale*2), count):
    y = z = 0

    start = time.perf_counter_ns()

    pos = [x, y, z]
    params['probe.to_world'] = T.translate(pos).scale(scale)
    params.set_dirty('probe.to_world')
    params.update()
    img = mi.render(scene)

    positions.append(pos)
    measurements.append(img.array)
            
    time_sum += time.perf_counter_ns() - start

print('total time: %.2f (sec.)' % ((time.perf_counter_ns()-total_start) * 1e-9))
print('avg. time %.3f (sec.) per sensor (count: %d)' % ((time_sum / count) * 1e-9, count))

positions = np.array(positions)

fig = plt.figure()
ax = fig.add_subplot(projection='3d')

data = prepare_scene(_for_rendering=True, _no_light=True, _res=128, _spp=128)

for i, (val, pos) in enumerate(zip(measurements, positions)):
    v = val.numpy()
    ax.scatter(pos[0], pos[1], pos[2], s=50, marker='o', color=(v/(1.0+v)).tolist())
    data['probe-%d' % i] = probe(pos, add_sensor=False, scale=scale, col=None, emi=(v*0.1).tolist())

scene = mi.load_dict(data)
img = mi.render(scene)

plt.figure()
plt.axis("off")
plt.imshow(mi.util.convert_to_bitmap(img));
plt.show()
   