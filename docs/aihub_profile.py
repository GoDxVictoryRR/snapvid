"""Run once manually to get NPU profile numbers for the README.

NOT called at runtime. Output goes to docs/benchmark_results.json
"""

import json

try:
    import qai_hub as hub
except ImportError:
    hub = None

MODEL_ID = "qwen3_4b_instruct_2507"  # official AI Hub model ID


def run_aihub_profile(api_token: str | None = None):
    if hub is None:
        print("qai-hub not installed. Run: pip install qai-hub")
        return

    print("Submitting Qualcomm AI Hub profile job for:", MODEL_ID)
    try:
        profile_job = hub.submit_profile_job(
            model=hub.get_model(MODEL_ID),
            device=hub.Device("Snapdragon X Elite CRD"),
        )
        print("Profile job submitted:", profile_job.job_id)
        print("Waiting for results (may take 5-10 min)...")
        profile_job.wait()
        results = profile_job.download_results()

        with open("docs/benchmark_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print("Results saved to docs/benchmark_results.json")
    except Exception as exc:
        print("Profile job failed:", exc)


if __name__ == "__main__":
    run_aihub_profile()
