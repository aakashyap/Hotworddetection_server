import dex2
import sys
import signal

#code for listening two hotwords at the same time

interrupted = False


def signal_handler(signal, frame):
    global interrupted
    interrupted = True


def interrupt_callback():
    global interrupted
    return interrupted

#Specify the model obtained from Snowboy website
if len(sys.argv) != 3:
    print("Error: need to specify 2 model names")
    print("Usage: python demo.py 1st.model 2nd.model")
    sys.exit(-1)

models = sys.argv[1:]
#to capture keyboard interrupt
signal.signal(signal.SIGINT, signal_handler)

#Here higher sensitivity means lower detection chances but more accuracy
sensitivity = [0.5]*len(models)
detector = dex2.HotwordDetector(models, sensitivity=sensitivity)
callbacks = [lambda: dex2.perform(dex2.DETECT_DING),
             lambda: dex2.perform(dex2.DETECT_DONG)]
print('Speak a keyword(computer) to initialize')


#In every 0.03 seconds program checks for the hotword
detector.start(detected_callback=callbacks,
               interrupt_check=interrupt_callback,
               sleep_time=0.03)

detector.terminate()
