/**
 * DBOS EV Charging Control Plane - System Dashboard Controller (Tab 1)
 * Handles the OS Ready Queue PCB Inspector, Real-Time Animated Battery Telemetry Growth Curves,
 * Physical Hardware Station Telemetry, and C++ Intelligent Scheduling Execution.
 *
 * Implements strict Step-by-Step OS Lifecycle:
 *   1. WAITING in Queue: Telemetry in Standby (shows arrival SoC, NO automatic charging).
 *   2. Auto-Scheduler: C++ engine decides execution order.
 *   3. Allocate Chargers: Transitions WAITING -> RUNNING. NOW and only now does battery actively charge!
 *   4. Simulate & Release: Completes session, releases hardware, advances NEXT car in queue!
 */

import { DBOSApi } from "./api.js?v=7";

export class DashboardController {
  constructor() {
    this.queue = [];
    this.activeCharging = [];
    this.telemetry = null;

    // Telemetry State Machine
    this.selectedJob = null;
    this.isActivelyCharging = false;
    this.liveSoc = 0.0;
    this.initialSoc = 0.0;
    this.targetSoc = 80.0;
    this.liveProgressRatio = 0.0;
    this.telemetryTimer = null;

    this.initElements();
    this.bindEvents();
    this.loadDashboardData();
  }

  initElements() {
    // PCB Queue Elements
    this.queueTableBody = document.getElementById("queueTableBody");
    this.queueCountBadge = document.getElementById("queueCountBadge");
    this.btnRefreshQueue = document.getElementById("btnRefreshQueue");

    // Battery Telemetry Elements
    this.batteryVisualFill = document.getElementById("batteryVisualFill");
    this.batteryGaugePct = document.getElementById("batteryGaugePct");
    this.batteryGaugeTarget = document.getElementById("batteryGaugeTarget");
    this.batteryVehicleTitle = document.getElementById("batteryVehicleTitle");
    this.batteryTelemetryInfo = document.getElementById("batteryTelemetryInfo");
    this.telemetrySvgContainer = document.getElementById("telemetrySvgContainer");
    this.telemetryStreamStatus = document.getElementById("telemetryStreamStatus");
    this.btnResetTelemetry = document.getElementById("btnResetTelemetry");

    // Hardware Telemetry Elements
    this.dashPowerBar = document.getElementById("dashPowerBar");
    this.dashPowerText = document.getElementById("dashPowerText");
    this.dashAvailPorts = document.getElementById("dashAvailPorts");
    this.dashOccPorts = document.getElementById("dashOccPorts");
    this.dashActiveSessions = document.getElementById("dashActiveSessions");

    // Scheduler & Console Elements (Step 6)
    this.btnRunScheduler = document.getElementById("btnRunScheduler");
    this.btnAllocateResources = document.getElementById("btnAllocateResources");
    this.btnSimulateRelease = document.getElementById("btnSimulateRelease");
    this.btnClearConsole = document.getElementById("btnClearConsole");
    this.schedulerConsole = document.getElementById("schedulerConsole");
    this.schedulerDecisionBox = document.getElementById("schedulerDecisionBox");
    this.schedAlgoName = document.getElementById("schedAlgoName");
    this.schedBinaryName = document.getElementById("schedBinaryName");
    this.schedReasonText = document.getElementById("schedReasonText");
  }

  bindEvents() {
    if (this.btnRefreshQueue) {
      this.btnRefreshQueue.addEventListener("click", () => {
        this.btnRefreshQueue.textContent = "🔄 Refreshing...";
        this.loadDashboardData().finally(() => {
          setTimeout(() => {
            if (this.btnRefreshQueue) this.btnRefreshQueue.textContent = "🔄 Refresh Queue";
          }, 400);
          this.toast("Queue & Telemetry refreshed.", "info");
        });
      });
    }

    if (this.btnResetTelemetry) {
      this.btnResetTelemetry.addEventListener("click", () => {
        this.resetLiveTelemetry();
      });
    }

    if (this.btnRunScheduler) {
      this.btnRunScheduler.addEventListener("click", () => this.runAutoScheduler());
    }

    if (this.btnAllocateResources) {
      this.btnAllocateResources.addEventListener("click", () => this.allocateResources());
    }

    if (this.btnSimulateRelease) {
      this.btnSimulateRelease.addEventListener("click", () => this.simulateRelease());
    }

    if (this.btnClearConsole) {
      this.btnClearConsole.addEventListener("click", () => {
        if (this.schedulerConsole) {
          this.schedulerConsole.textContent = "Console cleared.\n";
        }
        if (this.schedulerDecisionBox) {
          this.schedulerDecisionBox.style.display = "none";
        }
      });
    }

    // Refresh when Tab 1 becomes active
    window.addEventListener("dbos:tabChanged", (e) => {
      if (e.detail.tabId === "tab-dashboard") {
        this.loadDashboardData();
      }
    });
  }

  async runAutoScheduler() {
    if (!this.btnRunScheduler) return;

    this.btnRunScheduler.disabled = true;
    this.btnRunScheduler.textContent = "⚡ Running Auto-Scheduler (C++)...";

    const res = await DBOSApi.runAutoScheduler();

    this.btnRunScheduler.disabled = false;
    this.btnRunScheduler.textContent = "⚡ Run Intelligent Auto-Scheduler (C++)";

    if (res.ok && res.data.success) {
      if (this.schedulerConsole) {
        this.schedulerConsole.textContent = res.data.console_output;
      }

      if (this.schedulerDecisionBox) {
        this.schedulerDecisionBox.style.display = "block";
      }
      if (this.schedAlgoName) this.schedAlgoName.textContent = res.data.algorithm;
      if (this.schedBinaryName) this.schedBinaryName.textContent = `${res.data.selected_executable}.exe`;
      if (this.schedReasonText) this.schedReasonText.textContent = res.data.reason;

      this.toast(`[DONE] ${res.data.algorithm} selected! Next, click Allocate Chargers & Hardware Dispatch.`, "success");
    } else {
      const msg = res.data?.message || res.data?.error || "Scheduler execution failed.";
      if (this.schedulerConsole) {
        this.schedulerConsole.textContent = `[INFO] ${msg}\n`;
      }
      this.toast(`[INFO] ${msg}`, "info");
    }

    await this.loadDashboardData();
  }

  async allocateResources() {
    if (!this.btnAllocateResources) return;

    this.btnAllocateResources.disabled = true;
    this.btnAllocateResources.textContent = "🔌 Allocating Chargers & Dispatching...";

    const res = await DBOSApi.allocateResources();

    this.btnAllocateResources.disabled = false;
    this.btnAllocateResources.textContent = "🔌 Allocate Chargers & Hardware Dispatch";

    if (res.ok && res.data.success) {
      if (this.schedulerConsole) {
        this.schedulerConsole.textContent = res.data.console_output;
      }
      this.toast("[DISPATCHED] Chargers allocated & sessions started! Watch the battery gauge above.", "success");
    } else {
      const msg = res.data?.error || "Allocation failed.";
      this.toast(`[ERROR] ${msg}`, "error");
    }

    await this.loadDashboardData();
    if (window.dbosApp) {
      window.dbosApp.updateTelemetry();
    }
  }

  async simulateRelease() {
    if (!this.btnSimulateRelease) return;

    this.btnSimulateRelease.disabled = true;
    this.btnSimulateRelease.textContent = "🔄 Simulating & Releasing Chargers...";

    const res = await DBOSApi.simulateAndRelease();

    this.btnSimulateRelease.disabled = false;
    this.btnSimulateRelease.textContent = "🔄 Auto-Simulate & Release Chargers";

    if (res.ok && res.data.success) {
      if (this.schedulerConsole) {
        this.schedulerConsole.textContent = res.data.console_output;
      }
      this.toast("[RELEASED] Charging sessions completed and charger ports freed!", "success");
    } else {
      const msg = res.data?.error || "Release operation failed.";
      this.toast(`[ERROR] ${msg}`, "error");
    }

    await this.loadDashboardData();
    if (window.dbosApp) {
      window.dbosApp.updateTelemetry();
    }
  }

  async loadDashboardData() {
    await Promise.all([
      this.loadQueue(),
      this.loadTelemetry()
    ]);
  }

  async loadQueue() {
    const res = await DBOSApi.getQueue();
    if (res.ok && res.data.success) {
      this.queue = res.data.queue || [];
      this.activeCharging = res.data.active_charging || [];

      this.renderQueueTable(this.queue, this.activeCharging);
      if (this.queueCountBadge) {
        const waitingCount = this.queue.length;
        const activeCount = this.activeCharging.length;
        this.queueCountBadge.textContent = `${waitingCount} Waiting | ${activeCount} Charging`;
      }

      // Step-by-Step Lifecycle Telemetry Selection:
      // 1. If any car is ACTIVELY CHARGING (dispatched to a charger), focus on it!
      // 2. Otherwise, focus on the HEAD of the waiting queue in STANDBY (arrival SoC, not charging yet)
      // 3. Otherwise, empty state
      if (this.activeCharging.length > 0) {
        const chargingCar = this.activeCharging[0];
        this.selectJobForTelemetry(chargingCar, true);
      } else if (this.queue.length > 0) {
        const headCar = this.selectedJob && this.queue.some(j => j.request_id === this.selectedJob.request_id)
          ? this.queue.find(j => j.request_id === this.selectedJob.request_id)
          : this.queue[0];
        this.selectJobForTelemetry(headCar, false);
      } else {
        this.renderEmptyBatteryTelemetry();
      }
    }
  }

  renderQueueTable(queueList, activeList = []) {
    if (!this.queueTableBody) return;

    if (queueList.length === 0 && activeList.length === 0) {
      this.queueTableBody.innerHTML = `
        <tr>
          <td colspan="8" style="text-align: center; color: var(--text-muted); padding: 28px;">
            <div style="font-size: 14px; margin-bottom: 6px;">⚡ Ready Queue & Active Sessions Empty</div>
            <div style="font-size: 11px;">Open the <strong>Charging Request Admission</strong> tab to admit an EV process into the OS ready queue.</div>
          </td>
        </tr>
      `;
      return;
    }

    let rowsHtml = "";

    // Section 1: Actively Charging (RUNNING) Rows
    if (activeList.length > 0) {
      rowsHtml += activeList
        .map((r) => {
          const isSelected = this.selectedJob && this.selectedJob.request_id === r.request_id;
          return `
            <tr class="clickable-row ${isSelected ? 'selected-pcb-row' : ''}" data-pid="${r.request_id}" data-type="active" style="background: rgba(16, 185, 129, 0.08); cursor: pointer;">
              <td>
                <span class="pcb-pid-badge" style="background: #065f46; color: #34d399; border-color: #059669;">P${r.request_id}</span>
                <span class="badge badge-running" style="margin-left: 4px; font-size: 9px;">CHARGING</span>
              </td>
              <td>
                <strong style="color: #6ee7b7;">${this.escapeHtml(r.ev_model)}</strong>
                <div style="font-size: 10px; color: var(--text-muted);">${r.username ? `${this.escapeHtml(r.username)} • ` : ''}Port #${r.charger_id} @ ${this.escapeHtml(r.station_name || "Station")}</div>
              </td>
              <td>
                <div>Session #${r.session_id}</div>
                <div style="font-size: 10px; color: #34d399;">IN_PROGRESS</div>
              </td>
              <td>
                <strong style="color: #a78bfa;">${r.burst_time.toFixed(2)} hrs</strong>
                <div style="font-size: 10px; color: var(--text-muted);">Alloc: ${r.allocated_power} kW</div>
              </td>
              <td>
                <span class="badge badge-running">Active Flow</span>
              </td>
              <td>
                <strong style="font-size: 13px; color: #34d399;">RUNNING</strong>
              </td>
              <td>
                <span class="badge badge-tier1">Dispatched</span>
              </td>
              <td>
                <span class="badge badge-running">RUNNING</span>
              </td>
            </tr>
          `;
        })
        .join("");
    }

    // Section 2: Waiting Queue (WAITING) Rows
    if (queueList.length > 0) {
      rowsHtml += queueList
        .map((r, idx) => {
          const soc = parseFloat(r.soc_at_request);
          const burstTime = parseFloat(r.burst_time);
          const priorityScore = parseFloat(r.priority_score).toFixed(1);
          const isSelected = this.selectedJob && this.selectedJob.request_id === r.request_id && !this.isActivelyCharging;

          // Tier classification badge
          const tierBadgeClass = r.tier === 1 ? "badge-tier1" : "badge-tier2";
          const tierLabel = r.tier === 1 ? "Tier 1 (High SLA)" : "Tier 2 (Standard)";

          // SoC badge
          let socBadgeClass = "badge-waiting";
          if (soc <= 20) socBadgeClass = "badge-rejected";
          else if (soc >= 70) socBadgeClass = "badge-completed";

          return `
            <tr class="clickable-row ${isSelected ? 'selected-pcb-row' : ''}" data-pid="${r.request_id}" data-type="waiting" style="cursor: pointer;">
              <td>
                <span class="pcb-pid-badge">P${r.request_id}</span>
                ${idx === 0 ? '<span class="badge badge-waiting" style="margin-left: 4px; font-size: 9px;">HEAD</span>' : ''}
              </td>
              <td>
                <strong>${this.escapeHtml(r.ev_model)}</strong>
                <div style="font-size: 10px; color: var(--text-muted);">${r.username ? `${this.escapeHtml(r.username)} • ` : ''}EV ID: #${r.ev_id}</div>
              </td>
              <td>
                <div>${r.arrival_time ? r.arrival_time.substring(11, 16) : '--:--'}</div>
                <div style="font-size: 10px; color: var(--text-muted);">+${r.arrival_offset_hours.toFixed(2)} hrs</div>
              </td>
              <td>
                <strong style="color: #a78bfa;">${burstTime.toFixed(2)} hrs</strong>
                <div style="font-size: 10px; color: var(--text-muted);">(~${Math.round(burstTime * 60)} mins)</div>
              </td>
              <td>
                <span class="badge ${socBadgeClass}">${soc.toFixed(1)}%</span>
              </td>
              <td>
                <strong style="font-size: 13px; color: ${r.tier === 1 ? '#c084fc' : '#e2e8f0'};">${priorityScore}</strong>
                ${r.aging_bonus > 0 ? `<div style="font-size: 9px; color: #fbbf24;">Aging -${parseFloat(r.aging_bonus).toFixed(1)}</div>` : ''}
              </td>
              <td>
                <span class="badge ${tierBadgeClass}" title="${this.escapeHtml(r.tier_reason)}">
                  ${tierLabel}
                </span>
              </td>
              <td>
                <span class="badge badge-waiting">${r.process_state}</span>
              </td>
            </tr>
          `;
        })
        .join("");
    }

    this.queueTableBody.innerHTML = rowsHtml;

    // Attach row selection click listeners
    const rows = this.queueTableBody.querySelectorAll("tr.clickable-row");
    rows.forEach((row) => {
      row.addEventListener("click", () => {
        const pid = parseInt(row.getAttribute("data-pid"), 10);
        const type = row.getAttribute("data-type");

        let job = null;
        let isActivelyCharging = false;
        if (type === "active") {
          job = this.activeCharging.find((j) => j.request_id === pid);
          isActivelyCharging = true;
        } else {
          job = this.queue.find((j) => j.request_id === pid);
          isActivelyCharging = false;
        }

        if (job) {
          this.selectJobForTelemetry(job, isActivelyCharging);
          this.toast(`Pivoted telemetry view to P${job.request_id} (${job.ev_model})`, "info");
        }
      });
    });
  }

  selectJobForTelemetry(job, isActivelyCharging = false) {
    this.selectedJob = job;
    this.isActivelyCharging = isActivelyCharging;

    // Highlight active row in table
    const rows = this.queueTableBody.querySelectorAll("tr.clickable-row");
    rows.forEach((r) => {
      const pid = parseInt(r.getAttribute("data-pid"), 10);
      if (pid === job.request_id) {
        r.classList.add("selected-pcb-row");
      } else {
        r.classList.remove("selected-pcb-row");
      }
    });

    if (this.telemetryTimer) {
      clearInterval(this.telemetryTimer);
      this.telemetryTimer = null;
    }

    this.initialSoc = parseFloat(job.soc_at_request || 0);
    if (job.target_soc !== undefined && job.target_soc !== null) {
      this.targetSoc = Math.min(100, Math.max(this.initialSoc, parseFloat(job.target_soc)));
    } else if (parseFloat(job.battery_capacity) > 0) {
      const raw = this.initialSoc + (parseFloat(job.required_energy || 0) / parseFloat(job.battery_capacity)) * 100.0;
      const clamped = Math.min(100, Math.max(this.initialSoc, raw));
      this.targetSoc = Math.abs(clamped - Math.round(clamped)) <= 0.2 ? Math.round(clamped) : Math.round(clamped * 10) / 10;
    } else {
      this.targetSoc = this.initialSoc >= 80 ? 100 : 80;
    }
    this.liveSoc = this.initialSoc;
    this.liveProgressRatio = 0.0;

    const power = parseFloat(job.allocated_power || job.requested_power || 50);

    // Initial visual update
    this.updateTelemetryVisuals(job, this.isActivelyCharging);

    // ONLY IF ACTIVELY CHARGING (after charger allocation): start live increasing clock!
    if (this.isActivelyCharging) {
      this.telemetryTimer = setInterval(() => {
        if (this.liveSoc < this.targetSoc) {
          const rate = (power / 50.0) * 0.4;
          this.liveSoc = Math.min(this.targetSoc, +(this.liveSoc + rate).toFixed(2));
          const delta = this.targetSoc - this.initialSoc;
          this.liveProgressRatio = delta > 0 ? (this.liveSoc - this.initialSoc) / delta : 1.0;
        }

        this.updateTelemetryVisuals(job, true);
      }, 500);
    }
  }

  updateTelemetryVisuals(job, isCharging) {
    const power = parseFloat(job.allocated_power || job.requested_power || 50);
    const energy = parseFloat(job.required_energy || 20);
    const burstHours = parseFloat(job.burst_time || 0.5);

    // Header Title
    if (this.batteryVehicleTitle) {
      const statusPrefix = isCharging ? "[CHARGING]" : "[QUEUED]";
      const ownerTag = job.username ? ` (${job.username})` : "";
      this.batteryVehicleTitle.textContent = `${statusPrefix} P${job.request_id}: ${job.ev_model}${ownerTag}`;
    }

    // Gauge Percentage & Target
    const targetFmt = Number.isInteger(this.targetSoc) ? this.targetSoc.toFixed(0) : this.targetSoc.toFixed(1);
    if (this.batteryGaugePct) {
      this.batteryGaugePct.textContent = `${this.liveSoc.toFixed(1)}%`;
    }
    if (this.batteryGaugeTarget) {
      this.batteryGaugeTarget.textContent = `${targetFmt}% Target`;
    }

    // Visual Battery Fill Bar
    if (this.batteryVisualFill) {
      this.batteryVisualFill.style.width = `${Math.min(100, Math.max(12, this.liveSoc))}%`;
      this.batteryVisualFill.textContent = `${Math.round(this.liveSoc)}%`;

      let colorClass = "fill-medium";
      if (this.liveSoc <= 20) colorClass = "fill-critical";
      else if (this.liveSoc >= 60) colorClass = "fill-healthy";

      const shouldAnimate = isCharging && this.liveSoc < this.targetSoc;
      this.batteryVisualFill.className = `battery-visual-fill ${colorClass} ${shouldAnimate ? 'battery-charging-active' : ''}`;
    }

    // Status Header Badge
    if (this.telemetryStreamStatus) {
      if (isCharging) {
        if (this.liveSoc >= this.targetSoc) {
          this.telemetryStreamStatus.className = "badge badge-completed";
          this.telemetryStreamStatus.textContent = `✓ CHARGING COMPLETE (${this.targetSoc}%)`;
        } else {
          this.telemetryStreamStatus.className = "badge badge-running";
          const portStr = job.charger_id ? `Port #${job.charger_id}` : "Hardware";
          this.telemetryStreamStatus.textContent = `⚡ ACTIVE CHARGING (${portStr} @ ${power} kW)`;
        }
      } else {
        this.telemetryStreamStatus.className = "badge badge-waiting";
        this.telemetryStreamStatus.textContent = "⏳ QUEUED (Awaiting Charger Allocation)";
      }
    }

    // Subtitle Information
    if (this.batteryTelemetryInfo) {
      if (isCharging) {
        const isComplete = this.liveSoc >= this.targetSoc;
        const statusHtml = isComplete
          ? `<span class="badge badge-completed">CHARGED TO TARGET</span>`
          : `<span class="badge badge-running" style="font-size: 10px;">⚡ INFLUX: +${((power / 50.0) * 0.8).toFixed(1)}%/s</span>`;

        this.batteryTelemetryInfo.innerHTML = `
          Allocated: <strong>${power.toFixed(1)} kW</strong> | Port: <strong>#${job.charger_id || 1}</strong> | Energy: <strong>${energy.toFixed(1)} kWh</strong> | ${statusHtml}
        `;
      } else {
        this.batteryTelemetryInfo.innerHTML = `
          Arrival: <strong>${this.initialSoc.toFixed(1)}% SoC</strong> | Est. Duration: <strong>${burstHours.toFixed(2)}h</strong> | <span style="color: var(--text-secondary);">Click <strong>"Allocate Chargers"</strong> below to begin active charging.</span>
        `;
      }
    }

    // Render SVG Curve
    this.renderSvgChargingCurve(
      this.initialSoc,
      this.targetSoc,
      burstHours,
      job,
      this.liveSoc,
      this.liveProgressRatio,
      isCharging
    );
  }

  resetLiveTelemetry() {
    if (this.selectedJob) {
      this.selectJobForTelemetry(this.selectedJob, this.isActivelyCharging);
      this.toast(`Telemetry reset to initial ${this.initialSoc}% SoC.`, "info");
    }
  }

  renderEmptyBatteryTelemetry() {
    if (this.telemetryTimer) {
      clearInterval(this.telemetryTimer);
      this.telemetryTimer = null;
    }

    if (this.batteryVehicleTitle) this.batteryVehicleTitle.textContent = "No Process in Ready Queue";
    if (this.batteryGaugePct) this.batteryGaugePct.textContent = "--%";
    if (this.batteryGaugeTarget) this.batteryGaugeTarget.textContent = "--%";
    if (this.batteryVisualFill) {
      this.batteryVisualFill.style.width = "0%";
      this.batteryVisualFill.className = "battery-visual-fill fill-medium";
      this.batteryVisualFill.textContent = "";
    }
    if (this.batteryTelemetryInfo) {
      this.batteryTelemetryInfo.textContent = "Awaiting process admission into the Ready Queue.";
    }
    if (this.telemetryStreamStatus) {
      this.telemetryStreamStatus.className = "badge badge-waiting";
      this.telemetryStreamStatus.textContent = "IDLE (Queue Empty)";
    }
    if (this.telemetrySvgContainer) {
      this.telemetrySvgContainer.innerHTML = `
        <div style="height: 160px; display: flex; align-items: center; justify-content: center; color: var(--text-muted); font-size: 12px;">
          Battery trajectory curve will render when a process enters the Ready Queue.
        </div>
      `;
    }
  }

  renderSvgChargingCurve(startSoc, endSoc, burstHours, job, liveSoc, progressRatio, isCharging) {
    if (!this.telemetrySvgContainer) return;

    const width = 640;
    const height = 165;
    const padL = 45;
    const padR = 30;
    const padT = 24;
    const padB = 30;

    const plotW = width - padL - padR;
    const plotH = height - padT - padB;

    // Time steps from 0 to burstHours
    const steps = 20;
    const points = [];
    const expNorm = 1 - Math.exp(-3);

    for (let i = 0; i <= steps; i++) {
      const tRatio = i / steps;
      const tHours = tRatio * burstHours;
      // Linear CC phase charging equation with normalized CV tapering >80% so endpoint hits exact endSoc
      let soc = startSoc + (endSoc - startSoc) * tRatio;
      if (soc > 80 && endSoc > 80) {
        const knee = Math.max(80, startSoc);
        if (endSoc > knee && soc > knee) {
          const u = (soc - knee) / (endSoc - knee);
          soc = knee + (endSoc - knee) * ((1 - Math.exp(-3 * u)) / expNorm);
        }
      }

      const x = padL + (tRatio * plotW);
      const y = padT + plotH - ((soc / 100) * plotH);
      points.push({ x, y, tHours, soc });
    }

    const pathData = points.map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");

    // Grid lines for 20%, 50%, 80%, 100%
    const gridY20 = padT + plotH - (0.2 * plotH);
    const gridY50 = padT + plotH - (0.5 * plotH);
    const gridY80 = padT + plotH - (0.8 * plotH);
    const gridY100 = padT;

    // Current live tracking dot position along curve
    const clampedProgress = Math.min(1.0, Math.max(0.0, progressRatio));
    const liveX = padL + (clampedProgress * plotW);
    const liveY = padT + plotH - ((liveSoc / 100) * plotH);
    const liveAnchor = clampedProgress < 0.15 ? "start" : (clampedProgress > 0.85 ? "end" : "middle");
    const targetFmt = Number.isInteger(endSoc) ? endSoc.toFixed(0) : endSoc.toFixed(1);
    const lastPoint = points[points.length - 1];

    const activeTrackerHtml = isCharging
      ? `
        <!-- Vertical Scanline tracking live charging time -->
        <line x1="${liveX.toFixed(1)}" y1="${padT}" x2="${liveX.toFixed(1)}" y2="${padT + plotH}" stroke="#34d399" stroke-width="1.5" stroke-dasharray="3,3" opacity="0.85" />

        <!-- Live Animated Tracking Pulse Dot -->
        <circle cx="${liveX.toFixed(1)}" cy="${liveY.toFixed(1)}" r="7" fill="#10b981" stroke="#ffffff" stroke-width="2">
          <animate attributeName="r" values="6;9;6" dur="1.2s" repeatCount="indefinite" />
        </circle>
        <text x="${liveX.toFixed(1)}" y="${Math.max(14, liveY - 12).toFixed(1)}" fill="#34d399" font-size="10" font-weight="bold" font-family="monospace" text-anchor="${liveAnchor}">Live: ${liveSoc.toFixed(1)}%</text>
      `
      : `
        <!-- Stationary Queued Marker at Arrival -->
        <circle cx="${points[0].x.toFixed(1)}" cy="${points[0].y.toFixed(1)}" r="6" fill="#3b82f6" stroke="#ffffff" stroke-width="2" />
        <text x="${(points[0].x + 8).toFixed(1)}" y="${Math.max(14, points[0].y - 10).toFixed(1)}" fill="#93c5fd" font-size="10" font-weight="bold" font-family="monospace" text-anchor="start">Arrival: ${startSoc.toFixed(1)}% (Queued)</text>
      `;

    const svg = `
      <svg viewBox="0 0 ${width} ${height}" class="telemetry-svg">
        <defs>
          <linearGradient id="curveGradient" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="#3b82f6" />
            <stop offset="70%" stop-color="#10b981" />
            <stop offset="100%" stop-color="#34d399" />
          </linearGradient>
          <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="rgba(16, 185, 129, 0.25)" />
            <stop offset="100%" stop-color="rgba(16, 185, 129, 0.0)" />
          </linearGradient>
        </defs>

        <!-- Horizontal Grid Lines -->
        <line x1="${padL}" y1="${gridY20}" x2="${width - padR}" y2="${gridY20}" stroke="#1f2937" stroke-dasharray="4,4" />
        <text x="${padL - 8}" y="${gridY20 + 3}" fill="#6b7280" font-size="9" text-anchor="end" font-family="monospace">20%</text>

        <line x1="${padL}" y1="${gridY50}" x2="${width - padR}" y2="${gridY50}" stroke="#1f2937" stroke-dasharray="4,4" />
        <text x="${padL - 8}" y="${gridY50 + 3}" fill="#6b7280" font-size="9" text-anchor="end" font-family="monospace">50%</text>

        <line x1="${padL}" y1="${gridY80}" x2="${width - padR}" y2="${gridY80}" stroke="#374151" stroke-dasharray="2,2" />
        <text x="${padL - 8}" y="${gridY80 + 3}" fill="#9ca3af" font-size="9" text-anchor="end" font-family="monospace">80%</text>

        <line x1="${padL}" y1="${gridY100}" x2="${width - padR}" y2="${gridY100}" stroke="#374151" stroke-dasharray="2,2" />
        <text x="${padL - 8}" y="${gridY100 + 3}" fill="#34d399" font-size="9" text-anchor="end" font-family="monospace">100%</text>

        <!-- Axes -->
        <line x1="${padL}" y1="${padT}" x2="${padL}" y2="${padT + plotH}" stroke="#374151" stroke-width="1.5" />
        <line x1="${padL}" y1="${padT + plotH}" x2="${width - padR}" y2="${padT + plotH}" stroke="#374151" stroke-width="1.5" />

        <!-- Area under curve -->
        <path d="${pathData} L ${lastPoint.x.toFixed(1)} ${padT + plotH} L ${points[0].x.toFixed(1)} ${padT + plotH} Z" fill="url(#areaGradient)" />

        <!-- Trajectory Curve Path -->
        <path d="${pathData}" fill="none" stroke="url(#curveGradient)" stroke-width="2.5" />

        <!-- Dynamic Tracking Marker -->
        ${activeTrackerHtml}

        <!-- End Point Dot -->
        <circle cx="${lastPoint.x.toFixed(1)}" cy="${lastPoint.y.toFixed(1)}" r="4" fill="#10b981" stroke="#ffffff" stroke-width="1.5" />
        <text x="${(lastPoint.x - 6).toFixed(1)}" y="${Math.max(13, lastPoint.y - 8).toFixed(1)}" fill="#34d399" font-size="9.5" font-weight="bold" font-family="monospace" text-anchor="end">Target: ${targetFmt}%</text>

        <!-- X Axis Labels (Time) -->
        <text x="${padL}" y="${height - 10}" fill="#9ca3af" font-size="10" font-family="monospace">t = 0 hrs</text>
        <text x="${(padL + width - padR) / 2}" y="${height - 10}" fill="#9ca3af" font-size="10" font-family="monospace" text-anchor="middle">Time Elapsed (hours) &rarr;</text>
        <text x="${width - padR}" y="${height - 10}" fill="#a78bfa" font-size="10" font-weight="bold" font-family="monospace" text-anchor="end">t = ${burstHours.toFixed(2)}h (${Math.round(burstHours * 60)}m)</text>
      </svg>
    `;

    this.telemetrySvgContainer.innerHTML = svg;
  }

  async loadTelemetry() {
    const res = await DBOSApi.getTelemetry();
    if (res.ok && res.data.success) {
      this.telemetry = res.data.telemetry;
      const tel = this.telemetry;

      if (this.dashPowerBar) {
        this.dashPowerBar.style.width = `${Math.min(100, tel.power_utilization_pct)}%`;
      }
      if (this.dashPowerText) {
        this.dashPowerText.textContent = `${tel.used_power_kw} kW / ${tel.total_power_kw} kW (${tel.power_utilization_pct}% Load)`;
      }
      if (this.dashAvailPorts) this.dashAvailPorts.textContent = `${tel.available_chargers} Available`;
      if (this.dashOccPorts) this.dashOccPorts.textContent = `${tel.occupied_chargers} Occupied`;
      if (this.dashActiveSessions) this.dashActiveSessions.textContent = `${tel.active_sessions} Sessions Active`;
    }
  }

  toast(msg, type = "info") {
    if (window.dbosApp) {
      window.dbosApp.showToast(msg, type);
    } else {
      alert(msg);
    }
  }

  escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
}
