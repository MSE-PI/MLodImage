from torch.utils.data import DataLoader, Dataset
from dvclive import Live
import torch

import yaml
import pandas as pd
import os
import json
from tqdm import tqdm
import numpy as np

from model.audio_utils import AudioUtils
from model.audio_cnn import AudioCNN


DATA_DIR: str = os.path.join(os.getcwd(), 'data')
AUDIO_DIR: str = os.path.join(DATA_DIR, 'raw', 'audio')
METADATA: pd.DataFrame = pd.read_csv(os.path.join(DATA_DIR, 'prepared', 'test_genres.csv'))
with open(os.path.join(os.getcwd(), 'src', 'model', 'id_to_label.json')) as f:
    ID_TO_LABEL = json.load(f)
NB_CLASSES: int = len(ID_TO_LABEL)
PARAMS = yaml.safe_load(open("params.yaml"))
TEST_PARAMS = PARAMS['evaluate']
AUDIO_PARAMS = PARAMS['audio']

torch.multiprocessing.set_sharing_strategy('file_system')

class GenreDataset(Dataset):
    """
    Dataset for the FMA dataset.
    """
    def __init__(self, df, audio_dir):
        """
        Constructor.
        :param df: the dataframe containing the audio files ids and their genre label
        :type df: pandas.DataFrame
        :param audio_dir: the directory containing the audio files
        :type audio_dir: str
        """
        self.fma_df = df
        self.audio_dir = audio_dir
        
    def __len__(self):
        """
        Get the length of the dataset.
        :return: the length of the dataset
        :rtype: int
        """
        return len(self.fma_df)
    
    def __getitem__(self, idx):
        """
        Get the idx-th sample of the dataset.
        :param idx: the index of the sample
        :type idx: int
        :return: the idx-th sample of the dataset and its genre label
        :rtype: Tuple[torch.Tensor, int]
        """ 
        audio_file_path = os.path.join(self.audio_dir, str(self.fma_df.iloc[idx]['filename']))
        # get the genre class id
        genre_id = self.fma_df.iloc[idx]['genre_id']

        # load the audio file and apply the preprocessing
        audio = AudioUtils.open(audio_file_path)
        audio = AudioUtils.rechannel(audio, AUDIO_PARAMS['nb_channels'])
        audio = AudioUtils.resample(audio, AUDIO_PARAMS['sample_rate'])
        audio = AudioUtils.pad_truncate(audio, AUDIO_PARAMS['audio_duration'])
        mel_spectrogram = AudioUtils.mel_spectrogram(audio)

        return (mel_spectrogram, genre_id)
    
def main():
    test_dataset = GenreDataset(METADATA, AUDIO_DIR)
    test_loader = DataLoader(test_dataset, batch_size=TEST_PARAMS['batch_size'], shuffle=False, num_workers=TEST_PARAMS['nb_workers'])

    with Live(dir='dvc_logs', report='html') as live:
        model = AudioCNN.load_from_checkpoint(os.path.join(os.getcwd(), 'src', 'model', 'model.ckpt'), nb_classes=NB_CLASSES)
        model.eval()

        # evaluation
        print('Getting predictions...')

        # get all the predictions
        y_pred = []
        y_true = []
        for batch in tqdm(test_loader):
            x, y = batch
            x = x.to(model.device)
            y_true.append(y)
            with torch.no_grad():
                y_pred.append(torch.argmax(model(x), dim=1))

        # convert the predictions to a numpy array
        y_pred = torch.cat(y_pred).cpu().numpy()
        y_true = torch.cat(y_true).cpu().numpy()

        # log the accuracy
        accuracy = np.sum(y_pred == y_true) / len(y_pred)
        live.log_metric("accuracy", accuracy)

        live.log_sklearn_plot("confusion_matrix", y_true, y_pred, name='cm.json')

        # load the json of the confusion and rename the classes
        with open('dvc_logs/plots/sklearn/cm.json') as f:
            cm = json.load(f)

        # for all "actual" or "predicted" key in the json file, rename the classes
        for element in cm:
            element['actual'] = [ID_TO_LABEL[element['actual']]]
            element['predicted'] = [ID_TO_LABEL[element['predicted']]]

        # save the confusion matrix
        with open('dvc_logs/plots/sklearn/cm.json', 'w') as f:
            json.dump(cm, f, indent=4)


if __name__ == "__main__":
    main()