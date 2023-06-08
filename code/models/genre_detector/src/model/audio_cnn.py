import torch.nn as nn
import torch
import torch.nn.functional as F
from torchmetrics.functional import accuracy
import pytorch_lightning as pl

class AudioCNN(pl.LightningModule):
    """
    Audio classification model.
    """
    def __init__(self, nb_channels, nb_classes, lr=0.001):
        """
        Constructor.
        :param nb_channels: the number of channels in the input data
        :type nb_channels: int
        :param nb_classes: the number of classes
        :type nb_classes: int
        :param lr: the learning rate
        :type lr: float
        """
        super(AudioCNN, self).__init__()
        conv_layers = []

        self.conv1 = nn.Conv2d(nb_channels, 8, kernel_size=(5, 5), stride=(2, 2), padding=(2, 2))
        self.relu1 = nn.ReLU()
        self.bn1 = nn.BatchNorm2d(8)
        nn.init.kaiming_normal_(self.conv1.weight, a=0.1)
        self.conv1.bias.data.zero_()
        conv_layers += [self.conv1, self.relu1, self.bn1]

        self.conv2 = nn.Conv2d(8, 16, kernel_size=(3, 3), stride=(2, 2), padding=(1, 1))
        self.relu2 = nn.ReLU()
        self.bn2 = nn.BatchNorm2d(16)
        nn.init.kaiming_normal_(self.conv2.weight, a=0.1)
        self.conv2.bias.data.zero_()
        conv_layers += [self.conv2, self.relu2, self.bn2]

        self.conv3 = nn.Conv2d(16, 32, kernel_size=(3, 3), stride=(2, 2), padding=(1, 1))
        self.relu3 = nn.ReLU()
        self.bn3 = nn.BatchNorm2d(32)
        nn.init.kaiming_normal_(self.conv3.weight, a=0.1)
        self.conv3.bias.data.zero_()
        conv_layers += [self.conv3, self.relu3, self.bn3]

        self.conv4 = nn.Conv2d(32, 64, kernel_size=(3, 3), stride=(2, 2), padding=(1, 1))
        self.relu4 = nn.ReLU()
        self.bn4 = nn.BatchNorm2d(64)
        nn.init.kaiming_normal_(self.conv4.weight, a=0.1)
        self.conv4.bias.data.zero_()
        conv_layers += [self.conv4, self.relu4, self.bn4]

        self.conv5 = nn.Conv2d(64, 128, kernel_size=(3, 3), stride=(2, 2), padding=(1, 1))
        self.relu5 = nn.ReLU()
        self.bn5 = nn.BatchNorm2d(128)
        nn.init.kaiming_normal_(self.conv5.weight, a=0.1)
        self.conv5.bias.data.zero_()
        conv_layers += [self.conv5, self.relu5, self.bn5]

        self.ap = nn.AdaptiveAvgPool2d(output_size=1)
        self.linear = nn.Linear(in_features=128, out_features=nb_classes, bias=True)

        self.conv = nn.Sequential(*conv_layers)

        # loss function
        self.loss = nn.CrossEntropyLoss()

        # optimizer parameters
        self.lr = lr

        # number of classes
        self.nb_classes = nb_classes

        # save hyperparameters
        self.save_hyperparameters()

    def forward(self, x):
        """
        Forward pass.
        :param x: the input
        :type x: torch.Tensor
        :return: the output
        :rtype: torch.Tensor
        """
        x = self.conv(x)
        x = self.ap(x)
        x = x.view(x.shape[0], -1)
        return self.linear(x)
    
    def training_step(self, batch, batch_idx):
        """
        Training step.
        :param batch: the batch
        :type batch: Tuple[torch.Tensor, torch.Tensor]
        :param batch_idx: the batch index
        :type batch_idx: int
        :return: the loss
        :rtype: torch.Tensor
        """
        _, loss, acc = self._get_preds_loss_accuracy(batch)

        self.log('train_loss', loss, on_step=False, on_epoch=True, prog_bar=True)
        self.log('train_acc', acc, on_step=False, on_epoch=True, prog_bar=True)

        return loss
    
    def validation_step(self, batch, batch_idx):
        """
        Validation step.
        :param batch: the batch
        :type batch: Tuple[torch.Tensor, torch.Tensor]
        :param batch_idx: the batch index
        :type batch_idx: int
        :return: the loss
        :rtype: torch.Tensor
        """
        _, loss, acc = self._get_preds_loss_accuracy(batch)

        self.log('val_loss', loss, on_step=False, on_epoch=True, prog_bar=True)
        self.log('val_acc', acc, on_step=False, on_epoch=True, prog_bar=True)
    
    def test_step(self, batch, batch_idx):
        """
        Test step.
        :param batch: the batch
        :type batch: Tuple[torch.Tensor, torch.Tensor]
        :param batch_idx: the batch index
        :type batch_idx: int
        :return: the loss
        :rtype: torch.Tensor
        """
        _, loss, acc = self._get_preds_loss_accuracy(batch)

        self.log('test_loss', loss)
        self.log('test_acc', acc)
    
    def configure_optimizers(self):
        """
        Configure optimizers.
        :return: the optimizer
        :rtype: torch.optim.Optimizer
        """
        optimizer = torch.optim.Adam(self.parameters(), lr=self.lr)
        return optimizer
    
    def _get_preds_loss_accuracy(self, batch):
        """
        Get predictions, loss and accuracy."""
        x, y = batch
        logits = self(x)
        preds = torch.argmax(logits, dim=1)
        loss = self.loss(logits, y)
        acc = accuracy(preds, y, 'multiclass', num_classes=self.nb_classes)
        return preds, loss, acc