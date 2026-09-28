# Snapdragon AI hackathon entry without compatible hardware

**Created:** 9/28/2026 22:34:30  
**Updated:** 9/28/2026 23:08:06  
**Exported:** 9/28/2026 23:08:33  
**Link:** [https://claude.ai/chat/0af399d5-e6c6-47a1-9cb2-795b868096b4](https://claude.ai/chat/0af399d5-e6c6-47a1-9cb2-795b868096b4)  

## User:

> 9/28/2026 22:34:30

this is the hackathon that i wish to  win at any cost https://unstop.com/competitions/crp-snapdragon-ai-lab-build-present-challenge-qualcomm-1748893?utm_campaign=o_1748893&utm_source=Both&utm_medium=D2C-Customized but i dont have a snapdragon hp x laptop find community hacks on how i still can participate and my idea is to make use of this https://huggingface.co/datasets/MoreThought/Fable-5.1-Max-Reasoning-Filtered-10000x with nemotron 3 nano or qwen 3.5 b along with more distillaion and finetuning for video generation to make a agentic video maker to make videos like hypergen remotion manim Clipkit Revideo etc if these could work then tell or else make a new light weight low dependency lternative with top quality result you need to re design the full project idea so it wins the hackaton

## Assistant:

> 9/28/2026 22:35:40

> Drafting a cited, well-sourced project plan with a timeline.
>
> - Redesigning a hackathon project idea for broader hardware access.
> - Updating memory
> - [Unstop - Competitions, Quizzes, Hackathons, Scholarships and Internships for Students and
    Corporates (unstop.com)](https://unstop.com/competitions/crp-snapdragon-ai-lab-build-present-challenge-qualcomm-1748893?utm_campaign=o_1748893&utm_source=Both&utm_medium=D2C-Customized)
> - CRP Snapdragon AI Lab Build & Present Challenge Qualcomm Unstop
> - Checking eligibility rules and the approaching deadline.
> - Qualcomm AI Hub cloud-hosted devices Snapdragon X Elite profile inference without device
> - Reviewing dataset and model naming details.
> - [MoreThought/Fable-5.1-Max-Reasoning-Filtered-10000x · Datasets at Hugging Face (huggingface.co)](https://huggingface.co/datasets/MoreThought/Fable-5.1-Max-Reasoning-Filtered-10000x)
> - Assessing whether fine-tuning fits within the time and hardware limits.
> - Remotion Windows on ARM64 Chrome Headless Shell support
> - Drafting a cited, well-sourced project plan with a timeline.
> - **Done**

Read this part first: the Unstop rules say participants should own a Snapdragon-powered laptop, and the submission window closes 30 Sep 2026, 11:59 PM IST. That is about 2 days from now.

## Participating without the laptop

1. **Ask the organisers today.** Post in the Unstop discussion tab or email support and ask whether cloud-tested hardware is acceptable. The same page also says solutions can be *"intended to be optimised"* for Snapdragon HP PCs, so there is some room, but I can't promise the ownership rule won't be enforced. Don't claim you own a device you don't.
2. **Use Qualcomm AI Hub Workbench.** It lets you compile, profile and run inference on 50+ types of Qualcomm devices hosted in Qualcomm's cloud. The AI Hub Models repo lists Snapdragon X Elite and X2 Elite compute platforms among its targets, and its demos run inference on cloud-hosted hardware with `--eval-mode on-device`. This gives you real, honest NPU latency numbers without owning the laptop.
3. **Borrow a machine for the final hour.** A friend, your college lab or a retail demo unit would do, just to record the demo and one end-to-end run.
4. **Learn from other entrants.** Others have built on a Mac and openly stated that no NPU number is claimed. Real cloud NPU numbers plus honest documentation will beat that.

## Your stack: what works and what doesn't

- **Remotion:** its docs list Windows x64, not Windows ARM64 among supported platforms, so it is risky on a Snapdragon laptop. Manim needs Cairo, LaTeX and ffmpeg, which is heavy for the same reason. Both are poor fits for a "runs on Snapdragon" pitch.
- **The dataset:** it is 10,000 agentic coding traces averaging about 50,000 tokens, roughly 500M tokens in total. That is coding-agent behaviour, not video or scene planning, and you can't fine-tune on it in 2 days without a big GPU. Also check the terms of the model provider that generated it before building a competition entry on it. A 4B model already fine-tuned on it exists (Hob-forge/Qwen3.5-Fable5.1), but I can't vouch for its quality or AI Hub compatibility.
- **Models:** as far as I know, Nemotron 3 Nano is a ~30B-parameter MoE, too big for a laptop NPU. Use a 2B to 4B Qwen and confirm on AI Hub's model list which LLM is actually supported. GenieX is Qualcomm's on-device SDK that runs Gen AI models across NPU, GPU and CPU, with a llama.cpp plugin for community GGUF models, which is your route for a custom model.

## Redesigned project: SnapReel (offline agentic explainer-video maker)

The main insight is that small models can't write good Remotion code. Quality comes from a curated component library, and the LLM only chooses and fills it in.

**Pipeline:**
1. The user types or pastes notes (English or Hindi), and the local LLM plans the video.
2. The LLM outputs a constrained JSON scene script, using schema or grammar-constrained decoding so it is always valid. It only picks from your templates: title card, bullet reveal, animated bar or line chart, counter, code block, kinetic text, shape diagram, transitions.
3. A validator checks the JSON and feeds errors back to the LLM for a repair loop. This is the "agentic" part.
4. A small renderer (Python, Pillow and numpy, with easing and gradients) draws the frames and pipes them to one ffmpeg binary.
5. Narration uses Windows' built-in TTS (zero model dependencies). Whisper on the NPU then transcribes it to get word timestamps for karaoke-style captions, including Hindi.

**Why it fits the judging criteria** (technical implementation, use case and innovation, deployment and accessibility, presentation and documentation):
- NPU used twice, for the LLM and Whisper, with real AI Hub profile numbers in a table.
- Fully offline and private, aimed at students, teachers and small businesses in India with low bandwidth.
- Dependencies stay minimal, which is a real deployment advantage on Windows ARM.

**About distillation:** skip fine-tuning for the submission. If you have spare time, generate 500 to 1,000 (prompt → scene JSON) pairs with a large model, run a LoRA on Colab or Kaggle, and mention it as a roadmap item rather than betting the entry on it.

## 48-hour plan

- **Today:** sign up for AI Hub, get one LLM and Whisper profile job running on a cloud Snapdragon X device, and message the organisers.
- **Tomorrow:** build the schema, 6 to 8 templates and the renderer, then wire up the LLM planner and repair loop.
- **Deadline day:** add TTS with Whisper captions, record the benchmark table, write the README (including an honest limitations section), and record a 3-minute demo. Submit by the afternoon, not at 11:59 PM.

Do you want me to write the scene JSON schema and the renderer skeleton next?

---

**Sources:**

- [GitHub - challalokesh08/snapdragoon: On-device accessibility co-pilot: live captions and scene description. Whisper Tiny + MobileNet V2 over ONNX Runtime, with a Qualcomm AI Hub / QNN NPU path. Built for the Snapdragon AI Lab Build & Present Challenge. · GitHub](https://github.com/challalokesh08/snapdragoon)
- [Snapdragon® AI Lab Build & Present Challenge - 2026](https://unstop.com/competitions/crp-snapdragon-ai-lab-build-present-challenge-qualcomm-1748893)
- [GitHub - hemantrai-tech/Snapdragon-build-AI: On-device AI offline mode for ResponseNet — Whisper STT + on-device LLM triage on the Snapdragon Hexagon NPU, so disaster-response requests work with zero internet. Built for the Qualcomm Snapdragon AI Lab Build & Present Challenge.](https://github.com/hemantrai-tech/Snapdragon-build-AI)
- [Qualcomm Direct Test Internship Program - 2027](https://www.youtube.com/watch?v=LfDqW-NVYeU)
- [GitHub - Mukeshpadigela17/SnapCareer-AI-project · GitHub](https://github.com/Mukeshpadigela17/SnapCareer-AI-project)
- [Smart Move Hackathon - 2026](https://unstop.com/competitions/smart-move-hackathon-smart-move-hackathon-kalaignar-karunanidhi-institute-of-technology-kkit-coimbatore-1754608)
- [Snapdragon AI Lab Challenge 2026](https://www.youtube.com/watch?v=ZTT_be_nkv8)
- [Snapdragon AI Lab Build & Present Challenge 2026](https://www.aicompetition.dev/en/competitions/snapdragon-ai-lab-build-present-2026)
- [Snapdragon AI Lab Build & Present Challenge -](https://internfreak.com/snapdragon-ai-lab-build-present-challenge/)
- [GitHub - qualcomm/ai-hub-models: Qualcomm® AI Hub Models is our collection of state-of-the-art machine learning models optimized for performance (latency, memory etc.) and ready to deploy on Qualcomm® devices.](https://github.com/qualcomm/ai-hub-models)
- [Snapdragon](https://lablab.ai/tech/qualcomm/qualcomm-snapdragon)
- [Qualcomm's AI Hub will bring Stable Diffusion, Whisper, and more to Snapdragon devices](https://www.xda-developers.com/qualcomm-ai-hub-snapdragon-announced/)
- [AI Hub - Windows on Snapdragon - Windows on Snapdragon Documentation](https://docs.qualcomm.com/bundle/publicresource/topics/80-62010-1/ai-hub.html?product=1601111739937064)
- [Qualcomm Launches Its AI Hub, Offering Optimized On-Device AI Models with Four Times the Performance - Hackster.io](https://www.hackster.io/news/qualcomm-launches-its-ai-hub-offering-optimized-on-device-ai-models-with-four-times-the-performance-3dddfcb8a84f)
- [qualcomm (Qualcomm)](https://huggingface.co/qualcomm)
- [Qualcomm AI Hub](https://aihub.qualcomm.com/)
- [Release Notes — Qualcomm® AI Hub documentation](https://workbench.aihub.qualcomm.com/docs/hub/release_notes.html)
- [Qualcomm Becomes A Mobile AI Juggernaut.](https://www.forbes.com/sites/karlfreund/2024/03/14/qualcomm-becomes-a-mobile-ai-juggernaut/)
- [stat.ethz.ch](https://stat.ethz.ch/CRAN/web/packages/chromote/news/news.html)
- [github.com](https://github.com/microsoft/playwright/pull/38573/changes)
- [github.com](https://github.com/bush2021/chrome_plus/issues/37)
- [rstudio.github.io](https://rstudio.github.io/chromote/news/index.html)
- [Installing Chrome v4.0.247](https://www.remotion.dev/docs/chrome-headless-shell)
- [Installing Chrome v4.0.247](https://remotion.dev/docs/miscellaneous/chrome-headless-shell)
- [Installing Chrome v4.0.247](https://remotion.dev/docs/miscellaneous/thorium-browser)

## User:

> 9/28/2026 22:44:56

how can i build the entire project also tell which model to use nemotron 3 nabo 4b or qwen3.5-fable-5.1 4b can i make the entire project with google antigravity i want to build all of the above features you listed , and also be brutally honest and pratical with everything

## Assistant:

> 9/28/2026 22:45:50

> Compiling citations and sourcing claims for the technical details.
>
> - Comparing model options and build tools for the project.
> - Adding to memory
> - NVIDIA Nemotron 3 Nano 4B model GGUF ONNX
> - Correcting an earlier model size mistake.
> - Qwen3.5 4B Snapdragon NPU Qualcomm AI Hub GenieX supported models
> - Weighing runtime compatibility and performance across candidate models.
> - Google Antigravity IDE free plan limits Windows ARM
> - Compiling citations and sourcing claims for the technical details.
> - **Done**

Brutal version: you have about 2 days (the deadline is 30 Sep, 11:59 PM IST). A polished thin version of every feature, with real numbers and honest docs, beats a half-working "everything". The eligibility risk from my last message also still stands.

## Which model

A correction first: I earlier said Nemotron 3 Nano was about 30B. That is only its sibling, and a 4B variant does exist. Now the verdict.

**Don't ship either of your two as the primary model.** Use Qualcomm's own **Qwen3-4B-Instruct-2507** bundle from AI Hub. It lists Snapdragon X Elite CRD, X Plus and X2 Elite CRD as supported devices, so you can test on real NPU hardware in the cloud. Qualcomm's model card also publishes GenieX/QAIRT w4a16 numbers on X Elite, around 22 tokens/sec by my reading of the table, which you should reproduce in your own profile job. Run it in non-thinking mode, because you need short JSON, not long reasoning.

Between your two picks:
- **Nemotron 3 Nano 4B:** it is a real NVIDIA release with a GGUF, and it is trained for tool use with a reasoning on/off switch. But it is a hybrid Mamba-2 model with just four attention layers. I found no AI Hub NPU bundle for it, and I can't confirm that GenieX's llama.cpp path runs that architecture on the NPU. It also comes under NVIDIA's Open Model License, so read it.
- **Qwen3.5-Fable-5.1 4B:** it is a community fine-tune on ~50k-token coding traces, so expect it to overthink, which is bad for latency. Its quality is unverified for your task, and there is the licence question I raised earlier. GenieX can load Qwen3.5 GGUFs (its own example uses a Qwen3.5-2B GGUF), so it is possible but unproven.

Make your app talk to an OpenAI-compatible endpoint. GenieX serves one, and so do llama.cpp and Ollama on your current machine. Then the model is a config line, and you can benchmark Nemotron as a bonus row if time allows. GenieX itself only runs on Snapdragon, so locally you develop against llama.cpp or Ollama and switch the URL later.

## Can Antigravity build it?

Yes, it can write all of the code. Google lists an Individual tier at $0 with weekly agent quotas, but the free limits have been cut repeatedly since launch, so a heavy sprint could hit the cap. Installers exist for Windows x64 and ARM64.

Three practical warnings:
1. **Agents hallucinate new APIs.** GenieX and AI Hub are recent, so paste the docs into a `docs/` folder and tell the agent to follow only those.
2. **It can't test the NPU for you.** You run the AI Hub profile jobs yourself.
3. **Spec first.** Write a one-page `SPEC.md` and have it build one module at a time, running tests after each.

## What to build (and what to cut)

**Cut:** fine-tuning and distillation (your dataset doesn't fit the task and there's no time), Manim and LaTeX, and Hindi TTS unless a Hindi Windows voice is already installed.

**Must have (day 1):**
- **Scene JSON:** the LLM outputs `{scenes:[{template, text/data, duration, narration}]}`. Use 6 templates: title, bullets, bar chart, counter, code block, kinetic text.
- **Validator and repair loop:** if the JSON is invalid or references an unknown template, feed the error back for a retry (max 3).
- **Renderer:** Pillow and numpy draw 1280×720 frames at 30 fps with easing and gradients, piped to one ffmpeg binary. Quality here comes from good typography, spacing and motion, not from the LLM.
- **Local page:** one HTML page served with Python's `http.server`, with no framework.

**Should have (day 2):**
- **Narration:** Windows built-in TTS. Time the captions proportionally to the audio length.
- **Benchmarks:** an AI Hub profile job for the LLM on a cloud Snapdragon X device, with the numbers in your README.

**Stretch:** Whisper on the NPU for real word-level caption timing. This is hard to integrate in 2 days, so don't bet on it.

## Practical gotchas

- On Snapdragon Windows, AI Hub's `qai_hub_models` package only supports 64-bit x64 Python, and installing it on ARM64 Python fails.
- Check early that `pip install pillow numpy imageio-ffmpeg` works on a Snapdragon machine. I haven't verified ARM64 wheels for all of them.
- Grammar-constrained JSON output may not be exposed by the GenieX server. That is why the validator and repair loop is mandatory.

## 48-hour schedule

- **Now to tonight:** AI Hub signup, Qwen3-4B-Instruct-2507 profile job started, questions sent to the organisers, `SPEC.md` written.
- **Tomorrow:** renderer and templates first (they take longest to look good), then the LLM planner and repair loop.
- **Deadline day, morning:** narration, benchmark table, README with an honest limitations section.
- **Deadline day, afternoon:** 3-minute demo video. Submit that evening, not at 11:50 PM.

Nothing here guarantees a win. Judges will see many on-device demos, so your edge is a demo that produces a good-looking video from a paragraph, real NPU numbers, and no faked claims.

I can write the `SPEC.md` and the first Antigravity prompts for you next, including the scene JSON schema.

---

**Sources:**

- [NVIDIA-Nemotron-3-Nano-4B-GGUF Model Developer: NVIDIA Corporation](https://developer.nvidia.com/downloads/assets/ace/model_card/nemotron_3_nano_4b.pdf)
- [nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF · Hugging Face](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF)
- [Nemotron 3 Nano 4B: A Compact Hybrid Model for Efficient Local AI](https://huggingface.co/blog/nvidia/nemotron-3-nano-4b)
- [nvidia Nemotron 3 Nano 30B A3B GGUF](https://huggingface.co/bartowski/nvidia_Nemotron-3-Nano-30B-A3B-GGUF)
- [unsloth/NVIDIA-Nemotron-3-Nano-4B-GGUF · Hugging Face](https://huggingface.co/unsloth/NVIDIA-Nemotron-3-Nano-4B-GGUF)
- [lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF · Hugging Face](https://huggingface.co/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF)
- [1bit-MONSTER/NVIDIA-Nemotron-3-Nano-4B-GGUF · Hugging Face](https://huggingface.co/1bit-MONSTER/NVIDIA-Nemotron-3-Nano-4B-GGUF)
- [nvidia/nemotron-3-nano-4b • LM Studio](https://lmstudio.ai/models/nvidia/nemotron-3-nano-4b)
- [NVIDIA Nemotron 3 Nano - How To Run Guide](https://unsloth.ai/docs/models/nemotron-3)
- [Nemotron3 Nano 4B Uncensored HauhauCS Aggressive](https://huggingface.co/HauhauCS/Nemotron3-Nano-4B-Uncensored-HauhauCS-Aggressive)
- [github.com](https://github.com/qualcomm/GenieX/wiki)
- [GitHub - qualcomm/GenieX: Run frontier LLMs and VLMs locally on Qualcomm devices across NPU, GPU, and CPU with a few lines of code · GitHub](https://github.com/qualcomm/geniex)
- [qualcomm/Qwen3-4B · Hugging Face](https://huggingface.co/qualcomm/Qwen3-4B)
- [Qwen3-4B - Qualcomm AI Hub](https://aihub.qualcomm.com/models/qwen3_4b)
- [GitHub - tgerighty/GenieX: Run frontier LLMs and VLMs locally on Qualcomm devices across NPU, GPU, and CPU with a few lines of code · GitHub](https://github.com/tgerighty/GenieX)
- [Qwen3-VL-4B-Instruct: Optimized for Qualcomm Devices](https://huggingface.co/qualcomm/Qwen3-VL-4B-Instruct)
- [Qwen3-4B-Instruct-2507 - Qualcomm AI Hub](https://aihub.qualcomm.com/models/qwen3_4b_instruct_2507)
- [Qwen3-8B: Optimized for Qualcomm Devices](https://huggingface.co/qualcomm/Qwen3-8B)
- [Qwen3-0.6B: Optimized for Qualcomm Devices](https://huggingface.co/qualcomm/Qwen3-0.6B)
- [Intern3.5-VL-2B: Optimized for Qualcomm Devices](https://huggingface.co/qualcomm/Intern3.5-VL-2B)
- [Google Antigravity pricing 2026: tiers, limits, free plan](https://www.cloudzero.com/blog/google-antigravity-pricing/)
- [Google Antigravity: Features, Pricing & Alternatives](https://www.therundown.ai/tools/antigravity)
- [I Tried Google’s Antigravity IDE: Pros and Cons](https://medium.com/@theshivamlko/i-tried-googles-antigravity-ide-pros-and-cons-1b6bbb81dd1b)
- [Antigravity Pricing 2026: Free, Pro, Ultra and Rate Limits](https://www.codeagentswarm.com/en/guides/antigravity-plans-and-pricing)
- [Google Antigravity for Free: Access, Eligibility, Setup Steps, Limits, and Upgrade Triggers](https://www.datastudios.org/post/google-antigravity-for-free-access-eligibility-setup-steps-limits-and-upgrade-triggers)
- [Antigravity IDE Community - Guides, Tutorials & Reviews (Unofficial)](https://www.antigravity-ide.com/)
- [Google Antigravity Download for Windows, Mac & Linux (Free)](https://www.cloudspress.com/download-google-antigravity-for-free-on-windows-macos-and-linux/)
- [Is Google Antigravity free in 2026? Free tier, Pro, Ultra 5x/20x, limits, models, and AI credits](https://www.datastudios.org/post/is-google-antigravity-free-to-use-pricing-limits-and-what-developers-should-expect)
- [Increase Your Google Antigravity Limits for Free (Official Method)](https://resourify.com/resources/google-antigravity)

## Assistant:

> 9/28/2026 23:08:06

> Finalizing prop limits, gate checklists, and example file contents.
>
> - Setting up a full agents configuration folder for Antigravity.
> - Adding to memory
> - Antigravity .agents folder rules workflows skills AGENTS.md directory structure
> - Finalizing prop limits, gate checklists, and example file contents.
> - Always-on mission rule: objective, non-negotiables, context discipline
> - **Done**

---

**Sources:**

- [Agentic development](https://github.com/MatrixFounder/Agentic-development)
- [ag kit](https://docsearch.algolia.com/mcp/docs/repo/vudovn/ag-kit)
- [Dev Web](https://github.com/HarveySpecter85/Dev-Web)
- [Build Better AI Agents with Google Antigravity Skills and Workflows - KDnuggets](https://www.kdnuggets.com/build-better-ai-agents-with-google-antigravity-skills-and-workflows)
- [antigravity dev skills](https://github.com/balamuru/antigravity-dev-skills)
- [antigravity ide](https://github.com/Dokhacgiakhoa/antigravity-ide)
- [GitHub - CongDon1207/AGENTS.md: Copy .* folder and AGENTS.md then paste /root of project · GitHub](https://github.com/congdon1207/agents.md)
- [Google Antigravity and AGENTS.md: The Complete 2026 Guide — The Prompt Shelf](https://thepromptshelf.dev/blog/google-antigravity-agents-md-rules-guide-2026/)
- [Antigravity Rules: Guide with AGENTS.md & Examples (2026)](https://agentpedia.codes/blog/user-rules)
- [AGENTS.md Guide: Cross-Tool Rules for Antigravity (2026)](https://agentpedia.codes/blog/antigravity-agents-md-guide)

Powered by Claude Exporter (https://www.ai-chat-exporter.net)
