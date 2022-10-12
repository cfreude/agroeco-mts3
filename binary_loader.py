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

    [format] = struct.unpack('B', binary_array[0:1]); # uint8

    if _verbose:
        print(f'binary file format: {format}')
    
    map = {
        1: load_binary_mesh,        
        2: load_binary_primitives,
    }

    if format in map:
        return map[format](binary_array, _verbose, 1) # offset 1 to skip format byte
    else:
        warn(f"Invalid format: {format}, expected any of {list(map.keys())}, Falling back to format: 1")
        return map[1](binary_array, _verbose, 0)


def load_binary_mesh(binary_array, _verbose=False, _offset=0):
    """
    #INDEXED DATA
    uint8 version
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
    i = _offset
    [entitiesCount] = struct.unpack('I', binary_array[i:i+4]); i+=4 # uint32
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
    [pointsCount] = struct.unpack('I', binary_array[i:i+4]); i+=4 # uint32
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


def load_binary_primitives(binary_array, _verbose=False, _offset=0):
    """
    #Primitives Binary Serialization
    uint8 version = 2
    uint32 entitiesCount
        #foreach ENTITY
        uint32 surfacesCount
            #foreach SURFACE (for now, each surface is an irradiancemeter)
                uint8 primitiveType    (1 = disk, 2 = cylinder/stem, 4 = sphere/shoot, 8 = rectangle/leaf)
                #case disk (currently not used)
                    float32 matrix 4x3 (the bottom row is always 0 0 0 1)
                #case cylinder
                    float32 length
                    float32 radius
                    float32 matrix 4x3 (the bottom row is always 0 0 0 1)
                #case sphere
                    3xfloat32 center
                    float32 radius
                #case rectangle
                    float32 matrix 4x3 (the bottom row is always 0 0 0 1)
    """

    raise NotImplemented

    scene = {}
    i = _offset
    [entitiesCount] = struct.unpack('I', binary_array[i:i+4]); i+=4 # uint32
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
    [pointsCount] = struct.unpack('I', binary_array[i:i+4]); i+=4 # uint32
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
