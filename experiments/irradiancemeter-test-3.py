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

count = int(np.ceil(np.power(1000, 1./3.)))
print('#', count)

scale = 0.5 / count

positions = []
measurements = []

time_sum = 0

print('Loading scene | #irradiancemeter: %d ... ' % (count**3), end = ' ')

total_start = time.perf_counter_ns()
start = total_start

scene_data = prepare_scene(_for_rendering=False)
i = 0
for x in np.linspace(-(1-scale*2), (1-scale*2), count): 
    for y in np.linspace(-(1-scale*2), (1-scale*2), count):    
        for z in np.linspace(-(1-scale*2), (1-scale*2), count):
            pos = [x, y, z]    
            scene_data['probe-%d' % i] = probe(pos, add_sensor=True, col=None, emi=None)
            positions.append(pos)
            i+=1

scene = mi.load_dict(scene_data)

print('elapsed time: %.2f (sec.)' % ((time.perf_counter_ns()-start) * 1e-9))

print('Rendering | #irradiancemeter: %d ... ' % len(positions), end = ' ')
start = time.perf_counter_ns()

for i, _ in enumerate(positions):
    start = time.perf_counter_ns()    
    img = mi.render(scene, sensor=i)
    measurements.append(img.array)            
    time_sum += time.perf_counter_ns() - start

print('elapsed time: %.2f (sec.)' % ((time.perf_counter_ns()-start) * 1e-9))

print('Overall timings (#irradiancemeter: %d):' % len(positions))
print('- Avg. time %.3f (sec.) per sensor (count: %d)' % ((time_sum / count) * 1e-9, count))
print('- Total time: %.2f (sec.)' % ((time.perf_counter_ns()-total_start) * 1e-9))

print('Plotting ... ', end = ' ')

positions = np.array(positions)

data = prepare_scene(_for_rendering=True, _no_light=True, _res=512, _spp=512)

for i, (val, pos) in enumerate(zip(measurements, positions)):
    v = val.numpy()
    data['probe-%d' % i] = probe(pos, add_sensor=False, scale=scale, col=None, emi=(v*count*0.25).tolist())

scene = mi.load_dict(data)
img = mi.render(scene)

plt.figure()
plt.axis("off")
plt.imshow(mi.util.convert_to_bitmap(img))
print('done')
plt.show()
   