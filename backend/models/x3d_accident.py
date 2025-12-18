"""Wrapper for X3D from PyTorchVideo to be used as a lightweight accident model head."""
from __future__ import annotations
import logging
import os
from typing import Optional

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class X3DAccidentModel(nn.Module):
    """Loads an X3D backbone and attaches a small head that outputs a single logit.

    - If a `checkpoint_path` is provided and contains `model_state`, it will be
      applied to the backbone (best-effort, non-strict).
    - The head is dynamically sized based on the backbone output dimension.
    """

    def __init__(self, checkpoint_path: Optional[str] = None, device: str = "cpu"):
        super().__init__()
        self.device = device
        self.backbone = None
        self.head = None

        # Attempt to load X3D via torch.hub (pytorchvideo)
        try:
            logger.info("Loading X3D backbone (torch.hub)")
            # This uses the pytorchvideo repository's hubconf
            self.backbone = torch.hub.load("facebookresearch/pytorchvideo", "x3d_xs", pretrained=False)
            self.backbone.to(self.device)
            self.backbone.eval()
        except Exception as e:
            logger.error("Failed to instantiate X3D backbone: %s", e)
            raise

        # If checkpoint path available, try to load model_state
        if checkpoint_path and os.path.exists(checkpoint_path):
            try:
                ck = torch.load(checkpoint_path, map_location=self.device)
                model_state = None
                if isinstance(ck, dict):
                    # PyTorchVideo checkpoints often store under 'model_state'
                    model_state = ck.get("model_state") or ck.get("model") or ck.get("model_state_dict")
                if model_state:
                    try:
                        self.backbone.load_state_dict(model_state, strict=False)
                        logger.info("Loaded backbone weights from checkpoint")
                    except Exception as e:
                        logger.warning("Backbone load partial/fallback: %s", e)
            except Exception as e:
                logger.warning("Could not read checkpoint %s: %s", checkpoint_path, e)

        # Build a small head by running a dummy input to find output dims
        try:
            self._build_head_from_dummy()
        except Exception as e:
            logger.warning("Failed to build head from backbone: %s", e)
            logger.warning("X3D model will not be available - falling back to rule-based analysis")
            self.backbone = None
            self.head = None

    def _build_head_from_dummy(self):
        # X3D expects input shape (B, C, T, H, W). Use a small T/H/W for probing.
        with torch.no_grad():
            dummy = torch.zeros((1, 3, 4, 112, 112), dtype=torch.float32, device=self.device)
            out = self.backbone(dummy)
            # out shape is (B, num_classes) for classification models
            out_dim = out.shape[-1]
            # Attach a tiny head on top (num_classes -> 1)
            self.head = nn.Sequential(nn.Linear(out_dim, 64), nn.ReLU(), nn.Linear(64, 1))
            self.head.to(self.device)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward expects input as (B, C, T, H, W), returns logits (B, 1)"""
        if self.backbone is None or self.head is None:
            raise RuntimeError("X3D model not properly initialized")
        features = self.backbone(x)
        logits = self.head(features)
        return logits
