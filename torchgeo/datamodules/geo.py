# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Base classes for all :mod:`torchgeo` data modules."""

from typing import Any, Dict, Optional, Type

import kornia.augmentation as K
import matplotlib.pyplot as plt
import torch
from pytorch_lightning import LightningDataModule

# TODO: import from lightning_lite instead
from pytorch_lightning.utilities.exceptions import (  # type: ignore[attr-defined]
    MisconfigurationException,
)
from torch import Tensor
from torch.nn import Module
from torch.utils.data import DataLoader, Dataset

from ..datasets import NonGeoDataset
from ..transforms import AugmentationSequential


class NonGeoDataModule(LightningDataModule):
    """Base class for data modules lacking geospatial information."""

    mean = torch.tensor(0)
    std = torch.tensor(255)

    def __init__(
        self,
        dataset_class: Type[NonGeoDataset],
        batch_size: int = 1,
        num_workers: int = 0,
        **kwargs: Any,
    ) -> None:
        """Initialize a new NonGeoDataModule instance.

        Args:
            dataset_class: Class used to instantiate a new dataset.
            batch_size: Size of each mini-batch.
            num_workers: Number of workers for parallel data loading.
            **kwargs: Additional keyword arguments passed to ``dataset_class``
        """
        super().__init__()

        self.dataset_class = dataset_class
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.kwargs = kwargs

        # Datasets
        self.train_dataset: Optional[Dataset[Dict[str, Tensor]]] = None
        self.val_dataset: Optional[Dataset[Dict[str, Tensor]]] = None
        self.test_dataset: Optional[Dataset[Dict[str, Tensor]]] = None
        self.predict_dataset: Optional[Dataset[Dict[str, Tensor]]] = None

        # Data loaders
        self.train_batch_size: Optional[int] = None
        self.val_batch_size: Optional[int] = None
        self.test_batch_size: Optional[int] = None
        self.predict_batch_size: Optional[int] = None

        # Data augmentation
        self.aug: Module = AugmentationSequential(
            K.Normalize(mean=self.mean, std=self.std), data_keys=["image"]
        )
        self.train_aug: Optional[Module] = None
        self.val_aug: Optional[Module] = None
        self.test_aug: Optional[Module] = None
        self.predict_aug: Optional[Module] = None

    def prepare_data(self) -> None:
        """Download and prepare data.

        During distributed training, this method is called only within a single process
        to avoid corrupted data. This method should not set state since it is not called
        on every device, use :meth:`setup` instead.
        """
        if self.kwargs.get("download", False):
            self.dataset_class(**self.kwargs)

    def setup(self, stage: str) -> None:
        """Set up datasets.

        Called at the beginning of fit, validate, test, or predict. During distributed
        training, this method is called from every process across all the nodes. Setting
        state here is recommended.

        Args:
            stage: Either 'fit', 'validate', 'test', or 'predict'.
        """
        if stage in ["fit"]:
            self.train_dataset = self.dataset_class(  # type: ignore[call-arg]
                split="train", **self.kwargs
            )
        elif stage in ["fit", "validate"]:
            self.val_dataset = self.dataset_class(  # type: ignore[call-arg]
                split="val", **self.kwargs
            )
        elif stage in ["test"]:
            self.test_dataset = self.dataset_class(  # type: ignore[call-arg]
                split="test", **self.kwargs
            )

    def train_dataloader(self) -> DataLoader[Dict[str, Tensor]]:
        """Implement one or more PyTorch DataLoaders for training.

        Returns:
            A collection of data loaders specifying training samples.

        Raises:
            MisconfigurationException: If :meth:`setup` does not define a
                'train_dataset'.
        """
        if self.train_dataset is not None:
            return DataLoader(
                dataset=self.train_dataset,
                batch_size=self.train_batch_size or self.batch_size,
                shuffle=True,
                num_workers=self.num_workers,
            )
        else:
            msg = f"{self.__class__.__name__}.setup does not define a 'train_dataset'"
            raise MisconfigurationException(msg)

    def val_dataloader(self) -> DataLoader[Dict[str, Tensor]]:
        """Implement one or more PyTorch DataLoaders for validation.

        Returns:
            A collection of data loaders specifying validation samples.

        Raises:
            MisconfigurationException: If :meth:`setup` does not define a
                'val_dataset'.
        """
        if self.val_dataset is not None:
            return DataLoader(
                dataset=self.val_dataset,
                batch_size=self.val_batch_size or self.batch_size,
                shuffle=False,
                num_workers=self.num_workers,
            )
        else:
            msg = f"{self.__class__.__name__}.setup does not define a 'val_dataset'"
            raise MisconfigurationException(msg)

    def test_dataloader(self) -> DataLoader[Dict[str, Tensor]]:
        """Implement one or more PyTorch DataLoaders for testing.

        Returns:
            A collection of data loaders specifying testing samples.

        Raises:
            MisconfigurationException: If :meth:`setup` does not define a
                'test_dataset'.
        """
        if self.test_dataset is not None:
            return DataLoader(
                dataset=self.test_dataset,
                batch_size=self.test_batch_size or self.batch_size,
                shuffle=False,
                num_workers=self.num_workers,
            )
        else:
            msg = f"{self.__class__.__name__}.setup does not define a 'test_dataset'"
            raise MisconfigurationException(msg)

    def predict_dataloader(self) -> DataLoader[Dict[str, Tensor]]:
        """Implement one or more PyTorch DataLoaders for prediction.

        Returns:
            A collection of data loaders specifying prediction samples.

        Raises:
            MisconfigurationException: If :meth:`setup` does not define a
                'predict_dataset'.
        """
        if self.predict_dataset is not None:
            return DataLoader(
                dataset=self.predict_dataset,
                batch_size=self.predict_batch_size or self.batch_size,
                shuffle=False,
                num_workers=self.num_workers,
            )
        else:
            msg = f"{self.__class__.__name__}.setup does not define a 'predict_dataset'"
            raise MisconfigurationException(msg)

    def on_after_batch_transfer(
        self, batch: Dict[str, Tensor], dataloader_idx: int
    ) -> Dict[str, Tensor]:
        """Apply batch augmentations to the batch after it is transferred to the device.

        Args:
            batch: A batch of data that needs to be altered or augmented.
            dataloader_idx: The index of the dataloader to which the batch belongs.

        Returns:
            A batch of data.
        """
        if self.trainer:
            if self.trainer.training:
                aug = self.train_aug or self.aug
            elif self.trainer.validating:
                aug = self.val_aug or self.aug
            elif self.trainer.testing:
                aug = self.test_aug or self.aug
            elif self.trainer.predicting:
                aug = self.predict_aug or self.aug

            batch = aug(batch)

        return batch

    def plot(self, *args: Any, **kwargs: Any) -> plt.Figure:
        """Run the plot method of the dataset if one exists.

        Args:
            *args: Arguments passed to plot method.
            **kwargs: Keyword arguments passed to plot method.

        Returns:
            A matplotlib Figure with the image, ground truth, and predictions.
        """
        if self.val_dataset is not None:
            if hasattr(self.val_dataset, "plot"):
                return self.val_dataset.plot(*args, **kwargs)
