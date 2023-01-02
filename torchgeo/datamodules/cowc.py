# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""COWC datamodule."""

from typing import Any

import kornia.augmentation as K
from torch.utils.data import random_split

from ..datasets import COWCCounting
from ..transforms import AugmentationSequential
from .geo import NonGeoDataModule


class COWCCountingDataModule(NonGeoDataModule):
    """LightningDataModule implementation for the COWC Counting dataset."""

    def __init__(
        self, batch_size: int = 64, num_workers: int = 0, **kwargs: Any
    ) -> None:
        """Initialize a new COWCCountingDataModule instance.

        Args:
            batch_size: Size of each mini-batch.
            num_workers: Number of workers for parallel data loading.
            **kwargs: Additional keyword arguments passed to
                :class:`~torchgeo.datasets.COWCCounting`.
        """
        super().__init__(COWCCounting, batch_size, num_workers, **kwargs)

        self.aug = AugmentationSequential(
            K.Normalize(mean=0.0, std=255.0), data_keys=["image"]
        )

    def setup(self, stage: str) -> None:
        """Set up datasets.

        Args:
            stage: Either 'fit', 'validate', 'test', or 'predict'.
        """
        train_val_dataset = COWCCounting(split="train", **self.kwargs)
        self.test_dataset = COWCCounting(split="test", **self.kwargs)
        self.train_dataset, self.val_dataset = random_split(
            train_val_dataset,
            [len(train_val_dataset) - len(self.test_dataset), len(self.test_dataset)],
        )
