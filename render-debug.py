import os, logging, time, datetime
import numpy as np
from RendererMts3 import RendererMts3
from render import main
from binary_loader import load_path

def test_day_cylce():

    h = []
    val = []

    hour = 22
    day = 2
    for i in range(23):
        datetime_str = '2022-02-%00dT%00d:00:00+02:00' % (day, hour)
        measurments = main('./data/t1999.mesh', 48.21, 16.36, datetime_str, 128, _show_render=False)        
        avg = np.mean(measurments)   
        h.append(hour)
        val.append(avg)     
        logging.debug(datetime_str, avg)
        hour = (hour + 1) % 24
        day += 1
    
    import matplotlib.pyplot as plt
    plt.plot(val)
    plt.show()

def test_directional():

    '''
    ScalarVector3f direction(dr::normalize(props.get<ScalarVector3f>("direction")));
    auto [up, unused] = coordinate_system(direction);

    m_to_world = ScalarTransform4f::look_at(0.0f, ScalarPoint3f(direction), up);
    '''
    import numpy as np
    import mitsuba as mi

    #mi.set_variant("cuda_ad_rgb")
    #mi.set_variant("llvm_ad_rgb")
    mi.set_variant("scalar_rgb")

    from mitsuba import ScalarTransform4f as T

    direction = [1, 1, 0]
    
    scene = mi.load_dict({
        'type': 'scene',
        'sun': {
                'type': 'directional',
                'direction':  direction,
                'irradiance': {
                    'type': 'rgb',
                    'value': 1.0,
                }
            }
        })

    params = mi.traverse(scene)
    logging.debug(params['sun.to_world']) 
    
    dn = np.linalg.norm(direction)
    direction = [v / dn for v in direction]
    up, _ = mi.coordinate_system(direction)
    logging.debug(T.look_at([0,0,0], direction, up))
    

if __name__ == "__main__":
    
    np.random.seed(0)

    logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
    FORMAT = '%(name)s :: %(levelname)-8s :: %(message)s'
    FORMAT = '%(levelname)-8s :: %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.INFO)
    
    #load_path('./data/t126.mesh', True); quit()
    #test_directional(); quit()
    
    # test sun cycle
    #s = time.perf_counter_ns(); RendererMts3.test_sun(); logging.debug('classic', time.perf_counter_ns()-s); quit()
    #s = time.perf_counter_ns(); RendererMts3.test_sun_optimized(); logging.debug('optimized', time.perf_counter_ns()-s); quit()
    
    #main('./data/t126.mesh', 48.21, 16.36, "2022-08-23T10:34:48+00:00", 128, _verbose=True, _show_render=True); quit()

    if 0:
        show_render = True
        # test MESH scene simulation / rendering
        logging.info('Mesh test:')
        main('./data/t1999.mesh', 48.21, 16.36, "2022-08-23T10:34:48+00:00", 128, _verbose=True, _show_render=show_render)
        # test PRIMITIVE scene simulation / rendering
        logging.info('Primitive test:')
        main('./data/t1999.prim', 48.21, 16.36, "2022-08-23T10:34:48+00:00", 128, _verbose=True, _show_render=show_render)
        quit()


    # test day cycle
    #test_day_cylce(); quit()
    start = datetime.datetime(2022, 1, 30)
    end = datetime.datetime(2021, 2, 2)
    step = datetime.timedelta(minutes=30)
    c = 1

    print(start >= end)
    while (start >=  end):
        print(start)
        main('./data/t1999.prim', 48.21, 16.36, start.isoformat()+'+01:00', 4, _save_render=f'./{str(c).zfill(5)}.jpg')
        start += step
        c += 1

