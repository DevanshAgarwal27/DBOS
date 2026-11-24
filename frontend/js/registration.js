/**
 * DBOS EV Charging Control Plane - User & EV Registration Controller (Tab 2)
 * Manages workload injection, vehicle catalogue dropdowns, validation, and live fleet directory.
 */

import { DBOSApi } from "./api.js?v=7";

export class RegistrationController {
  constructor() {
    this.catalogue = [];
    this.locations = [];
    this.fleet = [];

    this.initElements();
    this.bindEvents();
    this.loadInitialData();
  }

  initElements() {
    // Form elements
    this.form = document.getElementById("evRegistrationForm");
    this.usernameInput = document.getElementById("regUsername");
    this.emailInput = document.getElementById("regEmail");
    this.phoneInput = document.getElementById("regPhone");
    this.modelSelect = document.getElementById("regModelSelect");
    this.customModelGroup = document.getElementById("customModelGroup");
    this.customModelInput = document.getElementById("regCustomModel");
    this.batteryInput = document.getElementById("regBatteryCapacity");
    this.batteryHint = document.getElementById("batteryCapacityHint");
    this.socInput = document.getElementById("regCurrentSoc");
    this.locationSelect = document.getElementById("regLocationSelect");
    this.btnSubmit = document.getElementById("btnRegisterEV");

    // Fleet Table & Search
    this.fleetTableBody = document.getElementById("fleetTableBody");
    this.fleetCountBadge = document.getElementById("fleetCountBadge");
    this.fleetSearchInput = document.getElementById("fleetSearchInput");
    this.btnRefreshFleet = document.getElementById("btnRefreshFleet");
  }

  bindEvents() {
    // Dropdown change for EV Model
    if (this.modelSelect) {
      this.modelSelect.addEventListener("change", () => this.handleModelChange());
    }

    // Submit button
    if (this.btnSubmit) {
      this.btnSubmit.addEventListener("click", (e) => {
        e.preventDefault();
        this.submitRegistration();
      });
    }

    // Fleet search filter
    if (this.fleetSearchInput) {
      this.fleetSearchInput.addEventListener("input", () => this.filterFleetTable());
    }

    // Refresh Fleet button
    if (this.btnRefreshFleet) {
      this.btnRefreshFleet.addEventListener("click", () => {
        this.btnRefreshFleet.textContent = "🔄 Refreshing...";
        this.loadFleet().finally(() => {
          setTimeout(() => {
            if (this.btnRefreshFleet) this.btnRefreshFleet.textContent = "🔄 Refresh";
          }, 400);
          this.toast("Fleet directory refreshed.", "info");
        });
      });
    }

    // Refresh when Tab 2 becomes active
    window.addEventListener("dbos:tabChanged", (e) => {
      if (e.detail.tabId === "tab-registration") {
        this.loadFleet();
      }
    });
  }

  async loadInitialData() {
    await Promise.all([
      this.loadCatalogue(),
      this.loadLocations(),
      this.loadFleet()
    ]);
  }

  async loadCatalogue() {
    const res = await DBOSApi.getEveCatalogue();
    if (res.ok && res.data.success) {
      this.catalogue = res.data.catalogue || [];
      this.renderModelDropdown();
    }
  }

  renderModelDropdown() {
    if (!this.modelSelect) return;
    this.modelSelect.innerHTML = `<option value="" disabled selected>-- Select an EV Model from Catalogue --</option>`;

    this.catalogue.forEach((item) => {
      const opt = document.createElement("option");
      opt.value = item.model;
      opt.textContent = `${item.model} (${item.battery_capacity.toFixed(2)} kWh Battery)`;
      opt.dataset.capacity = item.battery_capacity;
      this.modelSelect.appendChild(opt);
    });

    // Custom vehicle option
    const customOpt = document.createElement("option");
    customOpt.value = "__custom__";
    customOpt.textContent = "+ Custom / Other Vehicle Model...";
    this.modelSelect.appendChild(customOpt);
  }

  handleModelChange() {
    const selectedVal = this.modelSelect.value;

    if (selectedVal === "__custom__") {
      // Show custom model field and enable battery capacity editing
      if (this.customModelGroup) this.customModelGroup.style.display = "flex";
      if (this.customModelInput) {
        this.customModelInput.value = "";
        this.customModelInput.focus();
      }
      this.batteryInput.value = "";
      this.batteryInput.readOnly = false;
      this.batteryHint.textContent = "Enter verified battery capacity in kWh (e.g. 45.0).";
    } else {
      // Find from catalogue
      if (this.customModelGroup) this.customModelGroup.style.display = "none";
      const matched = this.catalogue.find((c) => c.model === selectedVal);
      if (matched) {
        this.batteryInput.value = matched.battery_capacity.toFixed(2);
        this.batteryInput.readOnly = true;
        this.batteryHint.textContent = `Auto-filled from verified manufacturer specs (${matched.battery_capacity.toFixed(2)} kWh).`;
      }
    }
  }

  async loadLocations() {
    const res = await DBOSApi.getLocations();
    if (res.ok && res.data.success) {
      this.locations = res.data.locations || [];
      this.renderLocationDropdown();
    }
  }

  renderLocationDropdown() {
    if (!this.locationSelect) return;
    this.locationSelect.innerHTML = `<option value="" disabled selected>-- Select Station Hub Location --</option>`;

    this.locations.forEach((loc) => {
      const opt = document.createElement("option");
      opt.value = loc.location_id;
      opt.textContent = `[Hub #${loc.location_id}] ${loc.location_name}`;
      this.locationSelect.appendChild(opt);
    });
  }

  async loadFleet() {
    const res = await DBOSApi.getFleet();
    if (res.ok && res.data.success) {
      this.fleet = res.data.fleet || [];
      this.renderFleetTable(this.fleet);
      if (this.fleetCountBadge) {
        this.fleetCountBadge.textContent = `${this.fleet.length} Vehicles`;
      }
    }
  }

  renderFleetTable(fleetList) {
    if (!this.fleetTableBody) return;

    if (fleetList.length === 0) {
      this.fleetTableBody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 24px;">
            No electric vehicles found in the database directory.
          </td>
        </tr>
      `;
      return;
    }

    this.fleetTableBody.innerHTML = fleetList
      .map((ev) => {
        const socVal = parseFloat(ev.current_soc);
        let socBadge = "badge-completed";
        if (socVal <= 20) socBadge = "badge-rejected"; // Emergency low battery
        else if (socVal <= 50) socBadge = "badge-waiting";

        // Vehicle Operational Status
        let statusBadge = `<span class="badge badge-completed" title="Parked & Available to request charging">IDLE (AVAILABLE)</span>`;
        if (ev.active_status === "WAITING") {
          statusBadge = `<span class="badge badge-waiting" title="Process in Ready Queue awaiting scheduler">QUEUED (WAITING)</span>`;
        } else if (ev.active_status === "RUNNING") {
          statusBadge = `<span class="badge badge-running" title="Actively plugged into station charger">CHARGING (ACTIVE)</span>`;
        }

        return `
          <tr>
            <td style="font-weight: 700; color: #60a5fa;">EV #${ev.ev_id}</td>
            <td style="color: #ffffff; font-weight: 500;">${this.escapeHtml(ev.username)}</td>
            <td><strong>${this.escapeHtml(ev.model)}</strong></td>
            <td>${parseFloat(ev.battery_capacity).toFixed(2)} kWh</td>
            <td>
              <span class="badge ${socBadge}">
                ${socVal.toFixed(1)}% SoC
              </span>
            </td>
            <td>${statusBadge}</td>
            <td style="color: var(--text-secondary);">${this.escapeHtml(ev.location_name)}</td>
          </tr>
        `;
      })
      .join("");
  }

  filterFleetTable() {
    const query = (this.fleetSearchInput ? this.fleetSearchInput.value : "").toLowerCase().trim();
    if (!query) {
      this.renderFleetTable(this.fleet);
      return;
    }

    const filtered = this.fleet.filter(
      (ev) =>
        ev.model.toLowerCase().includes(query) ||
        ev.username.toLowerCase().includes(query) ||
        ev.location_name.toLowerCase().includes(query) ||
        String(ev.ev_id).includes(query)
    );
    this.renderFleetTable(filtered);
  }

  async submitRegistration() {
    const username = this.usernameInput.value.trim();
    const email = this.emailInput.value.trim();
    const phone = this.phoneInput.value.trim();

    let model = this.modelSelect.value;
    if (model === "__custom__") {
      model = this.customModelInput ? this.customModelInput.value.trim() : "";
    }

    const battery_capacity = parseFloat(this.batteryInput.value);
    const current_soc = parseFloat(this.socInput.value);
    const location_id = parseInt(this.locationSelect.value, 10);

    // Client-side Validation
    if (!username || !email || !phone) {
      this.toast("Please fill in all user contact details (Username, Email, Phone).", "error");
      return;
    }

    if (!model) {
      this.toast("Please select or enter an EV Model.", "error");
      return;
    }

    if (isNaN(battery_capacity) || battery_capacity < 5 || battery_capacity > 250) {
      this.toast("Battery capacity must be a valid number between 5.0 and 250.0 kWh.", "error");
      return;
    }

    if (isNaN(current_soc) || current_soc < 0 || current_soc > 100) {
      this.toast("Current SoC percentage must be between 0.0% and 100.0%.", "error");
      return;
    }

    if (isNaN(location_id)) {
      this.toast("Please select a Hub Location.", "error");
      return;
    }

    // Disable button during network round-trip
    this.btnSubmit.disabled = true;
    this.btnSubmit.textContent = "Registering in MySQL...";

    const payload = {
      username,
      email,
      phone,
      model,
      battery_capacity,
      current_soc,
      location_id
    };

    const res = await DBOSApi.registerEV(payload);

    this.btnSubmit.disabled = false;
    this.btnSubmit.textContent = "⚡ Register Vehicle & Inject Workload";

    if (res.ok && res.data.success) {
      this.toast(`[SUCCESS] EV '${model}' registered for user '${username}'!`, "success");
      this.resetForm();
      await this.loadFleet();

      // Pre-select newly registered owner & vehicle in Tab 3 Admission
      if (window.admissionController && typeof window.admissionController.selectRegisteredContext === "function") {
        window.admissionController.selectRegisteredContext({
          user_id: res.data.user_id,
          username: res.data.username || username,
          model: res.data.model || model,
          current_soc: res.data.current_soc ?? current_soc
        });
      }

      // Trigger telemetry update for the top banner
      if (window.dbosApp) {
        window.dbosApp.updateTelemetry();
      }
    } else {
      const errMsg = res.data?.error || "Registration failed on server.";
      this.toast(`[ERROR] ${errMsg}`, "error");
    }
  }

  resetForm() {
    this.usernameInput.value = "";
    this.emailInput.value = "";
    this.phoneInput.value = "";
    this.modelSelect.selectedIndex = 0;
    if (this.customModelGroup) this.customModelGroup.style.display = "none";
    if (this.customModelInput) this.customModelInput.value = "";
    this.batteryInput.value = "";
    this.batteryInput.readOnly = false;
    this.batteryHint.textContent = "Select an EV model to auto-populate.";
    this.socInput.value = "";
    this.locationSelect.selectedIndex = 0;
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

