import logging
from pprint import pprint
import struct

from matplotlib.pyplot import loglog

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
        logging.error('Error While Opening the file!')

    if len(binary_array) < 1:
        logging.error("Data array length < 1")
    elif len(binary_array) > 1:
        logging.warn("Data array length > 1")

    binary_array = binary_array[0]

    logging.debug(f'{binary_array}')
    logging.debug(f'#bytes: {len(binary_array)}')

    if _return_binary:
        return binary_array
    else:
        return load_binary(binary_array, _verbose)


def load_binary(binary_array, _verbose=False):

    [format] = struct.unpack('B', binary_array[0:1]); # uint8

    logging.debug(f'binary file format: {format}')

    map = {
        1: load_binary_mesh,
        2: load_binary_primitives,
    }

    if format in map:
        return map[format](binary_array, _verbose, 1) # offset 1 to skip format byte
    else:
        logging.warn(f"Invalid format: {format}, expected any of {list(map.keys())}, Falling back to format: 1")
        return map[1](binary_array, _verbose, 0)


def unpack(_i, _bin_arr, _str, _bytePerType=4, _print_name=None):
    offset = len(_str) * _bytePerType 
    val = struct.unpack(_str, _bin_arr[_i:_i+offset])
    if len(_str) == 1: # extract single value from tuple
        val = val[0]
    else:
        val = list(val)
    if _print_name:
        logging.debug(f"{_print_name}: {val} | index: {_i}")
    return val, _i + offset


def load_mesh_entities(binary_array, _prefix, i, _verbose=False):
    entities = {}
    entitiesCount, i = unpack(i, binary_array, 'I', _print_name=f"{_prefix}-entitiesCount") # uint32
    for e in range(entitiesCount):
        entity_key = f"{_prefix}-entitiy{e}"
        surfacesCount, i = unpack(i, binary_array, 'I', _print_name=f"{entity_key}-surfacesCount") # uint32
        entities[entity_key] = {}
        for s in range(surfacesCount):
            surface_key = f"surface{s}"
            trianglesCount, i = unpack(i, binary_array, 'B', 1, _print_name=f"{surface_key}-trianglesCount") # uint8
            triangle_indices = []
            for t in range(trianglesCount):
                index_tripplet, i = unpack(i, binary_array, 'III', _print_name='index_tripplet')  # 3x uint32
                triangle_indices.append(index_tripplet)
                [ind0, ind1, ind2] = index_tripplet
                logging.debug(f'{surface_key}-triangle-index #{t}, | ({ind0}, {ind1}, {ind2}), | byte index: {i}')
            entities[entity_key][surface_key] = triangle_indices

    return entities, i


def load_binary_mesh(binary_array, _verbose=False, _offset=0):
    """
    uint8 version = 1
	#INDEXED DATA FOR OBSTACLES
	uint32 entitiesCount
	foreach ENTITY
		uint32 surfacesCount
		foreach SURFACE
			uint8 trianglesCount
			foreach TRIANGLE
				uint32 index0
				uint32 index1
				uint32 index2
	#INDEXED DATA FOR SENSORS
	uint32 entitiesCount
	foreach ENTITY
		uint32 surfacesCount
		foreach SURFACE
			uint8 trianglesCount
			foreach TRIANGLE
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

    scene = {'format': 1}
    i = _offset
    scene['obstacles'], i = load_mesh_entities(binary_array, 'obstacle', i, _verbose)
    scene['sensors'], i = load_mesh_entities(binary_array, 'sensor', i, _verbose)
    pointsCount, i = unpack(i, binary_array, 'I', _print_name='pointsCount') # uint32
    point_array = []
    for p in range(pointsCount):
        point, i = unpack(i, binary_array, 'fff') # 3x float32        
        point_array.append(point)
        [x, y, z] = point
        logging.debug(f'point #{p} | ({x}, {y}, {z}) | byte index: {i}')
    scene['pointArray'] = point_array

    if logging.root.level <= logging.DEBUG:
        pprint(scene)

    return scene


def disk(_i, _bin_arr):
    '''
    uint8 primitiveType    (1 = disk, 2 = cylinder/stem, 4 = sphere/bud, 8 = rectangle/leaf)
    #case disk (currently not used)
        float32 matrix 4x3 (the bottom row is always 0 0 0 1)
    '''
    data = {'type': 1}
    data['matrix'], _i = unpack(_i, _bin_arr, 'f'*12, _print_name='disk.matrix')
    return data, _i


def cylinder(_i, _bin_arr):
    '''
    uint8 primitiveType    (1 = disk, 2 = cylinder/stem, 4 = sphere/bud, 8 = rectangle/leaf)
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
    uint8 primitiveType    (1 = disk, 2 = cylinder/stem, 4 = sphere/bud, 8 = rectangle/leaf)
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
    uint8 primitiveType    (1 = disk, 2 = cylinder/stem, 4 = sphere/bud, 8 = rectangle/leaf)
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
            uint8 primitiveType    #1 = disk, 2 = cylinder(stem), 4 = sphere(bud), 8 = rectangle(leaf)
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
        logging.debug(entity_key)
        entities[entity_key] = {}
        for s in range(surfacesCount):            
            surface_key = f"surface{s}"
            logging.debug(surface_key)
            primitiveType, i = unpack(i, binary_array, 'B', 1, _print_name='primitiveType' if _verbose else None)
            data, i = primitive_map[primitiveType](i, binary_array)
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
            uint8 primitiveType    #1 = disk, 2 = cylinder(stem), 4 = sphere(bud), 8 = rectangle(leaf)
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
            uint8 primitiveType    #1 = disk, 2 = cylinder(stem), 4 = sphere(bud), 8 = rectangle(leaf)
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
    
    scene = {'format': 2}
    i = _offset
    logging.debug('Processing OBSTACLES ...')
    scene['obstacles'], i = load_primitve_entities(binary_array, 'obstacle', i, _verbose)       
    logging.debug('Processing SENSORS ...')
    scene['sensors'], i = load_primitve_entities(binary_array, 'sensor', i, _verbose)
    
    if logging.root.level <= logging.DEBUG:
        pass#pprint(scene)

    return scene
