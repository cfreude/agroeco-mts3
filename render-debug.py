import os, logging, time, datetime
import numpy as np
from RendererMts3 import RendererMts3
from render import main

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
        print(datetime_str, avg)
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
    print(params['sun.to_world']) 
    
    dn = np.linalg.norm(direction)
    direction = [v / dn for v in direction]
    up, _ = mi.coordinate_system(direction)
    print(T.look_at([0,0,0], direction, up))
    

if __name__ == "__main__":

    #test_directional(); quit()
    
    # test sun cycle
    #s = time.perf_counter_ns(); RendererMts3.test_sun(); print('classic', time.perf_counter_ns()-s); quit()
    #s = time.perf_counter_ns(); RendererMts3.test_sun_optimized(); print('optimized', time.perf_counter_ns()-s); quit()
    
    # test MESH scene simulation / rendering
    #main('./data/t1999.bin', 48.21, 16.36, "2022-08-23T10:34:48+00:00", 128, _show_render=True); quit()

    # test PRIMITIVE scene simulation / rendering
    main('./data/t1999.prim', 48.21, 16.36, "2022-08-23T10:34:48+00:00", 128, _verbose=True, _show_render=True); quit()

    # test day cycle
    test_day_cylce(); quit()

    """start = datetime.datetime(2022, 1, 30)
    end = datetime.datetime(2021, 2, 2)
    step = datetime.timedelta(minutes=30)
    c = 1

    while (start <= end):
        main('./data/t1999.mesh', 48.21, 16.36, start.isoformat()+'+01:00', 128, _save_render=f'img/{str(c).zfill(5)}.jpg')
        start += step
        c += 1
    """
