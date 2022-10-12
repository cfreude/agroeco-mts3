# Mitsuba 3 - Renderer

## CLI Interface

The CLI interface (render.py) for the Sustainable Agro Ecosystem projekt.

**Options:**
```
-h,--help | Print this help message and exit
scene_path (string, required) | Path to Scene
lat (flaot, required) | Latitude
long (flaot, required) | Longitude
datetime_str (string, required) | Time of day - should be in %Y-%m-%dT%H:%M:%S%z format
--ray_count (int, default=128) | Number of rays to cast from each sensor
--verbose (bool, default=False) | Be verbose.
```

## Server Interface

The server interface (render-server.py) for the Permaculture simulation projekt.

**Options:**
```
-h,--help | Print this help message and exit
--port (unsighed int, default=9000) | Port to start the server
--rays (unsigned int, default=128) | Number of rays to cast from each triangle in the mesh
--verbose | Be verbose.
```

**Notes**
The renderer is called via `http`. 
* *TODO: update this protocol* 
* Listening at port `9000`
* Respond with a status code `200` (OK) to a `GET` request, this is a check for whether the server is up
* Respond to `POST` requests with scene data by returning accummulated irradiances

## Input scene data format
The renderer will receive the scene data in binary form as a set of triangle meshes. A primitive-based alternative format is planned as well.
```
#Triangle Mesh Binary Serialization
#INDEXED DATA
uint32 entitiesCount
foreach ENTITY
    uint32 surfacesCount
    foreach SURFACE (for now, each surface is an irradiancemeter)
        uint8 trianglesCount
        foreach TRIANGLE
            uint32 index0
            uint32 index1
            uint32 index2
#POINTS DATA
uint32 pointsCount
foreach POINT
    float32 x
    float32 y
    float32 z
```
Plants correspond to entities. The surfaces are typically light-sensitive plant organs like leafs. Each surface should be associated with a sensor that measures the irradiance exposure (summed all over the surface). Each surface is represented as a set of triangles which are given by vertex indices. After the section with entities, a list of vertices with 3D coordinates is provided.

Per convention the up-direction is defined +Y and noth is -Z. 

**Result irradiance data format**
The resulting irradiances per surface need to be sent back as a simple array of floats preserving the order of the surfaces in the request.

## Implmentation details

This implementation is based on [Mitsuba 3](https://www.mitsuba-renderer.org/). It uses the [irradiance meter plugin](https://mitsuba.readthedocs.io/en/stable/src/generated/plugins_sensors.html#irradiance-meter-irradiancemeter) to calculate the irradiance (W/m^2) for each `SURFACE`.
The geometry is placed into a base scene consisting of a `disk` as ground plane and `directional emitter` as sun using the direction calculated from the location and time parameters.