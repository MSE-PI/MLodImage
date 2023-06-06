from torch.utils.data import DataLoader, Dataset, random_split
import pytorch_lightning as pl
from pytorch_lightning.loggers import WandbLogger

import yaml
import wandb
import pandas as pd
import os
import json
from datetime import datetime
from model.audio_utils import AudioUtils
from model.audio_cnn import AudioCNN

os.environ['WANDB_API_KEY'] = 'bd1669cb234715abd86c4a22de2e756e7013190c'

DATA_DIR: str = os.path.join(os.getcwd(), 'data')
AUDIO_DIR: str = os.path.join(DATA_DIR, 'raw', 'audio')
METADATA: pd.DataFrame = pd.read_csv(os.path.join(DATA_DIR, 'prepared', 'train_genres.csv'))
ID_TO_LABEL: dict = METADATA.set_index('genre_id')['genre_label'].to_dict()
NB_CLASSES: int = len(ID_TO_LABEL)
PARAMS = yaml.safe_load(open("params.yaml"))
TRAIN_PARAMS = PARAMS['train']
AUDIO_PARAMS = PARAMS['audio']

# set the config for wandb (train params + audio params)
config = {**TRAIN_PARAMS, **AUDIO_PARAMS}
wandb.init(project='genre-detector', entity='mlodimage', config=config, name='training_' + datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))

class GenreDataset(Dataset):
    """
    Genre dataset.
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
        audio = AudioUtils.time_shift(audio, AUDIO_PARAMS['time_shift'])
        mel_spectrogram = AudioUtils.mel_spectrogram(audio)

        return (mel_spectrogram, genre_id)
    
def main():
    dataset = GenreDataset(METADATA, AUDIO_DIR)

    # split the dataset into train and validation sets
    val_size = int(TRAIN_PARAMS['val_split'] * len(dataset))
    train_size = len(dataset) - val_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])

    # create the dataloaders
    train_loader = DataLoader(train_dataset, batch_size=TRAIN_PARAMS['batch_size'], shuffle=True, num_workers=TRAIN_PARAMS['nb_workers'])
    val_loader = DataLoader(val_dataset, batch_size=TRAIN_PARAMS['batch_size'], shuffle=False, num_workers=TRAIN_PARAMS['nb_workers'])

    # create the model
    model = AudioCNN(nb_channels=AUDIO_PARAMS['nb_channels'], nb_classes=NB_CLASSES, lr=TRAIN_PARAMS['init_lr'])

    # checkpoint callback to save only the best model
    checkpoint_callback = pl.callbacks.ModelCheckpoint(
        dirpath=os.path.join(os.getcwd(), 'src', 'model'),
        save_top_k=1,
        verbose=True,
        monitor='val_loss',
        filename='model',
        mode='min',
    )

    trainer = pl.Trainer(
        accelerator='auto',
        devices='auto',
        max_epochs=TRAIN_PARAMS['max_epochs'],
        logger=WandbLogger(),
        callbacks=[checkpoint_callback])
        
    # train the model
    trainer.fit(model, train_loader, val_loader)

    # export id_to_label dict
    with open(os.path.join(os.getcwd(), 'src', 'model', 'id_to_label.json'), 'w') as fp:
        json.dump(ID_TO_LABEL, fp, indent=4)

    # save the url wandb run
    with open(os.path.join(os.getcwd(), 'wandb_training_url.txt'), 'w') as f:
        f.write(wandb.run.get_url())

if __name__ == "__main__":
    main()