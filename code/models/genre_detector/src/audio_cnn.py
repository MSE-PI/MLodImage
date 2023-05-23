import torch.nn as nn
import torch
import torch.nn.functional as F
import torchmetrics
import pytorch_lightning as pl


class AudioCNN(pl.LightningModule):
    """
    Audio classification convolutional neural network.
    """
    def __init__(self, nb_classes):
        """
        Constructor.
        :param nb_classes: the number of classes
        :type nb_classes: int
        """
        super(AudioCNN, self).__init__()
        self.nb_classes = nb_classes
        self.conv1 = nn.Conv2d(2, 32, kernel_size=(3, 3), stride=(1, 1))
        self.convnorm1 = nn.BatchNorm2d(32)
        self.pool1 = nn.MaxPool2d(kernel_size=(2, 4))
        self.conv2 = nn.Conv2d(32, 64, kernel_size=(3, 3), stride=(1, 1))
        self.convnorm2 = nn.BatchNorm2d(64)
        self.pool2 = nn.MaxPool2d(kernel_size=(2, 4))
        self.linear1 = nn.Linear(64*14*160, 256)
        self.linear1_bn = nn.BatchNorm1d(256)
        self.drop = nn.Dropout(0.4)
        self.linear2 = nn.Linear(256, self.nb_classes)
        self.act = nn.LeakyReLU()

        self.accuracy = torchmetrics.Accuracy(task='multiclass', num_classes=self.nb_classes)

    def forward(self, x):
        """
        Forward pass.
        :param x: the input
        :type x: torch.Tensor
        :return: the output
        :rtype: torch.Tensor
        """
        # Conv 1
        x = self.conv1(x)
        x = self.convnorm1(x)
        x = self.act(x)
        x = self.pool1(x) # output of shape (batch_size, 32, 31, 644)
        # Conv 2
        x = self.conv2(x) # output of shape (batch_size, 64, 29, 642)
        x = self.convnorm2(x)
        x = self.act(x)
        x = self.pool2(x) # output of shape (batch_size, 64, 14, 160)
        # Linear 1
        x = x.view(x.size(0), -1)
        x = self.linear1(x)
        x = self.linear1_bn(x)
        x = self.act(x)
        x = self.drop(x)
        # Linear 2
        x = self.linear2(x)
        return x
    
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
        x, y = batch
        y_hat = self.forward(x)
        loss = F.cross_entropy(y_hat, y)
        self.log('train_loss', loss, on_step=False, on_epoch=True)
        self.log('train_acc', self.accuracy(y_hat, y), on_step=False, on_epoch=True)
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
        x, y = batch
        y_hat = self.forward(x)
        loss = F.cross_entropy(y_hat, y)
        self.log('val_loss', loss, on_step=False, on_epoch=True)
        self.log('val_acc', self.accuracy(y_hat, y), on_step=False, on_epoch=True)
        return loss
    
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
        x, y = batch
        y_hat = self.forward(x)
        loss = F.cross_entropy(y_hat, y)
        self.log('test_loss', loss, on_step=False, on_epoch=True)
        self.log('test_acc', self.accuracy(y_hat, y), on_step=False, on_epoch=True)
        return loss
    
    def configure_optimizers(self):
        """
        Configure optimizers.
        :return: the optimizer
        :rtype: torch.optim.Optimizer
        """
        optimizer = torch.optim.Adam(self.parameters(), lr=1e-3)
        return optimizer
    
    def predict_step(self, batch, batch_idx, dataloader_idx=0):
        return self(batch)