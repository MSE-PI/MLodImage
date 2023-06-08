
import torchaudio
import torch.nn.functional as F
import torch
import random

class AudioUtils():
    """
    Utility class for audio processing.
    """
    @staticmethod
    def open(audio_file: str):
        """
        Load an audio file. Return the signal as a tensor and the sample rate.
        :param audio_file : Path to the audio file.
        :type audio_file : str
        :return: signal as a tensor and the sample rate
        :rtype: Tuple[torch.Tensor, int]
        """
        signal, sample_rate = torchaudio.load(audio_file)
        return signal, sample_rate
    
    @staticmethod
    def rechannel(audio, new_channel):
        """
        Convert a given audio to the specified number of channels.
        :param audio: the audio, composed of the signal and the sample rate
        :type audio: Tuple[torch.Tensor, int]
        :param new_channel: the target number of channels
        :type new_channel: int
        :return: the audio with the target number of channels
        :rtype: Tuple[torch.Tensor, int]
        """
        signal, sample_rate = audio

        if signal.shape[0] == new_channel:
            # nothing to do as the signal already has the target number of channels
            return audio
        if new_channel == 1:
            # convert to mono by selecting only the first channel
            signal = signal[:1, :]
        else:
            # convert to stereo by duplicating the first channel
            signal = torch.cat([signal, signal])
        return signal, sample_rate
    
    @staticmethod
    def resample(audio, new_sample_rate):
        """
        Change the sample rate of the audio signal.
        :param audio: the audio, composed of the signal and the sample rate
        :type audio: Tuple[torch.Tensor, int]
        :param new_sample_rate: the target sample rate
        :type new_sample_rate: int
        :return: the audio with the target sample rate
        :rtype: Tuple[torch.Tensor, int]
        """
        signal, sample_rate = audio
        if sample_rate == new_sample_rate:
            # nothing to do
            return audio
        resample = torchaudio.transforms.Resample(sample_rate, new_sample_rate)
        signal = resample(signal)
        return signal, new_sample_rate
    
    @staticmethod
    def pad_truncate(audio, length):
        """
        Pad or truncate an audio signal to a fixed length (in ms).
        :param audio: the audio, composed of the signal and the sample rate
        :type audio: Tuple[torch.Tensor, int]
        :param length: the target length in ms
        :type length: int
        :return: the audio with the target length
        :rtype: Tuple[torch.Tensor, int]
        """
        signal, sample_rate = audio
        max_length = sample_rate//1000 * length

        if signal.shape[1] > max_length:
            signal = signal[:, :max_length]
        elif signal.shape[1] < max_length:
            padding = max_length - signal.shape[1]
            signal = F.pad(signal, (0, padding))
        return signal, sample_rate

    @staticmethod
    def time_shift(audio, shift_limit):
        """
        Shift the signal to the left or right by some percent. Values at the end
        are 'wrapped around' to the start of the transformed signal.
        :param audio: the audio, composed of the signal and the sample rate
        :type audio: Tuple[torch.Tensor, int]
        :param shift_limit: the maximum shift to apply (in percent)
        :type shift_limit: int
        :return: the shifted audio
        :rtype: Tuple[torch.Tensor, int]
        """
        signal, sample_rate = audio
        _, signal_length = signal.shape
        shift_amount = int(random.random() * shift_limit * signal_length)
        return (signal.roll(shift_amount), sample_rate)
    
    @staticmethod
    def mel_spectrogram(audio, n_mels=64, n_fft=2048, hop_length=None):
        """
        Create the mel spectogram for the given audio signal.
        :param audio: the audio, composed of the signal and the sample rate
        :type audio: Tuple[torch.Tensor, int]
        :param n_mels: the number of mel filterbanks
        :type n_mels: int
        :param n_fft: the size of the FFT
        :type n_fft: int
        :param hop_length: the length of hop between STFT windows
        :type hop_length: int
        :return: the mel spectogram
        :rtype: torch.Tensor
        """
        signal, sample_rate = audio
        
        mel_spectrogram = torchaudio.transforms.MelSpectrogram(
            sample_rate,
            n_fft=n_fft,
            hop_length=hop_length,
            n_mels=n_mels
        )(signal)

        # convert to decibels
        mel_spectrogram = torchaudio.transforms.AmplitudeToDB(top_db=80)(mel_spectrogram)

        return mel_spectrogram