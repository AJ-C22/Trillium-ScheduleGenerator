const state = {
  roles: [],
  staff: [],
  lastRequest: null,
  lastResult: null,
};

const $ = (id) => document.getElementById(id);
const slug = (value) => value.trim().replace(/\s+/g, " ").replace(/[^a-zA-Z0-9 _-]/g, "");

const DEMO_VERSION = 2;

function defaultRoles() {
  return [
    { name: "CTU", coverage: 1 },
    { name: "Inpatient", coverage: 3 },
    { name: "Clinic", coverage: 1 },
    { name: "ER", coverage: 2 },
    { name: "Consult", coverage: 1 },
  ];
}

function loadDemo() {
  // Small, always-feasible starter: 12 doctors, 8 weeks, 8 working slots/week.
  state.roles = defaultRoles();
  const allRoles = defaultRoles().map((role) => role.name);
  state.staff = [
    { name: "R Chandi", fte: 1, eligible: allRoles, unavailable: "2", fixed: "1:CTU" },
    { name: "R Sharma", fte: 1, eligible: allRoles, unavailable: "5", fixed: "" },
    { name: "M Holmes", fte: 0.75, eligible: ["CTU", "Inpatient", "Clinic", "Consult"], unavailable: "3", fixed: "" },
    { name: "J Levitz", fte: 0.75, eligible: ["CTU", "Inpatient", "ER", "Consult"], unavailable: "", fixed: "" },
    { name: "N Pirzada", fte: 0.75, eligible: allRoles, unavailable: "8", fixed: "" },
    { name: "S Narang", fte: 0.75, eligible: allRoles, unavailable: "", fixed: "4:Clinic" },
    { name: "M Robinson", fte: 0.75, eligible: ["Inpatient", "Clinic", "ER", "Consult"], unavailable: "1", fixed: "" },
    { name: "B Wang", fte: 0.5, eligible: ["Inpatient", "Clinic", "ER"], unavailable: "6", fixed: "" },
    { name: "S Zarabi", fte: 0.75, eligible: allRoles, unavailable: "", fixed: "" },
    { name: "S Rodic", fte: 0.5, eligible: ["Inpatient", "ER", "Consult"], unavailable: "4", fixed: "" },
    { name: "H Mahmood", fte: 0.5, eligible: ["Inpatient", "Clinic", "ER"], unavailable: "", fixed: "" },
    { name: "Y Gulzar", fte: 0.5, eligible: ["Inpatient", "ER", "Consult"], unavailable: "7", fixed: "" },
  ];
  $("scheduleName").value = "Demo: 8-week sample schedule";
  $("weekCount").value = 8;
  $("timeLimit").value = 30;
  renderAll();
  saveLocal();
}

function renderRoles() {
  const body = $("rolesBody");
  body.innerHTML = "";
  state.roles.forEach((role, index) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td><input value="${escapeHtml(role.name)}" data-role-name="${index}" aria-label="Service name"></td>
      <td><input type="number" min="0" max="100" value="${role.coverage}" data-role-coverage="${index}" aria-label="Required each week"></td>
      <td><button class="icon-button" data-remove-role="${index}" aria-label="Remove service">Remove</button></td>`;
    body.appendChild(row);
  });
  body.querySelectorAll("[data-role-name]").forEach((input) => input.addEventListener("change", (event) => {
    const index = Number(event.target.dataset.roleName);
    const oldName = state.roles[index].name;
    const newName = slug(event.target.value);
    state.roles[index].name = newName;
    state.staff.forEach((member) => {
      member.eligible = member.eligible.map((name) => name === oldName ? newName : name);
    });
    renderStaff();
    saveLocal();
  }));
  body.querySelectorAll("[data-role-coverage]").forEach((input) => input.addEventListener("change", (event) => {
    state.roles[Number(event.target.dataset.roleCoverage)].coverage = Number(event.target.value);
    saveLocal();
  }));
  body.querySelectorAll("[data-remove-role]").forEach((button) => button.addEventListener("click", () => {
    const index = Number(button.dataset.removeRole);
    const removed = state.roles[index].name;
    state.roles.splice(index, 1);
    state.staff.forEach((member) => member.eligible = member.eligible.filter((role) => role !== removed));
    renderAll();
    saveLocal();
  }));
}

function renderStaff() {
  const body = $("staffBody");
  body.innerHTML = "";
  state.staff.forEach((member, index) => {
    const row = document.createElement("tr");
    const options = state.roles.map((role) => `
      <label><input type="checkbox" data-staff-eligible="${index}" value="${escapeHtml(role.name)}"
        ${member.eligible.includes(role.name) ? "checked" : ""}>${escapeHtml(role.name)}</label>`).join("");
    row.innerHTML = `
      <td><input value="${escapeHtml(member.name)}" data-staff-name="${index}" aria-label="Staff name"></td>
      <td><input type="number" min="0" max="2" step="0.05" value="${member.fte}" data-staff-fte="${index}" aria-label="FTE"></td>
      <td><div class="role-options">${options}</div></td>
      <td><input value="${escapeHtml(member.unavailable)}" data-staff-unavailable="${index}" placeholder="1, 4, 8-10" aria-label="Unavailable weeks"></td>
      <td><input value="${escapeHtml(member.fixed)}" data-staff-fixed="${index}" placeholder="3:CTU, 12:Clinic" aria-label="Fixed assignments"></td>
      <td><button class="icon-button" data-remove-staff="${index}" aria-label="Remove staff member">Remove</button></td>`;
    body.appendChild(row);
  });
  ["name", "fte", "unavailable", "fixed"].forEach((field) => {
    body.querySelectorAll(`[data-staff-${field}]`).forEach((input) => input.addEventListener("change", (event) => {
      const index = Number(event.target.dataset[`staff${field[0].toUpperCase()}${field.slice(1)}`]);
      state.staff[index][field] = field === "fte" ? Number(event.target.value) : event.target.value;
      saveLocal();
    }));
  });
  body.querySelectorAll("[data-staff-eligible]").forEach((input) => input.addEventListener("change", (event) => {
    const index = Number(event.target.dataset.staffEligible);
    const role = event.target.value;
    state.staff[index].eligible = event.target.checked
      ? [...new Set([...state.staff[index].eligible, role])]
      : state.staff[index].eligible.filter((item) => item !== role);
    saveLocal();
  }));
  body.querySelectorAll("[data-remove-staff]").forEach((button) => button.addEventListener("click", () => {
    state.staff.splice(Number(button.dataset.removeStaff), 1);
    renderStaff();
    saveLocal();
  }));
}

function renderAll() {
  renderRoles();
  renderStaff();
}

function parseWeekList(text, weekCount) {
  const result = new Set();
  if (!text.trim()) return [];
  text.split(",").map((part) => part.trim()).filter(Boolean).forEach((part) => {
    if (part.includes("-")) {
      const [start, end] = part.split("-").map(Number);
      if (!start || !end || start > end) throw new Error(`Invalid week range: ${part}`);
      for (let week = start; week <= end; week++) result.add(week);
    } else {
      const week = Number(part);
      if (!week) throw new Error(`Invalid week: ${part}`);
      result.add(week);
    }
  });
  [...result].forEach((week) => {
    if (week < 1 || week > weekCount) throw new Error(`Week ${week} is outside 1-${weekCount}`);
  });
  return [...result].sort((a, b) => a - b);
}

function parseFixed(text, weekCount, roleNames) {
  const fixed = {};
  if (!text.trim()) return fixed;
  text.split(",").map((part) => part.trim()).filter(Boolean).forEach((part) => {
    const separator = part.indexOf(":");
    if (separator < 0) throw new Error(`Fixed assignment needs week:service: ${part}`);
    const week = Number(part.slice(0, separator).trim());
    const role = part.slice(separator + 1).trim();
    if (week < 1 || week > weekCount) throw new Error(`Fixed week ${week} is outside 1-${weekCount}`);
    if (!roleNames.includes(role)) throw new Error(`Unknown fixed service: ${role}`);
    fixed[`W${String(week).padStart(2, "0")}`] = role;
  });
  return fixed;
}

function allocateRoleTargets(weekCount) {
  const allocations = Object.fromEntries(state.staff.map((_, index) => [index, {}]));
  state.roles.forEach((role) => {
    const eligible = state.staff.map((member, index) => ({ member, index }))
      .filter(({ member }) => member.eligible.includes(role.name) && member.fte > 0);
    const total = role.coverage * weekCount;
    const weightTotal = eligible.reduce((sum, item) => sum + item.member.fte, 0);
    if (total && !weightTotal) throw new Error(`${role.name} has coverage but no eligible staff`);
    const shares = eligible.map((item) => {
      const raw = total * item.member.fte / weightTotal;
      return { ...item, base: Math.floor(raw), fraction: raw - Math.floor(raw) };
    });
    let remaining = total - shares.reduce((sum, item) => sum + item.base, 0);
    shares.sort((a, b) => b.fraction - a.fraction || a.index - b.index);
    shares.forEach((item) => {
      allocations[item.index][role.name] = item.base + (remaining-- > 0 ? 1 : 0);
    });
    state.staff.forEach((_, index) => {
      if (!(role.name in allocations[index])) allocations[index][role.name] = 0;
    });
  });
  return allocations;
}

function buildRequest() {
  const weekCount = Number($("weekCount").value);
  if (!Number.isInteger(weekCount) || weekCount < 1 || weekCount > 52) throw new Error("Weeks must be between 1 and 52");
  const roleNames = state.roles.map((role) => role.name.trim());
  if (!roleNames.length || roleNames.some((name) => !name)) throw new Error("Every service needs a name");
  if (new Set(roleNames).size !== roleNames.length) throw new Error("Service names must be unique");
  if (!state.staff.length) throw new Error("Add at least one staff member");
  const targets = allocateRoleTargets(weekCount);
  const ids = new Set();

  const staff = state.staff.map((member, index) => {
    const idBase = member.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || `staff-${index + 1}`;
    let id = idBase;
    let suffix = 2;
    while (ids.has(id)) id = `${idBase}-${suffix++}`;
    ids.add(id);
    const workload = {};
    let working = 0;
    roleNames.forEach((role) => {
      const preferred = targets[index][role] || 0;
      working += preferred;
      workload[role] = { min: 0, max: weekCount, preferred, weight: 10 };
    });
    workload.OFF = { min: 0, max: weekCount, preferred: Math.max(0, weekCount - working), weight: 4 };
    return {
      id,
      name: member.name,
      eligible_roles: member.eligible,
      unavailable: parseWeekList(member.unavailable, weekCount).map((week) => `W${String(week).padStart(2, "0")}`),
      fixed_assignments: parseFixed(member.fixed, weekCount, roleNames),
      workload_targets: workload,
    };
  });

  return {
    name: $("scheduleName").value || "Untitled schedule",
    roles: roleNames,
    periods: Array.from({ length: weekCount }, (_, index) => ({
      id: `W${String(index + 1).padStart(2, "0")}`,
      label: `Week ${String(index + 1).padStart(2, "0")}`,
      requirements: Object.fromEntries(state.roles.map((role) => [role.name, Number(role.coverage)])),
    })),
    staff,
    rules: {
      consecutive_assignment_weight: 4,
      consecutive_off_weight: 6,
      long_run_weight: 10,
      time_limit_seconds: Number($("timeLimit").value) || 120,
      random_seed: 1,
    },
  };
}

async function generate() {
  setStatus("working", "Solving", "Checking feasibility and optimizing preferences.");
  $("generateButton").disabled = true;
  try {
    const request = buildRequest();
    const response = await fetch("/api/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    const result = await response.json();
    state.lastRequest = request;
    state.lastResult = result;
    renderResult(result);
    if (result.report.success) {
      setStatus("success", result.report.status, "All hard constraints validated.");
      $("downloadCsvButton").disabled = false;
      $("downloadExcelButton").disabled = false;
      document.querySelector('[data-target="results"]').click();
    } else {
      setStatus("danger", result.report.status || "Not generated", "Review the diagnostics below.");
    }
  } catch (error) {
    setStatus("danger", "Input error", error.message);
    renderDiagnostics([error.message]);
  } finally {
    $("generateButton").disabled = false;
  }
}

function renderResult(result) {
  const report = result.report || {};
  const quality = report.quality || {};
  $("metrics").innerHTML = [
    [report.status || "—", "Solver status"],
    [result.periods?.length || 0, "Weeks"],
    [result.staff?.length || 0, "Staff"],
    [quality.consecutive_same_role_pairs ?? "—", "Repeated-role pairs"],
    [quality.consecutive_off_pairs ?? "—", "Consecutive-off pairs"],
  ].map(([value, label]) => `<div class="metric"><strong>${escapeHtml(String(value))}</strong><span>${label}</span></div>`).join("");
  renderDiagnostics([...(report.diagnostics || []), ...(report.validation_errors || [])]);
  if (!report.success) {
    $("scheduleShell").innerHTML = '<div class="empty-state">No schedule was produced because a hard constraint could not be satisfied.</div>';
    return;
  }
  const header = result.periods.map((period) => `<th>${escapeHtml(period.label)}</th>`).join("");
  const rows = result.staff.map((member) => {
    const cells = result.periods.map((period) => {
      const role = result.assignments[period.id][member.id];
      const display = role === "OFF" ? "X" : role;
      return `<td class="${roleClass(role)}">${escapeHtml(display)}</td>`;
    }).join("");
    return `<tr><td>${escapeHtml(member.name)}</td>${cells}</tr>`;
  }).join("");
  $("scheduleShell").innerHTML = `<table class="schedule-table"><thead><tr><th>Staff member</th>${header}</tr></thead><tbody>${rows}</tbody></table>`;
}

function renderDiagnostics(messages) {
  $("diagnostics").innerHTML = messages.map((message) => `<div class="diagnostic">${escapeHtml(message)}</div>`).join("");
}

function roleClass(role) {
  return `role-${String(role).toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
}

function setStatus(tone, title, detail) {
  $("statusBox").innerHTML = `<span class="status-dot ${tone}"></span><div><strong>${escapeHtml(title)}</strong><small>${escapeHtml(detail)}</small></div>`;
}

function download(name, content, type) {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([content], { type }));
  link.download = name;
  link.click();
  URL.revokeObjectURL(link.href);
}

function downloadCsv() {
  const result = state.lastResult;
  if (!result?.report?.success) return;
  const quote = (value) => `"${String(value).replaceAll('"', '""')}"`;
  const rows = [["Staff member", ...result.periods.map((period) => period.label)]];
  result.staff.forEach((member) => rows.push([
    member.name,
    ...result.periods.map((period) => {
      const role = result.assignments[period.id][member.id];
      return role === "OFF" ? "X" : role;
    }),
  ]));
  download("schedule.csv", rows.map((row) => row.map(quote).join(",")).join("\n"), "text/csv");
}

async function downloadExcel() {
  if (!state.lastResult?.report?.success) return;
  const response = await fetch("/api/export/xlsx", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request: state.lastRequest, assignments: state.lastResult.assignments }),
  });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(await response.blob());
  link.download = "schedule.xlsx";
  link.click();
  URL.revokeObjectURL(link.href);
}

function saveLocal() {
  localStorage.setItem("schedule-studio-config", JSON.stringify({
    demoVersion: DEMO_VERSION,
    roles: state.roles,
    staff: state.staff,
    setup: {
      name: $("scheduleName")?.value,
      weeks: $("weekCount")?.value,
      timeLimit: $("timeLimit")?.value,
    },
  }));
}

function loadConfig(config) {
  state.roles = config.roles || defaultRoles();
  state.staff = config.staff || [];
  if (config.setup) {
    $("scheduleName").value = config.setup.name || "New schedule";
    $("weekCount").value = config.setup.weeks || 8;
    $("timeLimit").value = config.setup.timeLimit || 30;
  }
  renderAll();
  saveLocal();
}

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = value ?? "";
  return element.innerHTML;
}

document.querySelectorAll(".step").forEach((button) => button.addEventListener("click", () => {
  document.querySelectorAll(".step").forEach((item) => item.classList.remove("active"));
  button.classList.add("active");
  $(button.dataset.target).scrollIntoView({ behavior: "smooth", block: "start" });
}));
$("addRoleButton").addEventListener("click", () => {
  state.roles.push({ name: `Service ${state.roles.length + 1}`, coverage: 1 });
  state.staff.forEach((member) => member.eligible.push(state.roles.at(-1).name));
  renderAll();
});
$("addStaffButton").addEventListener("click", () => {
  state.staff.push({ name: `Staff ${state.staff.length + 1}`, fte: 1, eligible: state.roles.map((role) => role.name), unavailable: "", fixed: "" });
  renderStaff();
});
$("loadDemoButton").addEventListener("click", loadDemo);
$("generateButton").addEventListener("click", generate);
$("downloadCsvButton").addEventListener("click", downloadCsv);
$("downloadExcelButton").addEventListener("click", downloadExcel);
$("exportConfigButton").addEventListener("click", () => {
  saveLocal();
  download("schedule-configuration.json", localStorage.getItem("schedule-studio-config"), "application/json");
});
$("importButton").addEventListener("click", () => $("importFile").click());
$("importFile").addEventListener("change", async (event) => {
  try {
    loadConfig(JSON.parse(await event.target.files[0].text()));
  } catch (error) {
    setStatus("danger", "Import failed", error.message);
  }
});
["scheduleName", "weekCount", "timeLimit"].forEach((id) => $(id).addEventListener("change", saveLocal));

const saved = localStorage.getItem("schedule-studio-config");
if (saved) {
  try {
    const config = JSON.parse(saved);
    if (config.demoVersion === DEMO_VERSION) {
      loadConfig(config);
    } else {
      loadDemo();
    }
  } catch {
    loadDemo();
  }
} else {
  loadDemo();
}
