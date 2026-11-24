/**
 * DBOS EV Charging Control Plane - Charging Request Admission Controller (Tab 3)
 * Handles vehicle selection, target SoC calculation, burst time calculation (BT = Energy / Power),
 * reservation grace-period leases, and OS process admission into CHARGING_REQUEST table.
 */

import { DBOSApi } from "./api.js?v=7";

export class AdmissionController {
  constructor() {
    this.catalogue = [];
    this.users = [];
    this.fleet = [];
    this.requests = [];
    this.selectedUser = null;
    this.selectedVehicle = null;
    this.userManuallyPickedModel = false;
    this.activeFilter = "ALL";
    this.lastAdmittedId = null;

    this.initElements();
    this.bindEvents();
    this.loadInitialData();
  }

  initElements() {
    // Form Inputs & Selectors
    this.form = document.getElementById("admitRequestForm");
    this.ownerNameInput = document.getElementById("admitOwnerName");
    this.usersDatalist = document.getElementById("admitUsersDatalist");
    this.vehicleSelect = document.getElementById("admitVehicleSelect");
    this.selectedEvCard = document.getElementById("selectedEvCard");
    this.evModelBadge = document.getElementById("evModelBadge");
    this.evOwnerBadge = document.getElementById("evOwnerBadge");
    this.evCapBadge = document.getElementById("evCapBadge");
    this.evSocBadge = document.getElementById("evSocBadge");
    this.batteryFullAlert = document.getElementById("batteryFullAlert");

    // Current SoC inputs
    this.currentSocInput = document.getElementById("admitCurrentSoc");
    this.currentSocNum = document.getElementById("admitCurrentSocNum");
    this.currentSocValue = document.getElementById("currentSocValue");
    this.currentSocPresetBtns = document.querySelectorAll(".current-soc-preset-btn");

    // Target SoC inputs
    this.targetSocInput = document.getElementById("admitTargetSoc");
    this.targetSocNum = document.getElementById("admitTargetSocNum");
    this.targetSocValue = document.getElementById("targetSocValue");
    this.targetSocHint = document.getElementById("targetSocHint");
    this.socPresetBtns = document.querySelectorAll(".soc-preset-btn");

    this.powerSelect = document.getElementById("admitPowerSelect");
    this.bookingTypeSelect = document.getElementById("admitBookingType");
    this.reservationGroup = document.getElementById("reservationGroup");
    this.slotTimeInput = document.getElementById("admitSlotTime");
    this.btnSubmit = document.getElementById("btnAdmitRequest");

    // Calculation Readouts
    this.calcEnergy = document.getElementById("calcEnergy");
    this.calcBurst = document.getElementById("calcBurst");
    this.calcMinutes = document.getElementById("calcMinutes");

    // Master Requests Table & Search
    this.requestsTableBody = document.getElementById("requestsTableBody");
    this.requestsCountBadge = document.getElementById("requestsCountBadge");
    this.requestsSearchInput = document.getElementById("requestsSearchInput");
    this.btnRefreshRequests = document.getElementById("btnRefreshRequests");

    // Status Filter Badges
    this.badgeCountAll = document.getElementById("badgeCountAll");
    this.badgeCountWaiting = document.getElementById("badgeCountWaiting");
    this.badgeCountCompleted = document.getElementById("badgeCountCompleted");
    this.filterBtnAll = document.getElementById("filterBtnAll");
    this.filterBtnWaiting = document.getElementById("filterBtnWaiting");
    this.filterBtnCompleted = document.getElementById("filterBtnCompleted");
  }

  bindEvents() {
    // Owner / Driver name input (supports direct typing + autocomplete suggestions)
    if (this.ownerNameInput) {
      this.ownerNameInput.addEventListener("input", () => this.handleOwnerNameInput());
      this.ownerNameInput.addEventListener("change", () => this.handleOwnerNameInput());
    }

    // Vehicle selection dropdown
    if (this.vehicleSelect) {
      this.vehicleSelect.addEventListener("change", () => {
        this.userManuallyPickedModel = true;
        this.handleVehicleChange();
      });
    }

    // Current SoC slider
    if (this.currentSocInput) {
      this.currentSocInput.addEventListener("input", () => {
        const val = parseInt(this.currentSocInput.value, 10);
        if (this.currentSocNum) this.currentSocNum.value = val;
        if (this.currentSocValue) this.currentSocValue.textContent = `${val}%`;
        this.syncSocConstraints();
        this.recalculate();
      });
    }

    // Current SoC number input
    if (this.currentSocNum) {
      this.currentSocNum.addEventListener("input", () => {
        let val = parseInt(this.currentSocNum.value, 10);
        if (isNaN(val)) val = 20;
        val = Math.max(1, Math.min(95, val));
        if (this.currentSocInput) this.currentSocInput.value = val;
        if (this.currentSocValue) this.currentSocValue.textContent = `${val}%`;
        this.syncSocConstraints();
        this.recalculate();
      });
    }

    // Current SoC Presets (10%, 20%, 35%)
    if (this.currentSocPresetBtns) {
      this.currentSocPresetBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
          const val = parseInt(btn.dataset.soc, 10);
          if (this.currentSocInput) this.currentSocInput.value = val;
          if (this.currentSocNum) this.currentSocNum.value = val;
          if (this.currentSocValue) this.currentSocValue.textContent = `${val}%`;
          this.syncSocConstraints();
          this.recalculate();
        });
      });
    }

    // Target SoC range slider input
    if (this.targetSocInput) {
      this.targetSocInput.addEventListener("input", () => {
        const val = parseInt(this.targetSocInput.value, 10);
        if (this.targetSocNum) this.targetSocNum.value = val;
        if (this.targetSocValue) this.targetSocValue.textContent = `${val}%`;
        this.recalculate();
      });
    }

    // Target SoC number input
    if (this.targetSocNum) {
      this.targetSocNum.addEventListener("input", () => {
        let val = parseInt(this.targetSocNum.value, 10);
        if (isNaN(val)) val = 80;
        val = Math.max(1, Math.min(100, val));
        if (this.targetSocInput) this.targetSocInput.value = val;
        if (this.targetSocValue) this.targetSocValue.textContent = `${val}%`;
        this.recalculate();
      });
    }

    // Target SoC Preset buttons (80% Standard, 90% Highway, 100% Full)
    if (this.socPresetBtns) {
      this.socPresetBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
          const presetVal = parseInt(btn.dataset.soc, 10);
          const currentSoc = this.currentSocInput ? parseFloat(this.currentSocInput.value) : 20.0;
          if (presetVal <= currentSoc) {
            this.toast(`Preset ${presetVal}% is less than or equal to Current Battery SoC (${currentSoc}%).`, "error");
            return;
          }
          if (this.targetSocInput) this.targetSocInput.value = presetVal;
          if (this.targetSocNum) this.targetSocNum.value = presetVal;
          if (this.targetSocValue) this.targetSocValue.textContent = `${presetVal}%`;
          this.recalculate();
        });
      });
    }

    // Charger Power selection
    if (this.powerSelect) {
      this.powerSelect.addEventListener("change", () => this.recalculate());
    }

    // Booking Type (WALK-IN vs RESERVED)
    if (this.bookingTypeSelect) {
      this.bookingTypeSelect.addEventListener("change", () => this.handleBookingTypeChange());
    }

    // Submit admission request button
    if (this.btnSubmit) {
      this.btnSubmit.addEventListener("click", (e) => {
        e.preventDefault();
        this.submitAdmission();
      });
    }

    // Prevent default form enter-key refresh
    if (this.form) {
      this.form.addEventListener("submit", (e) => {
        e.preventDefault();
        this.submitAdmission();
      });
    }

    // Search filter for requests table
    if (this.requestsSearchInput) {
      this.requestsSearchInput.addEventListener("input", () => this.filterRequestsTable());
    }

    // Refresh button
    if (this.btnRefreshRequests) {
      this.btnRefreshRequests.addEventListener("click", () => {
        this.btnRefreshRequests.textContent = "🔄 Refreshing...";
        this.loadRequests().finally(() => {
          setTimeout(() => {
            if (this.btnRefreshRequests) this.btnRefreshRequests.textContent = "🔄 Refresh";
          }, 400);
          this.toast("Requests refreshed from database.", "info");
        });
      });
    }

    // Status filter buttons (ALL vs WAITING vs COMPLETED)
    document.querySelectorAll(".req-filter-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        this.setActiveFilterButton(btn.dataset.filter || "ALL");
        this.filterRequestsTable();
      });
    });

    // Refresh when Tab 3 becomes active
    window.addEventListener("dbos:tabChanged", (e) => {
      if (e.detail.tabId === "tab-admission") {
        this.loadUsers();
        this.loadCatalogue();
        this.loadFleetData();
        this.loadRequests();
      }
    });
  }

  setActiveFilterButton(filterName) {
    this.activeFilter = filterName;
    document.querySelectorAll(".req-filter-btn").forEach((b) => {
      if (b.dataset.filter === filterName) {
        b.classList.remove("btn-secondary");
        b.classList.add("btn-primary");
      } else {
        b.classList.remove("btn-primary");
        b.classList.add("btn-secondary");
      }
    });
  }

  async loadInitialData() {
    await Promise.all([
      this.loadUsers(),
      this.loadCatalogue(),
      this.loadFleetData(),
      this.loadRequests()
    ]);
  }

  async loadUsers() {
    const res = await DBOSApi.getUsers();
    if (res.ok && res.data.success) {
      this.users = res.data.users || [];
      this.renderUsersDatalist();
    }
  }

  async loadFleetData() {
    const res = await DBOSApi.getFleet();
    if (res.ok && res.data.success) {
      this.fleet = res.data.fleet || [];
    }
  }

  async loadCatalogue() {
    const res = await DBOSApi.getEveCatalogue();
    if (res.ok && res.data.success) {
      this.catalogue = res.data.catalogue || [];
      this.renderVehicleDropdown();
    }
  }

  renderUsersDatalist() {
    if (!this.usersDatalist) return;
    this.usersDatalist.innerHTML = "";
    this.users.forEach((u) => {
      const opt = document.createElement("option");
      opt.value = u.username;
      this.usersDatalist.appendChild(opt);
    });
  }

  renderVehicleDropdown() {
    if (!this.vehicleSelect) return;
    const previousSelectedModel = this.vehicleSelect.value;

    this.vehicleSelect.innerHTML = `<option value="" disabled selected>-- Select an EV Model (with Battery Capacity) --</option>`;

    this.catalogue.forEach((item) => {
      const opt = document.createElement("option");
      opt.value = item.model;
      const cap = parseFloat(item.battery_capacity).toFixed(1);
      opt.textContent = `${item.model} — ${cap} kWh`;
      this.vehicleSelect.appendChild(opt);
    });

    if (previousSelectedModel && this.catalogue.some((c) => c.model === previousSelectedModel)) {
      this.vehicleSelect.value = previousSelectedModel;
      this.handleVehicleChange();
    }
  }

  handleOwnerNameInput() {
    if (!this.ownerNameInput) return;
    const typedName = this.ownerNameInput.value.trim();

    if (!typedName) {
      this.selectedUser = null;
      if (this.evOwnerBadge) this.evOwnerBadge.textContent = "--";
      if (this.selectedEvCard && !this.selectedVehicle) {
        this.selectedEvCard.style.display = "none";
      }
      return;
    }

    const matchedUser = this.users.find(
      (u) => u.username && u.username.trim().toLowerCase() === typedName.toLowerCase()
    );

    if (matchedUser) {
      this.selectedUser = {
        user_id: matchedUser.user_id,
        username: matchedUser.username,
        isNew: false
      };
      if (this.selectedEvCard) this.selectedEvCard.style.display = "block";
      if (this.evOwnerBadge) this.evOwnerBadge.textContent = matchedUser.username;

      // Auto-fill this owner's registered EV model & SoC if the operator has not manually overridden the model
      if (!this.userManuallyPickedModel && this.fleet.length > 0) {
        const ownerEvs = this.fleet.filter((ev) => Number(ev.user_id) === Number(matchedUser.user_id));
        const latestEv = ownerEvs.length > 0 ? ownerEvs[ownerEvs.length - 1] : null;
        if (latestEv) {
          if (this.vehicleSelect) {
            const matchedCat = this.catalogue.find(
              (c) => c.model.toLowerCase() === latestEv.model.toLowerCase()
            );
            if (matchedCat) {
              this.vehicleSelect.value = matchedCat.model;
              this.handleVehicleChange();
            }
          }
          const socVal = Math.max(1, Math.min(95, Math.round(parseFloat(latestEv.current_soc) || 20)));
          if (this.currentSocInput) this.currentSocInput.value = socVal;
          if (this.currentSocNum) this.currentSocNum.value = socVal;
          if (this.currentSocValue) this.currentSocValue.textContent = `${socVal}%`;
          this.syncSocConstraints();
          this.recalculate();
        }
      }
    } else {
      this.selectedUser = { user_id: null, username: typedName, isNew: true };
      if (this.selectedEvCard) this.selectedEvCard.style.display = "block";
      if (this.evOwnerBadge) this.evOwnerBadge.textContent = typedName;
    }
  }

  async selectRegisteredContext({ user_id, username, model, current_soc }) {
    this.userManuallyPickedModel = false;
    await Promise.all([
      this.loadUsers(),
      this.loadCatalogue(),
      this.loadFleetData()
    ]);

    const resolvedName = username || "";
    if (this.ownerNameInput && resolvedName) {
      this.ownerNameInput.value = resolvedName;
      this.selectedUser = {
        user_id: user_id ? Number(user_id) : null,
        username: resolvedName,
        isNew: false
      };
      if (this.selectedEvCard) this.selectedEvCard.style.display = "block";
      if (this.evOwnerBadge) this.evOwnerBadge.textContent = resolvedName;
    }

    if (this.vehicleSelect && model) {
      const matchedCat = this.catalogue.find((c) => c.model.toLowerCase() === model.toLowerCase());
      if (matchedCat) {
        this.vehicleSelect.value = matchedCat.model;
        this.handleVehicleChange();
      }
    }

    if (current_soc !== undefined && current_soc !== null) {
      const socVal = Math.max(1, Math.min(95, Math.round(parseFloat(current_soc) || 20)));
      if (this.currentSocInput) this.currentSocInput.value = socVal;
      if (this.currentSocNum) this.currentSocNum.value = socVal;
      if (this.currentSocValue) this.currentSocValue.textContent = `${socVal}%`;
      this.syncSocConstraints();
      this.recalculate();
    }
  }

  handleVehicleChange() {
    const selectedModel = this.vehicleSelect.value;
    const item = this.catalogue.find((c) => c.model === selectedModel);

    if (!item) {
      this.selectedVehicle = null;
      if (this.selectedEvCard && !this.selectedUser) this.selectedEvCard.style.display = "none";
      return;
    }

    this.selectedVehicle = {
      model: item.model,
      battery_capacity: item.battery_capacity
    };

    // Show Vehicle Telemetry Capsule
    if (this.selectedEvCard) this.selectedEvCard.style.display = "block";
    if (this.evOwnerBadge) {
      const enteredName = this.ownerNameInput ? this.ownerNameInput.value.trim() : "";
      this.evOwnerBadge.textContent =
        enteredName || (this.selectedUser && this.selectedUser.username) || "Enter Driver Name";
    }
    if (this.evModelBadge) this.evModelBadge.textContent = item.model;
    if (this.evCapBadge) this.evCapBadge.textContent = `${parseFloat(item.battery_capacity).toFixed(1)} kWh`;

    this.syncSocConstraints();
    this.recalculate();
  }

  syncSocConstraints() {
    const currentSoc = this.currentSocInput ? parseInt(this.currentSocInput.value, 10) : 20;
    const minTarget = Math.min(100, currentSoc + 1);

    if (this.targetSocInput) {
      this.targetSocInput.min = minTarget;
      if (parseInt(this.targetSocInput.value, 10) <= currentSoc) {
        const newTarget = Math.min(100, Math.max(currentSoc + 10, 80));
        this.targetSocInput.value = newTarget;
        if (this.targetSocNum) this.targetSocNum.value = newTarget;
        if (this.targetSocValue) this.targetSocValue.textContent = `${newTarget}%`;
      }
    }
    if (this.targetSocNum) {
      this.targetSocNum.min = minTarget;
    }
    if (this.targetSocHint) {
      this.targetSocHint.textContent = `Desired charge level (Must be > ${currentSoc}%, Max: 100%)`;
    }
  }

  recalculate() {
    if (!this.selectedVehicle) {
      if (this.calcEnergy) this.calcEnergy.textContent = "0.00 kWh";
      if (this.calcBurst) this.calcBurst.textContent = "0.00 hrs";
      if (this.calcMinutes) this.calcMinutes.textContent = "(0 mins)";
      return;
    }

    const currentSoc = this.currentSocInput ? parseFloat(this.currentSocInput.value) : 20.0;
    const targetSoc = this.targetSocInput ? parseFloat(this.targetSocInput.value) : 80.0;
    const capacity = parseFloat(this.selectedVehicle.battery_capacity);
    const power = this.powerSelect ? parseFloat(this.powerSelect.value) : 50.0;

    if (this.evSocBadge) {
      this.evSocBadge.textContent = `${currentSoc.toFixed(1)}%`;
      this.evSocBadge.className = `badge ${currentSoc <= 20 ? "badge-rejected" : "badge-waiting"}`;
    }

    if (targetSoc <= currentSoc) {
      if (this.batteryFullAlert) this.batteryFullAlert.style.display = "block";
      if (this.btnSubmit) {
        this.btnSubmit.disabled = true;
        this.btnSubmit.title = "Target SoC must be greater than current battery SoC.";
      }
    } else {
      if (this.batteryFullAlert) this.batteryFullAlert.style.display = "none";
      if (this.btnSubmit) {
        this.btnSubmit.disabled = false;
        this.btnSubmit.title = "";
      }
    }

    // Automotive Energy Formula: Energy = Capacity * (Target_SoC - Current_SoC) / 100
    const deltaSoc = Math.max(0, targetSoc - currentSoc);
    const requiredEnergy = capacity * (deltaSoc / 100.0);

    // CPU Process Burst Time Formula: BT = Energy / Power
    const burstTimeHours = power > 0 ? requiredEnergy / power : 0;
    const burstMinutes = Math.round(burstTimeHours * 60);

    if (this.calcEnergy) this.calcEnergy.textContent = `${requiredEnergy.toFixed(2)} kWh`;
    if (this.calcBurst) this.calcBurst.textContent = `${burstTimeHours.toFixed(2)} hrs`;
    if (this.calcMinutes) this.calcMinutes.textContent = `(~${burstMinutes} mins)`;
  }

  handleBookingTypeChange() {
    const isReserved = this.bookingTypeSelect.value === "RESERVED";
    if (this.reservationGroup) {
      this.reservationGroup.style.display = isReserved ? "flex" : "none";
    }

    if (isReserved && this.slotTimeInput && !this.slotTimeInput.value) {
      // Default to current time formatted for datetime-local
      const now = new Date();
      now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
      this.slotTimeInput.value = now.toISOString().slice(0, 16);
    }
  }

  async submitAdmission() {
    const typedName = this.ownerNameInput ? this.ownerNameInput.value.trim() : "";
    if (!typedName) {
      this.toast("Please enter the Driver / Owner name for this charging request.", "error");
      if (this.ownerNameInput) this.ownerNameInput.focus();
      return;
    }

    const matchedUser = this.users.find(
      (u) => u.username && u.username.trim().toLowerCase() === typedName.toLowerCase()
    );
    const user_id = matchedUser ? Number(matchedUser.user_id) : null;
    const username = matchedUser ? matchedUser.username : typedName;

    if (!this.selectedVehicle) {
      this.toast("Please select an EV model from the dropdown.", "error");
      return;
    }

    const currentSoc = this.currentSocInput ? parseFloat(this.currentSocInput.value) : 20.0;
    const targetSoc = this.targetSocInput ? parseFloat(this.targetSocInput.value) : 80.0;

    if (targetSoc <= currentSoc) {
      this.toast(`Target SoC (${targetSoc}%) must be greater than Current Battery SoC (${currentSoc}%).`, "error");
      return;
    }

    const capacity = parseFloat(this.selectedVehicle.battery_capacity);
    const requested_power = parseFloat(this.powerSelect.value);
    const required_energy = parseFloat((capacity * ((targetSoc - currentSoc) / 100.0)).toFixed(2));
    const is_reserved = this.bookingTypeSelect.value === "RESERVED";

    let reserved_slot_time = null;
    if (is_reserved && this.slotTimeInput && this.slotTimeInput.value) {
      // Format as YYYY-MM-DD HH:MM:SS for MySQL DATETIME
      reserved_slot_time = this.slotTimeInput.value.replace("T", " ") + ":00";
    }

    this.btnSubmit.disabled = true;
    this.btnSubmit.textContent = "Admitting Process into Ready Queue...";

    const payload = {
      user_id,
      username,
      model: this.selectedVehicle.model,
      battery_capacity: capacity,
      required_energy,
      requested_power,
      soc_at_request: currentSoc,
      is_reserved,
      reserved_slot_time
    };

    const res = await DBOSApi.admitRequest(payload);

    this.btnSubmit.disabled = false;
    this.btnSubmit.textContent = "📥 Admit Process into OS Ready Queue";

    if (res.ok && res.data.success) {
      const pidStr = res.data.request_id ? `P${res.data.request_id}` : "Process";
      const ownerLabel = res.data.username || username;
      const submittedModel = this.selectedVehicle.model;
      this.lastAdmittedId = res.data.request_id || null;
      this.userManuallyPickedModel = false;
      this.selectedUser = null;
      if (this.ownerNameInput) this.ownerNameInput.value = "";
      if (this.evOwnerBadge) this.evOwnerBadge.textContent = "Enter Driver Name";

      this.toast(
        `[SUCCESS] ${pidStr} (${ownerLabel} — ${submittedModel}) enqueued! Burst Time: ${res.data.burst_time_hours} hrs.`,
        "success"
      );

      // Switch active filter to WAITING so the new request is visible front and center
      this.setActiveFilterButton("WAITING");

      // Reload master requests directory, users, catalogue & fleet cache
      await Promise.all([
        this.loadRequests(),
        this.loadUsers(),
        this.loadCatalogue(),
        this.loadFleetData()
      ]);

      // Refresh top telemetry banner (ready queue counter increments)
      if (window.dbosApp) {
        window.dbosApp.updateTelemetry();
      }

      // Sync Tab 1 Dashboard PCB Queue
      if (window.dashboardController) {
        window.dashboardController.loadDashboardData();
      }

      // Sync Tab 2 Fleet Status (marked as QUEUED)
      if (window.registrationController) {
        window.registrationController.loadFleet();
      }
    } else {
      const errMsg = res.data?.error || res.data?.message || "Failed to admit charging request.";
      this.toast(`[ERROR] ${errMsg}`, "error");
    }
  }

  async loadRequests() {
    const res = await DBOSApi.getRequests();
    if (res.ok && res.data.success) {
      this.requests = res.data.requests || [];
      this.updateFilterBadges();
      this.filterRequestsTable();
    }
  }

  updateFilterBadges() {
    const allCount = this.requests.length;
    const waitingCount = this.requests.filter(
      (r) => r.process_state === "WAITING" || r.process_state === "READY"
    ).length;
    const completedCount = this.requests.filter((r) => r.process_state === "COMPLETED").length;

    if (this.badgeCountAll) this.badgeCountAll.textContent = allCount;
    if (this.badgeCountWaiting) this.badgeCountWaiting.textContent = waitingCount;
    if (this.badgeCountCompleted) this.badgeCountCompleted.textContent = completedCount;
  }

  filterRequestsTable() {
    this.updateFilterBadges();

    const query = (this.requestsSearchInput ? this.requestsSearchInput.value : "").toLowerCase().trim();
    let filtered = [...this.requests];

    if (this.activeFilter === "WAITING") {
      filtered = filtered.filter(
        (r) => r.process_state === "WAITING" || r.process_state === "READY"
      );
    } else if (this.activeFilter === "COMPLETED") {
      filtered = filtered.filter((r) => r.process_state === "COMPLETED");
    }

    if (query) {
      filtered = filtered.filter(
        (r) =>
          String(r.request_id).includes(query) ||
          (r.model && r.model.toLowerCase().includes(query)) ||
          (r.username && r.username.toLowerCase().includes(query)) ||
          (r.process_state && r.process_state.toLowerCase().includes(query))
      );
    }

    // Always sort by request_id DESC so newest admitted requests appear right at the top
    filtered.sort((a, b) => Number(b.request_id) - Number(a.request_id));

    if (this.requestsCountBadge) {
      this.requestsCountBadge.textContent = `Showing ${filtered.length} of ${this.requests.length} Requests`;
    }

    this.renderRequestsTable(filtered);
  }

  renderRequestsTable(requestsList) {
    if (!this.requestsTableBody) return;

    if (requestsList.length === 0) {
      let emptyMsg = "No charging requests found in the database.";
      if (this.activeFilter === "WAITING") {
        emptyMsg = `
          🟡 No active processes currently waiting in queue. All admitted requests have been allocated or completed.<br>
          <span style="color: var(--text-secondary); font-size: 11px;">Use the form above to admit a new EV charging request.</span>
        `;
      } else if (this.activeFilter === "COMPLETED") {
        emptyMsg = `🟢 No completed charging sessions in history yet.`;
      }

      this.requestsTableBody.innerHTML = `
        <tr>
          <td colspan="9" style="text-align: center; color: var(--text-muted); padding: 28px; line-height: 1.6;">
            ${emptyMsg}
          </td>
        </tr>
      `;
      return;
    }

    this.requestsTableBody.innerHTML = requestsList
      .map((r) => {
        const energy = parseFloat(r.required_energy || 0);
        const power = parseFloat(r.requested_power || 0);
        const bt = power > 0 ? (energy / power).toFixed(2) : "0.00";
        const soc = parseFloat(r.soc_at_request || 0).toFixed(1);

        // Process State Badge
        let stateBadge = "badge-waiting";
        if (r.process_state === "RUNNING") stateBadge = "badge-running";
        else if (r.process_state === "READY") stateBadge = "badge-waiting";
        else if (r.process_state === "COMPLETED") stateBadge = "badge-completed";
        else if (r.process_state === "REJECTED") stateBadge = "badge-rejected";

        // Booking Type Badge (Grace Period check)
        const isRes = Boolean(r.is_reserved);
        let bookingHtml = `<span class="badge badge-tier2">WALK-IN</span>`;
        if (isRes) {
          if (r.reservation_active) {
            bookingHtml = `<span class="badge badge-tier1" title="Grace Period Valid">RESERVED (Active)</span>`;
          } else {
            bookingHtml = `<span class="badge badge-rejected" title="15-min Grace Window Expired">EXPIRED (Late)</span>`;
          }
        }

        const isNew = this.lastAdmittedId && Number(r.request_id) === Number(this.lastAdmittedId);
        const rowClass = isNew ? "pulse-row" : "";

        return `
          <tr class="${rowClass}">
            <td style="font-weight: 700; color: #60a5fa;">P${r.request_id}</td>
            <td><strong>${this.escapeHtml(r.model || "Unknown EV")}</strong></td>
            <td style="color: var(--text-secondary);">${this.escapeHtml(r.username || "Anonymous")}</td>
            <td>${energy.toFixed(1)} kWh</td>
            <td>${power.toFixed(1)} kW</td>
            <td>${soc}%</td>
            <td><strong style="color: #a78bfa;">${bt} hrs</strong></td>
            <td>${bookingHtml}</td>
            <td><span class="badge ${stateBadge}">${r.process_state}</span></td>
          </tr>
        `;
      })
      .join("");
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
