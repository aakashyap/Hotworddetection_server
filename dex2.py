
import speech_recognition as sr
import collections
import pyaudio
import snowboydetect
import time
import wave
import os
import logging

logging.basicConfig()
logger = logging.getLogger("snowboy")
logger.setLevel(logging.INFO)
TOP_DIR = os.path.dirname(os.path.abspath(__file__))

#Resource files, only modify the path
RESOURCE_FILE = os.path.join(TOP_DIR, "resources/common.res")
DETECT_DING = os.path.join(TOP_DIR, "resources/ding.wav")
DETECT_DONG = os.path.join(TOP_DIR, "resources/dong.wav")


class RingBuffer(object):
    """This buffer object stores audio data from pyaudio which obtains it from the mic"""
    def __init__(self, size = 4096):
        self._buf = collections.deque(maxlen=size)

    def extend(self, data):
        """Appends new audio data to the end of buffer"""
        self._buf.extend(data)

    def get(self):
        """clears data after processing from the buffer"""
        tmp = bytes(bytearray(self._buf))
        self._buf.clear()
        return tmp


def perform(fname=DETECT_DING):
    """ function which start recognising audio input after detecting hotword"""
    r=sr.Recognizer()
    mic=sr.Microphone()
    #taking mike input,calibrating the external noise
    with mic as source:
        r.adjust_for_ambient_noise(source)
        audio=r.listen(source)
    #keep this in a try except block because if it fails then system will enter an inconsistent state
    try:
        print(r.recognize_google(audio))
    except:
        print("UNRECOGNIZABLE SPEECH...SPEAK CLEARLY")
    #pyaudio configurations,do not change
    ding_wav = wave.open(fname, 'rb')
    ding_data = ding_wav.readframes(ding_wav.getnframes())
    audio = pyaudio.PyAudio()
    stream_out = audio.open(
        format=audio.get_format_from_width(ding_wav.getsampwidth()),
        channels=ding_wav.getnchannels(),
        rate=ding_wav.getframerate(), input=False, output=True)
    stream_out.start_stream()
    stream_out.write(ding_data)
    time.sleep(0.2)
    stream_out.stop_stream()
    stream_out.close()
    audio.terminate()


class HotwordDetector(object):
    
    """To detect if a hotword exists in the mic input stream which matches the model specified"""
    def __init__(self, decoder_model,
                 resource=RESOURCE_FILE,
                 sensitivity=[],
                 audio_gain=1):

        def audio_callback(in_data, frame_count, time_info, status):
            self.ring_buffer.extend(in_data)
            play_data = chr(0) * len(in_data)
            return play_data, pyaudio.paContinue

        tm = type(decoder_model)
        ts = type(sensitivity)
        if tm is not list:
            decoder_model = [decoder_model]
        if ts is not list:
            sensitivity = [sensitivity]
        model_str = ",".join(decoder_model)

        self.detector = snowboydetect.SnowboyDetect(
            resource_filename=resource.encode(), model_str=model_str.encode())
        self.detector.SetAudioGain(audio_gain)
        self.num_hotwords = self.detector.NumHotwords()

        if len(decoder_model) > 1 and len(sensitivity) == 1:
            sensitivity = sensitivity*self.num_hotwords
        if len(sensitivity) != 0:
            assert self.num_hotwords == len(sensitivity), \
                "number of hotwords in decoder_model (%d) and sensitivity " \
                "(%d) does not match" % (self.num_hotwords, len(sensitivity))
        sensitivity_str = ",".join([str(t) for t in sensitivity])
        if len(sensitivity) != 0:
            self.detector.SetSensitivity(sensitivity_str.encode())

        self.ring_buffer = RingBuffer(
            self.detector.NumChannels() * self.detector.SampleRate() * 5)
        self.audio = pyaudio.PyAudio()
        self.stream_in = self.audio.open(
            input=True, output=False,
            format=self.audio.get_format_from_width(
                self.detector.BitsPerSample() / 8),
            channels=self.detector.NumChannels(),
            rate=self.detector.SampleRate(),
            frames_per_buffer=2048,
            stream_callback=audio_callback)


    def start(self, detected_callback=perform,
              interrupt_check=lambda: False,
              sleep_time=0.03):
        """
        starts the detector,checks every 0.03 seconds if any keyword has been spoken,
        if yes then call the perform function.If multiples models are specified then you 
        have multiple callback functions each doing something different.
        Also it check for interrupt from keyboard.
        """
        if interrupt_check():
            logger.debug("YES..INTERRUPTED")
            return

        tc = type(detected_callback)
        if tc is not list:
            detected_callback = [detected_callback]
        if len(detected_callback) == 1 and self.num_hotwords > 1:
            detected_callback *= self.num_hotwords

        assert self.num_hotwords == len(detected_callback), \
            "Error: hotwords (%d) do not match the number of " \
            "callbacks (%d)" % (self.num_hotwords, len(detected_callback))

        logger.debug("CHECKING...")

        while True:
            if interrupt_check():
                logger.debug("detect voice break")
                break
            data = self.ring_buffer.get()
            if len(data) == 0:
                time.sleep(sleep_time)
                continue

            ans = self.detector.RunDetection(data)
            if ans == -1:
                logger.warning("ERROR IN INITIALIZATION OR READING AUDIO DATA")
            elif ans > 0:
                message = "Hotword" + str(ans) + " detected: "
                message += time.strftime("%Y-%m-%d %H:%M:%S",
                                         time.localtime(time.time()))
                logger.info(message)
                callback = detected_callback[ans-1]
                if callback is not None:
                    callback()

        logger.debug("finished.")

    def terminate(self):
        """ Kills the program"""
        self.stream_in.stop_stream()
        self.stream_in.close()
        self.audio.terminate()
