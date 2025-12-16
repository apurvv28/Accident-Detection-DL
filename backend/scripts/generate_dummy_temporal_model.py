"""Generate a dummy temporal model for testing.

Run:
    python -m backend.scripts.generate_dummy_temporal_model

This will write `static/models/temporal_accident.pth` if PyTorch is available.
"""
import os

try:
    import torch
except Exception:
    print("PyTorch not available. Please install torch to generate the temporal model.")
    raise

from backend.models.temporal_analyzer import AccidentConvLSTM

MODEL_PATH = os.getenv('TEMPORAL_MODEL_PATH', 'static/models/temporal_accident.pth')

def main():
    dirpath = os.path.dirname(MODEL_PATH)
    if dirpath and not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)

    model = AccidentConvLSTM(input_channels=1, hidden_dim=8)
    try:
        torch.save(model.state_dict(), MODEL_PATH)
        print(f"Dummy temporal model saved to: {MODEL_PATH}")
    except Exception as e:
        print(f"Failed to save model: {e}")

if __name__ == '__main__':
    main()
