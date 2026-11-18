import os
import sys
import subprocess
import json
import pickle
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

OPRO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, OPRO_ROOT)


def run_experiment(name, cmd_args, output_dir):
    print(f"\n{'='*20} Running: {name} {'='*20}")
    os.makedirs(output_dir, exist_ok=True)
    full_cmd = [
        sys.executable,
        os.path.join(OPRO_ROOT, "opro", "optimization", "optimize_instructions.py"),
        "--dataset=bbh",
        "--task=movie_recommendation",
        "--instruction_pos=Q_begin",
        "--num_search_steps=5",
        "--max_train_samples=10",
        f"--output_dir={output_dir}",
    ] + cmd_args
    print("Command:", " ".join(full_cmd))
    res = subprocess.run(full_cmd, cwd=OPRO_ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error in {name}:")
        print(res.stderr[-2000:])
        raise RuntimeError(f"Experiment {name} failed with return code {res.returncode}")
    print(f"Finished {name} successfully.")


def extract_trajectory(output_dir):
    """Extract step-by-step best accuracy from results_dict.pkl."""
    pkl_path = os.path.join(output_dir, "results_dict.pkl")
    if not os.path.exists(pkl_path):
        return []
    with open(pkl_path, "rb") as f:
        d = pickle.load(f)
    if isinstance(d, dict) and "old_instructions_and_scores" in d:
        data = d["old_instructions_and_scores"]
    elif isinstance(d, list):
        data = d
    else:
        return []

    step_scores = {}
    init_score = 0.0
    for item in data:
        ins = item[0]
        score = float(item[1])
        step = int(item[2])
        if np.isnan(score):
            continue
        if step == -1:
            init_score = max(init_score, score)
        else:
            if step not in step_scores:
                step_scores[step] = []
            step_scores[step].append(score)

    max_step = max(step_scores.keys()) if step_scores else 0
    cum_best = [init_score]
    curr_best = init_score
    for s in range(max_step + 1):
        if s in step_scores:
            curr_best = max(curr_best, max(step_scores[s]))
        cum_best.append(curr_best)
    return cum_best


def main():
    experiments = [
        # Ablations
        (
            "Baseline (Ascending, Scores, 3-Exemplars, T=1.0, N=2)",
            [
                "--instruction_order=ascending",
                "--show_scores=true",
                "--num_exemplars=3",
                "--optimizer_temperature=1.0",
                "--num_generated_instructions_in_each_step=2",
            ],
            "runs/ablations/baseline",
        ),
        (
            "Ablation: Descending Order",
            [
                "--instruction_order=descending",
                "--show_scores=true",
                "--num_exemplars=3",
                "--optimizer_temperature=1.0",
                "--num_generated_instructions_in_each_step=2",
            ],
            "runs/ablations/order_descending",
        ),
        (
            "Ablation: Random Order",
            [
                "--instruction_order=random",
                "--show_scores=true",
                "--num_exemplars=3",
                "--optimizer_temperature=1.0",
                "--num_generated_instructions_in_each_step=2",
            ],
            "runs/ablations/order_random",
        ),
        (
            "Ablation: 0 Exemplars",
            [
                "--instruction_order=ascending",
                "--show_scores=true",
                "--num_exemplars=0",
                "--optimizer_temperature=1.0",
                "--num_generated_instructions_in_each_step=2",
            ],
            "runs/ablations/no_exemplars",
        ),
        (
            "Ablation: No Scores",
            [
                "--instruction_order=ascending",
                "--show_scores=false",
                "--num_exemplars=3",
                "--optimizer_temperature=1.0",
                "--num_generated_instructions_in_each_step=2",
            ],
            "runs/ablations/no_scores",
        ),
        # Sensitivity: Temperature
        (
            "Sensitivity: T=0.0",
            [
                "--instruction_order=ascending",
                "--show_scores=true",
                "--num_exemplars=3",
                "--optimizer_temperature=0.0",
                "--num_generated_instructions_in_each_step=2",
            ],
            "runs/sensitivity/temp_0_0",
        ),
        (
            "Sensitivity: T=0.5",
            [
                "--instruction_order=ascending",
                "--show_scores=true",
                "--num_exemplars=3",
                "--optimizer_temperature=0.5",
                "--num_generated_instructions_in_each_step=2",
            ],
            "runs/sensitivity/temp_0_5",
        ),
        (
            "Sensitivity: T=1.5",
            [
                "--instruction_order=ascending",
                "--show_scores=true",
                "--num_exemplars=3",
                "--optimizer_temperature=1.5",
                "--num_generated_instructions_in_each_step=2",
            ],
            "runs/sensitivity/temp_1_5",
        ),
        # Sensitivity: Batch Size
        (
            "Sensitivity: N=1 (Batch 1)",
            [
                "--instruction_order=ascending",
                "--show_scores=true",
                "--num_exemplars=3",
                "--optimizer_temperature=1.0",
                "--num_generated_instructions_in_each_step=1",
            ],
            "runs/sensitivity/batch_1",
        ),
        (
            "Sensitivity: N=4 (Batch 4)",
            [
                "--instruction_order=ascending",
                "--show_scores=true",
                "--num_exemplars=3",
                "--optimizer_temperature=1.0",
                "--num_generated_instructions_in_each_step=4",
            ],
            "runs/sensitivity/batch_4",
        ),
    ]

    summary_records = []
    trajectories = {}

    for name, args, out_dir in experiments:
        abs_out_dir = os.path.join(OPRO_ROOT, out_dir)
        # Run experiment if results_dict.pkl not present
        if not os.path.exists(os.path.join(abs_out_dir, "results_dict.pkl")):
            run_experiment(name, args, abs_out_dir)
        else:
            print(f"Skipping {name}, already completed at {out_dir}")

        traj = extract_trajectory(abs_out_dir)
        trajectories[name] = traj
        final_best = traj[-1] if traj else 0.0
        init_best = traj[0] if traj else 0.0
        summary_records.append({
            "Experiment": name,
            "Initial Accuracy": f"{init_best * 100:.1f}%",
            "Final Best Accuracy": f"{final_best * 100:.1f}%",
            "Trajectory": [round(x * 100, 1) for x in traj],
            "Output Directory": out_dir,
        })

    # Save summary table
    summary_df = pd.DataFrame(summary_records)
    summary_csv_path = os.path.join(OPRO_ROOT, "runs", "ablation_and_sensitivity_summary.csv")
    summary_df.to_csv(summary_csv_path, index=False)
    print(f"\nSummary saved to {summary_csv_path}")
    print(summary_df[["Experiment", "Initial Accuracy", "Final Best Accuracy"]].to_string())

    # Generate Figures in Paper Style
    plot_figures(trajectories)


def plot_figures(trajectories):
    """Plot figures styled like Figure 5 and Figure 24 in OPRO paper."""
    figures_dir = os.path.join(OPRO_ROOT, "runs", "figures")
    os.makedirs(figures_dir, exist_ok=True)

    # Set paper-like plot style
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Helvetica", "Arial"]
    plt.rcParams["axes.edgecolor"] = "#333333"
    plt.rcParams["axes.linewidth"] = 1.0
    plt.rcParams["grid.color"] = "#E0E0E0"
    plt.rcParams["grid.linestyle"] = "--"
    plt.rcParams["grid.alpha"] = 0.7

    # Figure 1: Ablations (Ordering, Exemplars, Scores)
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5), dpi=300)

    # Subplot A: Instruction Ordering
    ax = axes[0]
    ax.plot(trajectories["Baseline (Ascending, Scores, 3-Exemplars, T=1.0, N=2)"], marker="o", linewidth=2.2, label="Ascending (Default)", color="#1f77b4")
    ax.plot(trajectories["Ablation: Descending Order"], marker="s", linewidth=2.0, linestyle="--", label="Descending", color="#ff7f0e")
    ax.plot(trajectories["Ablation: Random Order"], marker="^", linewidth=2.0, linestyle=":", label="Random", color="#2ca02c")
    ax.set_title("(a) Instruction Ordering", fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Optimization Steps", fontsize=11)
    ax.set_ylabel("Accuracy", fontsize=11)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True)
    ax.legend(frameon=True, facecolor="white", edgecolor="#cccccc", fontsize=9)

    # Subplot B: Number of Exemplars
    ax = axes[1]
    ax.plot(trajectories["Baseline (Ascending, Scores, 3-Exemplars, T=1.0, N=2)"], marker="o", linewidth=2.2, label="3 Exemplars (Default)", color="#1f77b4")
    ax.plot(trajectories["Ablation: 0 Exemplars"], marker="x", linewidth=2.0, linestyle="--", label="0 Exemplars", color="#d62728")
    ax.set_title("(b) Number of Exemplars", fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Optimization Steps", fontsize=11)
    ax.set_ylabel("Accuracy", fontsize=11)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True)
    ax.legend(frameon=True, facecolor="white", edgecolor="#cccccc", fontsize=9)

    # Subplot C: Instruction Scores in Meta-Prompt
    ax = axes[2]
    ax.plot(trajectories["Baseline (Ascending, Scores, 3-Exemplars, T=1.0, N=2)"], marker="o", linewidth=2.2, label="With Scores (Default)", color="#1f77b4")
    ax.plot(trajectories["Ablation: No Scores"], marker="d", linewidth=2.0, linestyle="--", label="No Scores", color="#9467bd")
    ax.set_title("(c) Score Feedback", fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Optimization Steps", fontsize=11)
    ax.set_ylabel("Accuracy", fontsize=11)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True)
    ax.legend(frameon=True, facecolor="white", edgecolor="#cccccc", fontsize=9)

    plt.tight_layout()
    fig_ablation_path = os.path.join(figures_dir, "figure_ablation_studies.png")
    plt.savefig(fig_ablation_path, bbox_inches="tight")
    plt.close()
    print(f"Ablation figure saved to {fig_ablation_path}")

    # Figure 2: Sensitivity (Temperature & Batch Size)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.5), dpi=300)

    # Subplot A: Temperature
    ax = axes[0]
    ax.plot(trajectories["Baseline (Ascending, Scores, 3-Exemplars, T=1.0, N=2)"], marker="o", linewidth=2.2, label="T = 1.0 (Default)", color="#1f77b4")
    ax.plot(trajectories["Sensitivity: T=0.0"], marker="s", linewidth=2.0, linestyle="--", label="T = 0.0", color="#8c564b")
    ax.plot(trajectories["Sensitivity: T=0.5"], marker="v", linewidth=2.0, linestyle="-.", label="T = 0.5", color="#e377c2")
    ax.plot(trajectories["Sensitivity: T=1.5"], marker="^", linewidth=2.0, linestyle=":", label="T = 1.5", color="#7f7f7f")
    ax.set_title("(a) Optimizer Temperature", fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Optimization Steps", fontsize=11)
    ax.set_ylabel("Accuracy", fontsize=11)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True)
    ax.legend(frameon=True, facecolor="white", edgecolor="#cccccc", fontsize=9)

    # Subplot B: Batch Size (Number of Instructions per Step)
    ax = axes[1]
    ax.plot(trajectories["Sensitivity: N=1 (Batch 1)"], marker="^", linewidth=2.0, linestyle=":", label="N = 1 per step", color="#bcbd22")
    ax.plot(trajectories["Baseline (Ascending, Scores, 3-Exemplars, T=1.0, N=2)"], marker="o", linewidth=2.2, label="N = 2 per step (Default)", color="#1f77b4")
    ax.plot(trajectories["Sensitivity: N=4 (Batch 4)"], marker="s", linewidth=2.0, linestyle="--", label="N = 4 per step", color="#17becf")
    ax.set_title("(b) Generated Instructions per Step", fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Optimization Steps", fontsize=11)
    ax.set_ylabel("Accuracy", fontsize=11)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True)
    ax.legend(frameon=True, facecolor="white", edgecolor="#cccccc", fontsize=9)

    plt.tight_layout()
    fig_sens_path = os.path.join(figures_dir, "figure_parameter_sensitivity.png")
    plt.savefig(fig_sens_path, bbox_inches="tight")
    plt.close()
    print(f"Sensitivity figure saved to {fig_sens_path}")


if __name__ == "__main__":
    main()
