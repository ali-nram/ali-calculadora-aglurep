"use strict";
const $ = id => document.getElementById(id);
const polymers = ["PET", "PE", "PA", "EVOH"];
const state = { rows: [], configuration: null, defaults: null, result: null, snapshot: null, revision: 0 };
const format = value => value == null ? "—" : new Intl.NumberFormat("es-CO", {maximumFractionDigits: 6}).format(Number(value));
const decimalText = value => typeof value === "string" && value.includes(",") && !value.includes(".") ? value.replace(",", ".") : value;
const clone = value => structuredClone(value);
function element(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}
async function api(path, payload) {
  const response = await fetch(path, payload === undefined ? {} : {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)});
  if (!response.ok) {
    const data = await response.json();
    const error = new Error("Revise los datos de entrada.");
    error.details = data.errors;
    throw error;
  }
  return response;
}
function clearErrors() {
  $("errors").hidden = true; $("errors").replaceChildren();
  document.querySelectorAll('[aria-invalid="true"]').forEach(el => el.removeAttribute("aria-invalid"));
}
function fieldLabel(field) {
  const labels = {erp_id:"ID de parte ERP",material:"Material laminado",mass_kg:"Masa (kg)",total_thickness_um:"Espesor total (µm)",record_id:"ID de registro",laminates:"Laminados",snapshot:"Cálculo vigente",request:"Solicitud",configuration:"Configuración técnica",densities:"Densidades",default_thicknesses:"Espesores estándar",targets:"Objetivos",tolerances:"Tolerancias",pet_limit:"Límite máximo PET",thicknesses:"Espesores"};
  return (field || "").split(".").map(part => labels[part] || part).join(" · ");
}
function showError(error) {
  clearErrors();
  const entries = error.details || [{message: "No se pudo conectar con el servidor. Reintenta la operación."}];
  $("errors").hidden = false;
  for (const entry of entries) {
    const prefix = entry.record_id ? "Registro " + entry.record_id + " · " : "";
    $("errors").append(element("div", "", prefix + (entry.field ? fieldLabel(entry.field) + ": " : "") + entry.message));
    document.querySelectorAll("input[data-field]").forEach(input => {
      if (input.dataset.record === entry.record_id && input.dataset.field === entry.field) input.setAttribute("aria-invalid", "true");
    });
    document.querySelectorAll("input[data-config]").forEach(input => {
      if (entry.field && ("configuration." + input.dataset.config).startsWith(entry.field)) input.setAttribute("aria-invalid", "true");
    });
  }
  $("activity").textContent = "Corrige los campos indicados y vuelve a calcular.";
}
function normalizedConfiguration() {
  const result = clone(state.configuration);
  for (const group of ["densities", "default_thicknesses", "targets", "tolerances"]) {
    for (const key of Object.keys(result[group])) result[group][key] = decimalText(result[group][key]);
  }
  result.pet_limit = decimalText(result.pet_limit);
  return result;
}
function inputs() {
  const rows = clone(state.rows);
  for (const row of rows) {
    row.mass_kg = decimalText(row.mass_kg); row.total_thickness_um = decimalText(row.total_thickness_um);
    for (const p of ["PET","PA","EVOH"]) row.thicknesses[p] = decimalText(row.thicknesses[p]);
  }
  return {configuration:normalizedConfiguration(), laminates:rows};
}
function invalidate(message = "Hay cambios pendientes. Recalcula para actualizar los resultados.") {
  state.revision++; state.result = null; state.snapshot = null; clearErrors();
  $("export").disabled = true; $("activity").textContent = message;
  renderResults();

}
// El backend comparte la misma fórmula para la vista previa y el cálculo definitivo.
const peRequests = new Map();
function refreshPE(row) {
  const previous = peRequests.get(row.record_id);
  if (previous) clearTimeout(previous.timer);
  const request = {};
  peRequests.set(row.record_id, request);
  const cell = Array.from(document.querySelectorAll(".pe-value")).find(el => el.dataset.record === row.record_id);
  if (!cell) return;
  cell.textContent = "—"; cell.removeAttribute("title");
  const total = decimalText(row.total_thickness_um);
  const layers = Object.fromEntries(Object.entries(row.thicknesses).map(([p,value]) => [p,decimalText(value)]));
  if (!total.trim() || Object.values(layers).some(value => !value.trim())) return;
  cell.textContent = "…";
  request.timer = setTimeout(async () => {
    try {
      const response = await api("/api/pe-thickness",{total_thickness_um:total,thicknesses:layers});
      const data = await response.json();
      if (peRequests.get(row.record_id) !== request || !cell.isConnected) return;
      cell.textContent = format(data.pe_thickness_um); cell.title = data.pe_thickness_um;
    } catch (error) {
      if (peRequests.get(row.record_id) !== request || !cell.isConnected) return;
      cell.textContent = error.details ? "Revisar espesores" : "Sin conexión";
      cell.title = error.details?.[0]?.message || "No se pudo calcular PE. Edita un espesor para reintentar.";
    }
  }, 150);
}
function renderRows() {
  const tbody = $("laminate-rows"); tbody.replaceChildren();
  for (const row of state.rows) {
    const tr = element("tr"); tr.dataset.record = row.record_id;
    const idCell = element("td"); idCell.append(element("div", "record-id", row.record_id)); tr.append(idCell);
    for (const [key,label] of [["erp_id","ID de parte ERP"],["material","Material laminado"],["total_thickness_um","Espesor total (µm)"],["mass_kg","Masa total (kg)"],["thicknesses.PET","Espesor PET (µm)"],["thicknesses.PA","Espesor PA (µm)"],["thicknesses.EVOH","Espesor EVOH (µm)"]]) {
      const td = element("td"), input = element("input");
      const [group,p] = key.split(".");
      input.value = p ? row[group][p] : row[group];
      input.type = "text"; input.dataset.field = key; input.dataset.record = row.record_id;
      input.setAttribute("aria-label", label + " · " + row.record_id);
      if (["erp_id","material"].includes(key)) input.maxLength = 250;
      else input.inputMode = "decimal";
      input.addEventListener("input", () => {
        if (p) row[group][p] = input.value; else row[group] = input.value;
        invalidate();
        if (group === "total_thickness_um" || group === "thicknesses") refreshPE(row);
      });
      td.append(input); tr.append(td);
    }
    const pe = element("td", "pe-value", "—"); pe.dataset.record = row.record_id; tr.append(pe);
    const actions = element("td"), remove = element("button", "button remove", "Retirar"); remove.type = "button";
    remove.setAttribute("aria-label", "Retirar registro " + row.record_id);
    remove.addEventListener("click", () => { state.rows = state.rows.filter(x => x.record_id !== row.record_id); invalidate(); renderRows(); });
    actions.append(remove); tr.append(actions); tbody.append(tr);
  }
  state.rows.forEach(refreshPE);
  $("empty").hidden = state.rows.length > 0; $("count-badge").textContent = state.rows.length;
  $("active-count").textContent = state.rows.length; $("reset").disabled = state.rows.length === 0;
}
function statusBadge(status) {
  return element("span", "status " + (status === "CUMPLE" ? "pass" : status === "NO CUMPLE" ? "fail" : "neutral"), status);
}
function numericCell(value) {
  const td = element("td", "", format(value));
  if (value !== undefined) td.title = value;
  return td;
}
function renderResults() {
  const result = state.result, summary = $("summary-rows"); summary.replaceChildren();
  const badge = statusBadge(result ? result.validation.status : "SIN RESULTADOS");
  badge.id = "global-status"; badge.setAttribute("role","status"); $("global-status").replaceWith(badge);
  $("active-count").textContent = state.rows.length;
  $("total-mass").textContent = result ? format(result.composition.total_mass_kg) : "—";
  $("total-mass").title = result ? result.composition.total_mass_kg : "";
  $("profile").textContent = result ? result.configuration_profile : (state.configuration && state.defaults && JSON.stringify(state.configuration) !== JSON.stringify(state.defaults) ? "Personalizada" : "Aglurep v1");
  for (const p of polymers) {
    const criterion = result?.validation.criteria.find(c => c.polymer === p);
    const tr = element("tr"), label = element("td"), name = element("span", "polymer", p);
    name.prepend(element("span","polymer-dot " + p)); label.append(name); tr.append(label);
    tr.append(numericCell(result?.composition.masses_kg[p]),numericCell(criterion?.value),numericCell(criterion?.target));
    tr.append(element("td","",criterion ? (p === "PET" ? "≤ " + format(criterion.maximum) : format(criterion.minimum) + " – " + format(criterion.maximum)) : "—"));
    tr.append(numericCell(criterion?.difference));
    const status = element("td");
    status.append(statusBadge(criterion ? criterion.status : "PENDIENTE"));
    if (criterion) {
      status.title = criterion.explanation + " Valor exacto: " + criterion.value + " %";
      if (criterion.status === "NO CUMPLE") status.append(element("div","criterion-explanation",criterion.explanation));
    }
    tr.append(status); summary.append(tr);
  }
  $("result-note").textContent = result ? "Evaluación con valores sin redondear. Presentación: hasta 6 decimales; pasa el cursor sobre una cifra para ver su valor completo. " + (result.configuration_profile === "Personalizada" ? "Se utilizan parámetros personalizados." : "PET: límite máximo inclusivo del 10 %.") : "Sin evaluación vigente. Agrega laminados y recalcula.";
  $("calculation-id").textContent = result ? "Cálculo " + result.calculation_id : "Sin cálculo vigente";
  $("individual-details").hidden = !result;
  const individual = $("individual-results"); individual.replaceChildren();
  if (result) {
    for (const item of result.composition.laminates) {
      const pe = Array.from(document.querySelectorAll(".pe-value")).find(el => el.dataset.record === item.laminate.record_id);
      if (pe) {pe.textContent = format(item.thicknesses.PE); pe.title = item.thicknesses.PE;}
      const card = element("div","individual-card");
      card.append(element("h3","",item.laminate.erp_id + " · " + item.laminate.material),element("p","",item.laminate.record_id));
      const scroll = element("div","table-scroll"), table = element("table"), head = element("tr");
      ["Polímero","Fracción másica","Masa (kg)"].forEach(text => head.append(element("th","",text)));
      const thead = element("thead"); thead.append(head); table.append(thead);
      const body = element("tbody");
      for (const p of polymers) {const tr = element("tr"); tr.append(element("td","",p),numericCell(item.fractions[p]),numericCell(item.masses_kg[p])); body.append(tr);}
      table.append(body); scroll.append(table); card.append(scroll); individual.append(card);
    }
  }
}
function renderConfiguration() {
  const container = $("configuration-fields"); container.replaceChildren();
  const groups = [["densities","Densidades · kg/m³"],["default_thicknesses","Espesores estándar · µm"],["targets","Objetivos · %"],["tolerances","Tolerancias · pp"]];
  for (const [key,title] of groups) {
    const fieldset = element("fieldset"); fieldset.append(element("legend","",title));
    const entries = Object.entries(state.configuration[key]);
    if (key === "tolerances") entries.push(["pet_limit",state.configuration.pet_limit]);
    for (const [p,value] of entries) {
      const label = element("label","config-field",p === "pet_limit" ? "Límite máximo PET (%)" : p);
      const input = element("input"); input.type = "text"; input.inputMode = "decimal"; input.value = value;
      input.dataset.config = p === "pet_limit" ? p : key + "." + p;
      input.setAttribute("aria-label", title + " · " + (p === "pet_limit" ? "Límite máximo PET" : p));
      input.addEventListener("input", () => {
        if (p === "pet_limit") state.configuration.pet_limit = input.value; else state.configuration[key][p] = input.value;
        invalidate();
      });
      label.append(input); fieldset.append(label);
    }
    container.append(fieldset);
  }
}
$("add").addEventListener("click", async () => {
  $("add").disabled = true; clearErrors();
  try {
    const response = await api("/api/laminates",{configuration:normalizedConfiguration()});
    const data = await response.json();
    state.rows.push(data.laminate); invalidate(); renderRows();
    $("laminate-rows").lastElementChild.querySelector("input").focus();
  } catch (error) {showError(error);} finally {$("add").disabled = false;}
});
$("calculate").addEventListener("click", async () => {
  invalidate("Calculando…");
  const revision = state.revision;
  $("calculate").disabled = true;
  try {
    const response = await api("/api/calculate",inputs());
    const data = await response.json();
    if (revision !== state.revision) return;
    state.result = data.result; state.snapshot = data.snapshot;
    renderResults(); $("export").disabled = false; $("activity").textContent = "Composición actualizada.";
  } catch (error) {if (revision === state.revision) showError(error);}
  finally {$("calculate").disabled = false;}
});
$("export").addEventListener("click", async () => {
  if (!state.snapshot) return;
  $("export").disabled = true; clearErrors(); const revision = state.revision;
  try {
    const response = await api("/api/export",{snapshot:state.snapshot,inputs:inputs()});
    const blob = await response.blob();
    if (revision !== state.revision) return;
    const url = URL.createObjectURL(blob), anchor = element("a");
    anchor.href = url; anchor.download = "aglurep-" + state.result.calculation_id + ".csv";
    document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    $("activity").textContent = "CSV exportado con la configuración y resultados vigentes.";
  } catch (error) {if (revision === state.revision) showError(error);}
  finally {$("export").disabled = !state.snapshot;}
});
$("reset").addEventListener("click", () => $("reset-dialog").showModal());
$("cancel-reset").addEventListener("click", () => $("reset-dialog").close());
$("confirm-reset").addEventListener("click", () => {
  state.rows = []; invalidate("Mezcla restablecida."); renderRows(); $("reset-dialog").close();
});
$("default-config").addEventListener("click", () => {
  state.configuration = clone(state.defaults); renderConfiguration(); invalidate("Parámetros iniciales restaurados. Recalcula la mezcla.");
});
async function initialize() {
  renderRows(); renderResults();
  try {
    const response = await api("/api/configuration"), data = await response.json();
    state.defaults = clone(data.configuration); state.configuration = clone(data.configuration);
    renderConfiguration(); $("add").disabled = false; $("calculate").disabled = false; $("default-config").disabled = false;
    $("activity").textContent = "Listo para agregar laminados.";
  } catch (error) {showError(error);}
}
initialize();
