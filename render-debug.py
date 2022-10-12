import os, logging, time
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

if __name__ == "__main__":
    
    # test sun cycle
    #RendererMts3.test_sun(); quit()
    
    # test MESH scene simulation / rendering
    #main('./data/t1999.mesh', 48.21, 16.36, "2022-08-23T10:34:48+00:00", 128, _show_render=True); quit()

    # test PRIMITIVE scene simulation / rendering
    main('./data/t1999.bin', 48.21, 16.36, "2022-08-23T10:34:48+00:00", 128, _show_render=True); quit()

    # test day cycle
    test_day_cylce(); quit()