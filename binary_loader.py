from distutils.log import error, warn
from pprint import pprint
import struct

def load_path(_path, _verbose=False, _return_binary=False):

    binary_array = []

    try:
        f = open(_path, 'rb')
        while True:
            binarycontent = f.read(-1)
            if not binarycontent:
                break
            binary_array.append(binarycontent)
    except IOError:
        print('Error While Opening the file!')

    if len(binary_array) < 1:
        error("Data array length < 1")
    elif len(binary_array) > 1:
        warn("Data array length > 1")

    binary_array = binary_array[0]

    if _verbose:
        print(binary_array)
        print('#bytes:', len(binary_array))

    if _return_binary:
        return binary_array
    else:
        return load_binary(binary_array, _verbose)


def load_binary(binary_array, _verbose=False):
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
    #scene['entitiesCount'] = entitiesCount
    scene['entities'] = {}
    if _verbose:
        print('entitiesCount:', entitiesCount, '| byte index:', i)
    for e in range(entitiesCount):
        [surfacesCount] = struct.unpack('I', binary_array[i:i+4]); i+=4 # uint32
        entity_key = 'entitiy%d'%e
        scene['entities'][entity_key] = {}#'surfacesCount': surfacesCount }
        if _verbose:
            print(entity_key, '| surfacesCount:', surfacesCount, '| byte index:', i)
        for s in range(surfacesCount):
            [trianglesCount] = struct.unpack('B', binary_array[i:i+1]); i+=1 # uint8
            surface_key = 'surface%d'%s
            scene['entities'][entity_key][surface_key] = {}#'trianglesCount': trianglesCount }
            if _verbose:
                print(surface_key, '| trianglesCount:', trianglesCount, '| byte index:', i)
            triangle_indices = []
            for t in range(trianglesCount):
                [ind0, ind1, ind2] = struct.unpack('III', binary_array[i:i+12]); i+=12 # 3x uint32
                index_tripplet = [ind0, ind1, ind2]
                triangle_indices.append(index_tripplet)
                if _verbose:
                    print('index #%d' % t, '| (ind0, ind1, ind2):', index_tripplet, '| byte index:', i)
            scene['entities'][entity_key][surface_key] = triangle_indices
            #quit()
    [pointsCount] = struct.unpack('I', binary_array[i:i+4]); i+=4 # uint32
    #scene['pointsCount'] = pointsCount
    if _verbose:
        print('pointsCount:', pointsCount, '| byte index:', i)
    point_array = []
    for p in range(pointsCount):
        [x, y, z] = struct.unpack('fff', binary_array[i:i+12]); i+=12 # 3x float32
        point = [x, y, z]
        point_array.append(point)
        if _verbose:
            print('point #%d' % p, '| (x, y, z):', point, '| byte index:', i)
    scene['pointArray'] = point_array

    if _verbose:
        pprint(scene)

    return scene