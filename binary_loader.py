from distutils.log import error, warn
import imp
import struct
from pprint import pprint

path = "./t150.mesh"

binary_array = []

try:
    f = open(path, 'rb')
    while True:
        binarycontent = f.read(-1)  
        if not binarycontent:
            break
        binary_array.append(binarycontent)
except IOError:
    print('Error While Opening the file!')

print()
print(binary_array)

if len(binary_array) < 1:    
    error("Data array length < 1")
elif len(binary_array) > 1:
    warn("Data array length > 1")

binary_array = binary_array[0]
print(binary_array)
print('#bytes:', len(binary_array))

"""
#INDEXED DATA
uint32 entitiesCount
    #foreach ENTITY
    uint32 surfacesCount
        #foreach SURFACE (for now, each surface is an irradiancemeter)
        uint8 trianglesCount
        #foreach TRIANGLE
            uint32 index0
            uint32 index1
            uint32 index2
#POINTS DATA
uint32 pointsCount
    #foreach POINT
    float32 x
    float32 y
    float32 z
"""

scene = {}
i = 0
[entitiesCount] = struct.unpack('I', binary_array[i:i+4]); i+=4 # uint32
scene['entitiesCount'] = entitiesCount
print('entitiesCount:', entitiesCount, '|', i)
for e in range(entitiesCount):
    [surfacesCount] = struct.unpack('I', binary_array[i:i+4]); i+=4 # uint32
    entity_key = 'entitiy%d'%e
    scene[entity_key] = {'surfacesCount': surfacesCount }    
    print(entity_key, '| surfacesCount:', surfacesCount, '|', i)
    for s in range(surfacesCount):
        [trianglesCount] = struct.unpack('H', binary_array[i:i+2]); i+=2 # uint8
        surface_key = 'surface%d'%s
        scene[entity_key][surface_key] = {'trianglesCount': trianglesCount }        
        print(surface_key, '| trianglesCount:', trianglesCount, '|', i)
        triangle_indices = []
        for t in range(trianglesCount):
            [ind0, ind1, ind2] = struct.unpack('III', binary_array[i:i+12]); i+=12 # 3x uint32
            index_tripplet = [ind0, ind1, ind2]
            triangle_indices.append(index_tripplet)            
            print('index #%d' % t, '| (ind0, ind1, ind2):', index_tripplet, '|', i)
        scene[entity_key][surface_key]['indexArray'] = triangle_indices
[pointsCount] = struct.unpack('fff', binary_array[i:i+4]); i+=4 # uint32
scene['pointsCount'] = pointsCount
print('pointsCount:', pointsCount, '|', i)
point_array = []
for p in range(pointsCount):
    [x, y, z] = struct.unpack('I', binary_array[i:i+12]); i+=12 # 3x float32
    point = [x, y, z]
    point_array.append(point)
    print('point #%d' % p, '| (x, y, z):', point, '|', i)
scene['pointArray'] = point_array

pprint(scene)