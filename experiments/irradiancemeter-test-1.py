from turtle import color
import mitsuba as mi
import drjit as dr
from matplotlib import pyplot as plt
import numpy as np
import time

print(mi.variants())

#mi.set_variant("cuda_ad_rgb")
#mi.set_variant("llvm_ad_rgb")
mi.set_variant("scalar_rgb")

from mitsuba import ScalarTransform4f as T

#data = mi.cornell_box()
#xml_str = mi.xml.dict_to_xml(data, "./scene.xml")

sampler_dict =  {
    'type': 'independent',
    'sample_count': 1024
}

sensor_dict = {
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

def box(id, x, y, z, s, scale=0.05, col=[0.8, 0.8, 0.8], emi=None):
    d = {
        'type': 'sphere',
        'to_world': T.translate([x, y, z]).scale(scale),
        'bsdf': {
            'type': 'diffuse',
            'reflectance': {'type': 'rgb', 'value': col},
        },
    }
    if emi:
        d['emitter'] = {
            'type':'area',
            'radiance': {
                'type': 'rgb',
                'value': emi,
            }
        }
    if s:
        d['sensor'] = sensor_dict
    return d

#params = mi.traverse(mi.load_dict(data))
#print(params)

count = 25
step = 0.9 / count
render_camera = False

values = []
positions = []
iters = (len(range(-count, count+1)))**1

time_sum = 0

total_start = time.perf_counter_ns()

for j in range(iters):
    start = time.perf_counter_ns()

    data = mi.cornell_box()    
    
    #print(data)

    del data['small-box']
    del data['large-box']
    del data['light']

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

    xyz = None
    i = 0
    for x in range(-count, count+1):
        #for y in range(-count, count+1):
        #for z in range(-count, count+1):
        y = z = 0
        data['cube-%d'%i] = box(i, x*step, y*step, z*step, (i==j) and (not render_camera), scale=step*0.25)
        if(i==j):
            xyz = [x,y,z]
        i+=1
    
    #print(data)

    data['integrator']['max_depth'] = -1

    if render_camera:        
        data['sensor']['sampler']['sample_count'] = 256
        data['sensor']['film']['rfilter']['type'] = 'tent'
        data['sensor']['film']['width'] = 512
        data['sensor']['film']['height'] = 512
    else:
        del data['sensor']
        data['sampler'] = sampler_dict
            
    scene = mi.load_dict(data)
    img = mi.render(scene)
    print('--')

    if render_camera:        
        plt.axis("off")
        plt.imshow(mi.util.convert_to_bitmap(img));
        plt.show()
        quit()
    else:
        values.append(img.array)
        positions.append(xyz)

    time_sum += time.perf_counter_ns() - start

print('total time: %.2f (sec.)' % ((time.perf_counter_ns()-total_start) * 1e-9))
print('avg. time %.3f (sec.) per sensor (count: %d)' % ((time_sum / iters) * 1e-9, iters))

positions = np.array(positions)

fig = plt.figure()
ax = fig.add_subplot(projection='3d')

for val, pos in zip(values, positions):
    v = val.numpy()
    ax.scatter(pos[0], pos[1], pos[2], s=50, marker='o', color=(v/(1.0+v)).tolist())

data = mi.cornell_box()    
del data['small-box']
del data['large-box']
del data['light']

i = 0
for x in range(-count, count+1):
    #for y in range(-count, count+1):
    #for z in range(-count, count+1):
    y = z = 0
    val = values[i].numpy()
    data['cube-%d'%i] = box(i, x*step, y*step, z*step, False, scale=step*0.25, col=(1.0/(1.0+val)).tolist(), emi=(val*2).tolist())
    i+=1

data['integrator']['max_depth'] = -1
       
data['sensor']['sampler']['sample_count'] = 256
data['sensor']['film']['rfilter']['type'] = 'tent'
data['sensor']['film']['width'] = 512
data['sensor']['film']['height'] = 512

scene = mi.load_dict(data)
img = mi.render(scene)

plt.figure()
plt.axis("off")
plt.imshow(mi.util.convert_to_bitmap(img));
plt.show()
   