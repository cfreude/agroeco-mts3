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


def unpack(_i, _bin_arr, _str, _bytePerType=4, _print_name=None):
    offset = len(_str) * _bytePerType 
    val = struct.unpack(_str, _bin_arr[_i:_i+offset])
    if len(_str) == 1: # extract single value from tuple
        val = val[0]
    if _print_name is not None:
        print(f"{_print_name}: {val} | index: {_i}")
    return val, _i + offset


def disk(_i, _bin_arr):
    '''
    uint8 primitiveType    (1 = disk, 2 = cylinder/stem, 4 = sphere/shoot, 8 = rectangle/leaf)
    #case disk (currently not used)
        float32 matrix 4x3 (the bottom row is always 0 0 0 1)
    '''  
    data = {'type': 1} 
    data['matrix'], _i = unpack(_i, _bin_arr, 'f'*12, _print_name='disk.matrix') 
    return data, _i


def cylinder(_i, _bin_arr):
    '''
    uint8 primitiveType    (1 = disk, 2 = cylinder/stem, 4 = sphere/shoot, 8 = rectangle/leaf)
    #case cylinder
        float32 length
        float32 radius
        float32 matrix 4x3 (the bottom row is always 0 0 0 1)
    '''
    data = {'type': 2}
    data['length'], _i = unpack(_i, _bin_arr, 'f', _print_name='cylinder.length')                            
    data['radius'], _i = unpack(_i, _bin_arr, 'f', _print_name='cylinder.radius')                         
    data['matrix'], _i = unpack(_i, _bin_arr, 'f'*12, _print_name='cylinder.matrix')             
    return data, _i


def sphere(_i, _bin_arr):
    '''
    uint8 primitiveType    (1 = disk, 2 = cylinder/stem, 4 = sphere/shoot, 8 = rectangle/leaf)
    #case sphere
        3xfloat32 center
        float32 radius
    '''
    data = {'type': 4}
    data['center'], _i = unpack(_i, _bin_arr, 'fff', _print_name='sphere.center')             
    data['radius'], _i = unpack(_i, _bin_arr, 'f', _print_name='sphere.radius')               
    return data, _i


def rectangle(_i, _bin_arr):
    '''
    uint8 primitiveType    (1 = disk, 2 = cylinder/stem, 4 = sphere/shoot, 8 = rectangle/leaf)
    #case rectangle
        float32 matrix 4x3 (the bottom row is always 0 0 0 1)
    '''
    data = {'type': 8}
    data['matrix'], _i = unpack(_i, _bin_arr, 'f'*12, _print_name='rectangle.matrix')      
    return data, _i


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
    entitiesCount, i = unpack(i, binary_array, 'I', _print_name='entitiesCount' if _verbose else None)
    for e in range(entitiesCount):
        surfacesCount, i = unpack(i, binary_array, 'I', _print_name='surfacesCount' if _verbose else None)
        entity_key = f"{_prefix}-entitiy{e}"
        entities[entity_key] = {}
        for s in range(surfacesCount):            
            surface_key = f"surface{s}"
            primitiveType, i = unpack(i, binary_array, 'B', 1, _print_name='primitiveType' if _verbose else None)
            data, i = primitive_map[primitiveType](i, binary_array)
            #print(data, '| byte index:', i)
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
