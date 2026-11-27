"""The torch backend of ``fione.engine.embedding``: the mean over a text's tokens of one hidden
layer of a causal or masked language model. Torch and transformers are imported when a backend
is built, so Fione runs without them everywhere the vectors are only read from the cache.

The model is read from the directory in ``FIONE_EMBEDDING_MODEL_DIR`` (a Hugging Face model
directory); ``EmbeddingSpec.model`` is only its label. The layer is ``round(layer * depth)``."""

import os
from collections.abc import Sequence

import numpy as np

from fione.engine.embedding import MODEL_ENV, EmbeddingSpec, EmbeddingUnavailable

BATCH = 16


class TorchLMBackend:
    def __init__(self, spec: EmbeddingSpec):
        import torch
        from transformers import AutoModel, AutoTokenizer

        directory = os.environ.get(MODEL_ENV)
        if not directory:
            raise EmbeddingUnavailable(f"set {MODEL_ENV} to the directory of the model")
        self.spec, self._torch = spec, torch
        self.device = (
            "cuda"
            if torch.cuda.is_available()
            else "mps"
            if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()
            else "cpu"
        )
        dtype = torch.float16 if self.device != "cpu" else torch.float32
        self.tokenizer = AutoTokenizer.from_pretrained(directory)
        self.tokenizer.padding_side = "right"
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model = self._load(AutoModel, directory, dtype)
        depth = self.model.config.num_hidden_layers
        self.layer = max(1, min(depth, round(spec.layer * depth)))

    def _load(self, auto_model, directory: str, dtype):
        """The model on the GPU, or spread over several (a model larger than one of them); on
        another device, or where ``accelerate`` is missing, all on the one device."""
        if self.device == "cuda":
            try:
                model = auto_model.from_pretrained(directory, dtype=dtype, device_map="auto")
                self.device = model.device
                return model.eval()
            except (ImportError, ValueError):
                pass
        return auto_model.from_pretrained(directory, dtype=dtype).to(self.device).eval()

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        torch = self._torch
        order = np.argsort([len(t) for t in texts], kind="stable")  # similar lengths per batch
        out = None
        for start in range(0, len(texts), BATCH):
            at = order[start : start + BATCH]
            batch = self.tokenizer(
                [texts[i] or " " for i in at],  # a text of no tokens would be a batch of none
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self.spec.max_length,
            ).to(self.device)
            with torch.no_grad():
                states = self.model(**batch, output_hidden_states=True).hidden_states[self.layer]
            mask = batch["attention_mask"].unsqueeze(-1).to(states.device, torch.float32)
            mean = (states.float() * mask).sum(1) / mask.sum(1).clamp(min=1)
            if out is None:
                out = np.zeros((len(texts), mean.shape[1]), dtype=np.float32)
            out[at] = mean.float().cpu().numpy()
        return out if out is not None else np.zeros((0, 0), dtype=np.float32)
