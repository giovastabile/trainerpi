import asyncio
import bleCSC
import collections
import numpy
from scipy import interpolate
import os
import pygame
import time
tstart = time.time()



towrite=["time", "speed", "cadence", "power1", "power2" , "power3"]
f = open("training.txt","a+")
f.write(str(towrite)[1:-1]+"\n")
f.close()

def Average(lst): 
    return sum(lst) / len(lst)

# --------------------------------------------------------------------------- #
#  SETTINGS                                                                   #
# --------------------------------------------------------------------------- #
ROLLING_LENGTH = 2096.  # mm
POWER_CURVE1 = numpy.loadtxt("power-1.csv", delimiter=",")
POWER_CURVE2 = numpy.loadtxt("power-2.csv", delimiter=",")
POWER_CURVE3 = numpy.loadtxt("power-3.csv", delimiter=",")
POWER_CURVE4 = numpy.loadtxt("power-4.csv", delimiter=",")
POWER_CURVE5 = numpy.loadtxt("power-5.csv", delimiter=",")
SCREEN_SIZE = WIDTH, HEIGHT = 800, 1000
BORDER = 10
FONT_NAME = "DejaVuSans"
FONT_SIZE = 24
SCREEN_UPDATE_DELAY = 0.01  # Display update should be fast for the timer to "look" right
# CSC_SENSOR_ADDRESSES = (
#     "D0:75:E8:97:42:37",
#     "D4:75:F1:27:D1:56"
# )
CSC_SENSOR_ADDRESSES = (
    "D4:75:F1:27:D1:56",
    "D0:75:E8:97:42:37"
)

power1 = interpolate.interp1d(POWER_CURVE1[:, 0], POWER_CURVE1[:, 1],fill_value="extrapolate")
power2 = interpolate.interp1d(POWER_CURVE2[:, 0], POWER_CURVE2[:, 1],fill_value="extrapolate")
power3 = interpolate.interp1d(POWER_CURVE3[:, 0], POWER_CURVE3[:, 1],fill_value="extrapolate")
power4 = interpolate.interp1d(POWER_CURVE4[:, 0], POWER_CURVE4[:, 1],fill_value="extrapolate")
power5 = interpolate.interp1d(POWER_CURVE5[:, 0], POWER_CURVE5[:, 1],fill_value="extrapolate")
powHis1 = []
powHis2 = []
powHis3 = []
display_column = collections.namedtuple("display_column", ("title", "data"))
display_data = {}
SIGNAL_EXIT = False


class TrainerThread:
    def __init__(self):
        self.display_row = None


class CSCTrainer(TrainerThread):
    def __init__(self, address: str, display_row: int):
        super().__init__()
        self.address = address
        self.display_row = display_row
        self._location = ""
        self.should_activity_timer_run = False  # Should the activity timer be running?

    def handle_notification(self, wheel_speed: float, crank_speed: float, cumulative_rotations: int) -> None:
        global display_data

        self.should_activity_timer_run = (wheel_speed is not None and wheel_speed > 0) or\
                                         (crank_speed is not None and crank_speed > 0)

        if "Wheel" in self._location and wheel_speed is not None:
            speed = wheel_speed * 3600. * ROLLING_LENGTH / 1e+6
            p1 = power1(speed)
            p2 = power2(speed) 
            p3 = power3(speed)
            p4 = power4(speed)
            p5 = power5(speed)
            powHis1.append(p1)
            powHis2.append(p2)
            powHis3.append(p3)
            towrite[0]=time.time()-tstart
            towrite[1]=speed
            towrite[3]=float(p1)
            towrite[4]=float(p2)
            towrite[5]=float(p3)
            display_data[(1, 0)] = display_column(
                "Speed",
                "{:2.0f} km/h".format(
                    wheel_speed * 3600. * ROLLING_LENGTH / 1e+6
                )
            )

            display_data[(0, 1)] = display_column(
            	"Distance",
                "{:6.2f} km".format(cumulative_rotations * ROLLING_LENGTH / 1e+6)
            )
            display_data[(2, 0)] = display_column(
            	"P1",
                "{:3.0f} W".format(p1)
            )
            display_data[(2, 1)] = display_column(
            	"P2",
                "{:3.0f} W".format(p2)
            )
            display_data[(3, 0)] = display_column(
            	"P3",
                "{:3.0f} W".format(p3)
            )
            display_data[(3, 1)] = display_column(
            	"P4",
                "{:3.0f} W".format(p4)
            )
            display_data[(4, 0)] = display_column(
            	"P5",
                "{:3.0f} W".format(p5)
            )
            display_data[(4, 1)] = display_column(
            	"Pav1",
                "{:3.0f} W".format(Average(powHis1))
            )
            display_data[(5, 0)] = display_column(
            	"Pav2",
                "{:3.0f} W".format(Average(powHis2))
            )
            display_data[(5, 1)] = display_column(
            	"Pav3",
                "{:3.0f} W".format(Average(powHis3))
            )


        if "Crank" in self._location and crank_speed is not None:
            display_data[(1, 1)] = display_column(
                "Cadence",
                "{:3.0f} RPM".format(
                    crank_speed * 60.
                )
            )
            towrite[2] = crank_speed * 60.
        f = open("training.txt","a+")
        f.write(str(towrite)[1:-1]+"\n")
        f.close()

    async def worker(self):
        global SIGNAL_EXIT, display_data
        print(self.display_row)
        display_data[(self.display_row, 0)] = display_column("Connecting for Sensor:", self.address)

        sensor = bleCSC.CSCSensor()
        sensor.connect(self.address, self.handle_notification)
        display_data[(self.display_row, 0)] = display_column("Waiting for Loc'n:", self.address)
        await asyncio.sleep(0.0)
        print(self.address)
        if(self.address=="D0:75:E8:97:42:37"):
        	self._location = "Rear Wheel"

        if(self.address=="D4:75:F1:27:D1:56"):
        	self._location = "Right Crank"

        print(self._location)
        # self._location=sensor.get_location()
        
        #print(sensor.get_location())
        display_data[(self.display_row, 0)] = display_column("Waiting for Data:", self.address)
        await asyncio.sleep(0.0)
        sensor.notifications(True)
        while not SIGNAL_EXIT:
            await asyncio.sleep(0.0)
            notify_ret = await sensor.wait_for_notifications(1.0)
            if notify_ret:
                continue
            display_data[(self.display_row, 0)] = display_column("Waiting for Sensor:", self.address)
            self.should_activity_timer_run = False


class ActivityTimer(TrainerThread):
    def __init__(self, monitor_threads: list, display_row: int):
        super().__init__()
        self.monitor_threads = monitor_threads
        self.prev_accumulated_time = 0
        self.running = False
        self.start_time = 0
        self.display_row = display_row

    async def worker(self):
        global SIGNAL_EXIT, display_data
        while not SIGNAL_EXIT:
            if any([t.should_activity_timer_run for t in self.monitor_threads]):  # Timer should be running
                if not self.running:
                    self.start_time = time.time()
                    self.running = True
                    time_to_display = self.prev_accumulated_time
                else:
                    time_to_display = self.prev_accumulated_time + time.time() - self.start_time
            else:  # Timer should not be running
                if self.running:  # Timer needs to stop
                    self.prev_accumulated_time += time.time() - self.start_time
                    self.running = False
                time_to_display = self.prev_accumulated_time
            display_data[(self.display_row, 0)] = display_column(
                "Activity Time",
                time.strftime("%H:%M:%S", time.gmtime(time_to_display))
            )
            await asyncio.sleep(SCREEN_UPDATE_DELAY)


class ScreenUpdateTrainer(TrainerThread):
    def __init__(self, thread_list):
        super().__init__()
        self.thread_list = thread_list
        self.use_pygame = True

        try:
            os.putenv("SDL_FBDEV", "/dev/fb1")
            pygame.init()
            pygame.mouse.set_visible(False)
            self.screen = pygame.display.set_mode(SCREEN_SIZE)
            self.clock = pygame.time.Clock()
            self.font = pygame.font.SysFont(FONT_NAME, FONT_SIZE)
        except pygame.error:
            self.use_pygame = False

    async def worker(self):
        global SIGNAL_EXIT, display_data
        while not SIGNAL_EXIT:
            if self.use_pygame:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        SIGNAL_EXIT = True
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        SIGNAL_EXIT = True

                self.screen.fill((0, 0, 0))

                for seg, seg_data in display_data.items():
                    if seg_data is not None:
                        self.draw_segment(seg, seg_data.title, seg_data.data, (255, 255, 255))

                pygame.display.flip()
            else:
                for seg, seg_data in display_data.items():
                    if seg_data is not None:
                        print("{}\t{}\t{}".format(seg, seg_data.title, seg_data.data))

            await asyncio.sleep(SCREEN_UPDATE_DELAY)

    def draw_segment(self, seg: tuple, title: str, data: str, color: tuple):
        seg_width = WIDTH // 2
        seg_height = HEIGHT // 6
        x0 = seg_width * seg[1] + BORDER
        y0 = seg_height * seg[0] + BORDER
        x1 = seg_width * (seg[1] + 1) - BORDER
        y1 = seg_height * (seg[0] + 1) - BORDER

        title_text = self.font.render(title, True, color)
        self.screen.blit(title_text, (x0, y0))

        data_text = self.font.render(data, True, color)
        self.screen.blit(data_text, (x1 - data_text.get_width(), y1 - data_text.get_height()))


def run_trainer():
    csc_threads = list(
        [CSCTrainer(address, i + 1) for (i, address) in enumerate(CSC_SENSOR_ADDRESSES)]
    )
    all_threads = csc_threads.copy()
    all_threads.append(ActivityTimer(csc_threads, 0))
    all_threads.append(ScreenUpdateTrainer(all_threads))

    io_loop = asyncio.get_event_loop()
    tasks = list(
        [io_loop.create_task(thread.worker()) for thread in all_threads]
    )
    wait_tasks = asyncio.wait(tasks)
    io_loop.run_until_complete(wait_tasks)
    io_loop.close()


if __name__ == "__main__":
    run_trainer()

