import salabim as sim
import os
import base64
import streamlit as st

class TotalMonitor(sim.Monitor):
    def __init__(self, m_width, m_height, m_x, m_y, m_range, m_step, m_hscale, m_vscale):
        self.range_upper = None  # make sure that we update on first tally
        self.m_width = m_width
        self.m_height = m_height
        self.m_x = m_x
        self.m_y = m_y
        self.m_range = m_range
        self.m_step = m_step
        self.m_hscale = m_hscale
        self.m_vscale = m_vscale

        super().__init__(name="total", level=True)

    def tally(self, value):
        super().tally(value)
        max_tally = self.maximum()

        range_upper = int(max((max_tally + self.m_step) // self.m_step * self.m_step, self.m_range))

        if range_upper != self.range_upper:
            if hasattr(self, "an"):
                self.an.remove()
            self.range_upper = range_upper
            range_lower = range_upper - self.m_range
            vertical_scale = self.m_vscale
            vertical_offset = -range_lower * vertical_scale  # vertical_offset is in pixels!, thats why we need to multiply with vertical scale

            self.an = self.animate(
                width=self.m_width,
                height=self.m_height,
                x=self.m_x,
                y=self.m_y,
                horizontal_scale=self.m_hscale,
                linewidth=3,
                vertical_offset=vertical_offset,
                vertical_scale=vertical_scale,
                labels=range(range_upper - self.m_range, range_upper + 1, self.m_step),
            )


DISTANCE = 40  # Nm
DREDGE_RATE = 350  # m3/hr


class Barge(sim.Component):

    dumped = 0

    def setup(self, speed, hopper, hs_norm,color):
        self.speed = speed
        self.hopper = hopper
        self.color = color
        self.hs_norm=hs_norm
        self.y = -self.sequence_number() * 22 + 310

        self.dredge_duration = self.hopper / DREDGE_RATE
        self.sail_duration = DISTANCE / self.speed

        self.an = sim.AnimateRectangle(spec=(-40, -10, 60, 10), x=x_dredger, y=self.y, fillcolor=self.color, text=self.name())

        sim.AnimateText(x=300, y=350, text=lambda t: f"production {env.mon.value}", textcolor="black")
        self.work = sim.State(self.name()+".work")
        self.level_max = 0
        self.my_weather = MyWeather(barge=self)

    def drive(self, xfrom, yfrom, xto, yto):
        t0 = env.now()
        t1 = t0 + self.sail_duration
        self.an.x = lambda t: sim.interpolate(t, t0, t1, xfrom, xto)
        #        self.an.y = lambda t: sim.interpolate(t, t0, t1, yfrom, yto)

        yield self.hold(self.sail_duration)

    def process(self):
        for trip in range(10):

            yield self.request(dredger)
            self.txt = sim.AnimateText(text=f"Loading {self.name()} with {self.hopper} m3", x=85, y=350)

            # dredging
            yield self.hold(self.dredge_duration)
            self.txt.remove()
            self.release()
            
            print(f'self.level_max of {self.name()} is: {self.level_max} and its norm is {self.hs_norm}')

            if self.level_max >= self.hs_norm:
                # self.txt=sim.AnimateText(text=f'Waiting on Weather 5hr window', x=85, y=200)
                env.print_trace("","", f"{self.name()} is waiting for weather")
                yield self.wait(self.work)
                # self.txt.remove()

            # sailing from dredger to disposal
            yield from self.drive(x_dredger, y_dredger, x_dump, y_dump)

            # dump material
            yield self.hold(1)

            # Barge.dumped=Barge.dumped+self.hopper
            production_monitor.tally(self.hopper)
            env.mon.value += self.hopper

            # sail back
            yield from self.drive(x_dump, y_dump, x_dredger, y_dredger)

        self.an.remove()
        self.an2.remove()


class MyWeather(sim.Component):
    def setup(self, barge):
        self.barge=barge
 

    def process(self):
        hr = 0
        self.txt = sim.AnimateText(x=600, y=220)
        self.txt2 = sim.AnimateText(x=50, y=self.barge.y)
        while True:
            level = Hs[hr]
            self.barge.level_max = max(Hs[hr : (hr + 5)])  # max weather 5 hr window

            level_monitor.tally(level)
            if self.barge.level_max < self.barge.hs_norm:
                self.txt2.text = f"{self.barge.name()} is working"
                self.barge.work.set()
            else:
                self.txt2.text = f"{self.barge.name()} waiting on weather"
                self.barge.work.reset()

            if level < 3:
                self.txt.text = f"Workable weather Hs<3m"
                yield self.hold(1)  # wave height >3m wow
            else:
                self.txt.text = f"Unworkable weather Hs>3m"
                yield self.hold(1)
            hr += 1

class Dredger(sim.Component):
    def setup(self, res):
        self.txt = sim.AnimateText(x=300, y=220)
        self.res = res

    def process(self):
        while True:
            yield self.hold(ttf())
            self.res.set_capacity(0)
            self.txt.text = f"Dredger is broken"
            yield self.hold(ttr())
            self.res.set_capacity(1)
            self.txt.text = f"Dredger is working"


if os.path.exists("demo_blind.gif"):
    os.remove("demo_blind.gif")
    print("file removed")

	
def get_binary_file_downloader_html(bin_file, file_label='File'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{bin_str}" download="{os.path.basename(bin_file)}">Download {file_label}</a>'
    return href	



env = sim.Environment(blind_animation=True, trace=False)
env.animate(True)
env.video("demo_blind.gif")

ttf = sim.Uniform(3, 5)  # time to failure distribution
ttr = sim.Uniform(3, 5)  # time to repair distribution            
        
            
x_dredger, y_dredger = 100, 300
x_dump, y_dump = 700, 300
x_gate, y_gate = 400, 200

Barge(speed=7, hopper=500, hs_norm=2.5,color=("olive", 150))
Barge(speed=8, hopper=800, hs_norm=1.5,color=("navy", 150))
Barge(speed=11, hopper=900, hs_norm=4.0,color=("red", 150))
Barge(speed=10, hopper=1200, hs_norm=1.0,color=("blue", 150))


sim.AnimateRectangle(spec=(-10, -10, 50, 10), x=x_dredger, y=y_dredger + 40, text="Dredger")
sim.AnimateRectangle(spec=(-10, -10, 50, 10), x=x_dump, y=y_dump + 40, text="Disposal")

#work = sim.State("work")

dredger = sim.Resource("dredger", capacity=1)

Dredger(res=dredger)

production_monitor = sim.Monitor(level=True, name=("production"))
level_monitor = sim.Monitor(level=True, name=("Waveheight Hs at time=now"), type="int8")

env.mon = TotalMonitor(m_width=700, m_height=300, m_x=100, m_y=400, m_range=3000, m_step=500, m_hscale=35, m_vscale=0.1)


Hs = [3,3,3,3,3,3,3,3,3,3,3,2,2,2,2,2,2,2,2,2,2,2,2,2,1,1,1,1,1,1,1,1,1,1,1,1,1,1,4,4,4,4,4,4,4,4,
      3,3,3,3,3,3,3,3,3,3,3,2,2,2,2,2,2,2,2,2,2,2,2,2,1,1,1,1,1,1,1,1,1,1,1,1,1,1,4,4,4,4,4,4,4,4
      
]  # assuming this is a csv with significant waveheights

# w = Demo()

sim.AnimateMonitor(
    level_monitor,
    x=600,
    y=100,
    width=200,
    height=100,
    linewidth=3,
    linecolor="blue",
    vertical_scale=20,
    horizontal_scale=10,
    labels=range(0, 6, 1),
    label_linecolor=(255, 145, 0),
)

env.animate(True)
env.run(20)
env.video_close()	

file_ = open("demo_blind.gif", "rb")
contents = file_.read()
data_url = base64.b64encode(contents).decode("utf-8")
file_.close()

header=st.container()


with header:
    st.title('Welcome to my DES project')
    st.markdown(
    f'<img src="data:image/gif;base64,{data_url}" alt="demo" width="700">',
    unsafe_allow_html=True,
    )
with st.echo():
	x=15

st.markdown(get_binary_file_downloader_html('demo_blind.gif', 'Video'), unsafe_allow_html=True)
