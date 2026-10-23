"""Guarded collector; no weights load without explicit approval."""
from __future__ import annotations
import argparse
import torch
from src.interpretability.activation_extractor import HFActivationExtractor
from src.interpretability.balanced_counterfactual_dataset import generate_balanced_scenarios, collect_balanced_counterfactual_dataset
from src.interpretability.hf_episode import save_hf_trajectory

def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument('--allow-model-load',action='store_true'); p.add_argument('--local-files-only',action='store_true'); p.add_argument('--scenarios',type=int,default=12); p.add_argument('--seed',type=int,default=0); p.add_argument('--layers',type=int,nargs='+'); p.add_argument('--output',default='artifacts/interpretability/balanced-counterfactual-dataset.json'); a=p.parse_args()
    if not a.allow_model_load: p.error('Refusing to load model weights without --allow-model-load.')
    ex=HFActivationExtractor.from_pretrained('Qwen/Qwen2.5-0.5B-Instruct',revision='7ae557604adf67be50417f59c2c2f167def9a775',device_map='auto',torch_dtype=torch.float16,local_files_only=a.local_files_only)
    try: save_hf_trajectory(a.output,collect_balanced_counterfactual_dataset(ex,generate_balanced_scenarios(a.scenarios,a.seed),selected_layers=a.layers))
    finally: ex.close()
if __name__=='__main__': main()
