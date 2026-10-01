document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const topicInput = document.getElementById("topic");
  const generateBtn = document.getElementById("generate-btn");
  const btnText = generateBtn.querySelector(".btn-text");
  const btnSpinner = generateBtn.querySelector(".btn-spinner");
  const activeModelTag = document.getElementById("active-model-tag");
  const activeVoiceTag = document.getElementById("active-voice-tag");

  const agentPanel = document.getElementById("agent-panel");
  const agentLog = document.getElementById("agent-log");
  const agentStatusBadge = document.getElementById("agent-status-badge");

  const statusPanel = document.getElementById("status-panel");
  const statusTitle = document.getElementById("status-title");
  const statusText = document.getElementById("status-text");
  const progressPercent = document.getElementById("progress-percent");
  const progressFill = document.getElementById("progress-fill");

  const resultPanel = document.getElementById("result-panel");
  const resultTopic = document.getElementById("result-topic");
  const videoPreview = document.getElementById("preview");
  const downloadLink = document.getElementById("download-link");
  const createAnotherBtn = document.getElementById("create-another-btn");

  const errorPanel = document.getElementById("error-panel");
  const errorText = document.getElementById("error-text");
  const retryBtn = document.getElementById("retry-btn");

  const historyList = document.getElementById("history-list");
  const tagButtons = document.querySelectorAll(".tag-btn");

  // Settings Elements
  const openSettingsBtn = document.getElementById("open-settings-btn");
  const closeSettingsBtn = document.getElementById("close-settings-btn");
  const settingsDrawer = document.getElementById("settings-drawer");
  const settingsBackdrop = document.getElementById("settings-backdrop");
  const saveSettingsBtn = document.getElementById("save-settings-btn");
  const testLlmBtn = document.getElementById("test-llm-btn");
  const testLlmStatus = document.getElementById("test-llm-status");
  const toast = document.getElementById("toast");

  const settingProvider = document.getElementById("setting-provider");
  const settingBaseUrl = document.getElementById("setting-base-url");
  const settingModel = document.getElementById("setting-model");
  const settingApiKey = document.getElementById("setting-api-key");
  const settingTtsEngine = document.getElementById("setting-tts-engine");
  const settingTtsVoice = document.getElementById("setting-tts-voice");
  const settingQualityPass = document.getElementById("setting-quality-pass");

  // Benchmark stats
  const benchDevice = document.getElementById("bench-device");
  const benchLlm = document.getElementById("bench-llm");
  const benchTps = document.getElementById("bench-tps");
  const benchFps = document.getElementById("bench-fps");
  const badgeNpuText = document.getElementById("badge-npu-text");

  let pollInterval = null;
  let eventSource = null;

  // Provider presets matching UI_SETTINGS.md
  const PROVIDER_PRESETS = {
    ollama: {
      url: "http://localhost:11434/v1",
      model: "granite4.2:3b",
    },
    geniex: {
      url: "http://localhost:8080/v1",
      model: "Qwen3-4B-Instruct-2507",
    },
    llamacpp: {
      url: "http://localhost:8080/v1",
      model: "default",
    },
    nvidia: {
      url: "https://integrate.api.nvidia.com/v1",
      model: "meta/llama-3.1-8b-instruct",
    },
    gemini: {
      url: "https://generativelanguage.googleapis.com/v1beta/openai",
      model: "gemini-1.5-flash",
    },
    openai: {
      url: "https://api.openai.com/v1",
      model: "gpt-4o-mini",
    },
    groq: {
      url: "https://api.groq.com/openai/v1",
      model: "llama-3.1-8b-instant",
    },
    together: {
      url: "https://api.together.xyz/v1",
      model: "Qwen/Qwen2.5-7B-Instruct",
    },
    mistral: {
      url: "https://api.mistral.ai/v1",
      model: "mistral-small-latest",
    },
    custom: {
      url: "",
      model: "",
    },
  };

  // Voice engine presets
  const VOICE_OPTIONS = {
    auto: [{ id: "auto", name: "Auto-selected default" }],
    kokoro: [
      { id: "af_heart", name: "Warm Female (af_heart - best)" },
      { id: "af_nova", name: "Confident Female (af_nova)" },
      { id: "am_adam", name: "Clear Male (am_adam)" },
      { id: "am_echo", name: "Deep Male (am_echo)" },
      { id: "bf_emma", name: "British Female (bf_emma)" },
    ],
    edge: [
      { id: "en-US-AriaNeural", name: "Aria (US Female)" },
      { id: "en-US-GuyNeural", name: "Guy (US Male)" },
      { id: "en-IN-NeerjaNeural", name: "Neerja (Indian English)" },
    ],
    sapi: [{ id: "auto", name: "System Default Voice" }],
  };

  function updateVoiceDropdown(engine, selectedVoice = "auto") {
    settingTtsVoice.innerHTML = "";
    const options = VOICE_OPTIONS[engine] || VOICE_OPTIONS.auto;
    options.forEach((opt) => {
      const el = document.createElement("option");
      el.value = opt.id;
      el.textContent = opt.name;
      if (opt.id === selectedVoice) el.selected = true;
      settingTtsVoice.appendChild(el);
    });
  }

  async function loadSettings() {
    let serverConfig = null;
    try {
      const res = await fetch("/config");
      if (res.ok) {
        serverConfig = await res.json();
      }
    } catch (_) {}

    const savedProvider = localStorage.getItem("sr_provider");
    let provider = savedProvider;
    if (!provider && serverConfig) {
      const url = (serverConfig.llm_base_url || "").toLowerCase();
      if (url.includes("nvidia.com")) provider = "nvidia";
      else if (url.includes("generativelanguage.googleapis.com")) provider = "gemini";
      else if (url.includes("openai.com")) provider = "openai";
      else if (url.includes("groq.com")) provider = "groq";
      else if (url.includes("together.xyz")) provider = "together";
      else if (url.includes("mistral.ai")) provider = "mistral";
      else if (url.includes(":8080")) provider = "geniex";
      else provider = "ollama";
    }
    if (!provider) provider = "ollama";
    settingProvider.value = provider;

    const preset = PROVIDER_PRESETS[provider] || PROVIDER_PRESETS.ollama;
    const defaultUrl = (serverConfig && !savedProvider) ? serverConfig.llm_base_url : preset.url;
    const defaultModel = (serverConfig && !savedProvider) ? serverConfig.llm_model : preset.model;

    settingBaseUrl.value = localStorage.getItem("sr_base_url") ?? defaultUrl;
    settingModel.value = localStorage.getItem("sr_model") ?? defaultModel;
    settingApiKey.value = localStorage.getItem("sr_api_key") || "";
    if (!settingApiKey.value && serverConfig?.has_api_key) {
      settingApiKey.placeholder = "•••••••• (Server key active — or enter custom)";
    } else {
      settingApiKey.placeholder = "Leave blank for local backends";
    }

    const ttsEngine = localStorage.getItem("sr_tts_engine") || serverConfig?.tts_engine || "auto";
    settingTtsEngine.value = ttsEngine;
    const ttsVoice = localStorage.getItem("sr_tts_voice") || serverConfig?.tts_voice || "auto";
    updateVoiceDropdown(ttsEngine, ttsVoice);

    const quality = localStorage.getItem("sr_quality_pass");
    settingQualityPass.checked = quality === null ? true : quality === "true";

    updateHeaderBadges();
  }

  async function saveSettings() {
    const provider = settingProvider.value;
    const baseUrl = settingBaseUrl.value.trim();
    const model = settingModel.value.trim();
    const apiKey = settingApiKey.value.trim();
    const ttsEngine = settingTtsEngine.value;
    const ttsVoice = settingTtsVoice.value;
    const qualityPass = settingQualityPass.checked;

    // Secure Client-Side Storage: The key stays strictly in user's browser localStorage
    localStorage.setItem("sr_provider", provider);
    localStorage.setItem("sr_base_url", baseUrl);
    localStorage.setItem("sr_model", model);
    localStorage.setItem("sr_api_key", apiKey);
    localStorage.setItem("sr_tts_engine", ttsEngine);
    localStorage.setItem("sr_tts_voice", ttsVoice);
    localStorage.setItem("sr_quality_pass", qualityPass ? "true" : "false");

    // Do NOT send user's personal API key to global /config endpoint to avoid multi-user leakage.
    // The key is passed directly in /generate request headers/body strictly in memory.
    try {
      await fetch("/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          llm_base_url: baseUrl,
          llm_model: model,
          tts_engine: ttsEngine,
          tts_voice: ttsVoice,
        }),
      });
    } catch (_) {}

    updateHeaderBadges();
    showToast("Settings applied & saved!");
    closeSettings();
  }

  function updateHeaderBadges() {
    const providerName = settingProvider.options[settingProvider.selectedIndex]?.text || "Ollama";
    const model = settingModel.value || "default";
    const ttsEngine = settingTtsEngine.value;

    activeModelTag.textContent = `${providerName.split(" ")[0]}: ${model}`;
    activeVoiceTag.textContent = `TTS: ${ttsEngine}`;

    if (settingProvider.value === "geniex") {
      badgeNpuText.textContent = "Qualcomm NPU (GenieX)";
    } else if (settingProvider.value === "nvidia") {
      badgeNpuText.textContent = "NVIDIA NIM Cloud AI";
    } else if (settingProvider.value === "gemini") {
      badgeNpuText.textContent = "Google Gemini AI";
    } else if (["openai", "groq", "together", "mistral"].includes(settingProvider.value)) {
      badgeNpuText.textContent = "Cloud LLM Connected";
    } else {
      badgeNpuText.textContent = "Offline-Ready Local AI";
    }
  }

  function showToast(msg) {
    toast.textContent = msg;
    toast.hidden = false;
    setTimeout(() => {
      toast.hidden = true;
    }, 2800);
  }

  function openSettings() {
    settingsBackdrop.hidden = false;
    settingsDrawer.classList.add("open");
    settingsDrawer.setAttribute("aria-hidden", "false");
  }

  function closeSettings() {
    settingsDrawer.classList.remove("open");
    settingsDrawer.setAttribute("aria-hidden", "true");
    settingsBackdrop.hidden = true;
    testLlmStatus.textContent = "";
  }

  // Provider change handler
  settingProvider.addEventListener("change", () => {
    const val = settingProvider.value;
    const preset = PROVIDER_PRESETS[val];
    if (preset && val !== "custom") {
      settingBaseUrl.value = preset.url;
      settingModel.value = preset.model;
    }
  });

  // TTS Engine change handler
  settingTtsEngine.addEventListener("change", () => {
    updateVoiceDropdown(settingTtsEngine.value);
  });

  openSettingsBtn.addEventListener("click", openSettings);
  closeSettingsBtn.addEventListener("click", closeSettings);
  settingsBackdrop.addEventListener("click", closeSettings);
  saveSettingsBtn.addEventListener("click", saveSettings);

  // Test connection button
  testLlmBtn.addEventListener("click", async () => {
    testLlmStatus.textContent = "Testing...";
    testLlmStatus.className = "test-status";

    const payload = {
      llm_base_url: settingBaseUrl.value.trim(),
      llm_model: settingModel.value.trim(),
      llm_api_key: settingApiKey.value.trim(),
    };

    try {
      const res = await fetch("/test_llm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.ok) {
        testLlmStatus.textContent = `✅ Connected (${data.latency_ms}ms)`;
        testLlmStatus.className = "test-status ok";
      } else {
        testLlmStatus.textContent = `❌ ${data.error || "Failed"}`;
        testLlmStatus.className = "test-status err";
      }
    } catch (err) {
      testLlmStatus.textContent = `❌ ${err.message}`;
      testLlmStatus.className = "test-status err";
    }
  });

  // Quick suggestion tags
  tagButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      topicInput.value = btn.getAttribute("data-topic") || "";
      topicInput.focus();
    });
  });

  // Length and ratio selectors per FORMATS.md
  let selectedDuration = 60;
  let selectedRatio = "16:9";

  const durationPills = document.querySelectorAll("#duration-pills .pill-btn");
  const customDurationInput = document.getElementById("custom-duration");
  const ratioPills = document.querySelectorAll("#ratio-pills .pill-btn");

  durationPills.forEach((btn) => {
    btn.addEventListener("click", () => {
      durationPills.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const sec = btn.getAttribute("data-seconds");
      if (sec === "custom") {
        if (customDurationInput) {
          customDurationInput.style.display = "inline-block";
          customDurationInput.focus();
          selectedDuration = parseInt(customDurationInput.value, 10) || 60;
        }
      } else {
        if (customDurationInput) {
          customDurationInput.style.display = "none";
        }
        selectedDuration = parseInt(sec, 10) || 60;
      }
    });
  });

  if (customDurationInput) {
    customDurationInput.addEventListener("input", () => {
      selectedDuration = parseInt(customDurationInput.value, 10) || 60;
    });
  }

  ratioPills.forEach((btn) => {
    btn.addEventListener("click", () => {
      ratioPills.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      selectedRatio = btn.getAttribute("data-ratio") || "16:9";
    });
  });

  function setGeneratingState(isGenerating) {
    generateBtn.disabled = isGenerating;
    topicInput.disabled = isGenerating;
    btnSpinner.hidden = !isGenerating;
    btnText.textContent = isGenerating ? "Generating..." : "Generate Video";
  }

  function showError(msg) {
    clearInterval(pollInterval);
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    setGeneratingState(false);
    statusPanel.hidden = true;
    resultPanel.hidden = true;
    errorText.textContent = msg || "An unexpected error occurred.";
    errorPanel.hidden = false;
    agentStatusBadge.textContent = "Failed";
    agentStatusBadge.className = "badge error";
  }

  function resetPanels() {
    statusPanel.hidden = true;
    resultPanel.hidden = true;
    errorPanel.hidden = true;
    agentPanel.hidden = true;
    agentLog.innerHTML = "";
    progressFill.style.width = "0%";
    progressPercent.textContent = "0%";
    agentStatusBadge.textContent = "Running";
    agentStatusBadge.className = "badge running";
  }

  function appendAgentLog(type, icon, message) {
    const now = new Date();
    const timeStr = now.toTimeString().split(" ")[0];

    const line = document.createElement("div");
    line.className = `agent-log-line ${type}`;

    line.innerHTML = `
      <span class="log-time">[${timeStr}]</span>
      <span class="log-icon">${icon}</span>
      <span class="log-msg">${message}</span>
    `;

    agentLog.appendChild(line);
    agentLog.scrollTop = agentLog.scrollHeight;
  }

  function handleAgentEvent(type, data = {}) {
    switch (type) {
      case "planning_start":
        appendAgentLog("info", "🧠", `Planning scenes for: <strong>"${escapeHtml(data.topic || "")}"</strong>`);
        statusText.textContent = "Planning video script with LLM...";
        progressFill.style.width = "10%";
        progressPercent.textContent = "10%";
        break;

      case "llm_response":
        appendAgentLog("info", "⚙️", `LLM responded for attempt #${data.attempt} (${data.length || 0} chars)`);
        break;

      case "plan_rejected":
        appendAgentLog(
          "warn plan_rejected",
          "⚠️",
          `Scene JSON rejected (attempt #${data.attempt}). Self-healing error: <span class="error-text">${escapeHtml(data.error || "")}</span>`
        );
        statusText.textContent = "Self-correcting scene schema...";
        break;

      case "plan_accepted":
        appendAgentLog(
          "success plan_accepted",
          "✅",
          `Plan accepted! Formatted <strong>${data.scenes || 0} scenes</strong> on attempt #${data.attempt}.`
        );
        statusText.textContent = `Script accepted: ${data.scenes} scenes`;
        progressFill.style.width = "25%";
        progressPercent.textContent = "25%";
        break;

      case "quality_start":
        appendAgentLog("info", "🔍", `Quality Agent evaluating narration pacing (${data.scenes || 0} scenes)...`);
        statusText.textContent = "Quality Critic checking narration...";
        break;

      case "quality_accepted":
        appendAgentLog("success quality_accepted", "✨", `Quality Agent improved & polished script.`);
        break;

      case "quality_rejected":
        appendAgentLog("warn quality_rejected", "⚠️", `Quality check unvalidated; kept accepted plan.`);
        break;

      case "quality_skipped":
        appendAgentLog("info", "⏩", `Quality review skipped (${escapeHtml(data.reason || "fast-path")}).`);
        break;

      case "tts_start":
        appendAgentLog("info", "🎙️", `Generating narration audio via engine: <strong>${data.engine || "auto"}</strong>`);
        statusText.textContent = "Synthesizing voice audio...";
        progressFill.style.width = "30%";
        progressPercent.textContent = "30%";
        break;

      case "tts_done":
        const narrInfo = data.narration_duration ? ` (speech: ${data.narration_duration}s)` : "";
        appendAgentLog("success", "🔊", `Audio ready — video will be <strong>${data.duration}s</strong>${narrInfo}`);
        break;

      case "render_progress":
        appendAgentLog("info", "🎬", `Rendering scene <strong>${data.scene}/${data.total}</strong> (${data.percent}%)`);
        statusText.textContent = `Rendering scene ${data.scene} of ${data.total}...`;
        const pct = Math.max(30, Math.min(98, data.percent || 30));
        progressFill.style.width = `${pct}%`;
        progressPercent.textContent = `${pct}%`;
        break;

      case "done":
        appendAgentLog("success done", "🎉", `Video generated successfully!`);
        agentStatusBadge.textContent = "Completed";
        agentStatusBadge.className = "badge success";
        loadHistory();
        break;

      case "error":
        appendAgentLog("error plan_failed", "❌", `Error: <span class="error-text">${escapeHtml(data.error || "Failed")}</span>`);
        break;

      default:
        appendAgentLog("info", "•", JSON.stringify(data));
        break;
    }
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  async function startGeneration() {
    const topic = topicInput.value.trim();
    if (!topic) {
      topicInput.focus();
      return;
    }

    resetPanels();
    setGeneratingState(true);

    statusTitle.textContent = "Generating Video";
    statusText.textContent = "Initiating agentic scene planning...";
    progressFill.style.width = "5%";
    progressPercent.textContent = "5%";

    agentPanel.hidden = false;
    statusPanel.hidden = false;

    // Build payload including UI settings, format, and duration
    const payload = {
      topic,
      target_duration: selectedDuration,
      aspect_ratio: selectedRatio,
      llm_base_url: settingBaseUrl.value.trim() || localStorage.getItem("sr_base_url") || "",
      llm_model: settingModel.value.trim() || localStorage.getItem("sr_model") || "",
      llm_api_key: settingApiKey.value.trim(),
      tts_engine: settingTtsEngine.value || localStorage.getItem("sr_tts_engine") || "auto",
      tts_voice: settingTtsVoice.value || localStorage.getItem("sr_tts_voice") || "auto",
      quality_pass: settingQualityPass.checked,
    };

    try {
      const response = await fetch("/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || `Server error: ${response.status}`);
      }

      const data = await response.json();
      const jobId = data.job_id;
      if (!jobId) throw new Error("No job ID received from server.");

      // Connect to Server-Sent Events stream
      connectEventStream(jobId, topic);
      pollJobStatus(jobId, topic);
    } catch (err) {
      showError(err.message);
    }
  }

  function connectEventStream(jobId, topic) {
    if (eventSource) {
      eventSource.close();
    }

    eventSource = new EventSource(`/events/${jobId}`);

    eventSource.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data);
        handleAgentEvent(event.type, event.data);
      } catch (err) {
        console.error("Failed to parse SSE event:", err);
      }
    };

    eventSource.onerror = () => {
      if (eventSource) {
        eventSource.close();
        eventSource = null;
      }
    };
  }

  function pollJobStatus(jobId, topic) {
    clearInterval(pollInterval);
    pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`/status/${jobId}`);
        if (!res.ok) return;

        const status = await res.json();

        if (status.state === "running") {
          const pct = Math.max(5, Math.min(99, status.progress || 10));
          progressFill.style.width = `${pct}%`;
          progressPercent.textContent = `${pct}%`;
          if (status.status) statusText.textContent = status.status;
        } else if (status.state === "done") {
          clearInterval(pollInterval);
          if (eventSource) {
            eventSource.close();
            eventSource = null;
          }
          progressFill.style.width = "100%";
          progressPercent.textContent = "100%";
          statusText.textContent = "Complete!";

          setTimeout(() => {
            statusPanel.hidden = true;
            setGeneratingState(false);

            const videoSrc = status.output;
            videoPreview.src = videoSrc;
            resultTopic.textContent = topic;
            downloadLink.href = videoSrc;
            downloadLink.setAttribute("download", videoSrc.split("/").pop() || "snapreel.mp4");
            resultPanel.hidden = false;
            videoPreview.play().catch(() => {});
          }, 350);
        } else if (status.state === "error") {
          showError(status.error || "Generation process failed.");
        }
      } catch (err) {
        console.error("Status polling error:", err);
      }
    }, 1000);
  }

  async function loadHistory() {
    try {
      const res = await fetch("/history");
      if (!res.ok) return;
      const history = await res.json();

      historyList.innerHTML = "";
      if (!history || history.length === 0) {
        historyList.innerHTML = '<div class="history-empty">No videos generated yet. Create one on the left!</div>';
        return;
      }

      history.forEach((item) => {
        const div = document.createElement("div");
        div.className = "history-item";
        div.innerHTML = `
          <div class="history-item-left">
            <span class="history-play-icon" aria-hidden="true">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><polygon points="6 4 20 12 6 20 6 4"/></svg>
            </span>
            <span class="history-topic" title="${escapeHtml(item.topic)}">${escapeHtml(item.topic)}</span>
          </div>
          <span class="history-scenes">${item.scenes} scenes</span>
        `;
        div.addEventListener("click", () => {
          resultPanel.hidden = false;
          videoPreview.src = item.path;
          resultTopic.textContent = item.topic;
          downloadLink.href = item.path;
          downloadLink.setAttribute("download", item.path.split("/").pop() || "snapreel.mp4");
          videoPreview.play().catch(() => {});
          resultPanel.scrollIntoView({ behavior: "smooth" });
        });
        historyList.appendChild(div);
      });
    } catch (err) {
      console.warn("Could not load video history:", err);
    }
  }

  async function loadBenchmarks() {
    try {
      const res = await fetch("/benchmark");
      if (!res.ok) return;
      const bench = await res.json();
      if (bench.device) benchDevice.textContent = bench.device;
      if (bench.llm_latency_sec) benchLlm.textContent = `~${bench.llm_latency_sec}s / scene`;
      if (bench.llm_tokens_per_sec) benchTps.textContent = `${bench.llm_tokens_per_sec} tok/s`;
      if (bench.renderer_fps) benchFps.textContent = `${bench.renderer_fps} fps native`;
    } catch (err) {
      console.warn("Could not load benchmarks:", err);
    }
  }

  generateBtn.addEventListener("click", startGeneration);
  retryBtn.addEventListener("click", startGeneration);

  createAnotherBtn.addEventListener("click", () => {
    resultPanel.hidden = true;
    topicInput.value = "";
    topicInput.focus();
  });

  topicInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      startGeneration();
    }
  });

  // Initial load
  loadSettings();
  loadHistory();
  loadBenchmarks();
});
