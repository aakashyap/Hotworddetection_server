import dex2
import sys
import signal

interrupted = False


def signal_handler(signal, frame):
    global interrupted
    interrupted = True


def interrupt_callback():
    global interrupted
    return interrupted


#Specify the model obtained from Snowboy website
if len(sys.argv) == 1:
    print("MODEL NOT SPECIFIED")
    print("Please specify model with .pmdl or .umdl extension after python file")
    sys.exit(-1)

model = sys.argv[1]

#To capture signal such as keyboard interrupt
signal.signal(signal.SIGINT, signal_handler)

#Here higher sensitivity means lower detection chances but more accuracy
detector = dex2.HotwordDetector(model, sensitivity=0.5)
print('Speak a keyword(computer) to initialize')

#In every 0.03 seconds program checks for the hotword
detector.start(detected_callback=dex2.perform,
               interrupt_check=interrupt_callback,
               sleep_time=0.03)

detector.terminate()
