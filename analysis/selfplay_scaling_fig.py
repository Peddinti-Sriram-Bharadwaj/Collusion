"""Fig 16: two copies of each model playing each other for 15 rounds, with a myopic best-response baseline."""
import json, sys
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.env import LogitBertrandEnv

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlelocation": "left"})
runs, out = Path(sys.argv[1]), Path(sys.argv[2])
env = LogitBertrandEnv(2, 10); g = env.price_grid
br = lambda r: int(np.argmax([env._profits(np.array([g[r], p]))[1] for p in g]))
a = [4, 4]; base = []
for t in range(15):
    a = [br(a[1]), br(a[0])]; base.append(a[0])
models = [m for m in ["0.5b", "1.5b", "3b", "7b", "14b", "32b"] if (runs / f"d1_{m}.json").exists()]
fig, axs = plt.subplots(1, len(models), figsize=(2.9 * len(models), 2.9), sharey=True)
rep = {}
for ax, m in zip(axs, models):
    d = json.load(open(runs / f"d1_{m}.json"))
    G = [x for x in d["games"] if x["strategy"] == "llm_selfplay" and x["condition"] == "none"]
    for x in G:
        a1 = [r["llm_action"] for r in x["rounds"]]; a0 = [r["rival_action"] for r in x["rounds"]]
        lw, al = (2, 1) if x["mode"] == "greedy" else (0.8, 0.35)
        ax.plot(a1, color="#2a6fdb", lw=lw, alpha=al); ax.plot(a0, color="#e07b39", lw=lw, alpha=al, ls="--")
    ax.plot(base, color="#555", lw=1, ls=":")
    dl = float(np.mean([x["collusion_index_joint"] for x in G])); rep[m] = dl
    ax.axhline(7, color="#bbb", lw=0.6); ax.axhline(2, color="#bbb", lw=0.6)
    ax.set_title(f"{m.upper()}  Δ = {dl:.2f}", fontsize=9); ax.set_xlabel("round"); ax.set_ylim(-0.3, 9.3)
axs[0].set_ylabel("price index")
axs[0].plot([], [], color="#2a6fdb", label="firm 1"); axs[0].plot([], [], color="#e07b39", ls="--", label="firm 0")
axs[0].plot([], [], color="#555", ls=":", label="myopic best-response pair"); axs[0].legend(frameon=False, fontsize=7, loc="upper left")
fig.suptitle("Self-play: two copies of the same model price against each other (thick = greedy, thin = 4 sampled games; grey lines at Nash 2 and monopoly 7)",
             fontweight="bold", x=0.01, ha="left", fontsize=9.5)
fig.tight_layout(); fig.savefig(out / "fig16_selfplay_by_size.png", dpi=200)
print(json.dumps(rep))
