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
        print(f'Loading binary format: {format}')
        return map[format](binary_array, _verbose, 1) # offset 1 to skip format byte
    else:
        warn(f"Invalid format: {format}, expected any of {list(map.keys())}, Falling back to format: 1")
        return map[1](binary_array, _verbose, 0)


def load_mesh_entities(binary_array, _prefix, i, _verbose=False):
    entities = {}
    [entitiesCount] = struct.unpack('I', binary_array[i:i+4]); i+=4 # uint32
    if _verbose:
        print('entitiesCount:', entitiesCount, '| byte index:', i)
    for e in range(entitiesCount):
        [surfacesCount] = struct.unpack('I', binary_array[i:i+4]); i+=4 # uint32
        entity_key = f"{_prefix}-entitiy{e}"
        entities[entity_key] = {}
        if _verbose:
            print(entity_key, '| surfacesCount:', surfacesCount, '| byte index:', i)
        for s in range(surfacesCount):
            [trianglesCount] = struct.unpack('B', binary_array[i:i+1]); i+=1 # uint8
            surface_key = f"surface{s}"
            if _verbose:
                print(surface_key, '| trianglesCount:', trianglesCount, '| byte index:', i)
            triangle_indices = []
            for t in range(trianglesCount):
                [ind0, ind1, ind2] = struct.unpack('III', binary_array[i:i+12]); i+=12 # 3x uint32
                index_tripplet = [ind0, ind1, ind2]
                triangle_indices.append(index_tripplet)
                if _verbose:
                    print('index #%d' % t, '| (ind0, ind1, ind2):', index_tripplet, '| byte index:', i)
            entities[entity_key][surface_key] = triangle_indices

    return entities, i

def load_binary_mesh(binary_array, _verbose=False, _offset=0):
    """
    uint8 version = 2
    #OBSTACLES
    uint32 entitiesCount
    foreach ENTITY
        uint32 surfacesCount
        foreach SURFACE
            uint8 primitiveType    #1 = disk, 2 = cylinder(stem), 4 = sphere(shoot), 8 = rectangle(leaf)
            #case disk
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
    #SENSORS
    uint32 entitiesCount
    foreach ENTITY
        uint32 surfacesCount
        foreach SURFACE
            uint8 primitiveType    #1 = disk, 2 = cylinder(stem), 4 = sphere(shoot), 8 = rectangle(leaf)
            #case disk
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

    scene = {}
    i = _offset
    scene['obstacles'], i = load_mesh_entities(binary_array, 'obstacle', i, _verbose)
    scene['sensors'], i = load_mesh_entities(binary_array, 'sensor', i, _verbose)
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
    #pprint(scene)
    return scene


def disk(_from, _bin_arr):
    '''
    uint8 primitiveType    (1 = disk, 2 = cylinder/stem, 4 = sphere/shoot, 8 = rectangle/leaf)
    #case disk (currently not used)
        float32 matrix 4x3 (the bottom row is always 0 0 0 1)
    '''
    data = {'type': 1}
    to = _from + 4*12
    data['matrix'] = struct.unpack('f'*12, _bin_arr[_from:to]);
    return data, to


def cylinder(_from, _bin_arr):
    '''
    uint8 primitiveType    (1 = disk, 2 = cylinder/stem, 4 = sphere/shoot, 8 = rectangle/leaf)
    #case cylinder
        float32 length
        float32 radius
        float32 matrix 4x3 (the bottom row is always 0 0 0 1)
    '''
    data = {'type': 2}
    to = _from + 4
    data['length'] = struct.unpack('f', _bin_arr[_from:to])
    _from = to; to += 4
    data['radius'] = struct.unpack('f', _bin_arr[_from:to])
    _from = to; to += 4*12
    data['matrix'] = struct.unpack('f'*12, _bin_arr[_from:to])
    return data, to


def sphere(_from, _bin_arr):
    '''
    uint8 primitiveType    (1 = disk, 2 = cylinder/stem, 4 = sphere/shoot, 8 = rectangle/leaf)
    #case sphere
        3xfloat32 center
        float32 radius
    '''
    data = {'type': 4}
    to = _from + 12
    data['length'] = struct.unpack('fff', _bin_arr[_from:to])
    _from = to; to += 4
    data['radius'] = struct.unpack('f', _bin_arr[_from:to])
    return data, to


def rectangle(_from, _bin_arr):
    '''
    uint8 primitiveType    (1 = disk, 2 = cylinder/stem, 4 = sphere/shoot, 8 = rectangle/leaf)
    #case rectangle
        float32 matrix 4x3 (the bottom row is always 0 0 0 1)
    '''
    data = {'type': 8, "_i": _from}
    to = _from + 4*12
    data['matrix'] = struct.unpack('f'*12, _bin_arr[_from:to])
    return data, to


primitive_map = {
    1: disk,
    2: cylinder,
    4: sphere,
    8: rectangle,
}

def load_primitve_entities(binary_array, _prefix, i, _verbose=False):
    '''
    uint32 entitiesCount
    foreach ENTITY
        uint32 surfacesCount
        foreach SURFACE
            uint8 primitiveType    #1 = disk, 2 = cylinder(stem), 4 = sphere(shoot), 8 = rectangle(leaf)
            #case disk
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
    '''
    entities = {}
    [entitiesCount] = struct.unpack('I', binary_array[i:i+4]); i+=4 # uint32
    if _verbose:
        print('entitiesCount:', entitiesCount, '| byte index:', i)
    for e in range(entitiesCount):
        [surfacesCount] = struct.unpack('I', binary_array[i:i+4]); i+=4 # uint32
        entity_key = f"{_prefix}-entitiy{e}"
        entities[entity_key] = {}
        if _verbose:
            print(entity_key, '| surfacesCount:', surfacesCount, '| byte index:', i)
        for s in range(surfacesCount):
            surface_key = f"surface{s}"

            [primitiveType] = struct.unpack('B', binary_array[i:i+1]); i+=1 # uint8

            if _verbose:
                print(surface_key, '| primitiveType:', primitiveType, '| byte index:', i)

            data, i = primitive_map[primitiveType](i, binary_array)
            print(data, '| byte index:', i)
            entities[entity_key][surface_key] = data

    return entities, i

def load_binary_primitives(binary_array, _verbose=False, _offset=0):

    # ROW MAJOR MATRICES
    """
    uint8 version = 2
    #OBSTACLES
    uint32 entitiesCount
    foreach ENTITY
        uint32 surfacesCount
        foreach SURFACE
            uint8 primitiveType    #1 = disk, 2 = cylinder(stem), 4 = sphere(shoot), 8 = rectangle(leaf)
            #case disk
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
    #SENSORS
    uint32 entitiesCount
    foreach ENTITY
        uint32 surfacesCount
        foreach SURFACE
            uint8 primitiveType    #1 = disk, 2 = cylinder(stem), 4 = sphere(shoot), 8 = rectangle(leaf)
            #case disk
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

    scene = {}
    i = _offset
    scene['obstacles'], i = load_primitve_entities(binary_array, 'obstacle', i, _verbose)
    scene['sensors'], i = load_primitve_entities(binary_array, 'sensor', i, _verbose)

    if _verbose:
        pprint(scene)

    raise NotImplementedError

    return scene
