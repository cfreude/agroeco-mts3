import os, logging
from RendererMts3 import RendererMts3

def main(_path, _lat, _long, _datetime_str, _ray_count=128, _verbose=False, _show_render=False):
    
    renderer = RendererMts3(_verbose)
    renderer.load_path(_path, _lat, _long, _datetime_str)
    measurements = renderer.render(_ray_count)

    out_path = os.path.splitext(os.path.split(_path)[-1])[0] +'.irrbin'
    measurements.tofile(out_path)
    print('Irradiance (binary, type: %s) file saved to: %s' % (measurements.dtype,out_path))
    
    #logging.debug(measurements)
    
    if _show_render:
        renderer.show_render()


if __name__ == "__main__":

    #RendererMts3.test_sun(); quit()

    """
    Options:
    -h,--help | Print this help message and exit
    --scene_path (string, required) | Path to Scene
    --lat (flaot, required) | Latitude
    --long (flaot, required) | Longitude
    --rays-per-triangle (unsigned int, default=128) | Number of rays to cast from each triangle in the mesh
    --time (string, required) Time of day - should be in %Y-%m-%dT%H:%M:%S%z format
    --timestep (FLOAT, required) | Timestep (h)
    --verbose | Be verbose.
    --gui | Show GUI.
    """

    import argparse

    # example CMD
    # python render.py data/t700.mesh 48.21 16.36 2022-08-23T10:34:48+00:00

    parser = argparse.ArgumentParser(description='Irradaince measurment tool based on Mitsuba 3.')
    parser.add_argument('scene_path', type=str, help='Path of the simulation scene file.')
    parser.add_argument('lat', type=float, help='Latitude of the simulation location.')
    parser.add_argument('long', type=float, help='Longitude of the simulation location.')    
    parser.add_argument('datetime_str', type=str, help='Time of day - should be in %Y-%m-%dT%H:%M:%S%z format')    
    parser.add_argument('--ray_count', type=int, default=128, help='Number of rays per element.')    
    parser.add_argument('--verbose', type=bool, default=False, help='Number of rays per element.')

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)   
        #logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.ERROR)

    logging.debug('Args: %s', args)
    main(args.scene_path, args.lat, args.long, args.datetime_str, args.ray_count, _show_render=False)