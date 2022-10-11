import os, logging, time
from RendererMts3 import RendererMts3
from render import main

if __name__ == "__main__":
    
    # test sun cycle
    #RendererMts3.test_sun(); quit()
    
    # test scene simulation / rendering
    main('./data/t1999.mesh', 48.21, 16.36, "2022-08-23T10:34:48+00:00", 128, _show_render=True)