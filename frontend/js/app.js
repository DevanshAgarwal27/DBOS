/**
 * DBOS EV Charging Control Plane - Main Application Controller
 * Handles 3-tab navigation, live telemetry polling, and UI toast notifications.
 */

import { DBOSApi } from "./api.js?v=7";
import { RegistrationController } from "./registration.js?v=7";
import { AdmissionController } from "./admission.js?v=7";
import { DashboardController } from "./dashboard.js?v=7";

class DBOSApp {
  constructor() {
    this.activeTab = "tab-dashboard";
    this.telemetryPollInterval = null;
    this.initElements();
    this.bindEvents();
    this.startTelemetryPolling();
  }

  initElements() {
    this.tabButtons = document.querySelectorAll(".nav-tab-btn");
    this.tabContents = document.querySelectorAll(".tab-content");
    this.toastContainer = document.getElementById("toastContainer");

    // Quick-Start Guide Elements
    this.quickstartBanner = document.getElementById("quickstartBanner");
    this.btnToggleGuide = document.getElementById("btnToggleGuide");
    this.btnHideGuide = document.getElementById("btnHideGuide");
    this.quickstartSteps = document.querySelectorAll(".quickstart-step");

    // KPI Elements
    this.kpiTotalPower = document.getElementById("kpiTotalPower");
    this.kpiUsedPower = document.getElementById("kpiUsedPower");
    this.kpiRemainingPower = document.getElementById("kpiRemainingPower");
    this.kpiPowerUtil = document.getElementById("kpiPowerUtil");
    this.kpiChargersAvail = document.getElementById("kpiChargersAvail");
    this.kpiChargersOcc = document.getElementById("kpiChargersOcc");
    this.kpiWaitingQueue = document.getElementById("kpiWaitingQueue");
    this.kpiActiveSessions = document.getElementById("kpiActiveSessions");

    // Header badge
    this.serverStatusDot = document.getElementById("serverStatusDot");
    this.serverStatusText = document.getElementById("serverStatusText");
  }

  bindEvents() {
    this.tabButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const targetTab = btn.getAttribute("data-tab");
        this.switchTab(targetTab);
      });
    });

    if (this.btnHideGuide && this.quickstartBanner) {
      this.btnHideGuide.addEventListener("click", () => {
        this.quickstartBanner.style.display = "none";
      });
    }

    if (this.btnToggleGuide && this.quickstartBanner) {
      this.btnToggleGuide.addEventListener("click", () => {
        const isHidden = this.quickstartBanner.style.display === "none";
        this.quickstartBanner.style.display = isHidden ? "block" : "none";
      });
    }

    this.quickstartSteps.forEach((stepBtn) => {
      stepBtn.addEventListener("click", () => {
        const targetTab = stepBtn.getAttribute("data-goto-tab");
        const scrollToId = stepBtn.getAttribute("data-scroll-to");
        if (targetTab) {
          this.switchTab(targetTab);
        }
        if (scrollToId) {
          setTimeout(() => {
            const targetEl = document.getElementById(scrollToId);
            if (targetEl) targetEl.scrollIntoView({ behavior: "smooth", block: "start" });
          }, 80);
        }
      });
    });
  }

  switchTab(targetTabId) {
    if (this.activeTab === targetTabId) return;

    // Update buttons
    this.tabButtons.forEach((btn) => {
      if (btn.getAttribute("data-tab") === targetTabId) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    });

    // Update tab visibility without reloading or losing input state
    this.tabContents.forEach((tab) => {
      if (tab.id === targetTabId) {
        tab.classList.add("active");
      } else {
        tab.classList.remove("active");
      }
    });

    this.activeTab = targetTabId;

    // Dispatch event so individual tab modules can react when opened
    window.dispatchEvent(
      new CustomEvent("dbos:tabChanged", { detail: { tabId: targetTabId } })
    );
  }

  async updateTelemetry() {
    const res = await DBOSApi.getTelemetry();
    if (res.ok && res.data.success) {
      const tel = res.data.telemetry;
      if (this.kpiTotalPower) this.kpiTotalPower.textContent = `${tel.total_power_kw}`;
      if (this.kpiUsedPower) this.kpiUsedPower.textContent = `${tel.used_power_kw}`;
      if (this.kpiRemainingPower) this.kpiRemainingPower.textContent = `${tel.remaining_power_kw}`;
      if (this.kpiPowerUtil) this.kpiPowerUtil.textContent = `${tel.power_utilization_pct}%`;
      if (this.kpiChargersAvail) this.kpiChargersAvail.textContent = `${tel.available_chargers}`;
      if (this.kpiChargersOcc) this.kpiChargersOcc.textContent = `${tel.occupied_chargers}`;
      if (this.kpiWaitingQueue) this.kpiWaitingQueue.textContent = `${tel.waiting_requests}`;
      if (this.kpiActiveSessions) this.kpiActiveSessions.textContent = `${tel.active_sessions}`;

      if (this.serverStatusDot) this.serverStatusDot.style.backgroundColor = "#34d399";
      if (this.serverStatusText) this.serverStatusText.textContent = "CONNECTED (ACID)";
    } else {
      if (this.serverStatusDot) this.serverStatusDot.style.backgroundColor = "#f87171";
      if (this.serverStatusText) this.serverStatusText.textContent = "DISCONNECTED";
    }
  }

  startTelemetryPolling() {
    this.updateTelemetry();
    // Refresh telemetry every 5 seconds
    this.telemetryPollInterval = setInterval(() => this.updateTelemetry(), 5000);
  }

  showToast(message, type = "info") {
    if (!this.toastContainer) return;
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    this.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 4000);
  }
}

// Robust Initialization (handles cases where DOMContentLoaded already fired)
function initDBOS() {
  try {
    window.dbosApp = new DBOSApp();
    console.log("[DBOS] App controller initialized.");
  } catch (e) {
    console.error("[DBOS] Failed to initialize DBOSApp:", e);
  }

  try {
    window.dashboardController = new DashboardController();
    console.log("[DBOS] Dashboard controller initialized.");
  } catch (e) {
    console.error("[DBOS] Failed to initialize DashboardController:", e);
  }

  try {
    window.registrationController = new RegistrationController();
    console.log("[DBOS] Registration controller initialized.");
  } catch (e) {
    console.error("[DBOS] Failed to initialize RegistrationController:", e);
  }

  try {
    window.admissionController = new AdmissionController();
    console.log("[DBOS] Admission controller initialized.");
  } catch (e) {
    console.error("[DBOS] Failed to initialize AdmissionController:", e);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initDBOS);
} else {
  initDBOS();
}

