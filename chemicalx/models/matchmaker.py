"""An implementation of the MatchMaker model."""

import torch
from torch import nn

from chemicalx.data import DrugPairBatch
from chemicalx.models import Model

__all__ = [
    "MatchMaker",
]


class MatchMaker(Model):
    """An implementation of the MatchMaker model from [matchmaker]_.

    .. [matchmaker] `MatchMaker: A Deep Learning Framework for Drug Synergy Prediction
       <https://www.biorxiv.org/content/10.1101/2020.05.24.113241v3.full>`_
    """

    def __init__(
        self,
        *,
        context_channels: int,
        drug_channels: int,
        input_hidden_channels: int = 32,
        middle_hidden_channels: int = 32,
        final_hidden_channels: int = 32,
        out_channels: int = 1,
        dropout_rate: float = 0.5,
    ):
        """Instantiate the MatchMaker model.

        :param context_channels: The number of context features.
        :param drug_channels: The number of drug features.
        :param input_hidden_channels: The number of hidden layer neurons in the input layer.
        :param middle_hidden_channels: The number of hidden layer neurons in the middle layer.
        :param final_hidden_channels: The number of hidden layer neurons in the final layer.
        :param out_channels: The number of output channels.
        :param dropout_rate: The rate of dropout before the scoring head is used.
        """
        super().__init__()
        #: Applied to the left+context and right+context separately
        self.drug_context_layer = nn.Sequential(
            nn.Linear(drug_channels + context_channels, input_hidden_channels),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(input_hidden_channels, middle_hidden_channels),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(middle_hidden_channels, middle_hidden_channels),
        )
        # Applied to the concatenated left/right tensors
        self.final = nn.Sequential(
            nn.Linear(2 * middle_hidden_channels, final_hidden_channels),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(final_hidden_channels, out_channels),
            nn.Sigmoid(),
        )

    def unpack(self, batch: DrugPairBatch):
        """Return the context features, left drug features, and right drug features."""
        return (
            batch.context_features,
            batch.drug_features_left,
            batch.drug_features_right,
        )

    def forward(
        self,
        context_features: torch.FloatTensor,
        drug_features_left: torch.FloatTensor,
        drug_features_right: torch.FloatTensor,
    ) -> torch.FloatTensor:
        """
        Run a forward pass of the MatchMaker model.

        Args:
            context_features: A matrix of biological context features.
            drug_features_left: A matrix of head drug features.
            drug_features_right: A matrix of tail drug features.
        Returns:
            hidden: A column vector of predicted synergy scores.
        """
        # The left drug
        hidden_left = torch.cat([context_features, drug_features_left], dim=1)
        hidden_left = self.drug_context_layer(hidden_left)

        # The right drug
        hidden_right = torch.cat([context_features, drug_features_right], dim=1)
        hidden_right = self.drug_context_layer(hidden_right)

        # Merged
        hidden_merged = torch.cat([hidden_left, hidden_right], dim=1)
        hidden_merged = self.final(hidden_merged)

        return hidden_merged
