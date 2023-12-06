from ladybug_radiance import skymatrix
from ladybug.dt import DateTime

import os, csv
import numpy as np
import imageio

DEBUG_WRITE_ENV = False
ENABLE_MATPLOTLIB = False
if ENABLE_MATPLOTLIB:
    from mpl_toolkits.mplot3d import Axes3D
    import matplotlib.pyplot as plt
    from matplotlib import cm


class CumulativeSky():
    

    def __init__(self):

        # read sky patch definition
        reader = csv.reader(open(os.path.join('epw','Mardaljevic Zone Angles.csv')))

        tregenza = {}
        for row in reader:
            key = row[0]
            values = []
            for v in row[1:]:
                modstr = v.replace(',', '.')
                try:
                    values.append(float(modstr))
                except ValueError as err:
                    pass
            tregenza[key] = values

        altitude = tregenza['Altitude of band centre']
        self.num_zones = tregenza['Number of zones']
        self.solid_angles = tregenza['Solid angle']

        self.num_zones[-1] += 3 # add redundant zone to top area

        # compute sky patch coordinates
        self.altitude_mesh = [(altitude[i+1]+altitude[i])*0.5 for i in range(len(altitude)-1)]
        self.altitude_mesh.insert(0, 0.0)
        self.altitude_mesh.append(90.0)
        self.azimuth_mesh = [np.linspace(0.0, 360.0, int(n)+1, endpoint=True) for n in self.num_zones]

    @staticmethod
    def initialize_bitmap(data, w=120, h=64):

        texture_data = np.zeros([h,w])

        offset = 0 # texture offset
        ystep_per_row = round(float(h/2) / (len(data)-0.5))

        for i, patch_row in enumerate(data[::-1]):

            patches_per_row = len(patch_row)
            step = round(float(w) / patches_per_row)

            upsampled_row = np.repeat(patch_row, step)

            diff = w-len(upsampled_row)
            if diff > 0:
                pad = int(diff/2)
                upsampled_row = np.pad(upsampled_row, (pad, diff-pad), 'edge')

            upsampled_row = upsampled_row[:w]

            ystep = ystep_per_row if i!=0 else int(ystep_per_row/2)
            yrep = np.tile(upsampled_row, (ystep, 1))

            texture_data[offset:offset+ystep, :] = yrep[:, :w]
            offset += ystep

        #print(texture_data.shape)
        return np.moveaxis(np.tile(texture_data, (3,1,1)), 0, -1)

    def compute(self, _epw_path, _start_datetime, _end_datetime, _only_sun=False, _plot=False, _save=""):

        if not isinstance(_start_datetime, DateTime):
            _start_datetime = DateTime(_start_datetime.month, _start_datetime.day, _start_datetime.hour)

        if not isinstance(_end_datetime, DateTime):
            _end_datetime = DateTime(_end_datetime.month, _end_datetime.day, _end_datetime.hour)

        # compuate sky matrix values
        start_hoy = int(_start_datetime.hoy)
        end_hoy = int(_end_datetime.hoy)
        print(f"start_hoy: {start_hoy}, end_hoy: {end_hoy}")

        hoys = range(start_hoy, end_hoy)
        skymtx = skymatrix.SkyMatrix.from_epw(_epw_path, hoys=hoys)
        wea_duration = len(skymtx.wea) / skymtx.wea.timestep    
        print('wea_duration: ', wea_duration)    
        sky_density = 2 if skymtx.high_density else 1
        skymtx.compute_sky()

        if _only_sun:
            values = skymtx.direct_values
        else:
            values = np.add(skymtx.direct_values, skymtx.diffuse_values);

        # split values into zone arrays
        zone_values = []
        maxv = 0.0
        j = 0
        for i, n in enumerate(self.num_zones):
            num = int(n)
            vals = values[j:j+num] / skymtx.PATCH_ROW_COEFF[sky_density][i] # convert from W/m2 to radiance W/m2/sr
            vals /= wea_duration # convert back from (hour) cummulative to average radiance
            vals *= 1000 # convert from kW to W
            maxv = np.max([maxv, np.max(vals)])
            zone_values.append(vals)
            j+=num
        zone_values = np.array(zone_values, dtype=object)

        if not ENABLE_MATPLOTLIB:
            self.envmap = CumulativeSky.initialize_bitmap(zone_values, 240, 128).astype("float32")
        else:
            # normalize sky values
            if maxv == 0.0:
                maxv = 1.0

            zone_values = zone_values / maxv

            zone_values[-1] = np.repeat(zone_values[-1], 4, axis=-1)

            fig1 = plt.figure(figsize=(8,2), dpi=self.num_zones[0])
            ax = fig1.add_subplot()

            for i in range(len(self.altitude_mesh)-1):

                lo_v = self.azimuth_mesh[i]
                la_v = self.altitude_mesh[i:i+2]

                lo, la = np.meshgrid(lo_v, la_v)

                cols = zone_values[i]
                cols = np.expand_dims(cols, 0)

                img = ax.pcolormesh(lo, la, cols, cmap=cm.gray, vmin=0.0, vmax=1.0)

            ax.set_axis_off()
            ax.set_facecolor("black")
            fig1.tight_layout(pad=0)

            fig1.canvas.draw()

            self.envmap = np.array(fig1.canvas.renderer.buffer_rgba())
            self.envmap = self.envmap[:,:,:3]
            self.envmap = np.pad(self.envmap, ((0, self.envmap.shape[0]), (0, 0), (0,0)))

            self.envmap = self.envmap.astype("float32"); self.envmap *= maxv / 255.0

        if ENABLE_MATPLOTLIB:
            if _plot:
                # plot the sky
                fig2 = plt.figure()
                ax = fig2.add_subplot(projection='3d')

                to_rad = np.pi/180.0
                for i in range(len(self.altitude_mesh)-1):
                    lo_v = self.azimuth_mesh[i]
                    la_v = self.altitude_mesh[i:i+2]

                    lo, la =  np.meshgrid(lo_v, la_v)
                    x = np.cos(la*to_rad)*np.sin(lo*to_rad)
                    y = np.cos(la*to_rad)*np.cos(lo*to_rad)
                    z = np.sin(la*to_rad)

                    cols = np.expand_dims(cm.gray(zone_values[i]), 0)
                    ax.plot_surface(x, y, z, facecolors=cols, edgecolor="r", shade=False)

                ax.set_box_aspect((1,1,0.5))
                plt.show()
            else:
                plt.close('all')

            if len(_save) > 0:
                fig1.savefig(os.path.join(_save, f"{start_hoy}-{end_hoy}_sky.tiff"), format = "tiff")
        
        if DEBUG_WRITE_ENV:
            import pandas as pd
            env2D = self.envmap[:,:,0]
            df = pd.DataFrame(env2D)
            df.to_csv('env.csv', index=False)
            
            print('PIL:', env2D.shape)
            from PIL import Image
            im = Image.fromarray((env2D / np.max(env2D) * 255).astype(np.uint8), mode="L")
            im.save("./env.ppm")
        
        return self.envmap, end_hoy-start_hoy


# TEST FUNCTION
if __name__ == '__main__':

    #start_datetime = DateTime(6, 15, 12, 0)
    #end_datetime = DateTime(7, 15, 12, 0)

    import dateutil, datetime
    from dateutil import parser
    start_datetime = parser.parse(f"2022-06-01T6:00:00+00:00")
    start_datetime.replace(tzinfo=datetime.timezone.utc)

    end_datetime = parser.parse(f"2022-06-01T7:00:00+00:00")
    end_datetime.replace(tzinfo=datetime.timezone.utc)

    epw_path = os.path.join("epw","AUT_Vienna.Schwechat.110360_IWEC","AUT_Vienna.Schwechat.110360_IWEC.epw")

    sky = CumulativeSky()
    envmap, hoy_count = sky.compute(epw_path, start_datetime, end_datetime, _only_sun=False, _plot=False)

    print(envmap.shape)
    print(hoy_count)
    
    import matplotlib.pyplot as plt; plt.imshow(envmap / np.max(envmap)); plt.show()

    imageio.imwrite('./tmp/envmap.exr', envmap)

    maxv = np.max(envmap)
    print("Maximum Value:", maxv)
    if maxv != 0.0:
        envmap /= maxv
    imageio.imwrite('./tmp/envmap.png', np.uint8(envmap*255))

