import os, logging, time, datetime
from RendererMts3 import RendererMts3
from render import main

if __name__ == "__main__":

    # test sun cycle
    #RendererMts3.test_sun(); quit()

    # test scene simulation / rendering
    main('./data/t1999.mesh', 48.21, 16.36, "2022-08-23T7:11:48+00:00", 64, _save_render='result.jpg')

    """start = datetime.datetime(2022, 1, 30)
    end = datetime.datetime(2021, 2, 2)
    step = datetime.timedelta(minutes=30)
    c = 1

    while (start <= end):
        main('./data/t1999.mesh', 48.21, 16.36, start.isoformat()+'+01:00', 128, _save_render=f'img/{str(c).zfill(5)}.jpg')
        start += step
        c += 1
    """