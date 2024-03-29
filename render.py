import os, logging, time
import matplotlib.pyplot as plt
from RendererMts3 import RendererMts3

def show_render(img):
    plt.figure()
    plt.axis("off")
    plt.imshow(img)
    plt.savefig('result.png', format='png')
    plt.show()

def main(_path, _lat, _long, _datetime_str, _ray_count=128, _epw_path=None, _end_datetime_str=None, _verbose=False, _use_batch_rendering=False, _show_render=False, _save_path=''):

    t_total = time.perf_counter_ns()
    
    renderer = RendererMts3(_verbose, _use_batch_rendering)
    logging.info(f'Renderer initialization dur.: {(time.perf_counter_ns()-t_total) /1e9:.2f} sec.')
    
    t = time.perf_counter_ns()    
    renderer.load_path(_path, _lat, _long, _datetime_str, _ray_count, _epw_path, _end_datetime_str)
    logging.info(f'Scene loading dur.: {(time.perf_counter_ns()-t) /1e9:.2f} sec.')
    
    if len(_save_path) == 0: 
        t = time.perf_counter_ns()
        measurements = renderer.render(_ray_count)
        logging.info(f'Rendering dur.: {(time.perf_counter_ns()-t) /1e9:.2f} sec.')

        if measurements is not None:
            out_path = os.path.splitext(os.path.split(_path)[-1])[0] +'.irrbin'
            measurements.tofile(out_path)

        dur = time.perf_counter_ns() - t_total

        if measurements is not None:      
            logging.info(f'Irradiance (binary, type: {measurements.dtype}) file saved to: {out_path} ... dur.: {dur / 1e9:.2f} sec.')

        logging.debug(measurements)

    img = None 
    if _show_render or len(_save_path) > 0:        
        img = renderer.get_render_image(_ray_count) 

    if _show_render:
        show_render(img)

    if len(_save_path) > 0:
        renderer.save_render_image(_save_path, img)

if __name__ == "__main__":

    """
    Options:
    -h,--help | Print this help message and exit
    scene_path (string, required) | Path to Scene
    lat (flaot, required) | Latitude
    long (flaot, required) | Longitude
    datetime_str (string, required) | Time of day - should be in %Y-%m-%dT%H:%M:%S%z format
    --ray_count (int, default=128) | Number of rays to cast from each sensor
    --verbose (bool, default=False) | Be verbose.
    """

    import argparse

    # example CMD
    # python render.py data/t700.mesh 48.21 16.36 2022-08-23T10:34:48+00:00

    parser = argparse.ArgumentParser(description='Irradaince measurment tool based on Mitsuba 3.')
    parser.add_argument('scene_path', type=str, help='Path of the simulation scene file.')
    parser.add_argument('lat', type=float, help='Latitude of the simulation location.')
    parser.add_argument('long', type=float, help='Longitude of the simulation location.')
    parser.add_argument('datetime_str', type=str, help='Date and time - should be in %Y-%m-%dT%H:%M:%S%z format')    
    parser.add_argument('--ray_count', type=int, default=128, help='Number of rays per element.')
    parser.add_argument('--epw_path', type=str, default=None, help='EnergyPlus Weather File (EPW) path')    
    parser.add_argument('--end_datetime_str', type=str, default=None, help='End Date and time - should be in %Y-%m-%dT%H:%M:%S%z format')
    parser.add_argument('--verbose', type=bool, default=False, help='Number of rays per element.')

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
        #logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.ERROR)

    logging.debug(f'Args: {args}')
    main(args.scene_path, args.lat, args.long, args.datetime_str, args.ray_count, args.epw_path, args.end_datetime_str, _show_render=False)